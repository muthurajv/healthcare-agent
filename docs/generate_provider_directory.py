"""
Generates the Provider Directory specification PDF for the HCSC Healthcare Member Agent.
Run: python docs/generate_provider_directory.py
Output: docs/Provider_Directory.pdf
"""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ── Colour palette ──────────────────────────────────────────────────────────
BLUE_DARK   = colors.HexColor("#1A3A5C")
BLUE_MID    = colors.HexColor("#2563EB")
BLUE_LIGHT  = colors.HexColor("#DBEAFE")
TEAL        = colors.HexColor("#0D9488")
TEAL_LIGHT  = colors.HexColor("#CCFBF1")
GRAY_DARK   = colors.HexColor("#374151")
GRAY_MID    = colors.HexColor("#6B7280")
GRAY_LIGHT  = colors.HexColor("#F3F4F6")
WHITE       = colors.white
RED_LIGHT   = colors.HexColor("#FEE2E2")
RED_DARK    = colors.HexColor("#991B1B")

OUT_DIR = Path(__file__).parent
OUT_PATH = OUT_DIR / "Provider_Directory.pdf"


# ── Style sheet ──────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=28, textColor=WHITE, leading=34,
        alignment=TA_CENTER, spaceAfter=12,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, textColor=colors.HexColor("#BFDBFE"),
        alignment=TA_CENTER, spaceAfter=6,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontSize=10, textColor=colors.HexColor("#93C5FD"),
        alignment=TA_CENTER,
    )
    styles["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"],
        fontSize=18, textColor=BLUE_DARK, leading=22,
        spaceBefore=18, spaceAfter=8,
        borderPad=4,
    )
    styles["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"],
        fontSize=13, textColor=BLUE_MID, leading=17,
        spaceBefore=14, spaceAfter=6,
    )
    styles["h3"] = ParagraphStyle(
        "h3", parent=base["Heading3"],
        fontSize=11, textColor=TEAL, leading=14,
        spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold",
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, textColor=GRAY_DARK, leading=15,
        spaceAfter=6, alignment=TA_JUSTIFY,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", parent=base["Normal"],
        fontSize=10, textColor=GRAY_DARK, leading=14,
        leftIndent=16, spaceAfter=3,
        bulletIndent=4,
    )
    styles["code"] = ParagraphStyle(
        "code", parent=base["Code"],
        fontSize=8.5, textColor=colors.HexColor("#1E293B"),
        backColor=GRAY_LIGHT, leading=13,
        leftIndent=12, rightIndent=12,
        spaceBefore=4, spaceAfter=4,
        fontName="Courier",
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontSize=8.5, textColor=GRAY_MID, alignment=TA_CENTER,
        spaceAfter=8,
    )
    styles["note"] = ParagraphStyle(
        "note", parent=base["Normal"],
        fontSize=9, textColor=RED_DARK, leading=13,
        leftIndent=8, spaceAfter=4,
    )
    return styles


# ── Helpers ──────────────────────────────────────────────────────────────────
def section_rule():
    return HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=4)


def thin_rule():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=4)


def tbl(data, col_widths, header_bg=BLUE_DARK, stripe=True):
    style = [
        ("BACKGROUND",  (0, 0), (-1, 0),  header_bg),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("TOPPADDING",  (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT] if stripe else [WHITE]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",(0, 0), (-1, -1), 7),
    ]
    return Table(data, colWidths=col_widths, style=TableStyle(style), repeatRows=1)


def info_box(text, s, bg=BLUE_LIGHT, border=BLUE_MID):
    """Coloured callout box."""
    data = [[Paragraph(text, s["body"])]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX",        (0, 0), (-1, -1), 1.2, border),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))
    return t


# ── Cover page ───────────────────────────────────────────────────────────────
def cover_page(s):
    elements = []

    # Blue banner
    banner_data = [[
        Paragraph("HCSC Healthcare Member Agent", s["cover_title"]),
    ]]
    banner = Table(banner_data, colWidths=[7.5 * inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 40),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 40),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 0.3 * inch))

    # Subtitle block
    sub_data = [[
        Paragraph("Provider Directory", ParagraphStyle(
            "ptitle", fontSize=22, textColor=BLUE_DARK,
            alignment=TA_CENTER, leading=28,
        )),
    ]]
    sub_t = Table(sub_data, colWidths=[7.5 * inch])
    sub_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    elements.append(sub_t)
    elements.append(Spacer(1, 0.25 * inch))

    sub_ps = ParagraphStyle("cs", fontSize=12, textColor=GRAY_MID, alignment=TA_CENTER)
    elements.append(Paragraph(
        "Specification · Data Model · Search Schema · API Reference · Integration Guide",
        sub_ps,
    ))
    elements.append(Spacer(1, 0.35 * inch))

    # Meta table
    meta = [
        ["Version", "1.0"],
        ["Date",    "June 2026"],
        ["Project", "HCSC Healthcare Member Agent"],
        ["Status",  "Draft — Internal Use"],
        ["Owner",   "Platform Engineering / AI Team"],
    ]
    mt = Table(meta, colWidths=[2 * inch, 4 * inch])
    mt.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE_DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), GRAY_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -3), 0.4, colors.HexColor("#E5E7EB")),
    ]))
    elements.append(mt)
    elements.append(Spacer(1, 0.3 * inch))

    # HIPAA notice
    notice = info_box(
        "⚠  CONFIDENTIAL — This document may contain design details related to protected health "
        "information (PHI) systems. Do not distribute outside of authorised project personnel. "
        "All production implementations must comply with HIPAA Privacy and Security Rules.",
        s, bg=RED_LIGHT, border=RED_DARK,
    )
    elements.append(notice)
    elements.append(PageBreak())
    return elements


