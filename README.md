# HCSC Healthcare Member Agent

An agentic AI system that helps healthcare members find in-network specialists and schedule appointments — built with LangGraph, Azure OpenAI, Azure Health Data Services (FHIR), and Grafana observability.

## What It Does

A member says: *"Find me a cardiologist near Dallas who is in-network and available next week."*

The agent autonomously:
1. Redacts PHI from the input before any LLM call
2. Validates patient consent
3. Extracts structured intent (specialty, location, preferences) via Azure OpenAI
4. Searches the provider directory (Azure AI Search + FHIR Practitioner)
5. Validates in-network status via the payer eligibility API
6. Finds available appointment slots (FHIR Schedule/Slot)
7. Presents options and waits for human confirmation
8. Books the appointment (FHIR Appointment) only after user approval
9. Sends confirmation notification
10. Logs a PHI-safe audit trail

## Architecture

```
User App / Contact Center
        ↓
Azure API Management (Entra ID auth)
        ↓
PHI/PII Guardrail Layer (Presidio)
        ↓
LangGraph Agent Runtime (FastAPI)
        ↓
┌─────────────────────────────────────┐
│  input_phi_scan → consent_check     │
│  → parse_request                    │
│  → search_providers                 │
│  → validate_network                 │
│  → find_availability                │
│  → confirm_with_user (interrupt)    │
│  → schedule_appointment             │
│  → send_notification                │
│  → audit_event                      │
│  → response_redaction               │
└─────────────────────────────────────┘
        ↓
Healthcare APIs: FHIR · EHR · Payer · Provider Directory
        ↓
Observability: OpenTelemetry → Grafana (Tempo · Loki · Prometheus)
```

## Project Structure

```
hcsc-healthcare-agent/
├── agents/
│   ├── state.py                  # AppointmentState TypedDict
│   ├── workflow.py               # LangGraph graph (11 nodes)
│   ├── nodes/                    # 8 agent nodes
│   ├── guardrails/               # PHI scanner, consent check, response redaction
│   └── tools/                   # FHIR, AI Search, payer, secure tool wrapper
├── api/
│   ├── main.py                   # FastAPI app with OTEL middleware
│   └── routers/appointments.py  # REST endpoints
├── observability/
│   ├── tracing.py                # OTLP exporter setup
│   └── span_helpers.py           # PHI-safe span attribute wrapper
├── infrastructure/
│   ├── main.bicep                # Azure deployment entry point
│   └── modules/                  # OpenAI, AI Search, FHIR, Key Vault, APIM, monitoring
├── dashboards/grafana/           # 5 Grafana dashboard JSON files
├── tests/                        # 26 unit tests (26/26 passing)
├── docker-compose.yml            # Local observability stack
├── pyproject.toml
└── .env.example
```

## Azure Stack

| Capability | Azure Service |
|---|---|
| LLM | Azure OpenAI (GPT-4.1) |
| Agent orchestration | LangGraph + FastAPI |
| Provider search | Azure AI Search |
| Clinical data / scheduling | Azure Health Data Services (FHIR R4) |
| API security | Azure API Management + Entra ID |
| PHI/PII detection | Microsoft Presidio |
| Secrets | Azure Key Vault |
| Governance | Microsoft Purview |
| Monitoring | Azure Monitor + App Insights + Grafana |

## Key Design Principles

- **LLM orchestrates, APIs transact.** The LLM never decides network status or books appointments directly — those are deterministic API calls.
- **PHI never enters prompts.** Presidio redacts names, phone numbers, emails, SSNs, and other identifiers before the LLM sees the request.
- **Human confirmation before booking.** LangGraph's `interrupt()` pauses the workflow and surfaces available slots to the user; booking only proceeds after explicit selection.
- **PHI-safe observability.** Span attributes contain only `specialty`, `zip3`, `network_status`, `provider_count`, etc. — never name, DOB, member ID, or contact details.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop (for the local observability stack)
- Azure subscription with the services listed above

### Local Setup

```bash
# 1. Clone and install
git clone https://github.com/muthurajv/healthcare-agent.git
cd healthcare-agent
pip install -e ".[dev]"
python -m spacy download en_core_web_lg   # required by Presidio

# 2. Configure
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Start observability stack
docker-compose up -d
# Grafana → http://localhost:3000
# OTEL Collector (gRPC) → localhost:4317

# 4. Start the API
uvicorn api.main:app --reload
# API → http://localhost:8000
# Docs → http://localhost:8000/docs
```

### Run Tests

```bash
pytest tests/ -v
# 26 passed
```

### Deploy to Azure

```bash
az group create --name hcsc-dev-rg --location eastus
az deployment group create \
  --resource-group hcsc-dev-rg \
  --template-file infrastructure/main.bicep \
  --parameters environment=dev
```

## API Usage

### Start an appointment search

```bash
curl -X POST http://localhost:8000/appointments/request \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Find me a cardiologist near Frisco who is in-network and available next week.",
    "user_id": "user-123",
    "member_id_token": "tok-abc",
    "insurance_plan": "BCBS PPO"
  }'
```

Response includes `thread_id`, `available_slots`, and `awaiting_confirmation: true`.

### Confirm a slot

```bash
curl -X POST http://localhost:8000/appointments/confirm \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "<thread_id>", "selected_index": 1}'
```

## Grafana Dashboards

Import the JSON files from `dashboards/grafana/` into your Grafana instance:

| Dashboard | What it shows |
|---|---|
| `executive_kpi.json` | Booking rate, avg time to book, call deflection |
| `agent_workflow.json` | Node latency heatmap, drop-off funnel, error rate |
| `healthcare_integration.json` | FHIR / payer / provider API latency and errors |
| `llm_cost_usage.json` | Token usage, cost per appointment |
| `compliance_safety.json` | PHI detection events, consent denials, audit log |

## Security & HIPAA Controls

- Entra ID authentication on all API endpoints
- PHI/PII detection and redaction on every user input (Presidio)
- Data minimization: each tool receives only the fields it needs
- Consent validation before accessing insurance or scheduling data
- Response redaction before returning to the user
- No PHI in OpenTelemetry traces or logs
- Encrypted audit trail stored separately from operational telemetry
- Private endpoints and VNet isolation for all Azure services
- Least-privilege managed identity for service-to-service calls

## 12-Week Implementation Roadmap

| Phase | Weeks | Activities |
|---|---|---|
| Discovery | 1–2 | Workflows, systems, data sources, PHI controls |
| Architecture | 3–4 | Azure design, API contracts, security model |
| Agent Build | 5–7 | Build all 5 agents and guardrails |
| Integration | 8–9 | Connect FHIR, EHR, payer/network APIs |
| Testing | 10–11 | Security, compliance, hallucination, booking validation |
| Pilot | 12 | Launch with limited specialty/location |

## License

MIT
