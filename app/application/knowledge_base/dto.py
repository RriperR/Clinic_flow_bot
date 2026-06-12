from dataclasses import dataclass


@dataclass
class KnowledgeContentItem:
    title: str | None
    item_number: str | None
    text: str | None
    extra: str | None


@dataclass
class KnowledgeManipulationContent:
    items: list[KnowledgeContentItem]
