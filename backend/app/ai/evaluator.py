from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_predictions(y_true, predictions, probabilities, future_returns) -> dict:
    strategy_return = sum(value for signal, value in zip(predictions, future_returns) if signal == 1)
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)) if len(set(y_true)) > 1 else None,
        "strategy_return": float(strategy_return),
        "buy_and_hold_return": float(sum(future_returns)),
    }
