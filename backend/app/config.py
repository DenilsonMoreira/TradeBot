from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    binance_api_key: str
    binance_api_secret: str
    binance_testnet: bool = True
    database_url: str
    candle_symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT"
    candle_intervals: str = "15m"
    candle_sync_limit: int = 500
    candle_sync_interval_seconds: int = 60
    indicator_history_limit: int = 1000
    indicator_calculation_interval_seconds: int = 60
    model_artifact_dir: str = "/app/artifacts"
    research_automation_enabled: bool = False
    research_evaluation_interval_seconds: int = 3600
    research_dataset_limit: int = 3900
    research_horizon: int = 4
    research_train_ratio: float = 0.8
    research_minimum_new_candles: int = 0
    research_promote_qualified: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    auth_secret_key: str = ""
    auth_operator_email: str = ""
    auth_password_hash: str = ""
    auth_totp_secret: str = ""
    auth_session_minutes: int = 30
    auth_cookie_secure: bool = False
    auth_max_attempts: int = 5
    auth_attempt_window_seconds: int = 900
    auth_lockout_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
