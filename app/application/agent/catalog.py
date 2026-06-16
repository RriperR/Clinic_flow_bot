import json
from typing import Any

from app.application.agent.shift_tools import build_shift_tools
from app.application.agent.tools import AgentToolContext, Tool, ToolRegistry
from app.application.knowledge_base.dto import KnowledgeContentItem
from app.application.knowledge_base.use_case import KnowledgeBaseService
from app.application.llm.ports import ToolSpec
from app.application.shifts.use_case import ShiftService

_NO_ARGS: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}


def _format_knowledge_content(items: list[KnowledgeContentItem]) -> str:
    lines: list[str] = []
    for item in items:
        title = (item.title or "").strip()
        number = (item.item_number or "").strip()
        text = (item.text or "").strip()
        extra = (item.extra or "").strip()

        if title and not number and not text:
            lines.append(title)
            continue

        if not number or not text:
            continue

        line = f"{number}. {text}"
        if extra:
            line = f"{line} — {extra}"
        lines.append(line)
    return "\n".join(lines)


def build_tool_registry(knowledge_base: KnowledgeBaseService, shift_service: ShiftService) -> ToolRegistry:
    """Собрать реестр read-only тулов поверх существующих use case.

    Только чтение: изменяющие действия (запись на смену, перенос инструментов)
    намеренно не выставлены — их гейтят отдельные команды бота.
    """

    async def list_knowledge_sections(_arguments: dict[str, Any], _context: AgentToolContext | None) -> str:
        sections = await knowledge_base.list_sections()
        return json.dumps([{"id": s.id, "title": s.title} for s in sections], ensure_ascii=False)

    async def list_section_manipulations(arguments: dict[str, Any], _context: AgentToolContext | None) -> str:
        manipulations = await knowledge_base.list_manipulations(int(arguments["section_id"]))
        return json.dumps([{"id": m.id, "title": m.title} for m in manipulations], ensure_ascii=False)

    async def get_manipulation_content(arguments: dict[str, Any], _context: AgentToolContext | None) -> str:
        content = await knowledge_base.get_manipulation_content(int(arguments["manipulation_id"]))
        return json.dumps(
            {
                "kind": "knowledge_base_content",
                "answer_policy": (
                    "If the user asks for this procedure/list, answer from formatted_text verbatim. "
                    "Preserve headings, line breaks, numbering, item names, notes, and order. "
                    "Do not summarize or merge items unless the user explicitly asks for a summary."
                ),
                "formatted_text": _format_knowledge_content(content.items),
                "items": [
                    {"title": i.title, "number": i.item_number, "text": i.text, "extra": i.extra}
                    for i in content.items
                ],
            },
            ensure_ascii=False,
        )

    async def list_free_shifts_today(_arguments: dict[str, Any], _context: AgentToolContext | None) -> str:
        shift_type, shift_date = shift_service.guess_shift_type_from_now()
        if shift_type is None:
            return "Сейчас не время записи на смену (доступно с 07:30 до 21:00)."
        options = await shift_service.list_free_shifts(shift_date, shift_type)
        return json.dumps(
            {
                "date": shift_date.isoformat(),
                "shift_type": str(shift_type),
                "free_shift_count": len(options),
                "privacy_note": (
                    "Names are hidden from the LLM. Ask the user to open /shift if they need the full list."
                ),
            },
            ensure_ascii=False,
        )

    return ToolRegistry(
        [
            Tool(
                ToolSpec(
                    name="list_knowledge_sections",
                    description="Список разделов базы знаний клиники (id и название). "
                    "Вызови, когда нужно сориентироваться по доступным темам.",
                    parameters=_NO_ARGS,
                ),
                list_knowledge_sections,
            ),
            Tool(
                ToolSpec(
                    name="list_section_manipulations",
                    description="Список манипуляций внутри раздела базы знаний по его id.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "section_id": {"type": "integer", "description": "id из list_knowledge_sections"}
                        },
                        "required": ["section_id"],
                        "additionalProperties": False,
                    },
                ),
                list_section_manipulations,
            ),
            Tool(
                ToolSpec(
                    name="get_manipulation_content",
                    description=(
                        "Содержимое манипуляции по её id из list_section_manipulations. "
                        "Если пользователь спрашивает про процедуру, инструменты, материалы или оборудование, "
                        "используй formatted_text из результата дословно, сохраняя структуру и нумерацию."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {"manipulation_id": {"type": "integer"}},
                        "required": ["manipulation_id"],
                        "additionalProperties": False,
                    },
                ),
                get_manipulation_content,
            ),
            Tool(
                ToolSpec(
                    name="list_free_shifts_today",
                    description=(
                        "Свободные смены на текущий слот (утро/вечер): только количество, без имён сотрудников. "
                        "Для полного списка направь пользователя в /shift."
                    ),
                    parameters=_NO_ARGS,
                ),
                list_free_shifts_today,
            ),
            *build_shift_tools(shift_service),
        ]
    )
