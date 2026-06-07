from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_api_version: str = "2024-02-01"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_provider_index: str = "providers"

    # FHIR
    fhir_base_url: str = ""
    fhir_tenant_id: str = ""
    fhir_client_id: str = ""
    fhir_client_secret: str = ""

    # Payer API
    payer_api_base_url: str = ""
    payer_api_key: str = ""

    # Notification
    notification_api_url: str = ""
    notification_api_key: str = ""

    # Consent
    consent_service_url: str = ""

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "hcsc-healthcare-agent"
    otel_service_version: str = "0.1.0"

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
