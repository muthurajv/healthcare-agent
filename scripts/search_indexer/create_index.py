"""
Creates (or rebuilds) the 'providers' index in Azure AI Search.

Usage:
    python scripts/search_indexer/create_index.py [--recreate]

Flags:
    --recreate   Drop and recreate the index if it already exists.
                 WARNING: this deletes all indexed documents.
"""
from __future__ import annotations

import argparse
import sys

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ComplexField,
    CorsOptions,
    GeographyPoint,
    HnswAlgorithmConfiguration,
    MagnitudeScoringFunction,
    MagnitudeScoringParameters,
    ScoringProfile,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    TagScoringFunction,
    TagScoringParameters,
    VectorSearch,
    VectorSearchProfile,
)

# ── Load config ───────────────────────────────────────────────────────────────
import os, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2]))
from config import settings

INDEX_NAME = settings.azure_search_provider_index


def build_index() -> SearchIndex:
    fields = [
        # ── Primary key ──────────────────────────────────────────────────────
        SimpleField(
            name="provider_id",
            type=SearchFieldDataType.String,
            key=True,
            retrievable=True,
            filterable=False,
        ),

        # ── Identity / credentials ───────────────────────────────────────────
        SimpleField(name="npi",                  type=SearchFieldDataType.String, filterable=True, retrievable=True),
        SimpleField(name="fhir_practitioner_id", type=SearchFieldDataType.String, filterable=True, retrievable=True),

        # ── Searchable text fields ───────────────────────────────────────────
        SearchableField(name="name",             type=SearchFieldDataType.String, retrievable=True),
        SearchableField(name="specialty",        type=SearchFieldDataType.String, retrievable=True, filterable=True, facetable=True),
        SearchableField(name="subspecialty",     type=SearchFieldDataType.String, retrievable=True),
        SearchableField(name="location",         type=SearchFieldDataType.String, retrievable=True, filterable=True, facetable=True),
        SearchableField(name="hospital_affiliation", type=SearchFieldDataType.String, retrievable=True, filterable=True, facetable=True),
        SearchableField(name="education",        type=SearchFieldDataType.String, retrievable=True),
        SearchableField(name="profile_url",      type=SearchFieldDataType.String, retrievable=True),

        # ── Contact — retrievable only, never filterable or searchable ───────
        # (keeps address/phone out of query logs and LLM prompts)
        SimpleField(name="address", type=SearchFieldDataType.String, retrievable=True),
        SimpleField(name="phone",   type=SearchFieldDataType.String, retrievable=True),

        # ── Geo ──────────────────────────────────────────────────────────────
        SearchField(
            name="geo_point",
            type=SearchFieldDataType.GeographyPoint,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(name="zip_code", type=SearchFieldDataType.String, filterable=True, retrievable=True, facetable=True),

        # ── Boolean flags ────────────────────────────────────────────────────
        SimpleField(name="accepting_new_patients", type=SearchFieldDataType.Boolean, filterable=True, retrievable=True, facetable=True),
        SimpleField(name="board_certified",        type=SearchFieldDataType.Boolean, filterable=True, retrievable=True),
        SimpleField(name="telehealth_available",   type=SearchFieldDataType.Boolean, filterable=True, retrievable=True, facetable=True),

        # ── Categorical ──────────────────────────────────────────────────────
        SimpleField(name="gender", type=SearchFieldDataType.String, filterable=True, retrievable=True, facetable=True),

        # ── Collections ──────────────────────────────────────────────────────
        SearchField(
            name="languages",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            retrievable=True,
            facetable=True,
        ),
        SearchField(
            name="accepting_insurance",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            retrievable=True,
            facetable=True,
        ),

        # ── Numeric ──────────────────────────────────────────────────────────
        SimpleField(name="rating",          type=SearchFieldDataType.Double,  filterable=True, sortable=True, retrievable=True),
        SimpleField(name="review_count",    type=SearchFieldDataType.Int32,   filterable=True, sortable=True, retrievable=True),
        SimpleField(name="years_experience",type=SearchFieldDataType.Int32,   filterable=True, sortable=True, retrievable=True),

        # ── Audit ────────────────────────────────────────────────────────────
        SimpleField(name="last_updated", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
    ]

    # ── Scoring profile ───────────────────────────────────────────────────────
    scoring_profiles = [
        ScoringProfile(
            name="boost-rating-new-patients",
            function_aggregation="sum",
            functions=[
                MagnitudeScoringFunction(
                    field_name="rating",
                    boost=3,
                    parameters=MagnitudeScoringParameters(
                        boosting_range_start=4.0,
                        boosting_range_end=5.0,
                        should_boost_beyond_range_by_constant=True,
                    ),
                ),
                TagScoringFunction(
                    field_name="accepting_new_patients",
                    boost=5,
                    parameters=TagScoringParameters(tags_parameter="acceptingTag"),
                ),
            ],
        )
    ]

    # ── Semantic search ───────────────────────────────────────────────────────
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="provider-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="name"),
                    content_fields=[
                        SemanticField(field_name="specialty"),
                        SemanticField(field_name="hospital_affiliation"),
                        SemanticField(field_name="education"),
                    ],
                    keywords_fields=[
                        SemanticField(field_name="location"),
                        SemanticField(field_name="subspecialty"),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        scoring_profiles=scoring_profiles,
        default_scoring_profile="boost-rating-new-patients",
        semantic_search=semantic_search,
        cors_options=CorsOptions(allowed_origins=["*"], max_age_in_seconds=300),
    )


def main(recreate: bool = False) -> None:
    if not settings.azure_search_endpoint or not settings.azure_search_api_key:
        print("ERROR: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set in .env")
        sys.exit(1)

    client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key),
    )

    if recreate:
        try:
            client.delete_index(INDEX_NAME)
            print(f"Deleted existing index '{INDEX_NAME}'.")
        except ResourceNotFoundError:
            pass

    index = build_index()

    try:
        existing = client.get_index(INDEX_NAME)
        client.create_or_update_index(index)
        print(f"Updated existing index '{INDEX_NAME}'.")
    except ResourceNotFoundError:
        client.create_index(index)
        print(f"Created index '{INDEX_NAME}'.")

    # Verify
    created = client.get_index(INDEX_NAME)
    print(f"Index '{created.name}' has {len(created.fields)} fields.")
    print("Semantic configurations:", [c.name for c in (created.semantic_search.configurations or [])])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create the Azure AI Search providers index.")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate the index.")
    args = parser.parse_args()
    main(recreate=args.recreate)
