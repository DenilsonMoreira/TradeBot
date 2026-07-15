import hashlib
import json
import math
from datetime import datetime

from app.indicators import calculate_adx, calculate_atr, calculate_ema, calculate_macd, calculate_rsi
from app.models.candle import Candle


FEATURE_NAMES = [
    "return_1", "return_3", "return_6", "ema_9_gap", "ema_21_gap",
    "ema_spread", "rsi_14", "macd_pct", "macd_signal_pct",
    "atr_14_pct", "adx_14", "volume_change", "volume_ratio_20",
    "hour_sin", "hour_cos",
]
MAX_CANDLE_GAP = 0.20
TARGET_RETURN_THRESHOLD = 0.003


def validate_candle_continuity(
    candles: list[Candle],
    max_gap: float = MAX_CANDLE_GAP,
) -> float:
    largest_gap = 0.0
    for previous, current in zip(candles, candles[1:]):
        if previous.close <= 0:
            raise ValueError("fechamento de candle deve ser positivo")
        gap = abs(float(current.close / previous.close - 1))
        largest_gap = max(largest_gap, gap)
        if gap > max_gap:
            raise ValueError(
                "série de candles contém descontinuidade superior a "
                f"{max_gap:.0%}"
            )
    return largest_gap


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
    for index in range(20, len(candles) - horizon):
        if any(value is None for value in (rsi[index], atr[index], adx[index])):
            continue
        future_return = closes[index + horizon] / closes[index] - 1
        average_volume = sum(
            item.volume for item in candles[index - 19:index + 1]
        ) / 20
        hour = candles[index].open_time.hour + candles[index].open_time.minute / 60
        angle = 2 * math.pi * hour / 24
        features = {
            "return_1": float(closes[index] / closes[index - 1] - 1),
            "return_3": float(closes[index] / closes[index - 3] - 1),
            "return_6": float(closes[index] / closes[index - 6] - 1),
            "ema_9_gap": float(closes[index] / ema9[index] - 1),
            "ema_21_gap": float(closes[index] / ema21[index] - 1),
            "ema_spread": float(ema9[index] / ema21[index] - 1),
            "rsi_14": float(rsi[index]),
            "macd_pct": float(macd[index].macd / closes[index]),
            "macd_signal_pct": float(macd[index].signal / closes[index]),
            "atr_14_pct": float(atr[index] / closes[index]),
            "adx_14": float(adx[index]),
            "volume_change": float(candles[index].volume / candles[index - 1].volume - 1) if candles[index - 1].volume else 0.0,
            "volume_ratio_20": float(candles[index].volume / average_volume - 1) if average_volume else 0.0,
            "hour_sin": math.sin(angle),
            "hour_cos": math.cos(angle),
        }
        rows.append({"candle_id": candles[index].id, "open_time": candles[index].open_time.isoformat(), "features": features, "label": int(future_return > TARGET_RETURN_THRESHOLD), "future_return": float(future_return)})
    return rows


def dataset_version(symbol: str, interval: str, rows: list[dict], horizon: int) -> str:
    payload = {"symbol": symbol.upper(), "interval": interval, "horizon": horizon, "first": rows[0]["open_time"] if rows else None, "last": rows[-1]["open_time"] if rows else None, "count": len(rows), "features": FEATURE_NAMES}
    payload["target_return_threshold"] = TARGET_RETURN_THRESHOLD
    return "dataset-v2-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
