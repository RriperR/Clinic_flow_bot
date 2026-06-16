import json
from datetime import date
from typing import Any

from app.application.agent.tools import AgentPendingAction, AgentToolContext, Tool, ToolExecutionResult
from app.application.llm.ports import ToolSpec
from app.application.shifts.dto import ShiftSignupStatus
from app.application.shifts.use_case import ShiftService
from app.domain.entities import Worker

_TARGET_REF_SCHEMA = {
    "type": "object",
    "properties": {
        "target_ref": {
            "type": "string",
            "description": "Sanitized target reference from the user message, for example [SHIFT_TARGET_1].",
        }
    },
    "required": ["target_ref"],
    "additionalProperties": False,
}

_NO_ARGS: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}


def _readable_shift(shift_type: str) -> str:
    return "Утренняя" if shift_type == "morning" else "Вечерняя"


def _safe_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _require_context(context: AgentToolContext | None) -> AgentToolContext:
    if context is None or context.chat_id is None:
        raise ValueError("agent context is required")
    return context


async def _worker_for_context(shift_service: ShiftService, context: AgentToolContext) -> Worker | None:
    return await shift_service.get_worker(context.chat_id)


def _target_id(arguments: dict[str, Any], context: AgentToolContext) -> tuple[str, int | None]:
    target_ref = str(arguments.get("target_ref") or "")
    return target_ref, context.target_id(target_ref)


async def _current_slot(shift_service: ShiftService) -> tuple[str | None, date]:
    shift_type, shift_date = shift_service.guess_shift_type_from_now()
    return (str(shift_type) if shift_type else None), shift_date


