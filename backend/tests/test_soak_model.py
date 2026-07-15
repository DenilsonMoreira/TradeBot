from decimal import Decimal

from sqlalchemy import Numeric

from app.models.soak import TestnetSoakCampaign as SoakCampaign


def test_soak_campaign_uses_exact_financial_types() -> None:
    table = SoakCampaign.__table__

    for name in (
        "budget_brl",
        "reference_brl_per_usdt",
        "budget_quote",
        "max_quote_per_trade",
        "max_loss_quote",
    ):
        column_type = table.c[name].type
        assert isinstance(column_type, Numeric)
        assert column_type.precision == 20
        assert column_type.scale == 8


def test_soak_campaign_accepts_decimal_values() -> None:
    campaign = SoakCampaign(
        status="RUNNING",
        budget_brl=Decimal("500.00000000"),
        reference_brl_per_usdt=Decimal("5.00000000"),
        budget_quote=Decimal("100.00000000"),
        max_quote_per_trade=Decimal("6.00000000"),
        max_loss_quote=Decimal("5.00000000"),
        duration_hours=168,
        symbols=["BTCUSDT"],
        baseline_candle_counts={"BTCUSDT": 0},
        result={},
    )

    assert campaign.budget_quote == Decimal("100.00000000")
