#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CONFIG_ENV = "SALESFORCE_UPDATE_CONFIG"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "salesforce-update" / "config.json"
RUN_ROOT = Path.home() / ".local" / "share" / "salesforce-update" / "runs"
PIPELINE_STAGE_ORDER = {
    "Meeting Booked": 0,
    "Meeting Booked - Etai": 0,
    "S0": 1,
    "Identify": 2,
    "Discovery": 3,
    "Solution Development": 4,
    "Proposal": 5,
    "Validation": 6,
    "Contract": 7,
}
CANONICAL_STAGE_BY_ORDER = {
    0: "Meeting Booked",
    1: "S0",
    2: "Identify",
    3: "Discovery",
    4: "Solution Development",
    5: "Proposal",
    6: "Validation",
    7: "Contract",
}
SETTABLE_FIELDS = {
    "StageName",
    "Next_step__c",
    "Amount",
    "Summary__c",
    "Competition__c",
    "Next_Call_Date__c",
    "What_s_New_Changed__c",
    "What_s_New_What_s_Changed_Date__c",
}
MERGEABLE_FIELDS = {
    "Summary__c",
    "Redflag_s__c",
    "Metrics__c",
    "Decision_Criteria__c",
    "Decision_Process__c",
    "Implicate_the_Pain__c",
    "Paper_Process__c",
    "What_s_New_Changed__c",
}
CONTACT_LOOKUP_FIELDS = {
    "Champion__c",
    "Customer_Executive_Sponsor__c",
    "Decision_Maker__c",
    "Economic_Buyer__c",
    "Procurement_Contact__c",
    "Signer1__c",
}
DETAIL_WRITE_FIELDS = {
    "StageName",
    "Amount",
    "Summary__c",
    "Customer_Executive_Sponsor__c",
}
MEDDPICC_WRITE_FIELDS = {
    "Next_step__c",
    "Next_Call_Date__c",
    "Competition__c",
    "Redflag_s__c",
    "Metrics__c",
    "Decision_Criteria__c",
    "Decision_Process__c",
    "Implicate_the_Pain__c",
    "Paper_Process__c",
    "What_s_New_Changed__c",
    "What_s_New_What_s_Changed_Date__c",
} | CONTACT_LOOKUP_FIELDS
LEGACY_DISABLED_SET_FIELDS = {
    "NextStep": "Next_step__c",
}


class ScriptError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def json_dump(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, dict):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/", 1)[0]
    value = value.split(":", 1)[0]
    value = value.removeprefix("www.")
    return value or None


def extract_email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].lower()


def parse_sf_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if re.search(r"[+-]\d{4}$", value):
        value = value[:-5] + value[-5:-2] + ":" + value[-2:]
    return datetime.fromisoformat(value)


def parse_sf_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def slug_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    local = re.sub(r"[^a-zA-Z0-9]+", " ", local).strip()
    return local.title() or "Unknown"


def derive_contact_name(item: dict[str, Any]) -> tuple[str | None, str]:
    first_name = clean_string(item.get("first_name"))
    last_name = clean_string(item.get("last_name"))
    if last_name:
        return first_name, last_name
    display = clean_string(item.get("display_name")) or clean_string(item.get("full_name"))
    if display:
        parts = [part for part in display.split() if part]
        if len(parts) == 1:
            return None, parts[0]
        return " ".join(parts[:-1]), parts[-1]
    email = item["email"]
    guessed = slug_from_email(email).split()
    if len(guessed) == 1:
        return None, guessed[0]
    return " ".join(guessed[:-1]), guessed[-1]


def clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_plan_payload(plan: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    normalized = copy.deepcopy(plan)
    warnings: list[str] = []
    updates = normalized.get("updates")
    if not isinstance(updates, list):
        return normalized, warnings

    for idx, update in enumerate(updates):
        set_fields = update.get("set_fields")
        if not isinstance(set_fields, dict):
            continue
        for source_field, target_field in LEGACY_DISABLED_SET_FIELDS.items():
            if source_field not in set_fields:
                continue
            legacy_value = clean_string(set_fields.pop(source_field))
            target_value = clean_string(set_fields.get(target_field))
            if legacy_value and not target_value:
                set_fields[target_field] = legacy_value
                warnings.append(
                    f"updates[{idx}].set_fields.{source_field} was remapped to {target_field} because standard {source_field} writes are disabled"
                )
                continue
            warnings.append(
                f"updates[{idx}].set_fields.{source_field} was ignored because standard {source_field} writes are disabled"
            )

    return normalized, warnings


def load_config() -> tuple[Path, dict[str, Any]]:
    config_path = Path(os.environ.get(CONFIG_ENV, DEFAULT_CONFIG_PATH)).expanduser()
    if not config_path.exists():
        raise ScriptError(f"Missing config file: {config_path}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScriptError(f"Invalid JSON in config file {config_path}: {exc}") from exc
    required = [
        ("salesforce", "org_alias"),
        ("rep", "email"),
        ("rep", "initials"),
        ("notifications", "failure_alert_to"),
    ]
    for section, key in required:
        if not clean_string(config.get(section, {}).get(key)):
            raise ScriptError(f"Missing config value: {section}.{key}")
    config.setdefault("defaults", {})
    config["defaults"].setdefault("lookback_hours", 72)
    config.setdefault("matching", {})
    config["matching"].setdefault("internal_domains", ["folloze.com"])
    config["matching"].setdefault("ignored_domains", [])
    config["matching"].setdefault("ignored_company_keywords", [])
    return config_path, config


def run_sf_json(args: list[str]) -> dict[str, Any]:
    cmd = ["sf", *args, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        raise ScriptError(f"sf command failed: {' '.join(cmd)}\n{stderr or stdout}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ScriptError(f"sf command returned invalid JSON: {' '.join(cmd)}") from exc


@dataclass
class SalesforceSession:
    org_alias: str
    org_id: str
    api_version: str
    access_token: str
    instance_url: str

    @classmethod
    def from_alias(cls, org_alias: str) -> "SalesforceSession":
        payload = run_sf_json(["org", "display", "-o", org_alias, "--verbose"])
        result = payload["result"]
        return cls(
            org_alias=org_alias,
            org_id=result["id"],
            api_version=result["apiVersion"],
            access_token=result["accessToken"],
            instance_url=result["instanceUrl"].rstrip("/"),
        )

    @property
    def api_prefix(self) -> str:
        return f"/services/data/v{self.api_version}"

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.instance_url}{path}"
        data = None
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise ScriptError(f"Salesforce API {method} {path} failed: {exc.code} {raw}") from exc

    def query_all(self, soql: str) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(soql, safe="")
        path = f"{self.api_prefix}/query?q={encoded}"
        records: list[dict[str, Any]] = []
        while path:
            payload = self._request("GET", path)
            records.extend(payload.get("records", []))
            path = payload.get("nextRecordsUrl")
        return records

    def describe_sobject(self, sobject: str) -> dict[str, Any]:
        return self._request("GET", f"{self.api_prefix}/sobjects/{sobject}/describe")

    def create_record(self, sobject: str, fields: dict[str, Any]) -> str:
        payload = self._request("POST", f"{self.api_prefix}/sobjects/{sobject}", body=fields)
        record_id = payload.get("id")
        if not record_id:
            raise ScriptError(f"Create {sobject} did not return an id")
        return record_id

    def update_record(self, sobject: str, record_id: str, fields: dict[str, Any]) -> None:
        self._request("PATCH", f"{self.api_prefix}/sobjects/{sobject}/{record_id}", body=fields)


def field_metadata_map(opportunity_describe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    relevant = SETTABLE_FIELDS | MERGEABLE_FIELDS | CONTACT_LOOKUP_FIELDS | {"Amount"}
    result: dict[str, dict[str, Any]] = {}
    for field in opportunity_describe.get("fields", []):
        name = field["name"]
        if name not in relevant and name != "StageName":
            continue
        result[name] = {
            "label": field["label"],
            "type": field["type"],
            "length": field.get("length"),
            "picklist_values": [entry["value"] for entry in field.get("picklistValues", []) if entry.get("active")],
        }
    return result


def build_open_opportunity_records(session: SalesforceSession, owner_email: str) -> list[dict[str, Any]]:
    soql = f"""
SELECT Id, Name, StageName, LastModifiedDate, CreatedDate, Amount, LeadSource, NextStep, Next_step__c,
       Summary__c, Redflag_s__c, Decision_Criteria__c, Decision_Process__c, Implicate_the_Pain__c,
       Metrics__c, Paper_Process__c, Competition__c, What_s_New_Changed__c, What_s_New_What_s_Changed_Date__c,
       Next_Call_Date__c, AccountId, Account.Name, Account.Website, OwnerId, Owner.Name, Owner.Email,
       Customer_Executive_Sponsor__c, Customer_Executive_Sponsor__r.Name, Customer_Executive_Sponsor__r.Email,
       Champion__c, Champion__r.Name, Champion__r.Email,
       Decision_Maker__c, Decision_Maker__r.Name, Decision_Maker__r.Email,
       Economic_Buyer__c, Economic_Buyer__r.Name, Economic_Buyer__r.Email,
       Procurement_Contact__c, Procurement_Contact__r.Name, Procurement_Contact__r.Email,
       Signer1__c, Signer1__r.Name, Signer1__r.Email
FROM Opportunity
WHERE IsClosed = false AND Owner.Email = '{owner_email}'
ORDER BY LastModifiedDate DESC
""".strip()
    return session.query_all(soql)


def build_recent_closed_won_records(session: SalesforceSession, owner_email: str) -> list[dict[str, Any]]:
    soql = f"""
SELECT Id, Name, AccountId, Account.Name, StageName, LastModifiedDate, CreatedDate
FROM Opportunity
WHERE IsWon = true AND AccountId != null AND Owner.Email = '{owner_email}'
  AND LastModifiedDate = LAST_N_DAYS:30
ORDER BY LastModifiedDate DESC
""".strip()
    return session.query_all(soql)


def build_contact_roles(session: SalesforceSession, owner_email: str) -> list[dict[str, Any]]:
    soql = f"""
SELECT Id, OpportunityId, ContactId, Role, IsPrimary,
       Contact.Name, Contact.Email, Contact.AccountId
FROM OpportunityContactRole
WHERE Opportunity.IsClosed = false AND Opportunity.Owner.Email = '{owner_email}'
ORDER BY OpportunityId, Contact.Name
""".strip()
    return session.query_all(soql)


def decorate_opportunity(record: dict[str, Any], contact_roles: list[dict[str, Any]]) -> dict[str, Any]:
    def lookup(name: str) -> dict[str, Any] | None:
        relation = record.get(f"{name}__r")
        if not relation:
            return None
        return {
            "id": record.get(f"{name}__c"),
            "name": relation.get("Name"),
            "email": relation.get("Email"),
        }

    account = record.get("Account") or {}
    owner = record.get("Owner") or {}
    return {
        "id": record["Id"],
        "name": record["Name"],
        "stage_name": record.get("StageName"),
        "last_modified_at": record.get("LastModifiedDate"),
        "created_at": record.get("CreatedDate"),
        "amount": record.get("Amount"),
        "lead_source": record.get("LeadSource"),
        "next_step": record.get("NextStep"),
        "next_step_c": record.get("Next_step__c"),
        "summary": record.get("Summary__c"),
        "red_flags": record.get("Redflag_s__c"),
        "decision_criteria": record.get("Decision_Criteria__c"),
        "decision_process": record.get("Decision_Process__c"),
        "implicate_the_pain": record.get("Implicate_the_Pain__c"),
        "metrics": record.get("Metrics__c"),
        "paper_process": record.get("Paper_Process__c"),
        "competition": record.get("Competition__c"),
        "whats_new_changed": record.get("What_s_New_Changed__c"),
        "whats_new_changed_date": record.get("What_s_New_What_s_Changed_Date__c"),
        "next_call_date": record.get("Next_Call_Date__c"),
        "account": {
            "id": record.get("AccountId"),
            "name": account.get("Name"),
            "website": account.get("Website"),
            "domain": normalize_domain(account.get("Website")),
        },
        "owner": {
            "id": record.get("OwnerId"),
            "name": owner.get("Name"),
            "email": owner.get("Email"),
        },
        "meddpicc_contacts": {
            "champion": lookup("Champion"),
            "customer_executive_sponsor": lookup("Customer_Executive_Sponsor"),
            "decision_maker": lookup("Decision_Maker"),
            "economic_buyer": lookup("Economic_Buyer"),
            "procurement_contact": lookup("Procurement_Contact"),
            "signer": lookup("Signer1"),
        },
        "contact_roles": contact_roles,
    }


def candidate_suspicion_flags(
    opp: dict[str, Any], recent_closed_won_by_account: dict[str, list[dict[str, Any]]], cutoff_dt: datetime
) -> list[str]:
    flags: list[str] = []
    created_at = parse_sf_datetime(opp.get("created_at"))
    account_id = (opp.get("account") or {}).get("id")
    recent_wins = recent_closed_won_by_account.get(account_id, []) if account_id else []
    name = clean_string(opp.get("name")) or ""
    is_recent = bool(created_at and created_at >= cutoff_dt)
    is_blank = not any(
        [
            clean_string(opp.get("summary")),
            clean_string(opp.get("next_step_c")),
            clean_string(opp.get("whats_new_changed")),
            clean_string(opp.get("lead_source")),
            opp.get("contact_roles"),
        ]
    )

    if is_recent and is_blank and recent_wins:
        flags.append("recent_blank_open_opp_with_same_account_recent_closed_won")
    if is_recent and is_blank and name.lower().startswith("renewal for "):
        flags.append("recent_blank_renewal_opp")
    if is_recent and is_blank and name.lower().startswith("agency (direct)"):
        flags.append("recent_blank_agency_direct_opp")
    return flags


def build_context(
    session: SalesforceSession,
    config: dict[str, Any],
    lookback_hours: int,
    all_open: bool,
) -> dict[str, Any]:
    describe = session.describe_sobject("Opportunity")
    fields = field_metadata_map(describe)
    stage_values = fields["StageName"]["picklist_values"]
    competition_values = fields["Competition__c"]["picklist_values"]
    open_opps = build_open_opportunity_records(session, config["rep"]["email"])
    recent_closed_won = build_recent_closed_won_records(session, config["rep"]["email"])
    role_records = build_contact_roles(session, config["rep"]["email"])
    role_map: dict[str, list[dict[str, Any]]] = {}
    for role in role_records:
        role_map.setdefault(role["OpportunityId"], []).append(
            {
                "id": role["Id"],
                "contact_id": role.get("ContactId"),
                "email": (role.get("Contact") or {}).get("Email"),
                "name": (role.get("Contact") or {}).get("Name"),
                "account_id": (role.get("Contact") or {}).get("AccountId"),
                "role": role.get("Role"),
                "is_primary": role.get("IsPrimary"),
            }
        )

    cutoff_dt = utc_now() - timedelta(hours=lookback_hours)
    recent_closed_won_by_account: dict[str, list[dict[str, Any]]] = {}
    for opp in recent_closed_won:
        account_id = opp.get("AccountId")
        if not account_id:
            continue
        recent_closed_won_by_account.setdefault(account_id, []).append(
            {
                "id": opp["Id"],
                "name": opp.get("Name"),
                "stage_name": opp.get("StageName"),
                "created_at": opp.get("CreatedDate"),
                "last_modified_at": opp.get("LastModifiedDate"),
            }
        )

    all_open_decorated = []
    for record in open_opps:
        opp = decorate_opportunity(record, role_map.get(record["Id"], []))
        opp["suspicion_flags"] = candidate_suspicion_flags(opp, recent_closed_won_by_account, cutoff_dt)
        opp["recent_closed_won_same_account"] = recent_closed_won_by_account.get((opp.get("account") or {}).get("id"), [])
        all_open_decorated.append(opp)

    cutoff_date = cutoff_dt.date()
    if all_open:
        candidates = list(all_open_decorated)
    else:
        candidates = []
        for opp in all_open_decorated:
            modified_at = parse_sf_datetime(opp["last_modified_at"])
            next_call_date = parse_sf_date(opp["next_call_date"])
            if opp.get("suspicion_flags"):
                continue
            if modified_at and modified_at >= cutoff_dt:
                candidates.append(opp)
                continue
            if next_call_date and next_call_date >= cutoff_date:
                candidates.append(opp)

    return {
        "generated_at": utc_now().isoformat(),
        "lookback_hours": lookback_hours,
        "all_open_mode": all_open,
        "rep_email": config["rep"]["email"],
        "org_alias": config["salesforce"]["org_alias"],
        "stage_values": stage_values,
        "competition_values": competition_values,
        "field_metadata": fields,
        "candidate_count": len(candidates),
        "all_open_count": len(all_open_decorated),
        "candidates": candidates,
        "all_open_index": [
            {
                "id": opp["id"],
                "name": opp["name"],
                "stage_name": opp["stage_name"],
                "account": opp["account"],
                "owner": opp["owner"],
                "last_modified_at": opp["last_modified_at"],
                "next_call_date": opp["next_call_date"],
                "customer_executive_sponsor": opp["meddpicc_contacts"]["customer_executive_sponsor"],
                "contact_roles": opp["contact_roles"],
            }
            for opp in all_open_decorated
        ],
    }


def init_plan_template(run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "notes": "",
        "updates": [],
        "create_candidates": [],
    }


def load_run_context(run_dir: Path) -> dict[str, Any]:
    context_path = run_dir / "context.json"
    if not context_path.exists():
        raise ScriptError(f"Missing context file: {context_path}")
    return json.loads(context_path.read_text(encoding="utf-8"))


def load_plan(run_dir: Path, plan_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    target = plan_path or (run_dir / "plan.json")
    if not target.exists():
        raise ScriptError(f"Missing plan file: {target}")
    return target, json.loads(target.read_text(encoding="utf-8"))


def is_external_email(email: str, config: dict[str, Any]) -> bool:
    domain = extract_email_domain(email)
    if not domain:
        return False
    return domain not in {entry.lower() for entry in config["matching"]["internal_domains"]}


def validate_string_length(field_name: str, value: str, metadata: dict[str, dict[str, Any]], errors: list[str]) -> None:
    limit = metadata.get(field_name, {}).get("length")
    if limit and len(value) > limit:
        errors.append(f"{field_name} exceeds length {limit}")


def validate_plan_payload(plan: dict[str, Any], context: dict[str, Any], config: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan.get("updates"), list):
        errors.append("plan.updates must be a list")
        return errors, warnings

    metadata = context["field_metadata"]
    competition_values = set(context["competition_values"])
    opp_index = {opp["id"]: opp for opp in context["all_open_index"]}

    for idx, update in enumerate(plan["updates"]):
        prefix = f"updates[{idx}]"
        opp_id = clean_string(update.get("opportunity_id"))
        if not opp_id:
            errors.append(f"{prefix}.opportunity_id is required")
            continue
        current_opp = opp_index.get(opp_id)
        if not current_opp:
            errors.append(f"{prefix}.opportunity_id {opp_id} is not in the all-open index")
            continue

        set_fields = update.get("set_fields", {})
        merge_fields = update.get("merge_fields", {})
        lookup_fields = update.get("contact_lookup_updates", {})
        if not isinstance(set_fields, dict):
            errors.append(f"{prefix}.set_fields must be an object")
            set_fields = {}
        if not isinstance(merge_fields, dict):
            errors.append(f"{prefix}.merge_fields must be an object")
            merge_fields = {}
        if not isinstance(lookup_fields, dict):
            errors.append(f"{prefix}.contact_lookup_updates must be an object")
            lookup_fields = {}

        for field_name, value in set_fields.items():
            if field_name not in SETTABLE_FIELDS:
                errors.append(f"{prefix}.set_fields.{field_name} is not allowed")
                continue
            if field_name == "StageName":
                current_stage = current_opp["stage_name"]
                if value not in PIPELINE_STAGE_ORDER:
                    errors.append(f"{prefix}.set_fields.StageName must be one of {sorted(PIPELINE_STAGE_ORDER)}")
                elif PIPELINE_STAGE_ORDER[value] < PIPELINE_STAGE_ORDER.get(current_stage, -1):
                    errors.append(f"{prefix}.set_fields.StageName moves backward from {current_stage} to {value}")
                else:
                    validation_threshold = PIPELINE_STAGE_ORDER["Validation"]
                    current_order = PIPELINE_STAGE_ORDER.get(current_stage, -1)
                    if current_order < validation_threshold <= PIPELINE_STAGE_ORDER[value]:
                        existing_sponsor = current_opp.get("customer_executive_sponsor") or {}
                        incoming_sponsor = clean_string(lookup_fields.get("Customer_Executive_Sponsor__c"))
                        if not existing_sponsor.get("id") and not incoming_sponsor:
                            errors.append(
                                f"{prefix}.set_fields.StageName requires contact_lookup_updates.Customer_Executive_Sponsor__c or an existing Customer_Executive_Sponsor__c before moving into Validation or later"
                            )
            elif field_name == "Competition__c":
                if value not in competition_values:
                    errors.append(f"{prefix}.set_fields.Competition__c must match the Salesforce picklist or use Other")
            elif field_name == "Amount":
                if not isinstance(value, (int, float)):
                    errors.append(f"{prefix}.set_fields.Amount must be numeric")
            else:
                text = clean_string(value)
                if text is None:
                    errors.append(f"{prefix}.set_fields.{field_name} must be a non-empty string")
                else:
                    validate_string_length(field_name, text, metadata, errors)

        for field_name, spec in merge_fields.items():
            if field_name not in MERGEABLE_FIELDS:
                errors.append(f"{prefix}.merge_fields.{field_name} is not allowed")
                continue
            if not isinstance(spec, dict):
                errors.append(f"{prefix}.merge_fields.{field_name} must be an object")
                continue
            mode = spec.get("mode")
            value = clean_string(spec.get("value"))
            if mode not in {"prepend", "append"}:
                errors.append(f"{prefix}.merge_fields.{field_name}.mode must be prepend or append")
            if not value:
                errors.append(f"{prefix}.merge_fields.{field_name}.value is required")
            elif metadata.get(field_name, {}).get("length") and len(value) > metadata[field_name]["length"]:
                warnings.append(f"{prefix}.merge_fields.{field_name}.value alone is near or above the field limit")

        for field_name, email in lookup_fields.items():
            if field_name not in CONTACT_LOOKUP_FIELDS:
                errors.append(f"{prefix}.contact_lookup_updates.{field_name} is not allowed")
                continue
            email_text = clean_string(email)
            if not email_text or "@" not in email_text:
                errors.append(f"{prefix}.contact_lookup_updates.{field_name} must be an email")
                continue
            if not is_external_email(email_text, config):
                errors.append(f"{prefix}.contact_lookup_updates.{field_name} must be external")

        for key in ("contacts_to_ensure", "contact_roles_to_ensure"):
            value = update.get(key, [])
            if not isinstance(value, list):
                errors.append(f"{prefix}.{key} must be a list")

        for item_idx, item in enumerate(update.get("contacts_to_ensure", [])):
            item_prefix = f"{prefix}.contacts_to_ensure[{item_idx}]"
            email = clean_string(item.get("email"))
            if not email or "@" not in email:
                errors.append(f"{item_prefix}.email is required")
                continue
            if not is_external_email(email, config):
                errors.append(f"{item_prefix}.email must be external")

        for item_idx, item in enumerate(update.get("contact_roles_to_ensure", [])):
            item_prefix = f"{prefix}.contact_roles_to_ensure[{item_idx}]"
            email = clean_string(item.get("email"))
            if not email or "@" not in email:
                errors.append(f"{item_prefix}.email is required")
                continue
            if not is_external_email(email, config):
                errors.append(f"{item_prefix}.email must be external")

    return errors, warnings


def merge_text(current: str | None, incoming: str, mode: str) -> str:
    current = clean_string(current) or ""
    incoming = incoming.strip()
    if not incoming:
        return current
    if incoming in current:
        return current
    if not current:
        return incoming
    if mode == "prepend":
        return f"{incoming}\n\n{current}"
    return f"{current}\n\n{incoming}"


def split_opportunity_patch(fields: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    detail_patch: dict[str, Any] = {}
    meddpicc_patch: dict[str, Any] = {}
    for field_name, value in fields.items():
        if field_name in DETAIL_WRITE_FIELDS:
            detail_patch[field_name] = value
            continue
        if field_name in MEDDPICC_WRITE_FIELDS:
            meddpicc_patch[field_name] = value
            continue
        detail_patch[field_name] = value
    return detail_patch, meddpicc_patch


def stage_progression(current_stage: str | None, target_stage: str) -> list[str]:
    target_order = PIPELINE_STAGE_ORDER.get(target_stage)
    if target_order is None:
        return [target_stage]
    current_order = PIPELINE_STAGE_ORDER.get(current_stage)
    if current_order is None or target_order <= current_order:
        return [target_stage]
    steps: list[str] = []
    for order in range(current_order + 1, target_order):
        intermediate = CANONICAL_STAGE_BY_ORDER.get(order)
        if intermediate:
            steps.append(intermediate)
    steps.append(target_stage)
    return steps


def query_contacts_by_email(session: SalesforceSession, emails: list[str]) -> list[dict[str, Any]]:
    if not emails:
        return []
    quoted = ",".join(f"'{email}'" for email in sorted(set(emails)))
    soql = f"SELECT Id, Email, Name, FirstName, LastName, AccountId, OwnerId FROM Contact WHERE Email IN ({quoted})"
    return session.query_all(soql)


def choose_contact(records: list[dict[str, Any]], email: str, account_id: str | None = None) -> dict[str, Any] | None:
    exact = [record for record in records if (record.get("Email") or "").lower() == email.lower()]
    if not exact:
        return None
    if account_id:
        account_match = [record for record in exact if record.get("AccountId") == account_id]
        if account_match:
            return account_match[0]
    return exact[0]


def fetch_current_opportunities(session: SalesforceSession, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    quoted = ",".join(f"'{entry}'" for entry in sorted(set(ids)))
    soql = f"""
SELECT Id, AccountId, OwnerId, StageName, NextStep, Next_step__c, Amount, Summary__c, Redflag_s__c,
       Decision_Criteria__c, Decision_Process__c, Implicate_the_Pain__c, Metrics__c, Paper_Process__c,
       Competition__c, Next_Call_Date__c, What_s_New_Changed__c, What_s_New_What_s_Changed_Date__c,
       Customer_Executive_Sponsor__c
FROM Opportunity
WHERE Id IN ({quoted})
""".strip()
    return {record["Id"]: record for record in session.query_all(soql)}


def fetch_existing_roles(session: SalesforceSession, opportunity_ids: list[str]) -> list[dict[str, Any]]:
    if not opportunity_ids:
        return []
    quoted = ",".join(f"'{entry}'" for entry in sorted(set(opportunity_ids)))
    soql = f"""
SELECT Id, OpportunityId, ContactId, Role, IsPrimary, Contact.Email
FROM OpportunityContactRole
WHERE OpportunityId IN ({quoted})
""".strip()
    return session.query_all(soql)


def cmd_check_deps(args: argparse.Namespace) -> int:
    config_path, config = load_config()
    session = SalesforceSession.from_alias(config["salesforce"]["org_alias"])
    payload = {
        "ok": True,
        "config_path": str(config_path),
        "org_alias": config["salesforce"]["org_alias"],
        "org_id": session.org_id,
        "rep_email": config["rep"]["email"],
        "failure_alert_to": config["notifications"]["failure_alert_to"],
        "connectors_required": ["gmail", "google_calendar", "granola"],
    }
    json_print(payload, args.json)
    return 0


def cmd_init_run(args: argparse.Namespace) -> int:
    _, config = load_config()
    session = SalesforceSession.from_alias(config["salesforce"]["org_alias"])
    lookback_hours = args.lookback_hours or config["defaults"]["lookback_hours"]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{os.urandom(3).hex()}"
    run_dir = RUN_ROOT / run_id
    ensure_dir(run_dir)
    context = build_context(session, config, lookback_hours, args.all_open)
    plan = init_plan_template(run_id)
    json_dump(run_dir / "context.json", context)
    json_dump(run_dir / "plan.json", plan)
    payload = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "context_path": str(run_dir / "context.json"),
        "plan_path": str(run_dir / "plan.json"),
        "candidate_count": context["candidate_count"],
        "all_open_count": context["all_open_count"],
        "lookback_hours": lookback_hours,
        "all_open_mode": args.all_open,
    }
    json_print(payload, args.json)
    return 0


def cmd_validate_plan(args: argparse.Namespace) -> int:
    _, config = load_config()
    run_dir = Path(args.run_dir).expanduser()
    context = load_run_context(run_dir)
    plan_path, raw_plan = load_plan(run_dir, Path(args.plan).expanduser() if args.plan else None)
    plan, normalization_warnings = normalize_plan_payload(raw_plan)
    errors, warnings = validate_plan_payload(plan, context, config)
    warnings = normalization_warnings + warnings
    payload = {
        "ok": not errors,
        "plan_path": str(plan_path),
        "run_dir": str(run_dir),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    json_print(payload, args.json)
    return 0 if not errors else 1


def cmd_apply_plan(args: argparse.Namespace) -> int:
    _, config = load_config()
    run_dir = Path(args.run_dir).expanduser()
    context = load_run_context(run_dir)
    plan_path, raw_plan = load_plan(run_dir, Path(args.plan).expanduser() if args.plan else None)
    plan, normalization_warnings = normalize_plan_payload(raw_plan)
    errors, warnings = validate_plan_payload(plan, context, config)
    warnings = normalization_warnings + warnings
    if errors:
        payload = {
            "ok": False,
            "run_dir": str(run_dir),
            "plan_path": str(plan_path),
            "errors": errors,
            "warnings": warnings,
        }
        json_print(payload, True)
        return 1

    session = SalesforceSession.from_alias(config["salesforce"]["org_alias"])
    current_by_id = fetch_current_opportunities(session, [entry["opportunity_id"] for entry in plan["updates"]])
    role_records = fetch_existing_roles(session, [entry["opportunity_id"] for entry in plan["updates"]])
    role_keys = {
        (record.get("OpportunityId"), (record.get("Contact") or {}).get("Email", "").lower())
        for record in role_records
    }
    email_pool: set[str] = set()
    for update in plan["updates"]:
        for email in update.get("contact_lookup_updates", {}).values():
            if clean_string(email):
                email_pool.add(email.lower())
        for item in update.get("contacts_to_ensure", []):
            email_pool.add(item["email"].lower())
        for item in update.get("contact_roles_to_ensure", []):
            email_pool.add(item["email"].lower())

    contact_records = query_contacts_by_email(session, sorted(email_pool))
    contacts_by_email: dict[str, list[dict[str, Any]]] = {}
    for record in contact_records:
        contacts_by_email.setdefault(record["Email"].lower(), []).append(record)

    apply_log: dict[str, Any] = {
        "run_id": plan.get("run_id"),
        "applied_at": utc_now().isoformat(),
        "warnings": warnings,
        "created_contacts": [],
        "created_contact_roles": [],
        "updated_opportunities": [],
        "failed_updates": [],
        "skipped_updates": [],
        "create_candidates": plan.get("create_candidates", []),
    }

    for update in plan["updates"]:
        opp_id = update["opportunity_id"]
        opp_record = current_by_id.get(opp_id)
        if not opp_record:
            raise ScriptError(f"Opportunity {opp_id} could not be fetched during apply")

        pending_contact_records: list[dict[str, Any]] = []
        try:
            for item in update.get("contacts_to_ensure", []):
                email = item["email"].lower()
                existing = choose_contact(contacts_by_email.get(email, []), email, item.get("account_id") or opp_record.get("AccountId"))
                if existing:
                    continue
                if not is_external_email(email, config):
                    raise ScriptError(f"Refusing to create internal contact: {email}")
                first_name, last_name = derive_contact_name(item)
                payload = {
                    "AccountId": item.get("account_id") or opp_record.get("AccountId"),
                    "OwnerId": item.get("owner_id") or opp_record.get("OwnerId"),
                    "LastName": last_name,
                    "Email": email,
                }
                if first_name:
                    payload["FirstName"] = first_name
                contact_id = session.create_record("Contact", payload)
                created = dict(payload)
                created["Id"] = contact_id
                pending_contact_records.append(created)
                apply_log["created_contacts"].append(
                    {
                        "opportunity_id": opp_id,
                        "email": email,
                        "contact_id": contact_id,
                        "account_id": payload["AccountId"],
                    }
                )

            if pending_contact_records:
                refreshed = query_contacts_by_email(session, [entry["Email"] for entry in pending_contact_records])
                for record in refreshed:
                    contacts_by_email.setdefault(record["Email"].lower(), []).append(record)

            for item in update.get("contact_roles_to_ensure", []):
                email = item["email"].lower()
                contact = choose_contact(contacts_by_email.get(email, []), email, opp_record.get("AccountId"))
                if not contact:
                    raise ScriptError(f"Could not resolve contact for role creation: {email}")
                key = (opp_id, email)
                if key in role_keys:
                    continue
                payload = {
                    "OpportunityId": opp_id,
                    "ContactId": contact["Id"],
                    "IsPrimary": bool(item.get("is_primary", False)),
                }
                role = clean_string(item.get("role"))
                if role:
                    payload["Role"] = role
                role_id = session.create_record("OpportunityContactRole", payload)
                role_keys.add(key)
                apply_log["created_contact_roles"].append(
                    {
                        "opportunity_id": opp_id,
                        "email": email,
                        "role_id": role_id,
                        "is_primary": payload["IsPrimary"],
                        "role": role,
                    }
                )
        except ScriptError as exc:
            apply_log["failed_updates"].append(
                {
                    "opportunity_id": opp_id,
                    "summary_reason": clean_string(update.get("summary_reason")) or "Updated opportunity fields",
                    "step": "contact_resolution",
                    "error": str(exc),
                }
            )
            continue

        patch: dict[str, Any] = {}
        for field_name, value in update.get("set_fields", {}).items():
            patch[field_name] = value

        for field_name, spec in update.get("merge_fields", {}).items():
            merged = merge_text(opp_record.get(field_name), spec["value"], spec["mode"])
            validate_string_length(field_name, merged, context["field_metadata"], errors := [])
            if errors:
                raise ScriptError("; ".join(errors))
            patch[field_name] = merged

        for field_name, email in update.get("contact_lookup_updates", {}).items():
            contact = choose_contact(contacts_by_email.get(email.lower(), []), email.lower(), opp_record.get("AccountId"))
            if not contact:
                raise ScriptError(f"Could not resolve contact for lookup field {field_name}: {email}")
            patch[field_name] = contact["Id"]

        changed_patch = {}
        for field_name, value in patch.items():
            if opp_record.get(field_name) != value:
                changed_patch[field_name] = value

        if not changed_patch:
            apply_log["skipped_updates"].append(
                {
                    "opportunity_id": opp_id,
                    "reason": "No effective field changes",
                }
            )
            continue

        detail_patch, meddpicc_patch = split_opportunity_patch(changed_patch)
        write_groups: list[dict[str, Any]] = []
        applied_fields: set[str] = set()
        target_stage = clean_string(detail_patch.get("StageName"))
        if target_stage:
            try:
                for stage_name in stage_progression(opp_record.get("StageName"), target_stage):
                    if opp_record.get("StageName") == stage_name:
                        continue
                    session.update_record("Opportunity", opp_id, {"StageName": stage_name})
                    opp_record["StageName"] = stage_name
                applied_fields.add("StageName")
                write_groups.append(
                    {
                        "name": "stage_progression",
                        "fields": ["StageName"],
                        "target_stage": target_stage,
                    }
                )
            except ScriptError as exc:
                apply_log["failed_updates"].append(
                    {
                        "opportunity_id": opp_id,
                        "summary_reason": clean_string(update.get("summary_reason")) or "Updated opportunity fields",
                        "step": "stage_progression",
                        "fields": ["StageName"],
                        "error": str(exc),
                    }
                )
            detail_patch.pop("StageName", None)
        if detail_patch:
            try:
                session.update_record("Opportunity", opp_id, detail_patch)
                opp_record.update(detail_patch)
                applied_fields.update(detail_patch.keys())
                write_groups.append({"name": "detail", "fields": sorted(detail_patch.keys())})
            except ScriptError as exc:
                apply_log["failed_updates"].append(
                    {
                        "opportunity_id": opp_id,
                        "summary_reason": clean_string(update.get("summary_reason")) or "Updated opportunity fields",
                        "step": "detail",
                        "fields": sorted(detail_patch.keys()),
                        "error": str(exc),
                    }
                )
        if meddpicc_patch:
            try:
                session.update_record("Opportunity", opp_id, meddpicc_patch)
                opp_record.update(meddpicc_patch)
                applied_fields.update(meddpicc_patch.keys())
                write_groups.append({"name": "meddpicc", "fields": sorted(meddpicc_patch.keys())})
            except ScriptError as exc:
                apply_log["failed_updates"].append(
                    {
                        "opportunity_id": opp_id,
                        "summary_reason": clean_string(update.get("summary_reason")) or "Updated opportunity fields",
                        "step": "meddpicc",
                        "fields": sorted(meddpicc_patch.keys()),
                        "error": str(exc),
                    }
                )
        if applied_fields:
            apply_log["updated_opportunities"].append(
                {
                    "opportunity_id": opp_id,
                    "summary_reason": clean_string(update.get("summary_reason")) or "Updated opportunity fields",
                    "fields": sorted(applied_fields),
                    "write_groups": write_groups,
                }
            )
        elif not any(entry["opportunity_id"] == opp_id for entry in apply_log["failed_updates"]):
            apply_log["skipped_updates"].append(
                {
                    "opportunity_id": opp_id,
                    "reason": "No opportunity fields applied",
                }
            )

    result_path = run_dir / "apply-result.json"
    json_dump(result_path, apply_log)
    had_failures = bool(apply_log["failed_updates"])
    payload = {
        "ok": not had_failures,
        "run_dir": str(run_dir),
        "plan_path": str(plan_path),
        "result_path": str(result_path),
        "updated_count": len(apply_log["updated_opportunities"]),
        "created_contacts_count": len(apply_log["created_contacts"]),
        "created_contact_roles_count": len(apply_log["created_contact_roles"]),
        "failed_count": len(apply_log["failed_updates"]),
        "skipped_count": len(apply_log["skipped_updates"]),
        "updated_opportunities": apply_log["updated_opportunities"],
        "failed_updates": apply_log["failed_updates"],
        "warnings": warnings,
    }
    json_print(payload, args.json)
    return 0 if not had_failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual Salesforce opportunity reconciliation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    deps = subparsers.add_parser("check-deps", help="Validate config and Salesforce auth.")
    deps.add_argument("--json", action="store_true")
    deps.set_defaults(func=cmd_check_deps)

    init = subparsers.add_parser("init-run", help="Create a run directory with candidate opps and a plan template.")
    init.add_argument("--lookback-hours", type=int)
    init.add_argument("--all-open", action="store_true")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=cmd_init_run)

    validate = subparsers.add_parser("validate-plan", help="Validate a run plan before applying it.")
    validate.add_argument("--run-dir", required=True)
    validate.add_argument("--plan")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate_plan)

    apply_plan = subparsers.add_parser("apply-plan", help="Apply a validated run plan.")
    apply_plan.add_argument("--run-dir", required=True)
    apply_plan.add_argument("--plan")
    apply_plan.add_argument("--json", action="store_true")
    apply_plan.set_defaults(func=cmd_apply_plan)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ScriptError as exc:
        payload = {"ok": False, "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
