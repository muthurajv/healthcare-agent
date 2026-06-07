"""
Populates the Azure AI Search 'providers' index.

Supports three modes:
  --source sample   Load from sample_providers.json (default — for dev/test)
  --source fhir     Pull live data from Azure Health Data Services FHIR
  --source file     Load from a custom JSON file (--file-path required)

Usage:
    python scripts/search_indexer/populate_index.py --source sample
    python scripts/search_indexer/populate_index.py --source fhir
    python scripts/search_indexer/populate_index.py --source file --file-path /path/to/providers.json
    python scripts/search_indexer/populate_index.py --source sample --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import IndexingResult

sys.path.insert(0, str(Path(__file__).parents[2]))
from config import settings

SAMPLE_DATA_PATH = Path(__file__).parent / "sample_providers.json"
BATCH_SIZE = 100  # Azure AI Search max documents per upload batch


# ── Document normalisation ────────────────────────────────────────────────────

def normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a raw provider record into the exact shape the index expects.
    Adds last_updated timestamp and converts geo_point to the SDK format.
    """
    doc = dict(raw)

    # Timestamp
    doc["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Azure AI Search expects geo as a dict with type/coordinates
    if isinstance(doc.get("geo_point"), dict):
        coords = doc["geo_point"].get("coordinates", [0, 0])
        doc["geo_point"] = {
            "type": "Point",
            "coordinates": coords,  # [longitude, latitude]
        }

    # Ensure collection fields are lists
    for field in ("languages", "accepting_insurance"):
        if field in doc and not isinstance(doc[field], list):
            doc[field] = [doc[field]]

    # Ensure numeric defaults
    doc.setdefault("rating", 0.0)
    doc.setdefault("review_count", 0)
    doc.setdefault("years_experience", 0)

    return doc


# ── Data sources ──────────────────────────────────────────────────────────────

def load_sample() -> list[dict]:
    with open(SAMPLE_DATA_PATH, encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records from sample_providers.json")
    return [normalise(r) for r in records]


def load_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records from {path}")
    return [normalise(r) for r in records]


def load_from_fhir() -> list[dict]:
    """
    Pull Practitioner + PractitionerRole resources from Azure Health Data Services
    and convert them to provider index documents.
    """
    import httpx
    from azure.identity import ClientSecretCredential

    FHIR_SCOPE = "https://healthcareapis.azure.com/.default"

    credential = ClientSecretCredential(
        tenant_id=settings.fhir_tenant_id,
        client_id=settings.fhir_client_id,
        client_secret=settings.fhir_client_secret,
    )
    token = credential.get_token(FHIR_SCOPE).token
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/fhir+json",
    }

    providers = []
    next_url = f"{settings.fhir_base_url}/PractitionerRole?_include=PractitionerRole:practitioner&_count=100"

    with httpx.Client(timeout=30) as client:
        while next_url:
            resp = client.get(next_url, headers=headers)
            resp.raise_for_status()
            bundle = resp.json()

            roles = [e["resource"] for e in bundle.get("entry", [])
                     if e.get("resource", {}).get("resourceType") == "PractitionerRole"]
            practitioners = {
                e["resource"]["id"]: e["resource"]
                for e in bundle.get("entry", [])
                if e.get("resource", {}).get("resourceType") == "Practitioner"
            }

            for role in roles:
                doc = _fhir_role_to_doc(role, practitioners)
                if doc:
                    providers.append(normalise(doc))

            # Follow pagination
            next_link = next((l["url"] for l in bundle.get("link", []) if l["relation"] == "next"), None)
            next_url = next_link

    print(f"Pulled {len(providers)} providers from FHIR.")
    return providers


def _fhir_role_to_doc(role: dict, practitioners: dict) -> dict | None:
    """Map a FHIR PractitionerRole + Practitioner to a flat provider index document."""
    prac_ref = role.get("practitioner", {}).get("reference", "")
    prac_id = prac_ref.split("/")[-1] if "/" in prac_ref else prac_ref
    prac = practitioners.get(prac_id, {})

    if not prac:
        return None

    # Name
    names = prac.get("name", [{}])
    given = " ".join(names[0].get("given", []))
    family = names[0].get("family", "")
    prefix = " ".join(names[0].get("prefix", []))
    full_name = f"{prefix} {given} {family}".strip()

    # Specialty
    specialties = role.get("specialty", [{}])
    specialty = ""
    if specialties:
        codings = specialties[0].get("coding", [{}])
        specialty = codings[0].get("display", "") if codings else ""

    # Languages
    comms = prac.get("communication", [])
    languages = []
    for c in comms:
        for coding in c.get("coding", []):
            if coding.get("display"):
                languages.append(coding["display"])

    # NPI
    npi = ""
    for ident in prac.get("identifier", []):
        if "npi" in ident.get("system", "").lower():
            npi = ident.get("value", "")
            break

    return {
        "provider_id": f"fhir-{role.get('id', prac_id)}",
        "npi": npi,
        "fhir_practitioner_id": prac_id,
        "name": full_name,
        "specialty": specialty,
        "subspecialty": "",
        "location": "",          # enriched separately from Location resource
        "address": "",
        "zip_code": "",
        "phone": "",
        "accepting_new_patients": role.get("acceptingPatients", {}).get("coding", [{}])[0].get("code", "false") == "true",
        "gender": prac.get("gender", ""),
        "languages": languages,
        "hospital_affiliation": "",
        "rating": 0.0,
        "review_count": 0,
        "board_certified": False,
        "education": "",
        "years_experience": 0,
        "accepting_insurance": [],
        "telehealth_available": False,
        "profile_url": "",
    }


# ── Upload ────────────────────────────────────────────────────────────────────

def upload(documents: list[dict], dry_run: bool = False) -> None:
    if dry_run:
        print(f"\n[DRY RUN] Would upload {len(documents)} documents.")
        print("First document preview:")
        print(json.dumps(documents[0], indent=2, default=str))
        return

    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_provider_index,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )

    total_success = 0
    total_failed = 0

    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        results: list[IndexingResult] = client.upload_documents(documents=batch)

        succeeded = sum(1 for r in results if r.succeeded)
        failed = [r for r in results if not r.succeeded]
        total_success += succeeded
        total_failed += len(failed)

        print(f"Batch {i // BATCH_SIZE + 1}: {succeeded}/{len(batch)} uploaded successfully.")
        for f in failed:
            print(f"  FAILED key={f.key!r}: {f.error_message}")

    print(f"\nDone. {total_success} uploaded, {total_failed} failed.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Populate Azure AI Search provider index.")
    parser.add_argument(
        "--source", choices=["sample", "fhir", "file"], default="sample",
        help="Data source: 'sample' (JSON fixture), 'fhir' (live FHIR pull), 'file' (custom JSON).",
    )
    parser.add_argument("--file-path", help="Path to custom JSON file (required when --source file).")
    parser.add_argument("--dry-run", action="store_true", help="Print first document without uploading.")
    args = parser.parse_args()

    if not settings.azure_search_endpoint or not settings.azure_search_api_key:
        print("ERROR: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set in .env")
        sys.exit(1)

    if args.source == "sample":
        documents = load_sample()
    elif args.source == "fhir":
        if not settings.fhir_base_url:
            print("ERROR: FHIR_BASE_URL must be set for --source fhir")
            sys.exit(1)
        documents = load_from_fhir()
    elif args.source == "file":
        if not args.file_path:
            print("ERROR: --file-path required when --source file")
            sys.exit(1)
        documents = load_file(args.file_path)
    else:
        documents = []

    if not documents:
        print("No documents to upload. Exiting.")
        sys.exit(0)

    upload(documents, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