def build_shift_tools(shift_service: ShiftService) -> list[Tool]:
    async def check_shift_availability(
        arguments: dict[str, Any], context: AgentToolContext | None
    ) -> ToolExecutionResult:
        ctx = _require_context(context)
        target_ref, worker_id = _target_id(arguments, ctx)
        shift_type, shift_date = await _current_slot(shift_service)
        if not shift_type:
            return ToolExecutionResult(
                _safe_json({"kind": "shift_availability", "status": "outside_signup_time"})
            )
        if worker_id is None:
            return ToolExecutionResult(_safe_json({"kind": "shift_availability", "status": "target_not_found"}))

        target = await shift_service.get_worker_by_id(worker_id)
        if not target:
            return ToolExecutionResult(_safe_json({"kind": "shift_availability", "status": "target_not_found"}))

        target_ref = ctx.remember_label(target.full_name, prefix="SHIFT_TARGET")
        target_shifts = await shift_service.list_doctor_shifts(shift_date, shift_type, target.full_name)
        if not target_shifts:
            status = "no_schedule_slots"
        elif any(shift.assistant_id is None for shift in target_shifts):
            status = "free_slot_available"
        else:
            status = "all_slots_taken"

        return ToolExecutionResult(
            _safe_json(
                {
                    "kind": "shift_availability",
                    "status": status,
                    "target_ref": target_ref,
                    "date": shift_date.isoformat(),
                    "shift_type": shift_type,
                }
            )
        )

    async def prepare_shift_signup(
        arguments: dict[str, Any], context: AgentToolContext | None
    ) -> ToolExecutionResult:
        ctx = _require_context(context)
        target_ref, worker_id = _target_id(arguments, ctx)
        shift_type, shift_date = await _current_slot(shift_service)
        if not shift_type:
            return ToolExecutionResult(_safe_json({"kind": "shift_signup", "status": "outside_signup_time"}))

        worker = await _worker_for_context(shift_service, ctx)
        if not worker:
            return ToolExecutionResult(_safe_json({"kind": "shift_signup", "status": "worker_not_found"}))
        if worker_id is None:
            return ToolExecutionResult(_safe_json({"kind": "shift_signup", "status": "target_not_found"}))

        target = await shift_service.get_worker_by_id(worker_id)
        if not target:
            return ToolExecutionResult(_safe_json({"kind": "shift_signup", "status": "target_not_found"}))

        target_ref = ctx.remember_label(target.full_name, prefix="SHIFT_TARGET")
        current_shift = await shift_service.get_current_shift(worker.id, shift_date, shift_type)
        if current_shift:
            current_ref = ctx.remember_label(current_shift.doctor_name, prefix="SHIFT_TARGET")
            return ToolExecutionResult(
                _safe_json(
                    {
                        "kind": "shift_signup",
                        "status": ShiftSignupStatus.CURRENT_SHIFT_EXISTS,
                        "current_shift_ref": current_ref,
                        "shift_type": shift_type,
                        "date": shift_date.isoformat(),
                    }
                )
            )

        target_shifts = await shift_service.list_doctor_shifts(shift_date, shift_type, target.full_name)
        if not target_shifts:
            status = "needs_manual_confirmation_no_schedule"
            manual = True
        else:
            free_slot = await shift_service.get_preferred_free_doctor_slot(
                shift_date,
                shift_type,
                target.full_name,
                worker.full_name,
            )
            status = "ready_for_confirmation" if free_slot and free_slot.id is not None else (
                "needs_manual_confirmation_all_slots_taken"
            )
            manual = not (free_slot and free_slot.id is not None)

        return ToolExecutionResult(
            _safe_json(
                {
                    "kind": "shift_signup",
                    "status": status,
                    "target_ref": target_ref,
                    "date": shift_date.isoformat(),
                    "shift_type": shift_type,
                    "requires_user_confirmation": True,
                }
            ),
            pending_action=AgentPendingAction(
                kind="shift_signup",
                target_id=target.id,
                target_ref=target_ref,
                shift_date=shift_date.isoformat(),
                shift_type=shift_type,
                manual=manual,
            ),
        )

    async def get_my_current_shift(
        _arguments: dict[str, Any], context: AgentToolContext | None
    ) -> ToolExecutionResult:
        ctx = _require_context(context)
        shift_type, shift_date = await _current_slot(shift_service)
        if not shift_type:
            return ToolExecutionResult(_safe_json({"kind": "current_shift", "status": "outside_signup_time"}))
        worker = await _worker_for_context(shift_service, ctx)
        if not worker:
            return ToolExecutionResult(_safe_json({"kind": "current_shift", "status": "worker_not_found"}))
        shift = await shift_service.get_current_shift(worker.id, shift_date, shift_type)
        if not shift:
            return ToolExecutionResult(
                _safe_json(
                    {
                        "kind": "current_shift",
                        "status": "not_assigned",
                        "date": shift_date.isoformat(),
                        "shift_type": shift_type,
                    }
                )
            )
        shift_ref = ctx.remember_label(shift.doctor_name, prefix="SHIFT_TARGET")
        return ToolExecutionResult(
            _safe_json(
                {
                    "kind": "current_shift",
                    "status": "assigned",
                    "target_ref": shift_ref,
                    "date": shift_date.isoformat(),
                    "shift_type": shift_type,
                }
            )
        )

    async def prepare_shift_cancel(
        _arguments: dict[str, Any], context: AgentToolContext | None
    ) -> ToolExecutionResult:
        ctx = _require_context(context)
        shift_type, shift_date = await _current_slot(shift_service)
        if not shift_type:
            return ToolExecutionResult(_safe_json({"kind": "shift_cancel", "status": "outside_signup_time"}))
        worker = await _worker_for_context(shift_service, ctx)
        if not worker:
            return ToolExecutionResult(_safe_json({"kind": "shift_cancel", "status": "worker_not_found"}))
        shift = await shift_service.get_current_shift(worker.id, shift_date, shift_type)
        if not shift:
            return ToolExecutionResult(_safe_json({"kind": "shift_cancel", "status": "not_assigned"}))
        shift_ref = ctx.remember_label(shift.doctor_name, prefix="SHIFT_TARGET")
        return ToolExecutionResult(
            _safe_json(
                {
                    "kind": "shift_cancel",
                    "status": "ready_for_confirmation",
                    "target_ref": shift_ref,
                    "date": shift_date.isoformat(),
                    "shift_type": shift_type,
                    "requires_user_confirmation": True,
                }
            ),
            pending_action=AgentPendingAction(
                kind="shift_cancel",
                shift_date=shift_date.isoformat(),
                shift_type=shift_type,
            ),
        )

    return [
        Tool(
            ToolSpec(
                name="check_shift_availability",
                description=(
                    "Check whether a sanitized shift target has free slots in the current shift window. "
                    "Use for questions like whether there is a free slot with [SHIFT_TARGET_1]."
                ),
                parameters=_TARGET_REF_SCHEMA,
            ),
            check_shift_availability,
        ),
        Tool(
            ToolSpec(
                name="prepare_shift_signup",
                description=(
                    "Prepare signup to a sanitized shift target. This does not write data; it only prepares "
                    "a confirmation action for the user."
                ),
                parameters=_TARGET_REF_SCHEMA,
            ),
            prepare_shift_signup,
        ),
        Tool(
            ToolSpec(
                name="get_my_current_shift",
                description="Check whether the current Telegram user already has a shift in the current shift window.",
                parameters=_NO_ARGS,
            ),
            get_my_current_shift,
        ),
        Tool(
            ToolSpec(
                name="prepare_shift_cancel",
                description="Prepare cancellation of the current Telegram user's shift. Requires user confirmation.",
                parameters=_NO_ARGS,
            ),
            prepare_shift_cancel,
        ),
    ]
