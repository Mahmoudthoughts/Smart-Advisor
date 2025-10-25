"""Initial schema for Smart Advisor."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


transaction_type = sa.Enum("BUY", "SELL", "DIVIDEND", "FEE", "SPLIT", name="transaction_type")


def upgrade() -> None:
    op.create_table(
        "portfolio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Dubai"),
    )

    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolio.id", ondelete="CASCADE")),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("fee", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("broker_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_transaction_symbol_datetime", "transaction", ["symbol", "datetime"])

    op.create_table(
        "lot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transaction.id", ondelete="CASCADE")),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("open_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qty_open", sa.Numeric(18, 4), nullable=False),
        sa.Column("cost_per_share_adj", sa.Numeric(18, 6), nullable=False),
        sa.Column("fees_alloc", sa.Numeric(18, 6), nullable=False, server_default="0"),
    )
    op.create_index("ix_lot_symbol_open", "lot", ["symbol", "open_datetime"])

    op.create_table(
        "daily_bar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("adj_close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("split_coefficient", sa.Float(), nullable=True),
        sa.Column("dividend_amount", sa.Float(), nullable=True),
        sa.UniqueConstraint("symbol", "date", name="uq_daily_bar_symbol_date"),
    )
    op.create_index("ix_daily_bar_symbol_date", "daily_bar", ["symbol", "date"])

    op.create_table(
        "fx_rate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("from_ccy", sa.String(length=3), nullable=False),
        sa.Column("to_ccy", sa.String(length=3), nullable=False),
        sa.Column("rate_close", sa.Numeric(18, 8), nullable=False),
        sa.UniqueConstraint("date", "from_ccy", "to_ccy", name="uq_fx_rate_date_pair"),
    )
    op.create_index("ix_fx_rate_pair", "fx_rate", ["from_ccy", "to_ccy", "date"])

    op.create_table(
        "daily_portfolio_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("shares_open", sa.Numeric(18, 6), nullable=False),
        sa.Column("market_value_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("cost_basis_open_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("unrealized_pl_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("realized_pl_to_date_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("hypo_liquidation_pl_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("day_opportunity_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("peak_hypo_pl_to_date_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("drawdown_from_peak_pct", sa.Numeric(10, 4), nullable=False),
        sa.UniqueConstraint("symbol", "date", name="uq_snapshot_symbol_date"),
    )
    op.create_index("ix_snapshot_symbol_date", "daily_portfolio_snapshot", ["symbol", "date"])

    op.create_table(
        "signal_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_signal_event_symbol", "signal_event", ["symbol"])
    op.create_index("ix_signal_event_date", "signal_event", ["date"])
    op.create_index("ix_signal_event_rule", "signal_event", ["rule_id"])

    op.create_table(
        "ticker_sentiment_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("score", sa.Numeric(6, 4), nullable=False),
    )
    op.create_index("ix_ticker_sentiment_symbol", "ticker_sentiment_daily", ["symbol"])
    op.create_index("ix_ticker_sentiment_date", "ticker_sentiment_daily", ["date"])

    op.create_table(
        "analyst_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("rating", sa.String(length=32), nullable=True),
        sa.Column("target_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_analyst_snapshot_symbol", "analyst_snapshot", ["symbol"])
    op.create_index("ix_analyst_snapshot_as_of", "analyst_snapshot", ["as_of"])

    op.create_table(
        "forecast_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("prob_retake_peak_30d", sa.Numeric(6, 4), nullable=True),
        sa.Column("expected_regret_delta", sa.Numeric(18, 6), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_forecast_daily_symbol", "forecast_daily", ["symbol"])
    op.create_index("ix_forecast_daily_date", "forecast_daily", ["date"])

    op.create_table(
        "macro_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("importance", sa.String(length=16), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("impact_score", sa.Numeric(6, 3), nullable=True),
    )
    op.create_index("ix_macro_event_type", "macro_event", ["event_type"])
    op.create_index("ix_macro_event_timestamp", "macro_event", ["timestamp_utc"])

    op.create_table(
        "dashboard_kpi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_dashboard_kpi_date", "dashboard_kpi", ["date"])
    op.create_index("ix_dashboard_kpi_metric", "dashboard_kpi", ["metric"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_kpi_metric", table_name="dashboard_kpi")
    op.drop_index("ix_dashboard_kpi_date", table_name="dashboard_kpi")
    op.drop_table("dashboard_kpi")

    op.drop_index("ix_macro_event_timestamp", table_name="macro_event")
    op.drop_index("ix_macro_event_type", table_name="macro_event")
    op.drop_table("macro_event")

    op.drop_index("ix_forecast_daily_date", table_name="forecast_daily")
    op.drop_index("ix_forecast_daily_symbol", table_name="forecast_daily")
    op.drop_table("forecast_daily")

    op.drop_index("ix_analyst_snapshot_as_of", table_name="analyst_snapshot")
    op.drop_index("ix_analyst_snapshot_symbol", table_name="analyst_snapshot")
    op.drop_table("analyst_snapshot")

    op.drop_index("ix_ticker_sentiment_date", table_name="ticker_sentiment_daily")
    op.drop_index("ix_ticker_sentiment_symbol", table_name="ticker_sentiment_daily")
    op.drop_table("ticker_sentiment_daily")

    op.drop_index("ix_signal_event_rule", table_name="signal_event")
    op.drop_index("ix_signal_event_date", table_name="signal_event")
    op.drop_index("ix_signal_event_symbol", table_name="signal_event")
    op.drop_table("signal_event")

    op.drop_index("ix_snapshot_symbol_date", table_name="daily_portfolio_snapshot")
    op.drop_table("daily_portfolio_snapshot")

    op.drop_index("ix_fx_rate_pair", table_name="fx_rate")
    op.drop_table("fx_rate")

    op.drop_index("ix_daily_bar_symbol_date", table_name="daily_bar")
    op.drop_table("daily_bar")

    op.drop_index("ix_lot_symbol_open", table_name="lot")
    op.drop_table("lot")

    op.drop_index("ix_transaction_symbol_datetime", table_name="transaction")
    op.drop_table("transaction")

    op.drop_table("portfolio")
    transaction_type.drop(op.get_bind(), checkfirst=False)
