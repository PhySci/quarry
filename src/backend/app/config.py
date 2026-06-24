from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ner:ner@localhost:5432/ner_manager"
    frontend_origin: str = "http://localhost:3000"
    cors_allow_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
