import pandas as pd


def calculate_ema_rsi_signal(candles: list) -> dict:
    """
    Recebe candles no formato da Binance e retorna um sinal baseado em:
    EMA 9, EMA 21, RSI 14 e confirmação simples de volume.
    """

    if len(candles) < 30:
        return {
            "signal_type": "HOLD",
            "confidence": 0,
            "price": 0,
            "details": "Candles insuficientes para calcular indicadores.",
        }

    dataframe = pd.DataFrame(
        candles,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    for column in ["open", "high", "low", "close", "volume"]:
        dataframe[column] = pd.to_numeric(dataframe[column])

    dataframe["ema_fast"] = dataframe["close"].ewm(span=9, adjust=False).mean()
    dataframe["ema_slow"] = dataframe["close"].ewm(span=21, adjust=False).mean()

    delta = dataframe["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(window=14).mean()
    average_loss = loss.rolling(window=14).mean()
    rs = average_gain / average_loss.replace(0, float("nan"))
    dataframe["rsi"] = 100 - (100 / (1 + rs))

    dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

    # Ignora o candle atual, que pode ainda estar aberto.
    current = dataframe.iloc[-2]
    previous = dataframe.iloc[-3]

    price = float(current["close"])
    ema_fast = float(current["ema_fast"])
    ema_slow = float(current["ema_slow"])
    previous_fast = float(previous["ema_fast"])
    previous_slow = float(previous["ema_slow"])
    rsi = float(current["rsi"]) if pd.notna(current["rsi"]) else 50.0
    volume = float(current["volume"])
    volume_mean = float(current["volume_mean"]) if pd.notna(current["volume_mean"]) else volume

    bullish_cross = previous_fast <= previous_slow and ema_fast > ema_slow
    bearish_cross = previous_fast >= previous_slow and ema_fast < ema_slow
    volume_confirmed = volume >= volume_mean

    if bullish_cross and 45 <= rsi <= 70 and volume_confirmed:
        return {
            "signal_type": "BUY",
            "confidence": 75.0,
            "price": price,
            "details": (
                f"Cruzamento EMA 9/21 para cima; RSI={rsi:.2f}; "
                f"volume confirmado={volume_confirmed}."
            ),
        }

    if bearish_cross and 30 <= rsi <= 65:
        return {
            "signal_type": "SELL",
            "confidence": 70.0,
            "price": price,
            "details": (
                f"Cruzamento EMA 9/21 para baixo; RSI={rsi:.2f}."
            ),
        }

    return {
        "signal_type": "HOLD",
        "confidence": 0.0,
        "price": price,
        "details": (
            f"Sem entrada. EMA9={ema_fast:.2f}; EMA21={ema_slow:.2f}; "
            f"RSI={rsi:.2f}; volume confirmado={volume_confirmed}."
        ),
    }