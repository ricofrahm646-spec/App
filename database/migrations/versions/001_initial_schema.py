"""Initial JARVIS schema

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_superuser", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    # ── User Settings ──────────────────────────────────────────────────────────
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_token_encrypted", sa.Text(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("mt5_login", sa.Integer(), nullable=True),
        sa.Column("mt5_password_encrypted", sa.Text(), nullable=True),
        sa.Column("mt5_server", sa.String(100), nullable=True),
        sa.Column("tradingview_secret", sa.String(255), nullable=True),
        sa.Column("risk_per_trade", sa.Float(), default=2.0, nullable=True),
        sa.Column("max_daily_loss", sa.Float(), default=5.0, nullable=True),
        sa.Column("max_total_drawdown", sa.Float(), default=20.0, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Strategies ─────────────────────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), default="INACTIVE", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("winrate", sa.Float(), default=0.0, nullable=True),
        sa.Column("profit_factor", sa.Float(), default=0.0, nullable=True),
        sa.Column("total_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("win_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("loss_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("total_profit", sa.Float(), default=0.0, nullable=True),
        sa.Column("max_drawdown", sa.Float(), default=0.0, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── Trades ─────────────────────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("lot_size", sa.Float(), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("profit_loss", sa.Float(), default=0.0, nullable=True),
        sa.Column("status", sa.String(10), default="OPEN", nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=True),
        sa.Column("magic_number", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(255), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])

    # ── Trade Signals ──────────────────────────────────────────────────────────
    op.create_table(
        "trade_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=True),
        sa.Column("signal_type", sa.String(10), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), default=0.0, nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("processed", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Backtest Results ───────────────────────────────────────────────────────
    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_capital", sa.Float(), nullable=False),
        sa.Column("total_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("win_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("loss_trades", sa.Integer(), default=0, nullable=True),
        sa.Column("winrate", sa.Float(), default=0.0, nullable=True),
        sa.Column("profit_factor", sa.Float(), default=0.0, nullable=True),
        sa.Column("total_profit", sa.Float(), default=0.0, nullable=True),
        sa.Column("max_drawdown", sa.Float(), default=0.0, nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), default=0.0, nullable=True),
        sa.Column("sortino_ratio", sa.Float(), default=0.0, nullable=True),
        sa.Column("calmar_ratio", sa.Float(), default=0.0, nullable=True),
        sa.Column("equity_curve", postgresql.JSONB(), nullable=True),
        sa.Column("monthly_returns", postgresql.JSONB(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Market Data ────────────────────────────────────────────────────────────
    op.create_table(
        "market_data",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_data_symbol_tf_ts", "market_data", ["symbol", "timeframe", "timestamp"])

    # ── AI Analysis ────────────────────────────────────────────────────────────
    op.create_table(
        "ai_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("market_phase", sa.String(20), nullable=True),
        sa.Column("signal", sa.String(10), nullable=True),
        sa.Column("confidence", sa.Float(), default=0.0, nullable=True),
        sa.Column("indicators", postgresql.JSONB(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Telegram Messages Log ──────────────────────────────────────────────────
    op.create_table(
        "telegram_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("success", sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("telegram_messages")
    op.drop_table("ai_analysis")
    op.drop_index("ix_market_data_symbol_tf_ts", table_name="market_data")
    op.drop_table("market_data")
    op.drop_table("backtest_results")
    op.drop_table("trade_signals")
    op.drop_index("ix_trades_opened_at", table_name="trades")
    op.drop_index("ix_trades_status", table_name="trades")
    op.drop_index("ix_trades_symbol", table_name="trades")
    op.drop_table("trades")
    op.drop_table("strategies")
    op.drop_table("user_settings")
    op.drop_table("users")
