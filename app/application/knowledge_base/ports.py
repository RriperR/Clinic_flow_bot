from typing import Protocol


class KnowledgeBaseSourceSettings(Protocol):
    knowledge_table: str


class KnowledgeBaseSource(Protocol):
    settings: KnowledgeBaseSourceSettings

    def list_sheet_titles(self) -> list[str]: ...
    def read_sheet_rows(self, sheet_name: str) -> list[list[str]]: ...
