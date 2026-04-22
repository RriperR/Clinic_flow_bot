from collections.abc import Iterable
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from app.config import SheetsSettings


class SheetsGateway:
    """Thin wrapper over gspread to isolate IO with Google Sheets."""

    def __init__(self, settings: SheetsSettings):
        self.settings = settings
        self.client = self._build_client(settings.credentials_path)
        self.spreadsheet = self._open_spreadsheet(settings.main_table)
        self.knowledge_spreadsheet = None

    def _build_client(self, credentials_path: Path) -> gspread.Client:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(credentials_path), scope)
        return gspread.authorize(creds)

    # --- Readers ---
    def read_workers(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.workers_sheet)
        return worksheet.get_all_values()[1:]

    def read_pairs(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.pairs_sheet)
        return worksheet.get_all_values()[1:]

    def read_surveys(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.surveys_sheet)
        return worksheet.get_all_values()[1:]

    def read_shifts(self) -> list[list[str]]:
        worksheet = self._require_main_sheet(self.settings.shifts_source_sheet)
        return worksheet.get_all_values()[1:]

    def read_sheet_rows(self, sheet_name: str) -> list[list[str]]:
        worksheet = self._require_knowledge_sheet(sheet_name)
        return worksheet.get_all_values()

    def list_sheet_titles(self) -> list[str]:
        spreadsheet = self._require_knowledge_spreadsheet()
        return [worksheet.title for worksheet in spreadsheet.worksheets()]

    # --- Writers ---
    def upsert_worker_registration(
        self,
        full_name: str,
        chat_id: str | None = None,
        file_id: str | None = None,
    ) -> None:
        worksheet = self._require_main_sheet(self.settings.workers_sheet)
        rows = worksheet.get_all_values()
        target_row = None
        normalized = full_name.strip()

        for idx, row in enumerate(rows[1:], start=2):
            if not row:
                continue
            name = row[0].strip() if len(row) > 0 else ""
            if name == normalized:
                target_row = idx
                break

        if target_row is None:
            worksheet.append_row(
                [
                    normalized,
                    file_id or "",
                    chat_id or "",
                    "",
                    "",
                ],
                value_input_option="RAW",
            )
            return

        if file_id is not None:
            worksheet.update_cell(target_row, 2, file_id)
        if chat_id is not None:
            worksheet.update_cell(target_row, 3, chat_id)

    def export_answers(self, headers: list[str], rows: Iterable[list[str]]) -> None:
        worksheet = self._require_main_sheet(self.settings.answers_sheet)
        worksheet.clear()
        worksheet.append_row(headers)
        if rows:
            worksheet.append_rows(list(rows), value_input_option="RAW")

    def export_shifts(self, headers: list[str], rows: Iterable[list[str]]) -> None:
        worksheet = self._require_main_sheet(self.settings.shift_report_sheet)
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.append_row(headers)
        worksheet.format(
            "D:D",
            {
                "numberFormat": {
                    "type": "DATE",
                    "pattern": "dd.MM.yyyy",
                }
            },
        )
        if rows:
            worksheet.append_rows(list(rows), value_input_option="USER_ENTERED")

    # --- Helpers ---
    def _open_spreadsheet(self, spreadsheet_ref: str):
        if not spreadsheet_ref:
            return None

        # Prefer opening by key if an ID or URL is provided, otherwise fall back to title.
        if "/d/" in spreadsheet_ref:
            spreadsheet_ref = spreadsheet_ref.split("/d/", 1)[1].split("/", 1)[0]

        try:
            return self.client.open_by_key(spreadsheet_ref)
        except gspread.SpreadsheetNotFound:
            try:
                return self.client.open(spreadsheet_ref)
            except gspread.SpreadsheetNotFound:
                raise

    def _require_main_sheet(self, name: str):
        if not self.spreadsheet:
            raise RuntimeError("Main spreadsheet is not configured (TABLE env missing)")
        return self.spreadsheet.worksheet(name)

    def _require_knowledge_sheet(self, name: str):
        return self._require_knowledge_spreadsheet().worksheet(name)

    def _require_knowledge_spreadsheet(self):
        if not self.settings.knowledge_table:
            raise RuntimeError("Knowledge spreadsheet is not configured (KNOWLEDGE_TABLE env missing)")
        if not self.knowledge_spreadsheet:
            self.knowledge_spreadsheet = self._open_spreadsheet(self.settings.knowledge_table)
        return self.knowledge_spreadsheet
