import os
from functools import lru_cache
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

SERVICE_ACCOUNT_PATH = os.environ.get("SERVICE_ACCOUNT_PATH", "")
DEFAULT_DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")

mcp = FastMCP("google-sheets")


def _require_service_account_path() -> str:
    if not SERVICE_ACCOUNT_PATH:
        raise ValueError("SERVICE_ACCOUNT_PATH is not set")
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(f"SERVICE_ACCOUNT_PATH does not exist: {SERVICE_ACCOUNT_PATH}")
    return SERVICE_ACCOUNT_PATH


@lru_cache(maxsize=1)
def _credentials():
    return service_account.Credentials.from_service_account_file(
        _require_service_account_path(),
        scopes=SCOPES,
    )


@lru_cache(maxsize=1)
def _drive_service():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


@lru_cache(maxsize=1)
def _sheets_service():
    return build("sheets", "v4", credentials=_credentials(), cache_discovery=False)


def _escape_drive_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _resolve_folder_id(folder_id: str | None) -> str:
    resolved = (folder_id or DEFAULT_DRIVE_FOLDER_ID).strip()
    if not resolved:
        raise ValueError("No folder ID provided and DRIVE_FOLDER_ID is not set")
    return resolved


def _find_spreadsheets(
    *,
    title: str | None = None,
    title_contains: str | None = None,
    folder_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    query_parts = [
        "mimeType = 'application/vnd.google-apps.spreadsheet'",
        "trashed = false",
    ]

    if title:
        query_parts.append(f"name = '{_escape_drive_query_value(title)}'")
    if title_contains:
        query_parts.append(f"name contains '{_escape_drive_query_value(title_contains)}'")
    if folder_id or DEFAULT_DRIVE_FOLDER_ID:
        query_parts.append(f"'{_resolve_folder_id(folder_id)}' in parents")

    response = _drive_service().files().list(
        q=" and ".join(query_parts),
        pageSize=max(1, min(limit, 100)),
        fields="files(id,name,parents,webViewLink)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    return response.get("files", [])


def _resolve_spreadsheet_id(
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
) -> str:
    if spreadsheet_id:
        return spreadsheet_id
    if not spreadsheet_title:
        raise ValueError("Provide spreadsheet_id or spreadsheet_title")

    matches = _find_spreadsheets(title=spreadsheet_title, folder_id=folder_id, limit=10)
    if not matches:
        raise ValueError(f"Spreadsheet not found: {spreadsheet_title}")
    if len(matches) > 1:
        ids = ", ".join(item["id"] for item in matches)
        raise ValueError(f"Multiple spreadsheets found for '{spreadsheet_title}': {ids}")
    return matches[0]["id"]


def _get_spreadsheet_metadata(spreadsheet_id: str) -> dict[str, Any]:
    return _sheets_service().spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="properties.title,sheets.properties(sheetId,title,index,gridProperties)",
    ).execute()


def _find_sheet_properties(spreadsheet_id: str, sheet_title: str) -> dict[str, Any] | None:
    metadata = _get_spreadsheet_metadata(spreadsheet_id)
    for sheet in metadata.get("sheets", []):
        properties = sheet["properties"]
        if properties["title"] == sheet_title:
            return properties
    return None


@mcp.tool(description="List spreadsheets visible to the service account in the configured Google Drive folder")
def list_spreadsheets(
    title_contains: str | None = None,
    folder_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    files = _find_spreadsheets(title_contains=title_contains, folder_id=folder_id, limit=limit)
    return {
        "count": len(files),
        "spreadsheets": files,
    }


@mcp.tool(description="List sheet tab names for a spreadsheet by ID or exact title")
def list_sheet_tabs(
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    metadata = _get_spreadsheet_metadata(resolved_id)
    return {
        "spreadsheet_id": resolved_id,
        "spreadsheet_title": metadata["properties"]["title"],
        "sheets": [sheet["properties"] for sheet in metadata.get("sheets", [])],
    }


@mcp.tool(description="Read values from a sheet range in A1 notation")
def read_sheet_range(
    range_a1: str,
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    result = _sheets_service().spreadsheets().values().get(
        spreadsheetId=resolved_id,
        range=range_a1,
    ).execute()
    return {
        "spreadsheet_id": resolved_id,
        "range": result.get("range", range_a1),
        "majorDimension": result.get("majorDimension", "ROWS"),
        "values": result.get("values", []),
    }


@mcp.tool(description="Create a sheet tab if it does not exist and return its properties")
def ensure_sheet(
    sheet_title: str,
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
    row_count: int = 1000,
    column_count: int = 26,
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    existing = _find_sheet_properties(resolved_id, sheet_title)
    if existing:
        return {
            "spreadsheet_id": resolved_id,
            "created": False,
            "sheet": existing,
        }

    result = _sheets_service().spreadsheets().batchUpdate(
        spreadsheetId=resolved_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_title,
                            "gridProperties": {
                                "rowCount": max(1, row_count),
                                "columnCount": max(1, column_count),
                            },
                        }
                    }
                }
            ]
        },
    ).execute()
    properties = result["replies"][0]["addSheet"]["properties"]
    return {
        "spreadsheet_id": resolved_id,
        "created": True,
        "sheet": properties,
    }


@mcp.tool(description="Clear values in a sheet range")
def clear_sheet(
    range_a1: str,
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    result = _sheets_service().spreadsheets().values().clear(
        spreadsheetId=resolved_id,
        range=range_a1,
        body={},
    ).execute()
    return {
        "spreadsheet_id": resolved_id,
        "clearedRange": result.get("clearedRange", range_a1),
    }


@mcp.tool(description="Write values to a sheet range in A1 notation")
def write_sheet_range(
    range_a1: str,
    values: list[list[Any]],
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    result = _sheets_service().spreadsheets().values().update(
        spreadsheetId=resolved_id,
        range=range_a1,
        valueInputOption=value_input_option,
        body={"values": values},
    ).execute()
    return {
        "spreadsheet_id": resolved_id,
        "updatedRange": result.get("updatedRange"),
        "updatedRows": result.get("updatedRows", 0),
        "updatedColumns": result.get("updatedColumns", 0),
        "updatedCells": result.get("updatedCells", 0),
    }


@mcp.tool(description="Append rows to a sheet range in A1 notation")
def append_sheet_rows(
    range_a1: str,
    values: list[list[Any]],
    spreadsheet_id: str | None = None,
    spreadsheet_title: str | None = None,
    folder_id: str | None = None,
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]:
    resolved_id = _resolve_spreadsheet_id(spreadsheet_id, spreadsheet_title, folder_id)
    result = _sheets_service().spreadsheets().values().append(
        spreadsheetId=resolved_id,
        range=range_a1,
        valueInputOption=value_input_option,
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    updates = result.get("updates", {})
    return {
        "spreadsheet_id": resolved_id,
        "tableRange": result.get("tableRange"),
        "updatedRange": updates.get("updatedRange"),
        "updatedRows": updates.get("updatedRows", 0),
        "updatedColumns": updates.get("updatedColumns", 0),
        "updatedCells": updates.get("updatedCells", 0),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
