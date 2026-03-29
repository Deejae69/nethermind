"""
Entry point for the AI-powered cryptocurrency trading bot.

Configuration is loaded from ``config.json`` (or environment variables).
Run in dry-run mode by default; set ``"dry_run": false`` in config to
enable live trading.

Usage:
    python main.py
    python main.py --config path/to/config.json
    python main.py --backtest
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging setup (before importing project modules so they inherit the config)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("crypto_bot.main")

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from trading_bot.api_connector import APIConnector
from trading_bot.risk_manager import RiskParameters
from trading_bot.trade_executor import TradeExecutor
from strategies.basic_strategies import momentum_signal
from strategies.ai_strategy import LSTMStrategy
from tests.backtesting import Backtester

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(config_path: str | Path = _DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load configuration from a JSON file, falling back to env variables.

    Args:
        config_path: Path to ``config.json``.

    Returns:
        Configuration dict.
    """
    cfg: dict[str, Any] = {}

    if os.path.exists(config_path):
        with open(config_path) as fh:
            cfg = json.load(fh)
        logger.info("Loaded config from %s", config_path)
    else:
        logger.warning(
            "config.json not found at %s – relying on environment variables.",
            config_path,
        )

    # Environment variables override file values
    if os.getenv("EXCHANGE_ID"):
        cfg["exchange"] = os.getenv("EXCHANGE_ID")
    if os.getenv("EXCHANGE_API_KEY"):
        cfg["api_key"] = os.getenv("EXCHANGE_API_KEY")
    if os.getenv("EXCHANGE_API_SECRET"):
        cfg["api_secret"] = os.getenv("EXCHANGE_API_SECRET")

    return cfg


# ---------------------------------------------------------------------------
# Backtest mode
# ---------------------------------------------------------------------------

def run_backtest(cfg: dict[str, Any]) -> None:
    """Run a momentum-strategy backtest on the bundled CSV sample data."""
    import pandas as pd

    data_path = Path(__file__).parent / "data" / "market_data.csv"
    if not data_path.exists():
        logger.error("Market data not found at %s", data_path)
        sys.exit(1)

    df = pd.read_csv(data_path, parse_dates=["timestamp"], index_col="timestamp")
    logger.info("Loaded %d rows from %s", len(df), data_path)

    short_w = cfg.get("short_window", 10)
    long_w = cfg.get("long_window", 30)

    def _strategy(df_slice):
        return momentum_signal(df_slice, short_window=short_w, long_window=long_w)

    bt = Backtester(
        strategy_fn=_strategy,
        initial_capital=cfg.get("initial_capital", 10_000.0),
        stop_loss_pct=cfg.get("stop_loss_pct", 2.0),
        take_profit_pct=cfg.get("take_profit_pct", 5.0),
        commission_pct=cfg.get("commission_pct", 0.1),
    )
    results = bt.run(df, warmup=long_w)
    Backtester.report(results)


# ---------------------------------------------------------------------------
# Live / paper trading mode
# ---------------------------------------------------------------------------

class _MomentumWrapper:
    """Thin wrapper so the momentum function conforms to the strategy protocol."""

    def __init__(self, short_window: int, long_window: int) -> None:
        self._short = short_window
        self._long = long_window

    def predict(self, df) -> str:
        return momentum_signal(df, short_window=self._short, long_window=self._long)


def run_live(cfg: dict[str, Any]) -> None:
    """Start the live (or paper) trading loop."""
    connector = APIConnector(
        exchange_id=cfg.get("exchange", "binance"),
        api_key=cfg.get("api_key", ""),
        api_secret=cfg.get("api_secret", ""),
        sandbox=cfg.get("sandbox", True),
    )

    risk_params = RiskParameters(
        stop_loss_pct=cfg.get("stop_loss_pct", 2.0),
        take_profit_pct=cfg.get("take_profit_pct", 5.0),
        max_position_pct=cfg.get("max_position_pct", 10.0),
        leverage=cfg.get("leverage", 1.0),
    )

    strategy_name = cfg.get("strategy", "momentum")
    if strategy_name == "lstm":
        strategy = LSTMStrategy(
            look_back=cfg.get("look_back", 20),
            epochs=cfg.get("lstm_epochs", 20),
        )
        logger.info(
            "LSTM strategy selected – pre-training on recent data …"
        )
        df_init = connector.fetch_ohlcv(
            cfg.get("symbol", "BTC/USDT"),
            timeframe=cfg.get("timeframe", "1h"),
            limit=cfg.get("lstm_pretrain_candles", 500),
        )
        strategy.train(df_init)
    else:
        short_w = cfg.get("short_window", 10)
        long_w = cfg.get("long_window", 30)
        strategy = _MomentumWrapper(short_window=short_w, long_window=long_w)

    executor = TradeExecutor(
        connector=connector,
        strategy=strategy,
        risk_params=risk_params,
        symbol=cfg.get("symbol", "BTC/USDT"),
        timeframe=cfg.get("timeframe", "1h"),
        candle_limit=cfg.get("candle_limit", 100),
        dry_run=cfg.get("dry_run", True),
    )

    interval = cfg.get("poll_interval_seconds", 60)
    logger.info(
        "Trading loop started (symbol=%s, interval=%ds, dry_run=%s)",
        cfg.get("symbol", "BTC/USDT"),
        interval,
        cfg.get("dry_run", True),
    )

    while True:
        try:
            action = executor.run_once()
            logger.info("Iteration completed – action: %s", action)
        except KeyboardInterrupt:
            logger.info("Interrupted by user – shutting down.")
            break
        except Exception as exc:
            logger.error("Unexpected error: %s", exc, exc_info=True)

        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-powered cryptocurrency trading bot"
    )
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG_PATH),
        help="Path to config.json (default: config.json in project root)",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest on bundled sample data and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    if args.backtest:
        run_backtest(cfg)
    else:
        run_live(cfg)


if __name__ == "__main__":
    main()