# ── Table of contents ────────────────────────────────────────────────────────
def toc_page(s):
    elements = [
        Paragraph("Table of Contents", s["h1"]),
        section_rule(),
        Spacer(1, 0.1 * inch),
    ]
    toc_items = [
        ("1.", "Overview",                                          "3"),
        ("2.", "Provider Data Model",                              "4"),
        ("2.1", "FHIR Resource Mapping",                           "4"),
        ("2.2", "Core Provider Schema",                            "5"),
        ("3.", "Azure AI Search Index",                            "6"),
        ("3.1", "Index Schema",                                    "6"),
        ("3.2", "Semantic Configuration",                          "7"),
        ("4.", "Search API Reference",                             "8"),
        ("4.1", "Search Providers Endpoint",                       "8"),
        ("4.2", "Get Provider by ID",                              "9"),
        ("4.3", "FHIR Practitioner Lookup",                        "9"),
        ("5.", "NPI Registry Integration",                        "10"),
        ("6.", "Network & Eligibility Validation",                "11"),
        ("7.", "Agent Integration",                               "12"),
        ("7.1", "search_providers Node",                          "12"),
        ("7.2", "Data Flow Diagram",                              "13"),
        ("8.", "Sample Provider Records",                         "14"),
        ("9.", "PHI / HIPAA Controls",                            "15"),
        ("10.", "Operational Considerations",                      "16"),
    ]
    toc_data = [["#", "Section", "Page"]] + [list(r) for r in toc_items]
    t = Table(toc_data, colWidths=[0.5 * inch, 5.5 * inch, 0.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND",(0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR", (0, 1), (0, -1), BLUE_MID),
        ("TEXTCOLOR", (1, 1), (1, -1), GRAY_DARK),
        ("TEXTCOLOR", (2, 1), (2, -1), GRAY_MID),
        ("FONTNAME",  (0, 1), (-1, -1), "Helvetica"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ]))
    elements.append(t)
    elements.append(PageBreak())
    return elements


