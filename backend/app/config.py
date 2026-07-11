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
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
