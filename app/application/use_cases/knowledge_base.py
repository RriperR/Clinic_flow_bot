from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities import KnowledgeItem, KnowledgeManipulation, KnowledgeSection
from app.domain.repositories import KnowledgeBaseRepository
from app.infrastructure.sheets.gateway import SheetsGateway

KnowledgeCache = list[tuple[KnowledgeSection, list[tuple[KnowledgeManipulation, list[KnowledgeItem]]]]]


class KnowledgeBaseService:
    SECTION_EMOJIS = {
        "ИНСТРУМЕНТЫ": "🛠",
        "МАТЕРИАЛ": "🧱",
        "ОБОРУДОВАНИЕ": "💻",
        "ДО ПРИЕМА": "🕔",
        "ВО ВРЕМЯ ПРИЕМА": "🕕",
        "ПОСЛЕ ПРИЕМА": "🕗",
    }

    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        sheets_gateway: SheetsGateway,
    ):
        self.repository = repository
        self.sheets_gateway = sheets_gateway

    def is_configured(self) -> bool:
        return bool(self.sheets_gateway.settings.knowledge_table.strip())

    async def sync_from_sheets(self) -> int:
        if not self.is_configured():
            return 0

        sections: KnowledgeCache = []
        for section_position, section_title in enumerate(self.sheets_gateway.list_sheet_titles()):
            rows = self.sheets_gateway.read_sheet_rows(section_title)
            manipulations = self._parse_manipulations(rows)
            if not manipulations:
                continue
            sections.append(
                (
                    KnowledgeSection(
                        id=None,
                        title=section_title,
                        position=section_position,
                    ),
                    manipulations,
                )
            )

        await self.repository.replace_all(sections)
        return sum(len(manipulations) for _, manipulations in sections)

    async def list_sections(self) -> Sequence[KnowledgeSection]:
        return await self.repository.list_sections()

    async def get_section(self, section_id: int) -> KnowledgeSection | None:
        return await self.repository.get_section(section_id)

    async def list_manipulations(self, section_id: int) -> Sequence[KnowledgeManipulation]:
        return await self.repository.list_manipulations(section_id)

    async def get_manipulation(self, manipulation_id: int) -> KnowledgeManipulation | None:
        return await self.repository.get_manipulation(manipulation_id)

    async def build_manipulation_text(self, manipulation_id: int) -> str:
        items = await self.repository.list_items(manipulation_id)
        lines: list[str] = []

        for item in items:
            title = item.title or ""
            item_number = item.item_number or ""
            item_text = item.text or ""
            extra = item.extra or ""

            if title and not item_number and not item_text:
                lines.append(self._format_section_title(title))
                continue

            if item_number and item_text:
                lines.append(self._format_knowledge_item(item_number, item_text, extra))

        return "\n".join(lines) if lines else "Нет информации для выбранной манипуляции."

    def _parse_manipulations(self, rows: list[list[str]]) -> list[tuple[KnowledgeManipulation, list[KnowledgeItem]]]:
        manipulations: list[tuple[KnowledgeManipulation, list[KnowledgeItem]]] = []
        seen: set[str] = set()

        for index, row in enumerate(rows[1:], start=1):
            manipulation_title = self._value(row, 1).strip()
            if not manipulation_title or manipulation_title in seen:
                continue

            seen.add(manipulation_title)
            body_rows = self._collect_section_rows(rows, index + 1)
            items = self._parse_items(body_rows)
            manipulations.append(
                (
                    KnowledgeManipulation(
                        id=None,
                        section_id=0,
                        title=manipulation_title,
                        position=len(manipulations),
                    ),
                    items,
                )
            )

        return manipulations

    def _parse_items(self, rows: list[list[str]]) -> list[KnowledgeItem]:
        items: list[KnowledgeItem] = []
        for row in rows:
            title = self._value(row, 2).strip() or None
            item_number = self._value(row, 3).strip() or None
            item_text = self._value(row, 4).strip() or None
            extra = self._value(row, 5).strip() or None

            if not any((title, item_number, item_text, extra)):
                continue

            items.append(
                KnowledgeItem(
                    id=None,
                    manipulation_id=0,
                    title=title,
                    item_number=item_number,
                    text=item_text,
                    extra=extra,
                    position=len(items),
                )
            )
        return items

    def _collect_section_rows(self, rows: list[list[str]], start_index: int) -> list[list[str]]:
        result: list[list[str]] = []
        for row in rows[start_index:]:
            if self._value(row, 1):
                break
            result.append(row)
        return result

    @staticmethod
    def _format_knowledge_item(item_number: str, item_text: str, extra: str) -> str:
        line = f"{item_number.strip()}. {item_text.strip()}"
        extra_text = extra.strip()
        if not extra_text:
            return line
        if extra_text.upper() == "ВАЖНО!!!":
            return f"{line} ❗❗❗"
        return f"{line} — {extra_text}"

    @classmethod
    def format_section_label(cls, section: str) -> str:
        normalized = section.strip()
        emoji = cls.SECTION_EMOJIS.get(normalized.upper())
        if not emoji:
            return normalized
        return f"{emoji}{normalized}"

    @classmethod
    def _format_section_title(cls, title: str) -> str:
        return cls.format_section_label(title)

    @staticmethod
    def _value(row: list[str], index: int) -> str:
        if index < len(row):
            return row[index] or ""
        return ""
