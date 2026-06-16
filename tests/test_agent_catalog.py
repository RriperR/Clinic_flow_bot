import json
from datetime import date

from app.application.agent.catalog import build_tool_registry
from app.application.knowledge_base.dto import KnowledgeContentItem, KnowledgeManipulationContent
from app.domain.entities import KnowledgeManipulation, KnowledgeSection


class FakeKnowledgeBase:
    async def list_sections(self):
        return [KnowledgeSection(id=1, title="Протоколы", position=0)]

    async def list_manipulations(self, section_id: int):
        return [KnowledgeManipulation(id=10, section_id=section_id, title="Кариес", position=0)]

    async def get_manipulation_content(self, manipulation_id: int):
        assert manipulation_id == 10
        return KnowledgeManipulationContent(
            items=[
                KnowledgeContentItem(title="📌 КАРИЕС", item_number=None, text=None, extra=None),
                KnowledgeContentItem(title="ИНСТРУМЕНТЫ", item_number=None, text=None, extra=None),
                KnowledgeContentItem(title=None, item_number="1", text="Лоток", extra=None),
                KnowledgeContentItem(title="МАТЕРИАЛЫ", item_number=None, text=None, extra=None),
                KnowledgeContentItem(title=None, item_number="1", text="Перчатки", extra="ВАЖНО!!!"),
            ]
        )


class FakeShiftService:
    def guess_shift_type_from_now(self):
        return "morning", date(2026, 1, 2)

    async def list_free_shifts(self, shift_date, shift_type):
        return []


async def test_knowledge_tool_returns_formatted_text_for_verbatim_answer() -> None:
    registry = build_tool_registry(FakeKnowledgeBase(), FakeShiftService())

    raw_result = await registry.invoke("get_manipulation_content", {"manipulation_id": 10})
    result = json.loads(raw_result.content)

    assert result["kind"] == "knowledge_base_content"
    assert result["formatted_text"] == "📌 КАРИЕС\nИНСТРУМЕНТЫ\n1. Лоток\nМАТЕРИАЛЫ\n1. Перчатки — ВАЖНО!!!"
    assert "verbatim" in result["answer_policy"]
