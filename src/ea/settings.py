from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    ea_host: str = "0.0.0.0"
    ea_port: int = 8000
    database_url: str = "postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    honcho_base_url: str = "http://127.0.0.1:8787"
    honcho_api_key: str = ""
    llm_wiki_workspace: str = "./data/knowledge"
    llm_wiki_cli: str = "llm-wiki"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
