from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter

from app.application.agent.privacy import SanitizedAgentMessage, ShiftTargetCandidate, ShiftTargetResolver
from app.application.agent.tools import AgentPendingAction, AgentToolContext, ToolRegistry
from app.application.llm.ports import LlmClient, LlmMessage, LlmRole
from app.application.shifts.use_case import ShiftService
from app.logger import setup_logger

logger = setup_logger("agent", "agent.log")


@dataclass(frozen=True)
class AgentRunResult:
    text: str
    sanitized_text: str
    sanitized_user_message: str
    pending_action: AgentPendingAction | None = None
    ambiguous_ref: str | None = None
    candidates: tuple[ShiftTargetCandidate, ...] = ()
    needs_target_clarification: bool = False

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguous_ref is not None and bool(self.candidates)


class AgentService:
    """Агент на ручном цикле tool-use поверх провайдер-агностичного LlmClient.

    Шаг: вызвать модель → если она запросила тулы, исполнить их через реестр
    и вернуть результаты → повторить, пока не получим финальный текст или не
    упрёмся в лимит шагов.
    """

    def __init__(
        self,
        llm: LlmClient,
        tools: ToolRegistry,
        system_prompt: str,
        shift_service: ShiftService | None = None,
        target_resolver: ShiftTargetResolver | None = None,
        max_steps: int = 5,
    ):
        self._llm = llm
        self._tools = tools
        self._system_prompt = system_prompt
        self._shift_service = shift_service
        self._target_resolver = target_resolver or ShiftTargetResolver()
        self._max_steps = max_steps

    async def run(self, user_message: str, history: Sequence[LlmMessage] | None = None) -> str:
        result = await self.run_with_context(None, user_message, history)
        return result.text

    async def run_with_context(
        self,
        chat_id: int | None,
        user_message: str,
        history: Sequence[LlmMessage] | None = None,
        preprocessed: SanitizedAgentMessage | None = None,
    ) -> AgentRunResult:
        started = perf_counter()
        sanitized = preprocessed or await self._sanitize_message(user_message)
        logger.info(
            "agent.run start chat_id=%s sanitized=%r targets=%s ambiguous=%s clarification=%s history=%s",
            chat_id,
            sanitized.text,
            list(sanitized.targets),
            sanitized.is_ambiguous,
            sanitized.needs_target_clarification,
            len(history or []),
        )
        if sanitized.is_ambiguous or sanitized.needs_target_clarification:
            logger.info(
                "agent.run needs_resolution chat_id=%s elapsed_ms=%d",
                chat_id,
                int((perf_counter() - started) * 1000),
            )
            return AgentRunResult(
                text=self._format_resolution_problem(sanitized),
                sanitized_text=self._format_resolution_problem(sanitized, sanitized_output=True),
                sanitized_user_message=sanitized.text,
                ambiguous_ref=sanitized.ambiguous_ref,
                candidates=sanitized.candidates,
                needs_target_clarification=sanitized.needs_target_clarification,
            )

        labels = {target.ref: target.label for target in sanitized.targets.values()}
        context = AgentToolContext(
            chat_id=chat_id,
            targets={target.ref: target.worker_id for target in sanitized.targets.values()},
            labels=labels,
        )
        result = await self._run_sanitized(sanitized.text, history, context)
        logger.info(
            "agent.run done chat_id=%s elapsed_ms=%d pending=%s answer_chars=%d",
            chat_id,
            int((perf_counter() - started) * 1000),
            result.pending_action.kind if result.pending_action else None,
            len(result.sanitized_text),
        )
        return result

    async def _run_sanitized(
        self,
        user_message: str,
        history: Sequence[LlmMessage] | None,
        context: AgentToolContext,
    ) -> AgentRunResult:
        messages: list[LlmMessage] = list(history or [])
        messages.append(LlmMessage(role=LlmRole.USER, content=user_message))
        tools = self._tools.specs() or None
        pending_action: AgentPendingAction | None = None

        for step in range(1, self._max_steps + 1):
            logger.info("agent.llm start step=%s messages=%s tools=%s", step, len(messages), bool(tools))
            completion = await self._llm.complete(messages, system=self._system_prompt, tools=tools)
            logger.info(
                "agent.llm done step=%s finish_reason=%s tool_calls=%s text_chars=%d",
                step,
                completion.finish_reason,
                [call.name for call in completion.tool_calls],
                len(completion.text or ""),
            )
            if not completion.tool_calls:
                sanitized_text = completion.text or ""
                return AgentRunResult(
                    text=context.restore_labels(sanitized_text),
                    sanitized_text=sanitized_text,
                    sanitized_user_message=user_message,
                    pending_action=pending_action,
                )

            messages.append(
                LlmMessage(
                    role=LlmRole.ASSISTANT,
                    content=completion.text or "",
                    tool_calls=completion.tool_calls,
                )
            )
            for call in completion.tool_calls:
                logger.info("agent.tool start step=%s name=%s args=%s", step, call.name, call.arguments)
                result = await self._tools.invoke(call.name, call.arguments, context)
                logger.info(
                    "agent.tool done step=%s name=%s result_chars=%d pending=%s",
                    step,
                    call.name,
                    len(result.content),
                    result.pending_action.kind if result.pending_action else None,
                )
                pending_action = result.pending_action or pending_action
                messages.append(LlmMessage(role=LlmRole.TOOL, content=result.content, tool_call_id=call.id))

        # Лимит шагов исчерпан — последний вызов без тулов, чтобы вернуть текст.
        logger.warning("agent.llm max_steps_exhausted steps=%s", self._max_steps)
        final = await self._llm.complete(messages, system=self._system_prompt)
        sanitized_text = final.text or ""
        return AgentRunResult(
            text=context.restore_labels(sanitized_text),
            sanitized_text=sanitized_text,
            sanitized_user_message=user_message,
            pending_action=pending_action,
        )

    async def _sanitize_message(self, user_message: str) -> SanitizedAgentMessage:
        if self._shift_service is None:
            return SanitizedAgentMessage(text=user_message, targets={})
        workers = await self._shift_service.list_all_doctors()
        return self._target_resolver.sanitize(user_message, workers)

    def _format_resolution_problem(self, sanitized: SanitizedAgentMessage, sanitized_output: bool = False) -> str:
        if sanitized.is_ambiguous:
            return "Нашёл несколько похожих вариантов. Выберите нужный."
        if sanitized.needs_target_clarification:
            return "Не понял, к кому именно относится смена. Напишите фамилию, ФИО или название точнее."
        return "" if sanitized_output else "Не удалось обработать запрос."
