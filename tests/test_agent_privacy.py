from app.application.agent.privacy import ShiftTargetResolver
from app.domain.entities import Worker


def test_resolver_sanitizes_declined_surname() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize(
        "Есть ли свободный слот у Ивановой?",
        [Worker(id=1, full_name="Иванова Мария Сергеевна")],
    )

    assert result.text == "Есть ли свободный слот у [SHIFT_TARGET_1]?"
    assert result.targets["[SHIFT_TARGET_1]"].worker_id == 1


def test_resolver_handles_sterilization_target() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize(
        "Запиши меня в стерилизационную",
        [Worker(id=7, full_name="Стерилизационная")],
    )

    assert result.text == "Запиши меня в [SHIFT_TARGET_1]"
    assert result.targets["[SHIFT_TARGET_1]"].worker_id == 7


def test_resolver_reports_ambiguous_target() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize(
        "Запиши к Ивановой",
        [
            Worker(id=1, full_name="Иванова Мария Сергеевна"),
            Worker(id=2, full_name="Иванова Анна Петровна"),
        ],
    )

    assert result.is_ambiguous
    assert result.text == "Запиши к [SHIFT_TARGET_1]"
    assert [candidate.worker_id for candidate in result.candidates] == [2, 1]


def test_resolver_blocks_unmasked_shift_target_request() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize("Есть ли свободный слот у Петровой?", [])

    assert result.needs_target_clarification


def test_resolver_sanitizes_multiple_targets() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize(
        "Есть ли слот у Ивановой или Петровой?",
        [
            Worker(id=1, full_name="Иванова Мария Сергеевна"),
            Worker(id=2, full_name="Петрова Анна Игоревна"),
        ],
    )

    assert result.text == "Есть ли слот у [SHIFT_TARGET_1] или [SHIFT_TARGET_2]?"
    assert result.targets["[SHIFT_TARGET_1]"].worker_id == 1
    assert result.targets["[SHIFT_TARGET_2]"].worker_id == 2


def test_resolver_blocks_unmatched_write_request_without_preposition() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize("Запиши Петрову", [])

    assert result.needs_target_clarification


def test_resolver_blocks_unmatched_shift_target_with_extended_preposition() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize("Есть ли свободный слот с Петровой?", [])

    assert result.needs_target_clarification


def test_resolver_allows_shift_status_without_target() -> None:
    resolver = ShiftTargetResolver()

    result = resolver.sanitize("Какая у меня смена?", [])

    assert result.text == "Какая у меня смена?"
    assert not result.needs_target_clarification
