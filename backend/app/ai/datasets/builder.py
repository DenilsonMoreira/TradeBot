import hashlib
import json
from datetime import datetime

from app.indicators import calculate_adx, calculate_atr, calculate_ema, calculate_macd, calculate_rsi
from app.models.candle import Candle


FEATURE_NAMES = ["return_1", "ema_9_gap", "ema_21_gap", "rsi_14", "macd", "macd_signal", "atr_14_pct", "adx_14", "volume_change"]


def build_rows(candles: list[Candle], horizon: int = 1) -> list[dict]:
    if horizon < 1:
        raise ValueError("horizon deve ser positivo")
    closes = [item.close for item in candles]
    highs = [item.high for item in candles]
    lows = [item.low for item in candles]
    ema9, ema21 = calculate_ema(closes, 9), calculate_ema(closes, 21)
    rsi, macd = calculate_rsi(closes, 14), calculate_macd(closes)
    atr, adx = calculate_atr(highs, lows, closes, 14), calculate_adx(highs, lows, closes, 14)
    rows = []
    for index in range(1, len(candles) - horizon):
        if any(value is None for value in (rsi[index], atr[index], adx[index])):
            continue
        future_return = closes[index + horizon] / closes[index] - 1
        features = {
            "return_1": float(closes[index] / closes[index - 1] - 1),
            "ema_9_gap": float(closes[index] / ema9[index] - 1),
            "ema_21_gap": float(closes[index] / ema21[index] - 1),
            "rsi_14": float(rsi[index]),
            "macd": float(macd[index].macd),
            "macd_signal": float(macd[index].signal),
            "atr_14_pct": float(atr[index] / closes[index]),
            "adx_14": float(adx[index]),
            "volume_change": float(candles[index].volume / candles[index - 1].volume - 1) if candles[index - 1].volume else 0.0,
        }
        rows.append({"candle_id": candles[index].id, "open_time": candles[index].open_time.isoformat(), "features": features, "label": int(future_return > 0), "future_return": float(future_return)})
    return rows


def dataset_version(symbol: str, interval: str, rows: list[dict], horizon: int) -> str:
    payload = {"symbol": symbol.upper(), "interval": interval, "horizon": horizon, "first": rows[0]["open_time"] if rows else None, "last": rows[-1]["open_time"] if rows else None, "count": len(rows), "features": FEATURE_NAMES}
    return "dataset-v1-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
