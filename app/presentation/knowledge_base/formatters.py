from app.application.knowledge_base.dto import KnowledgeManipulationContent

SECTION_EMOJIS = {
    "ИНСТРУМЕНТЫ": "🛠",
    "МАТЕРИАЛ": "🧱",
    "ОБОРУДОВАНИЕ": "💻",
    "ДО ПРИЕМА": "🕔",
    "ВО ВРЕМЯ ПРИЕМА": "🕕",
    "ПОСЛЕ ПРИЕМА": "🕗",
}


def format_knowledge_section_label(section: str) -> str:
    normalized = section.strip()
    emoji = SECTION_EMOJIS.get(normalized.upper())
    if not emoji:
        return normalized
    return f"{emoji}{normalized}"


def format_knowledge_manipulation(content: KnowledgeManipulationContent) -> str:
    lines: list[str] = []
    for item in content.items:
        title = item.title or ""
        item_number = item.item_number or ""
        item_text = item.text or ""
        extra = item.extra or ""

        if title and not item_number and not item_text:
            lines.append(format_knowledge_section_label(title))
            continue

        if item_number and item_text:
            lines.append(_format_knowledge_item(item_number, item_text, extra))

    if lines:
        return "\n".join(lines)
    return "Нет информации для выбранной манипуляции."


def _format_knowledge_item(item_number: str, item_text: str, extra: str) -> str:
    line = f"{item_number.strip()}. {item_text.strip()}"
    extra_text = extra.strip()
    if not extra_text:
        return line
    if extra_text.upper() == "ВАЖНО!!!":
        return f"{line} ❗❗❗"
    return f"{line} — {extra_text}"
