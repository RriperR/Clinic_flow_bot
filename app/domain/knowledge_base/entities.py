from dataclasses import dataclass


@dataclass
class KnowledgeSection:
    id: int | None
    title: str
    position: int
    is_active: bool = True


@dataclass
class KnowledgeManipulation:
    id: int | None
    section_id: int
    title: str
    position: int
    is_active: bool = True


@dataclass
class KnowledgeItem:
    id: int | None
    manipulation_id: int
    title: str | None
    item_number: str | None
    text: str | None
    extra: str | None
    position: int