# ── Section 1: Overview ───────────────────────────────────────────────────────
def section_overview(s):
    elements = [
        Paragraph("1. Overview", s["h1"]), section_rule(),
        Paragraph(
            "The Provider Directory is the authoritative source of healthcare provider information "
            "used by the HCSC Healthcare Member Agent. It enables members to discover in-network "
            "specialists by specialty, location, language, gender preference, hospital affiliation, "
            "and availability of new-patient appointments.",
            s["body"],
        ),
        Spacer(1, 0.1 * inch),
        Paragraph("The directory integrates three complementary data sources:", s["body"]),
        Paragraph("• <b>Azure AI Search</b> — full-text and semantic search over a provider index populated from the health system's CRM and provider master.", s["bullet"]),
        Paragraph("• <b>Azure Health Data Services (FHIR R4)</b> — Practitioner, PractitionerRole, and Organization resources for interoperable clinical data.", s["bullet"]),
        Paragraph("• <b>NPI Registry (CMS)</b> — authoritative provider identification via National Provider Identifier lookups.", s["bullet"]),
        Spacer(1, 0.1 * inch),
        info_box(
            "<b>Design principle:</b> The LangGraph agent calls the provider directory with "
            "only non-PHI search parameters (specialty, location, preferences). Member-specific "
            "data (member ID, insurance plan) is passed only to the payer eligibility API in a "
            "separate, authenticated call.",
            s,
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Supported Search Dimensions", s["h2"]),
        tbl(
            [
                ["Dimension",           "Example Values",                           "Source"],
                ["Specialty",           "Cardiology, Dermatology, Orthopedics",     "AI Search + FHIR"],
                ["Location / ZIP",      "Frisco TX, 75034, within 25 miles",        "AI Search (geo)"],
                ["Language",            "Spanish, Mandarin, Arabic",                "AI Search"],
                ["Gender preference",   "Male, Female",                             "AI Search"],
                ["Accepting new pts",   "True / False",                             "AI Search"],
                ["Hospital affiliation","Baylor Scott & White, UT Southwestern",    "AI Search + FHIR"],
                ["Rating",              "≥ 4.0 stars",                              "AI Search"],
                ["NPI",                 "1234567890",                               "NPI Registry"],
                ["FHIR Practitioner ID","prac-abc123",                              "FHIR R4"],
            ],
            [2 * inch, 3 * inch, 1.5 * inch],
        ),
        PageBreak(),
    ]
    return elements


# ── Section 2: Data Model ────────────────────────────────────────────────────
def section_data_model(s):
    elements = [
        Paragraph("2. Provider Data Model", s["h1"]), section_rule(),
        Paragraph("2.1  FHIR Resource Mapping", s["h2"]),
        Paragraph(
            "The provider directory maps to the following HL7 FHIR R4 resources as defined in "
            "the US Core Implementation Guide. Azure Health Data Services exposes these via "
            "RESTful FHIR APIs secured with Azure AD.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        tbl(
            [
                ["FHIR Resource",       "Purpose",                                          "Key Fields"],
                ["Practitioner",        "Identity and credentials of the provider",         "name, identifier (NPI), qualification, communication"],
                ["PractitionerRole",    "Provider's role at a specific location",           "practitioner, organization, specialty, location, availableTime, acceptingPatients"],
                ["Organization",        "Health system, clinic, or hospital group",         "name, address, type, telecom"],
                ["Location",            "Physical address of a clinic or office",           "name, address, telecom, position (lat/lon)"],
                ["Schedule",            "Provider's scheduling resource",                   "actor (Practitioner), serviceType, planningHorizon"],
                ["Slot",                "A bookable time block on a Schedule",              "status (free/busy), start, end, schedule"],
                ["Appointment",         "A confirmed booking",                              "participant, slot, status, serviceType"],
            ],
            [1.6 * inch, 2.2 * inch, 3.2 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("2.2  Core Provider Schema", s["h2"]),
        Paragraph(
            "The following schema represents a flattened provider record as stored in the "
            "Azure AI Search index. This is denormalized from FHIR for fast full-text retrieval.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        tbl(
            [
                ["Field",               "Type",         "Description",                              "Indexed"],
                ["provider_id",         "string",       "Internal provider UUID (primary key)",     "✓ Retrievable"],
                ["npi",                 "string",       "10-digit National Provider Identifier",    "✓ Filterable"],
                ["fhir_practitioner_id","string",       "FHIR Practitioner resource ID",            "✓ Retrievable"],
                ["name",                "string",       "Full name: Dr. Jane Smith",                "✓ Searchable"],
                ["specialty",           "string",       "Primary specialty (SNOMED coded)",         "✓ Searchable, Filterable"],
                ["subspecialty",        "string",       "Sub-specialty if applicable",              "✓ Searchable"],
                ["location",            "string",       "City, State (e.g. Frisco, TX)",            "✓ Searchable, Filterable"],
                ["address",             "string",       "Street address — NOT exposed to LLM",      "✓ Retrievable only"],
                ["geo_point",           "GeographyPoint","Lat/lon for geo-distance filtering",      "✓ Filterable"],
                ["zip_code",            "string",       "5-digit ZIP code",                         "✓ Filterable"],
                ["phone",               "string",       "Office phone number",                      "✓ Retrievable only"],
                ["accepting_new_patients","bool",       "Currently accepting new patients",         "✓ Filterable"],
                ["gender",              "string",       "Provider gender: male / female",           "✓ Filterable"],
                ["languages",           "Collection(string)","Languages spoken",                    "✓ Filterable"],
                ["hospital_affiliation","string",       "Affiliated hospital or health system",     "✓ Searchable, Filterable"],
                ["rating",              "double",       "Member satisfaction score (0–5)",          "✓ Sortable, Filterable"],
                ["review_count",        "int32",        "Number of reviews",                        "✓ Sortable"],
                ["board_certified",     "bool",         "Board certification status",               "✓ Filterable"],
                ["education",           "string",       "Medical school and residency",             "✓ Searchable"],
                ["years_experience",    "int32",        "Years in practice",                        "✓ Filterable, Sortable"],
                ["accepting_insurance", "Collection(string)","Insurance plans accepted",            "✓ Filterable"],
                ["telehealth_available","bool",         "Offers telehealth appointments",           "✓ Filterable"],
                ["profile_url",         "string",       "URL to provider bio/profile page",         "✓ Retrievable"],
                ["last_updated",        "DateTimeOffset","Last data refresh timestamp",             "✓ Filterable, Sortable"],
            ],
            [1.7 * inch, 1.0 * inch, 2.8 * inch, 1.5 * inch],
        ),
        PageBreak(),
    ]
    return elements


# ── Section 3: Azure AI Search Index ─────────────────────────────────────────
def section_search_index(s):
    elements = [
        Paragraph("3. Azure AI Search Index", s["h1"]), section_rule(),
        Paragraph("3.1  Index Schema (JSON)", s["h2"]),
        Paragraph(
            "The provider index is defined in Azure AI Search with semantic ranking enabled. "
            "The index is populated via an Azure Data Factory pipeline that pulls from the "
            "provider master database and FHIR on a scheduled basis.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        Paragraph("""POST https://&lt;search-name&gt;.search.windows.net/indexes?api-version=2024-05-01-preview

{
  "name": "providers",
  "fields": [
    { "name": "provider_id",    "type": "Edm.String",   "key": true, "retrievable": true },
    { "name": "npi",            "type": "Edm.String",   "filterable": true },
    { "name": "name",           "type": "Edm.String",   "searchable": true, "retrievable": true },
    { "name": "specialty",      "type": "Edm.String",   "searchable": true, "filterable": true },
    { "name": "location",       "type": "Edm.String",   "searchable": true, "filterable": true },
    { "name": "geo_point",      "type": "Edm.GeographyPoint", "filterable": true },
    { "name": "zip_code",       "type": "Edm.String",   "filterable": true },
    { "name": "accepting_new_patients", "type": "Edm.Boolean", "filterable": true },
    { "name": "gender",         "type": "Edm.String",   "filterable": true },
    { "name": "languages",      "type": "Collection(Edm.String)", "filterable": true },
    { "name": "hospital_affiliation", "type": "Edm.String", "searchable": true },
    { "name": "rating",         "type": "Edm.Double",   "filterable": true, "sortable": true },
    { "name": "telehealth_available", "type": "Edm.Boolean", "filterable": true },
    { "name": "accepting_insurance", "type": "Collection(Edm.String)", "filterable": true }
  ],
  "scoringProfiles": [{
    "name": "boost-rating-new-patients",
    "functionAggregation": "sum",
    "functions": [
      { "fieldName": "rating",   "type": "magnitude", "boost": 3,
        "magnitude": { "boostingRangeStart": 4, "boostingRangeEnd": 5,
                       "constantBoostBeyondRange": true }},
      { "fieldName": "accepting_new_patients", "type": "tag",
        "boost": 5, "tag": { "tagsParameter": "acceptingTag" }}
    ]
  }]
}""", s["code"]),
        Spacer(1, 0.15 * inch),
        Paragraph("3.2  Semantic Configuration", s["h2"]),
        Paragraph(
            "Semantic ranking uses Azure AI to re-rank results based on meaning, not just "
            "keyword frequency. The configuration below prioritises specialty and location "
            "as the primary semantic fields.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        Paragraph("""  "semanticConfiguration": {
    "name": "provider-semantic",
    "prioritizedFields": {
      "titleField":        { "fieldName": "name" },
      "prioritizedContentFields": [
        { "fieldName": "specialty" },
        { "fieldName": "hospital_affiliation" },
        { "fieldName": "education" }
      ],
      "prioritizedKeywordsFields": [
        { "fieldName": "location" },
        { "fieldName": "subspecialty" }
      ]
    }
  }""", s["code"]),
        Spacer(1, 0.1 * inch),
        info_box(
            "<b>Tip:</b> Use <i>queryType=semantic</i> with <i>semanticConfiguration=provider-semantic</i> "
            "to return a <i>captions</i> field containing AI-generated answer fragments. These are "
            "safe to surface in the agent's response because they are derived from provider bios, "
            "not from member data.",
            s,
        ),
        PageBreak(),
    ]
    return elements


# ── Section 4: API Reference ──────────────────────────────────────────────────
def section_api(s):
    elements = [
        Paragraph("4. Search API Reference", s["h1"]), section_rule(),
        Paragraph("4.1  Search Providers", s["h2"]),
        Paragraph("Performs a full-text + filter search against the Azure AI Search provider index.", s["body"]),
        Spacer(1, 0.08 * inch),
        Paragraph("POST  /indexes/providers/docs/search?api-version=2024-05-01-preview", s["code"]),
        Spacer(1, 0.06 * inch),
        Paragraph("<b>Request body parameters:</b>", s["body"]),
        tbl(
            [
                ["Parameter",       "Type",     "Required", "Description"],
                ["search",          "string",   "Yes",      "Free-text query, e.g. 'Cardiologist Frisco TX'"],
                ["filter",          "string",   "No",       "OData filter, e.g. accepting_new_patients eq true and rating ge 4.0"],
                ["select",          "string",   "No",       "Comma-separated fields to return"],
                ["top",             "integer",  "No",       "Max results to return (default 10, max 50)"],
                ["queryType",       "string",   "No",       "'semantic' enables semantic re-ranking"],
                ["semanticConfiguration", "string", "No",  "'provider-semantic'"],
                ["scoringProfile",  "string",   "No",       "'boost-rating-new-patients'"],
                ["facets",          "string[]", "No",       "e.g. ['specialty', 'location', 'languages']"],
            ],
            [1.5 * inch, 0.8 * inch, 0.7 * inch, 3.5 * inch],
        ),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Example request:</b>", s["body"]),
        Paragraph("""{
  "search": "cardiologist Frisco",
  "filter": "accepting_new_patients eq true and rating ge 4.0",
  "select": "provider_id,name,specialty,location,rating,accepting_new_patients,npi",
  "top": 5,
  "queryType": "semantic",
  "semanticConfiguration": "provider-semantic",
  "scoringProfile": "boost-rating-new-patients"
}""", s["code"]),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Example response:</b>", s["body"]),
        Paragraph("""{
  "value": [
    {
      "provider_id": "prov-001",
      "name": "Dr. Jane Smith",
      "specialty": "Cardiology",
      "location": "Frisco, TX",
      "rating": 4.8,
      "accepting_new_patients": true,
      "npi": "1234567890"
    }
  ],
  "@odata.count": 1,
  "@search.answers": [ { "text": "Board-certified cardiologist in Frisco, TX" } ]
}""", s["code"]),
        Spacer(1, 0.15 * inch),
        Paragraph("4.2  Get Provider by ID", s["h2"]),
        Paragraph("GET  /indexes/providers/docs/&lt;provider_id&gt;?api-version=2024-05-01-preview", s["code"]),
        Spacer(1, 0.08 * inch),
        tbl(
            [
                ["Response Field",   "Description"],
                ["provider_id",      "Internal UUID"],
                ["npi",              "National Provider Identifier"],
                ["name",             "Provider full name"],
                ["specialty",        "Primary medical specialty"],
                ["location",         "City, State"],
                ["rating",           "Member satisfaction score"],
                ["telehealth_available", "Telehealth option flag"],
                ["accepting_new_patients", "New patient status"],
            ],
            [2.5 * inch, 4.5 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("4.3  FHIR Practitioner Lookup", s["h2"]),
        Paragraph(
            "After the AI Search call returns providers, the agent enriches results with FHIR "
            "Practitioner and PractitionerRole data from Azure Health Data Services.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        Paragraph("""GET {FHIR_BASE_URL}/PractitionerRole
  ?specialty={snomed_code}
  &location={location_id}
  &_include=PractitionerRole:practitioner
  &_count=20
Authorization: Bearer {azure_ad_token}""", s["code"]),
        PageBreak(),
    ]
    return elements


# ── Section 5: NPI Registry ───────────────────────────────────────────────────
def section_npi(s):
    elements = [
        Paragraph("5. NPI Registry Integration", s["h1"]), section_rule(),
        Paragraph(
            "The National Provider Identifier (NPI) registry (maintained by CMS) provides "
            "authoritative provider identity verification. The agent uses NPI lookups to "
            "validate that a provider record in the directory matches a real, active provider.",
            s["body"],
        ),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>NPI Registry API (public, no auth required):</b>", s["body"]),
        Paragraph("""GET https://npiregistry.cms.hhs.gov/api/
  ?number={npi}
  &version=2.1""", s["code"]),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Key fields returned:</b>", s["body"]),
        tbl(
            [
                ["Field",               "Description"],
                ["number",              "10-digit NPI"],
                ["enumeration_type",    "NPI-1 (individual) or NPI-2 (organization)"],
                ["basic.name_prefix",   "Dr., Prof., etc."],
                ["basic.first_name",    "First name"],
                ["basic.last_name",     "Last name"],
                ["basic.status",        "A = Active, D = Deactivated"],
                ["taxonomies[].code",   "Provider taxonomy code (specialty)"],
                ["taxonomies[].primary","Primary taxonomy flag"],
                ["addresses[].city",    "Practice city"],
                ["addresses[].state",   "Practice state"],
            ],
            [2.5 * inch, 4 * inch],
        ),
        Spacer(1, 0.12 * inch),
        info_box(
            "<b>Validation rule:</b> Before displaying a provider to a member, confirm "
            "<i>basic.status == 'A'</i> (active). Deactivated NPI records must be excluded "
            "from search results and flagged for removal from the provider index.",
            s, bg=TEAL_LIGHT, border=TEAL,
        ),
        PageBreak(),
    ]
    return elements


# ── Section 6: Network Validation ────────────────────────────────────────────
def section_network(s):
    elements = [
        Paragraph("6. Network & Eligibility Validation", s["h1"]), section_rule(),
        Paragraph(
            "After the provider search returns candidates, the Network Validation Agent checks "
            "each provider against the member's insurance plan using the payer eligibility API. "
            "This is a deterministic API call — the LLM does not make network decisions.",
            s["body"],
        ),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Eligibility API request:</b>", s["body"]),
        Paragraph("""POST {PAYER_API_BASE_URL}/eligibility/validate
x-api-key: {api_key}
Content-Type: application/json

{
  "member_token":    "tok-abc123",     // opaque token — not raw member ID
  "plan_id":         "BCBS-PPO-TX",
  "provider_id":     "prov-001",
  "appointment_type": "new_patient"
}""", s["code"]),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Eligibility API response:</b>", s["body"]),
        Paragraph("""{
  "network_status":       "in_network",
  "referral_required":    false,
  "prior_auth_required":  false,
  "contract_active":      true,
  "copay_estimate":       35.00
}""", s["code"]),
        Spacer(1, 0.1 * inch),
        Paragraph("<b>Validation outcomes and routing:</b>", s["body"]),
        tbl(
            [
                ["network_status",    "contract_active", "Agent action"],
                ["in_network",        "true",            "Include in results — proceed to availability"],
                ["in_network",        "false",           "Exclude — contract expired, flag for ops review"],
                ["out_of_network",    "—",               "Exclude from primary results; optionally surface with OON cost warning"],
                ["unknown",           "—",               "Exclude — eligibility check inconclusive"],
            ],
            [1.5 * inch, 1.3 * inch, 3.7 * inch],
        ),
        Spacer(1, 0.12 * inch),
        info_box(
            "<b>PHI minimization:</b> The eligibility API receives a <i>member_token</i> — an "
            "opaque reference resolved by the payer's identity layer. Raw member IDs, SSNs, and "
            "dates of birth are never passed through the agent workflow.",
            s,
        ),
        PageBreak(),
    ]
    return elements


# ── Section 7: Agent Integration ─────────────────────────────────────────────
def section_agent(s):
    elements = [
        Paragraph("7. Agent Integration", s["h1"]), section_rule(),
        Paragraph("7.1  search_providers Node", s["h2"]),
        Paragraph(
            "The <b>search_providers</b> LangGraph node orchestrates the provider directory "
            "lookup. It receives parsed intent from <b>parse_request</b> and passes results "
            "to <b>validate_network</b>.",
            s["body"],
        ),
        Spacer(1, 0.08 * inch),
        Paragraph("""# agents/nodes/search_providers.py
def search_providers(state: AppointmentState) -> dict:
    specialty = state.get("specialty") or ""
    location  = state.get("location") or ""
    language  = state.get("language_preference")
    gender    = state.get("gender_preference")

    # 1. Azure AI Search — primary provider directory
    providers = ai_search_providers(
        specialty=specialty,
        location=location,
        accepting_new_patients=True,
        language=language,
        gender=gender,
        top=10,
    )

    # 2. FHIR enrichment — add fhir_id for downstream scheduling
    if providers:
        fhir_roles = search_practitioners(specialty=specialty, location=location)
        fhir_by_npi = {r.get("npi"): r for r in fhir_roles if r.get("npi")}
        for p in providers:
            fhir_data = fhir_by_npi.get(p.get("npi"), {})
            if fhir_data:
                p["fhir_id"] = fhir_data.get("fhir_id")

    return {
        "providers": providers,
        "status": "providers_found" if providers else "no_providers_found",
    }""", s["code"]),
        Spacer(1, 0.15 * inch),
        Paragraph("7.2  Data Flow Diagram", s["h2"]),
        Spacer(1, 0.08 * inch),
        tbl(
            [
                ["Step", "Component",              "Input",                        "Output"],
                ["1",    "parse_request",           "safe_request (PHI-redacted)", "specialty, location, preferences"],
                ["2",    "search_providers",        "specialty, location",         "providers[] (up to 10 records)"],
                ["3",    "FHIR enrichment",         "NPI from AI Search",          "fhir_id per provider"],
                ["4",    "validate_network",        "member_token, plan_id, provider_id", "in_network_providers[]"],
                ["5",    "find_availability",       "fhir_id, date range",         "available_slots[]"],
                ["6",    "confirm_with_user",       "available_slots[]",           "selected_slot"],
                ["7",    "schedule_appointment",    "patient_token, slot_fhir_id", "appointment_id (FHIR)"],
            ],
            [0.4 * inch, 1.8 * inch, 2.3 * inch, 3.0 * inch],
        ),
        Spacer(1, 0.12 * inch),
        Paragraph("<b>OpenTelemetry span attributes emitted by search_providers:</b>", s["body"]),
        tbl(
            [
                ["Attribute",               "Value example",        "PHI-safe?"],
                ["agent.node",              "search_providers",     "✓ Yes"],
                ["workflow.name",           "find_specialist_schedule", "✓ Yes"],
                ["request.specialty",       "Cardiology",           "✓ Yes"],
                ["request.location",        "Frisco",               "✓ Yes (city only)"],
                ["provider.count",          "8",                    "✓ Yes"],
                ["agent.status",            "providers_found",      "✓ Yes"],
            ],
            [2.5 * inch, 2.5 * inch, 1.5 * inch],
        ),
        Spacer(1, 0.08 * inch),
        Paragraph("Never emitted: provider name, address, phone, NPI (all retrievable-only, not logged).", s["note"]),
        PageBreak(),
    ]
    return elements


# ── Section 8: Sample Records ─────────────────────────────────────────────────
def section_samples(s):
    elements = [
        Paragraph("8. Sample Provider Records", s["h1"]), section_rule(),
        Paragraph(
            "The following sample records illustrate the structure of provider directory "
            "entries. All names are fictitious.",
            s["body"],
        ),
        Spacer(1, 0.1 * inch),
        tbl(
            [
                ["Field",               "Record A",                     "Record B",                     "Record C"],
                ["provider_id",         "prov-001",                     "prov-002",                     "prov-003"],
                ["name",                "Dr. Jane Smith",               "Dr. Carlos Reyes",             "Dr. Priya Nair"],
                ["specialty",           "Cardiology",                   "Cardiology",                   "Cardiology"],
                ["subspecialty",        "Interventional Cardiology",    "Heart Failure",                "Electrophysiology"],
                ["location",            "Frisco, TX",                   "Plano, TX",                    "McKinney, TX"],
                ["zip_code",            "75034",                        "75023",                        "75069"],
                ["distance (example)",  "3.2 miles",                    "7.8 miles",                    "12.1 miles"],
                ["gender",              "Female",                       "Male",                         "Female"],
                ["languages",           "English, Spanish",             "English, Spanish, Portuguese", "English, Hindi, Tamil"],
                ["hospital_affiliation","Baylor Scott & White",         "UT Southwestern",              "Medical City McKinney"],
                ["rating",              "4.8",                          "4.6",                          "4.9"],
                ["accepting_new_patients","Yes",                        "Yes",                          "No"],
                ["board_certified",     "Yes",                          "Yes",                          "Yes"],
                ["telehealth_available","Yes",                          "No",                           "Yes"],
                ["npi",                 "1234567890",                   "0987654321",                   "1122334455"],
            ],
            [1.7 * inch, 1.8 * inch, 1.8 * inch, 1.7 * inch],
        ),
        PageBreak(),
    ]
    return elements


# ── Section 9: PHI Controls ───────────────────────────────────────────────────
def section_phi(s):
    elements = [
        Paragraph("9. PHI / HIPAA Controls", s["h1"]), section_rule(),
        Paragraph(
            "The provider directory itself does not contain member PHI — it holds provider "
            "information. However, several fields (name, address, phone, NPI) are considered "
            "sensitive and must be handled according to the following policy.",
            s["body"],
        ),
        Spacer(1, 0.1 * inch),
        tbl(
            [
                ["Field",               "Classification",   "LLM Prompt?",  "OTEL Span?",   "Audit Log?"],
                ["provider_id",         "Internal ID",      "✓ Allowed",    "✓ Allowed",    "✓ Allowed"],
                ["npi",                 "Business ID",      "✗ No",         "✗ No",         "✓ Allowed"],
                ["name",                "Public directory", "✓ Allowed",    "✗ No",         "✗ No"],
                ["specialty",           "Non-sensitive",    "✓ Allowed",    "✓ Allowed",    "✓ Allowed"],
                ["location (city)",     "Non-sensitive",    "✓ Allowed",    "✓ Allowed",    "✓ Allowed"],
                ["address (street)",    "Sensitive",        "✗ No",         "✗ No",         "✗ No"],
                ["phone",               "Sensitive",        "✗ No",         "✗ No",         "✗ No"],
                ["rating",              "Non-sensitive",    "✓ Allowed",    "✓ Allowed",    "✓ Allowed"],
                ["fhir_id",             "Internal ref",     "✗ No",         "✗ No",         "✓ Allowed"],
            ],
            [1.6 * inch, 1.2 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("<b>PHI controls checklist:</b>", s["body"]),
        Paragraph("□  Provider name is public information — it may appear in the agent's response to the member.", s["bullet"]),
        Paragraph("□  Street address and phone number are retrieved from the API but never included in LLM prompts or OTEL spans.", s["bullet"]),
        Paragraph("□  NPI is used only for verification calls to the CMS registry — not surfaced in conversational responses.", s["bullet"]),
        Paragraph("□  The Azure AI Search select parameter is restricted to non-sensitive fields when the agent constructs queries.", s["bullet"]),
        Paragraph("□  Azure AI Search uses private endpoints — no public internet access to the provider index.", s["bullet"]),
        Paragraph("□  Access to the provider index requires a managed identity or API Management policy-issued token.", s["bullet"]),
        PageBreak(),
    ]
    return elements


# ── Section 10: Operational Considerations ────────────────────────────────────
def section_ops(s):
    elements = [
        Paragraph("10. Operational Considerations", s["h1"]), section_rule(),
        Paragraph("Data Refresh", s["h2"]),
        tbl(
            [
                ["Data Source",             "Refresh Frequency",    "Method"],
                ["Provider master / CRM",   "Daily",                "Azure Data Factory pipeline → AI Search indexer"],
                ["FHIR Practitioner",        "Real-time",            "FHIR change feed via Azure Event Grid"],
                ["NPI Registry",            "Weekly",               "CMS bulk download + diff indexing"],
                ["Network/eligibility",      "Real-time",            "Payer API call at query time"],
                ["Availability / Slots",    "Real-time",            "FHIR Slot API at query time"],
            ],
            [2.2 * inch, 1.6 * inch, 3.2 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Grafana Monitoring", s["h2"]),
        tbl(
            [
                ["Metric",                          "Dashboard",                "Alert threshold"],
                ["Provider search latency (p95)",   "healthcare_integration",   "> 2 s"],
                ["No-result rate",                  "healthcare_integration",   "> 15%"],
                ["AI Search error rate",            "healthcare_integration",   "> 1%"],
                ["FHIR Practitioner API latency",   "healthcare_integration",   "> 3 s"],
                ["NPI validation failures",         "compliance_safety",        "> 5/hr"],
                ["Index staleness (last refresh)",  "agent_workflow",           "> 25 hrs"],
            ],
            [2.8 * inch, 2.0 * inch, 1.5 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Error Handling", s["h2"]),
        tbl(
            [
                ["Scenario",                        "Agent behaviour"],
                ["AI Search returns 0 results",     "Return status='no_providers_found'; route to audit; suggest broader search"],
                ["FHIR enrichment fails",           "Skip FHIR enrichment (best-effort); log warning; continue with AI Search results"],
                ["Payer API timeout",               "Exclude provider from in-network list; log timeout; do not surface error to member"],
                ["NPI status = Deactivated",        "Filter provider from results before returning to agent; flag for ops review"],
                ["All providers out-of-network",    "Return status='no_in_network_providers'; route to audit; offer OON alternatives"],
            ],
            [2.8 * inch, 4.2 * inch],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("MVP Exclusions (Phase 1)", s["h2"]),
        Paragraph("• Multi-location providers — only primary practice location is searched in MVP.", s["bullet"]),
        Paragraph("• Telehealth-only providers — filtered out until telehealth booking flow is implemented.", s["bullet"]),
        Paragraph("• Group NPI (NPI-2 / organization) — individual practitioner NPI only in Phase 1.", s["bullet"]),
        Paragraph("• Real-time wait time — not available in FHIR R4; deferred to Phase 2.", s["bullet"]),
        Spacer(1, 0.2 * inch),
        thin_rule(),
        Spacer(1, 0.1 * inch),
        Paragraph(
            "For questions about this specification, contact the Platform Engineering team. "
            "This document is version-controlled in the healthcare-agent GitHub repository "
            "under docs/Provider_Directory.pdf.",
            ParagraphStyle("footer_body", fontSize=9, textColor=GRAY_MID, alignment=TA_CENTER),
        ),
    ]
    return elements


# ── Page template (header + footer) ──────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter

    # Header bar
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, h - 0.45 * inch, w, 0.45 * inch, fill=True, stroke=False)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.5 * inch, h - 0.28 * inch, "HCSC Healthcare Member Agent")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - 0.5 * inch, h - 0.28 * inch, "Provider Directory — CONFIDENTIAL")

    # Footer
    canvas.setFillColor(GRAY_MID)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.5 * inch, 0.35 * inch, "© 2026 HCSC Healthcare Member Agent Project")
    canvas.drawRightString(w - 0.5 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(0.5 * inch, 0.5 * inch, w - 0.5 * inch, 0.5 * inch)

    canvas.restoreState()


def on_first_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(GRAY_MID)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 0.5 * inch, 0.35 * inch, "Page 1")
    canvas.restoreState()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="HCSC Provider Directory",
        author="HCSC Healthcare Member Agent Project",
        subject="Provider Directory Specification",
    )

    s = build_styles()
    story = []
    story += cover_page(s)
    story += toc_page(s)
    story += section_overview(s)
    story += section_data_model(s)
    story += section_search_index(s)
    story += section_api(s)
    story += section_npi(s)
    story += section_network(s)
    story += section_agent(s)
    story += section_samples(s)
    story += section_phi(s)
    story += section_ops(s)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"PDF generated: {OUT_PATH}")


if __name__ == "__main__":
    main()
