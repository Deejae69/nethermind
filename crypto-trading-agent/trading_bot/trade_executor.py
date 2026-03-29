"""
Automated trade executor.

Combines the API connector, a strategy, and the risk manager to form the
core trading loop.  Each call to :meth:`TradeExecutor.run_once` fetches
the latest market data, evaluates the active strategy, checks open-position
risk limits, and places orders accordingly.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from trading_bot.api_connector import APIConnector
from trading_bot.risk_manager import RiskManager, RiskParameters

logger = logging.getLogger(__name__)

_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "trade_log.csv")
_LOG_HEADERS = [
    "timestamp",
    "symbol",
    "action",
    "price",
    "amount",
    "order_id",
    "note",
]


def _append_trade_log(row: dict) -> None:
    """Append a single trade record to the CSV log file."""
    write_header = not os.path.exists(_LOG_FILE)
    with open(_LOG_FILE, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_LOG_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


class TradeExecutor:
    """Orchestrates strategy evaluation and order execution.

    Args:
        connector: Initialised :class:`~trading_bot.api_connector.APIConnector`.
        strategy: Any object with a ``predict(df) -> str`` method.
        risk_params: Optional risk configuration; defaults to
            :class:`~trading_bot.risk_manager.RiskParameters` defaults.
        symbol: Trading pair to operate on.
        timeframe: Candle timeframe for data fetching.
        candle_limit: Number of candles to fetch per iteration.
        dry_run: When ``True``, log intended actions without placing real orders.
    """

    def __init__(
        self,
        connector: APIConnector,
        strategy,
        risk_params: Optional[RiskParameters] = None,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        candle_limit: int = 100,
        dry_run: bool = True,
    ) -> None:
        self.connector = connector
        self.strategy = strategy
        self.risk_manager = RiskManager(risk_params or RiskParameters())
        self.symbol = symbol
        self.timeframe = timeframe
        self.candle_limit = candle_limit
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Core loop step
    # ------------------------------------------------------------------

    def run_once(self) -> str:
        """Execute a single iteration of the trading loop.

        Steps:
        1. Fetch OHLCV data.
        2. Check existing positions against stop-loss / take-profit.
        3. Ask the strategy for a signal.
        4. Place or skip orders depending on the signal and dry_run flag.

        Returns:
            The action taken: ``'buy'``, ``'sell'``, ``'hold'``,
            ``'stop_loss'``, or ``'take_profit'``.
        """
        df = self.connector.fetch_ohlcv(
            self.symbol, self.timeframe, self.candle_limit
        )
        current_price = float(df["close"].iloc[-1])
        logger.info("%s current price: %.4f", self.symbol, current_price)

        # --- Check exit conditions for open positions ---
        exit_signal = self.risk_manager.evaluate(self.symbol, current_price)
        if exit_signal in ("stop_loss", "take_profit"):
            pos = self.risk_manager.close_position(self.symbol)
            self._execute("sell", current_price, pos.amount if pos else 0.0, exit_signal)
            return exit_signal

        # --- Strategy signal ---
        signal = self.strategy.predict(df)
        logger.info("Strategy signal for %s: %s", self.symbol, signal)

        if signal == "buy" and self.symbol not in self.risk_manager.open_positions:
            balance = self.connector.fetch_balance()
            portfolio_value = float(
                balance.get("total", {}).get("USDT", 0)
            )
            if portfolio_value <= 0:
                logger.warning("No USDT balance available; skipping buy.")
                return "hold"

            pos = self.risk_manager.open_position(
                self.symbol, "long", current_price, portfolio_value
            )
            self._execute("buy", current_price, pos.amount, "strategy_signal")

        elif signal == "sell" and self.symbol in self.risk_manager.open_positions:
            pos = self.risk_manager.close_position(self.symbol)
            self._execute("sell", current_price, pos.amount if pos else 0.0, "strategy_signal")

        return signal

    # ------------------------------------------------------------------
    # Order placement helper
    # ------------------------------------------------------------------

    def _execute(
        self, side: str, price: float, amount: float, note: str = ""
    ) -> Optional[dict]:
        """Place a market order (or log it in dry-run mode).

        Args:
            side: ``'buy'`` or ``'sell'``.
            price: Current market price (used for logging; actual fill may differ).
            amount: Quantity in base currency.
            note: Free-text annotation stored in the trade log.

        Returns:
            ccxt order dict, or ``None`` in dry-run mode.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_row = {
            "timestamp": timestamp,
            "symbol": self.symbol,
            "action": side,
            "price": price,
            "amount": amount,
            "order_id": "",
            "note": note,
        }

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would %s %.6f %s @ ~%.4f (%s)",
                side,
                amount,
                self.symbol,
                price,
                note,
            )
            log_row["note"] = f"[dry_run] {note}"
            _append_trade_log(log_row)
            return None

        try:
            order = self.connector.place_market_order(self.symbol, side, amount)
            log_row["order_id"] = order.get("id", "")
            logger.info(
                "Order placed: %s %s id=%s", side, self.symbol, log_row["order_id"]
            )
            _append_trade_log(log_row)
            return order
        except Exception as exc:
            logger.error("Order failed: %s", exc)
            log_row["note"] = f"ERROR: {exc}"
            _append_trade_log(log_row)
            return None
