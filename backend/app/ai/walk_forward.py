from math import prod


def build_walk_forward_splits(
    sample_count: int,
    *,
    folds: int = 3,
    minimum_initial_train: int = 50,
    minimum_test_size: int = 10,
) -> list[tuple[int, int]]:
    """Return expanding train ends and consecutive, non-overlapping test ends."""
    if sample_count < minimum_initial_train + minimum_test_size:
        return []

    initial_train = max(minimum_initial_train, int(sample_count * 0.4))
    available = sample_count - initial_train
    fold_count = min(folds, available // minimum_test_size)
    if fold_count < 1:
        return []

    test_size = available // fold_count
    splits = []
    for fold in range(fold_count):
        train_end = initial_train + fold * test_size
        test_end = (
            sample_count
            if fold == fold_count - 1
            else train_end + test_size
        )
        splits.append((train_end, test_end))
    return splits


def aggregate_walk_forward_metrics(fold_metrics: list[dict]) -> dict:
    if not fold_metrics:
        return {
            "walk_forward_folds": 0,
            "walk_forward_return": 0.0,
            "walk_forward_profitable_folds": 0,
            "walk_forward_mean_f1": 0.0,
            "walk_forward_mean_roc_auc": None,
            "walk_forward_trade_count": 0,
            "walk_forward_worst_fold_return": 0.0,
            "walk_forward_details": [],
        }

    roc_auc_values = [
        float(item["roc_auc"])
        for item in fold_metrics
        if item.get("roc_auc") is not None
    ]
    returns = [float(item["strategy_return"]) for item in fold_metrics]
    return {
        "walk_forward_folds": len(fold_metrics),
        "walk_forward_return": float(prod(1.0 + value for value in returns) - 1.0),
        "walk_forward_profitable_folds": sum(value > 0 for value in returns),
        "walk_forward_mean_f1": sum(float(item["f1"]) for item in fold_metrics) / len(fold_metrics),
        "walk_forward_mean_roc_auc": (
            sum(roc_auc_values) / len(roc_auc_values)
            if roc_auc_values
            else None
        ),
        "walk_forward_trade_count": sum(int(item["trade_count"]) for item in fold_metrics),
        "walk_forward_worst_fold_return": min(returns),
        "walk_forward_details": fold_metrics,
    }
