from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


def compounded_return(values) -> float:
    equity = 1.0
    for value in values:
        equity *= 1.0 + float(value)
    return equity - 1.0


def evaluate_predictions(
    y_true,
    predictions,
    probabilities,
    future_returns,
    *,
    holding_period: int = 1,
    cost_rate: float = 0.0015,
) -> dict:
    if holding_period < 1:
        raise ValueError("holding_period deve ser positivo")
    if not 0 <= cost_rate < 1:
        raise ValueError("cost_rate deve estar entre 0 e 1")

    gross_factors = []
    net_factors = []
    index = 0
    while index < len(future_returns):
        if predictions[index] == 1:
            gross_factor = 1.0 + float(future_returns[index])
            gross_factors.append(gross_factor)
            net_factors.append(
                (1.0 - cost_rate) * gross_factor * (1.0 - cost_rate)
            )
            index += holding_period
        else:
            index += 1

    buy_and_hold_returns = future_returns[::holding_period]
    strategy_return = _factors_return(net_factors)
    gross_strategy_return = _factors_return(gross_factors)
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)) if len(set(y_true)) > 1 else None,
        "strategy_return": float(strategy_return),
        "gross_strategy_return": float(gross_strategy_return),
        "buy_and_hold_return": compounded_return(buy_and_hold_returns),
        "trade_count": len(net_factors),
        "holding_period": holding_period,
        "cost_rate_per_side": cost_rate,
    }


def _factors_return(factors) -> float:
    equity = 1.0
    for factor in factors:
        equity *= factor
    return equity - 1.0
