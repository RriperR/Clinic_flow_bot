from dataclasses import dataclass


@dataclass(kw_only=True)
class KnowledgeSection:
    id: int | None = None
    title: str
    position: int
    is_active: bool = True


@dataclass(kw_only=True)
class KnowledgeManipulation:
    id: int | None = None
    section_id: int
    title: str
    position: int
    is_active: bool = True


@dataclass(kw_only=True)
class KnowledgeItem:
    id: int | None = None
    manipulation_id: int
    title: str | None
    item_number: str | None
    text: str | None
    extra: str | None
    position: int
