from __future__ import annotations

from app.infrastructure.sheets.gateway import SheetsGateway


class KnowledgeBaseService:
    SECTION_EMOJIS = {
        "ИНСТРУМЕНТЫ": "🛠",
        "МАТЕРИАЛ": "🧱",
        "ОБОРУДОВАНИЕ": "💻",
        "ДО ПРИЕМА": "🕔",
        "ВО ВРЕМЯ ПРИЕМА": "🕕",
        "ПОСЛЕ ПРИЕМА": "🕗",
    }

    def __init__(self, sheets_gateway: SheetsGateway):
        self.sheets_gateway = sheets_gateway

    def is_configured(self) -> bool:
        return bool(self.sheets_gateway.settings.knowledge_table.strip())

    def list_sections(self) -> list[str]:
        return self.sheets_gateway.list_sheet_titles()

    def list_manipulations(self, section: str) -> list[str]:
        if section not in self.list_sections():
            return []

        rows = self.sheets_gateway.read_sheet_rows(section)
        manipulations: list[str] = []

        for row in rows[1:]:
            manipulation = self._value(row, 1)
            if manipulation:
                normalized = manipulation.strip()
                if normalized and normalized not in manipulations:
                    manipulations.append(normalized)

        return manipulations

    def build_manipulation_text(self, section: str, manipulation: str) -> str:
        if section not in self.list_sections():
            return "Раздел не найден."

        rows = self.sheets_gateway.read_sheet_rows(section)
        start_index = self._find_manipulation_start(rows, manipulation)
        if start_index is None:
            return "Манипуляция не найдена."

        body_rows = self._collect_section_rows(rows, start_index)
        lines: list[str] = []

        for row in body_rows:
            title = self._value(row, 2)
            item_number = self._value(row, 3)
            item_text = self._value(row, 4)
            extra = self._value(row, 5)

            if title and not item_number and not item_text:
                lines.append(self._format_section_title(title))
                continue

            if item_number and item_text:
                lines.append(self._format_knowledge_item(item_number, item_text, extra))

        return "\n".join(lines) if lines else "Нет информации для выбранной манипуляции."

    def _find_manipulation_start(self, rows: list[list[str]], manipulation: str) -> int | None:
        for index, row in enumerate(rows[1:], start=1):
            if self._value(row, 1).strip() == manipulation.strip():
                return index + 1
        return None

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
