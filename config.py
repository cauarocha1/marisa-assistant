"""Configuração centralizada do Marisa Assistant."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variáveis obrigatórias para executar o aplicativo."""

    telegram_bot_token: str = Field(validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: int = Field(validation_alias="TELEGRAM_ADMIN_ID")
    gemini_api_key: str = Field(validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(validation_alias="GEMINI_MODEL")
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_key: str = Field(validation_alias="SUPABASE_KEY")
    caldav_url: str = Field(validation_alias="CALDAV_URL")
    caldav_username: str = Field(validation_alias="CALDAV_USERNAME")
    app_specific_password: str = Field(validation_alias="APP_SPECIFIC_PASSWORD")
    caldav_calendar_url: str = Field(validation_alias="CALDAV_CALENDAR_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna uma instância cacheada das configurações do processo."""

    return Settings()
