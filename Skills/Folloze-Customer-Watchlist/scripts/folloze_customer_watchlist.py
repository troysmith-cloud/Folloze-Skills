#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from typing import Any


class ScriptError(RuntimeError):
    pass


@dataclass
class AccountRecord:
    account_id: str
    account_name: str
    account_type: str | None
    csm_name: str | None
    contract_start_date: date | None
    contract_renewal_date: date | None
    first_contract_start_date: date | None = None


def run_sf_query(org: str, soql: str) -> list[dict[str, Any]]:
    proc = subprocess.run(
        ["sf", "data", "query", "-o", org, "-q", soql, "--json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ScriptError(proc.stderr.strip() or proc.stdout.strip() or "Salesforce query failed")
    try:
        payload = json.loads(proc.stdout)
        return payload["result"]["records"]
    except Exception as exc:  # noqa: BLE001
        raise ScriptError("Unable to parse Salesforce query response") from exc


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def flatten_record(record: dict[str, Any]) -> AccountRecord:
    assigned_csm = record.get("Assigned_CSM__r") or {}
    return AccountRecord(
        account_id=record.get("Id") or "Unknown Account Id",
        account_name=record.get("Name") or "Unknown Account",
        account_type=record.get("Type"),
        csm_name=assigned_csm.get("Name"),
        contract_start_date=parse_date(record.get("Contract_Start_Date__c")),
        contract_renewal_date=parse_date(record.get("Contract_Renewal_Date__c")),
    )


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def fetch_first_contract_start_dates(org: str, account_ids: list[str]) -> dict[str, date]:
    earliest_by_account: dict[str, date] = {}
    if not account_ids:
        return earliest_by_account

    for batch in chunked(account_ids, 150):
        quoted = ",".join(f"'{account_id}'" for account_id in batch)
        soql = f"""
SELECT AccountId, MIN(StartDate) earliestStart
FROM Contract
WHERE AccountId IN ({quoted})
  AND StartDate != NULL
GROUP BY AccountId
"""
        for record in run_sf_query(org, soql):
            account_id = record.get("AccountId")
            earliest = parse_date(record.get("expr0") or record.get("earliestStart"))
            if account_id and earliest:
                earliest_by_account[account_id] = earliest
    return earliest_by_account


def recent_accounts(records: list[AccountRecord], signed_within_days: int, as_of: date) -> list[AccountRecord]:
    matches: list[AccountRecord] = []
    for item in records:
        if not item.contract_start_date:
            continue
        if item.first_contract_start_date and item.contract_start_date != item.first_contract_start_date:
            continue
        days_since_start = (as_of - item.contract_start_date).days
        if 0 <= days_since_start <= signed_within_days:
            matches.append(item)
    return sorted(matches, key=lambda item: item.contract_start_date or date.min, reverse=True)


def renewal_accounts(records: list[AccountRecord], renewal_within_days: int, as_of: date) -> list[AccountRecord]:
    matches: list[AccountRecord] = []
    for item in records:
        if not item.contract_renewal_date:
            continue
        days_to_renewal = (item.contract_renewal_date - as_of).days
        if 0 <= days_to_renewal <= renewal_within_days:
            matches.append(item)
    return sorted(matches, key=lambda item: item.contract_renewal_date or date.max)


def format_recent_line(item: AccountRecord, as_of: date) -> str:
    days_since_start = (as_of - item.contract_start_date).days
    account_type = item.account_type or "Unknown type"
    csm = item.csm_name or "Unassigned"
    return (
        f"- {item.account_name} | start {item.contract_start_date.isoformat()} "
        f"({days_since_start} days ago) | type {account_type} | CSM {csm}"
    )


def format_renewal_line(item: AccountRecord, as_of: date) -> str:
    days_to_renewal = (item.contract_renewal_date - as_of).days
    account_type = item.account_type or "Unknown type"
    csm = item.csm_name or "Unassigned"
    return (
        f"- {item.account_name} | renews {item.contract_renewal_date.isoformat()} "
        f"(in {days_to_renewal} days) | type {account_type} | CSM {csm}"
    )


def build_markdown(records: list[AccountRecord], signed_within_days: int, renewal_within_days: int, as_of: date) -> str:
    recent = recent_accounts(records, signed_within_days, as_of)
    renewals = renewal_accounts(records, renewal_within_days, as_of)
    lines = [
        f"Folloze customer watchlist as of {as_of.isoformat()}",
        "",
        f"Started in last {signed_within_days} days ({len(recent)})",
    ]
    if recent:
        lines.extend(format_recent_line(item, as_of) for item in recent)
    else:
        lines.append("- None")

    lines.extend(["", f"Renewing in next {renewal_within_days} days ({len(renewals)})"])
    if renewals:
        lines.extend(format_renewal_line(item, as_of) for item in renewals)
    else:
        lines.append("- None")
    return "\n".join(lines)


def build_json(records: list[AccountRecord], signed_within_days: int, renewal_within_days: int, as_of: date) -> dict[str, Any]:
    recent = recent_accounts(records, signed_within_days, as_of)
    renewals = renewal_accounts(records, renewal_within_days, as_of)
    return {
        "as_of": as_of.isoformat(),
        "signed_within_days": signed_within_days,
        "renewal_within_days": renewal_within_days,
        "recently_started": [
            {
                "account_id": item.account_id,
                "account_name": item.account_name,
                "type": item.account_type,
                "csm_name": item.csm_name,
                "contract_start_date": item.contract_start_date.isoformat(),
                "days_since_start": (as_of - item.contract_start_date).days,
            }
            for item in recent
            if item.contract_start_date
        ],
        "upcoming_renewals": [
            {
                "account_id": item.account_id,
                "account_name": item.account_name,
                "type": item.account_type,
                "csm_name": item.csm_name,
                "contract_renewal_date": item.contract_renewal_date.isoformat(),
                "days_to_renewal": (item.contract_renewal_date - as_of).days,
            }
            for item in renewals
            if item.contract_renewal_date
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Folloze customer watchlist from Salesforce account fields.")
    parser.add_argument("--org", default="folloze-prod", help="Salesforce org alias")
    parser.add_argument("--signed-within-days", type=int, default=120, help="Days since contract start")
    parser.add_argument("--renewal-within-days", type=int, default=30, help="Days until contract renewal")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="As-of date in YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    as_of = parse_date(args.as_of)
    if as_of is None:
        raise ScriptError("--as-of must be a valid YYYY-MM-DD date")

    soql = """
SELECT Id, Name, Type, Account_Status__c, Contract_Start_Date__c, Contract_Renewal_Date__c,
       Assigned_CSM__r.Name
FROM Account
WHERE Account_Status__c = 'Active'
  AND Type IN ('Agency', 'Customer')
  AND (Contract_Start_Date__c != NULL OR Contract_Renewal_Date__c != NULL)
"""
    records = [flatten_record(record) for record in run_sf_query(args.org, soql)]
    first_contract_start_dates = fetch_first_contract_start_dates(
        args.org, [record.account_id for record in records if record.account_id]
    )
    for record in records:
        record.first_contract_start_date = first_contract_start_dates.get(record.account_id)
    if args.json:
        print(json.dumps(build_json(records, args.signed_within_days, args.renewal_within_days, as_of), indent=2))
    else:
        print(build_markdown(records, args.signed_within_days, args.renewal_within_days, as_of))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScriptError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
