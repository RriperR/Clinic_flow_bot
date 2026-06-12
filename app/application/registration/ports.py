from typing import Protocol


class WorkerRegistrationSync(Protocol):
    def upsert_worker_registration(
        self,
        full_name: str,
        chat_id: str | None = None,
        file_id: str | None = None,
    ) -> None: ...
