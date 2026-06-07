"""
Interactive query tool for the Azure AI Search provider index.
Useful for verifying the index after population.

Usage:
    python scripts/search_indexer/query_index.py --query "cardiologist Frisco"
    python scripts/search_indexer/query_index.py --query "cardiology" --filter "accepting_new_patients eq true and rating ge 4.5"
    python scripts/search_indexer/query_index.py --query "cardiology" --geo-filter "75034" --distance-km 20
    python scripts/search_indexer/query_index.py --count          # show total document count
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

sys.path.insert(0, str(Path(__file__).parents[2]))
from config import settings

# Fields safe to display — excludes address and phone (PHI policy)
DISPLAY_FIELDS = (
    "provider_id,name,specialty,subspecialty,location,rating,"
    "accepting_new_patients,gender,languages,hospital_affiliation,"
    "board_certified,telehealth_available,years_experience,npi"
)

# Known ZIP → lat/lon for geo distance filtering (extend as needed)
ZIP_GEO = {
    "75034": (33.1507, -96.8230),  # Frisco
    "75075": (33.0198, -96.7527),  # Plano
    "75071": (33.2148, -96.7594),  # McKinney
    "75013": (33.1032, -96.6706),  # Allen
}


def build_geo_filter(zip_code: str, distance_km: float) -> str | None:
    coords = ZIP_GEO.get(zip_code)
    if not coords:
        print(f"Warning: ZIP {zip_code} not in local lookup. Skipping geo filter.")
        return None
    lat, lon = coords
    return f"geo.distance(geo_point, geography'POINT({lon} {lat})') le {distance_km}"


def run_query(
    query: str,
    odata_filter: str | None = None,
    geo_filter: str | None = None,
    top: int = 5,
    semantic: bool = True,
) -> None:
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_provider_index,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )

    # Combine filters
    filters = [f for f in [odata_filter, geo_filter] if f]
    combined_filter = " and ".join(f"({f})" for f in filters) if filters else None

    kwargs: dict = dict(
        search_text=query,
        filter=combined_filter,
        select=DISPLAY_FIELDS,
        top=top,
        include_total_count=True,
        scoring_profile="boost-rating-new-patients",
    )
    if semantic:
        kwargs["query_type"] = QueryType.SEMANTIC
        kwargs["semantic_configuration_name"] = "provider-semantic"
        kwargs["query_caption"] = "extractive"

    results = client.search(**kwargs)

    print(f"\nQuery : '{query}'")
    if combined_filter:
        print(f"Filter: {combined_filter}")
    print(f"Total matching: {results.get_count()}")
    print("=" * 72)

    for i, doc in enumerate(results, start=1):
        score = doc.get("@search.score", 0)
        captions = doc.get("@search.captions", [])
        caption_text = captions[0].text if captions else ""

        print(f"\n{i}. {doc.get('name')}  |  {doc.get('specialty')}  |  Rating: {doc.get('rating')}")
        print(f"   Location : {doc.get('location')}  |  Hospital: {doc.get('hospital_affiliation')}")
        print(f"   Languages: {', '.join(doc.get('languages', []))}")
        accepting = "✓ Accepting" if doc.get("accepting_new_patients") else "✗ Not accepting"
        telehealth = "✓ Telehealth" if doc.get("telehealth_available") else ""
        print(f"   Status   : {accepting}  {telehealth}")
        print(f"   Score    : {score:.4f}")
        if caption_text:
            print(f"   Caption  : {caption_text}")
        print(f"   NPI      : {doc.get('npi')}  |  ID: {doc.get('provider_id')}")


def show_count() -> None:
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_provider_index,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )
    results = client.search("*", include_total_count=True, top=0)
    print(f"Total documents in index '{settings.azure_search_provider_index}': {results.get_count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the Azure AI Search provider index.")
    parser.add_argument("--query",       default="*",  help="Search query string.")
    parser.add_argument("--filter",      default=None, help="OData filter expression.")
    parser.add_argument("--geo-filter",  default=None, metavar="ZIP", help="Filter by ZIP code proximity.")
    parser.add_argument("--distance-km", default=25,   type=float, help="Distance in km for geo filter (default 25).")
    parser.add_argument("--top",         default=5,    type=int,   help="Max results to return.")
    parser.add_argument("--no-semantic", action="store_true",      help="Disable semantic ranking.")
    parser.add_argument("--count",       action="store_true",      help="Show total document count and exit.")
    args = parser.parse_args()

    if not settings.azure_search_endpoint or not settings.azure_search_api_key:
        print("ERROR: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set in .env")
        sys.exit(1)

    if args.count:
        show_count()
        return

    geo_filter = None
    if args.geo_filter:
        geo_filter = build_geo_filter(args.geo_filter, args.distance_km)

    run_query(
        query=args.query,
        odata_filter=args.filter,
        geo_filter=geo_filter,
        top=args.top,
        semantic=not args.no_semantic,
    )


if __name__ == "__main__":
    main()
