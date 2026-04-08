#!/usr/bin/env python3
"""
Upload a local org-chart workbook into the correct Google Drive company folder
as a native Google Sheet, then optionally open it in the browser.

Resolution order for the target folder:
1. Explicit `--folder-id`
2. Exact folder-name match
3. Parent folder of the most recently modified "[Company] ... Deal Notes" doc,
   but only when that parent folder also looks company-specific
4. Folder-name contains company
5. Last-resort fallback to the deal-notes parent even if the folder name is generic
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


DEFAULT_TOKEN_PATH = Path.home() / ".config" / "openclaw" / "google" / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True, help="Company name, e.g. Neo4j")
    parser.add_argument("--xlsx", required=True, help="Absolute path to the local .xlsx workbook")
    parser.add_argument(
        "--sheet-title",
        help="Final Google Sheet title. Defaults to '<Company> Org Chart'.",
    )
    parser.add_argument(
        "--folder-id",
        help="Drive folder id override. If omitted, resolve from Drive automatically.",
    )
    parser.add_argument(
        "--token-path",
        default=str(DEFAULT_TOKEN_PATH),
        help=f"OAuth token path. Defaults to {DEFAULT_TOKEN_PATH}",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the resulting Google Sheet URL in the default browser.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the target folder and print metadata without uploading.",
    )
    return parser.parse_args()


def load_drive_service(token_path: Path):
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def list_files(service: Any, query: str, fields: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields=f"nextPageToken, files({fields})",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def get_file_metadata(service: Any, file_id: str) -> dict[str, Any]:
    return (
        service.files()
        .get(
            fileId=file_id,
            fields="id,name,webViewLink,parents,mimeType,modifiedTime",
            supportsAllDrives=True,
        )
        .execute()
    )


def pick_most_recent(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not files:
        return None
    return sorted(files, key=lambda f: f.get("modifiedTime", ""), reverse=True)[0]


def resolve_company_folder(service: Any, company: str) -> dict[str, Any]:
    company_q = escape_query_value(company)
    company_norm = company.casefold()

    exact_folders = list_files(
        service,
        (
            "mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false "
            f"and name = '{company_q}'"
        ),
        "id,name,webViewLink,modifiedTime",
    )
    picked_folder = pick_most_recent(exact_folders)
    if picked_folder:
        picked_folder["resolution"] = {"strategy": "exact_folder_name"}
        return picked_folder

    deal_notes = list_files(
        service,
        (
            "mimeType = 'application/vnd.google-apps.document' "
            "and trashed = false "
            f"and name contains '{company_q}' "
            "and name contains 'Deal Notes'"
        ),
        "id,name,parents,modifiedTime,webViewLink",
    )
    deal_notes = [doc for doc in deal_notes if doc.get("parents")]
    picked_doc = pick_most_recent(deal_notes)
    if picked_doc:
        folder = get_file_metadata(service, picked_doc["parents"][0])
        if company_norm in folder.get("name", "").casefold():
            folder["resolution"] = {
                "strategy": "deal_notes_parent",
                "source_doc_id": picked_doc["id"],
                "source_doc_name": picked_doc["name"],
                "source_doc_url": picked_doc.get("webViewLink"),
            }
            return folder

    fuzzy_folders = list_files(
        service,
        (
            "mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false "
            f"and name contains '{company_q}'"
        ),
        "id,name,webViewLink,modifiedTime",
    )
    picked_folder = pick_most_recent(fuzzy_folders)
    if picked_folder:
        picked_folder["resolution"] = {"strategy": "contains_folder_name"}
        return picked_folder

    if picked_doc:
        folder = get_file_metadata(service, picked_doc["parents"][0])
        folder["resolution"] = {
            "strategy": "deal_notes_parent_fallback",
            "source_doc_id": picked_doc["id"],
            "source_doc_name": picked_doc["name"],
            "source_doc_url": picked_doc.get("webViewLink"),
        }
        return folder

    raise SystemExit(f"Could not resolve a Drive folder for company '{company}'.")


def upload_sheet(
    service: Any,
    xlsx_path: Path,
    folder_id: str,
    sheet_title: str,
) -> dict[str, Any]:
    metadata = {
        "name": sheet_title,
        "mimeType": GSHEET_MIME,
        "parents": [folder_id],
    }
    media = MediaFileUpload(str(xlsx_path), mimetype=XLSX_MIME, resumable=False)
    return (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink,parents,mimeType",
            supportsAllDrives=True,
        )
        .execute()
    )


def maybe_open(url: str) -> None:
    subprocess.run(["open", url], check=True)


def main() -> int:
    args = parse_args()
    xlsx_path = Path(args.xlsx).expanduser().resolve()
    token_path = Path(args.token_path).expanduser().resolve()

    if not xlsx_path.exists():
        raise SystemExit(f"Workbook not found: {xlsx_path}")
    if xlsx_path.suffix.lower() != ".xlsx":
        raise SystemExit(f"Expected an .xlsx workbook, got: {xlsx_path.name}")
    if not token_path.exists():
        raise SystemExit(f"OAuth token not found: {token_path}")

    service = load_drive_service(token_path)
    sheet_title = args.sheet_title or f"{args.company} Org Chart"

    if args.folder_id:
        folder = get_file_metadata(service, args.folder_id)
        folder["resolution"] = {"strategy": "explicit_folder_id"}
    else:
        folder = resolve_company_folder(service, args.company)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "company": args.company,
                    "xlsx": str(xlsx_path),
                    "sheet_title": sheet_title,
                    "folder": folder,
                },
                indent=2,
            )
        )
        return 0

    created = upload_sheet(service, xlsx_path, folder["id"], sheet_title)
    payload = {
        "company": args.company,
        "xlsx": str(xlsx_path),
        "folder": folder,
        "created": created,
    }
    print(json.dumps(payload, indent=2))

    if args.open and created.get("webViewLink"):
        maybe_open(created["webViewLink"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
