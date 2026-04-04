"""
Backtesting framework.

Simulates a strategy on historical OHLCV data and reports performance metrics
such as total return, win rate, maximum drawdown, and Sharpe ratio.

Usage::

    from tests.backtesting import Backtester
    from strategies.basic_strategies import momentum_signal

    bt = Backtester(strategy_fn=momentum_signal, initial_capital=10_000)
    results = bt.run(df)
    bt.report(results)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Aggregated metrics from a single backtest run.

    Attributes:
        total_return_pct: Percentage return over the entire period.
        win_rate_pct: Percentage of profitable trades.
        max_drawdown_pct: Largest peak-to-trough decline (percentage).
        sharpe_ratio: Risk-adjusted return (annualised, assuming hourly bars).
        num_trades: Total number of completed round-trip trades.
        trades: DataFrame with individual trade records.
    """

    total_return_pct: float
    win_rate_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    num_trades: int
    trades: pd.DataFrame = field(repr=False)


class Backtester:
    """Event-driven backtester for a single symbol.

    Args:
        strategy_fn: Callable that accepts a ``pd.DataFrame`` slice and
            returns ``'buy'``, ``'sell'``, or ``'hold'``.  Must accept keyword
            argument *short_window* / *long_window* if they apply; simpler
            callables that only accept ``df`` are also supported.
        initial_capital: Starting capital in quote currency (e.g. USDT).
        stop_loss_pct: Percentage drop from entry that triggers an early exit.
        take_profit_pct: Percentage rise from entry that triggers an early exit.
        commission_pct: Round-trip commission percentage per trade leg
            (e.g. ``0.1`` for 0.1 %).
    """

    def __init__(
        self,
        strategy_fn: Callable[[pd.DataFrame], str],
        initial_capital: float = 10_000.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 5.0,
        commission_pct: float = 0.1,
    ) -> None:
        self.strategy_fn = strategy_fn
        self.initial_capital = initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.commission_pct = commission_pct

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, df: pd.DataFrame, warmup: int = 30) -> BacktestResult:
        """Run the backtest against *df*.

        Args:
            df: OHLCV DataFrame (must have a ``close`` column).
            warmup: Number of initial rows skipped to allow indicators
                to warm up.

        Returns:
            :class:`BacktestResult` with performance metrics.
        """
        capital = self.initial_capital
        position: Optional[float] = None  # entry price when in a trade
        position_amount: float = 0.0
        equity_curve: list[float] = [capital]
        trade_records: list[dict] = []

        for i in range(warmup, len(df)):
            window = df.iloc[: i + 1]
            close = float(df["close"].iloc[i])

            # --- Check stop-loss / take-profit if in a position ---
            if position is not None:
                change_pct = (close - position) / position * 100
                if change_pct <= -self.stop_loss_pct:
                    capital, trade_records, position, position_amount = self._close(
                        capital, position, position_amount, close, i, trade_records, "stop_loss"
                    )
                    equity_curve.append(capital)
                    continue
                if change_pct >= self.take_profit_pct:
                    capital, trade_records, position, position_amount = self._close(
                        capital, position, position_amount, close, i, trade_records, "take_profit"
                    )
                    equity_curve.append(capital)
                    continue

            # --- Strategy signal ---
            try:
                signal = self.strategy_fn(window)
            except Exception as exc:
                logger.debug("Strategy raised at index %d: %s", i, exc)
                equity_curve.append(capital)
                continue

            if signal == "buy" and position is None:
                commission = capital * (self.commission_pct / 100)
                capital -= commission
                position_amount = capital / close
                position = close
                logger.debug("BUY at %.4f (index %d)", close, i)

            elif signal == "sell" and position is not None:
                capital, trade_records, position, position_amount = self._close(
                    capital, position, position_amount, close, i, trade_records, "signal"
                )

            equity_curve.append(capital)

        # Close any remaining position at the last price
        if position is not None:
            last_price = float(df["close"].iloc[-1])
            capital, trade_records, position, position_amount = self._close(
                capital, position, position_amount, last_price, len(df) - 1,
                trade_records, "end_of_data"
            )

        return self._compute_metrics(equity_curve, trade_records)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _close(
        self,
        capital: float,
        entry: float,
        amount: float,
        exit_price: float,
        index: int,
        records: list[dict],
        reason: str,
    ) -> tuple[float, list[dict], None, float]:
        proceeds = amount * exit_price
        commission = proceeds * (self.commission_pct / 100)
        net_proceeds = proceeds - commission
        pnl = net_proceeds - capital  # capital was fully invested in this position
        records.append(
            {
                "index": index,
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl,
                "reason": reason,
            }
        )
        logger.debug(
            "CLOSE at %.4f (index %d) pnl=%.2f reason=%s",
            exit_price,
            index,
            pnl,
            reason,
        )
        return net_proceeds, records, None, 0.0

    def _compute_metrics(
        self, equity_curve: list[float], trade_records: list[dict]
    ) -> BacktestResult:
        equity = np.array(equity_curve)
        total_return = (equity[-1] / equity[0] - 1) * 100

        # Win rate
        trades_df = pd.DataFrame(trade_records)
        if not trades_df.empty:
            wins = (trades_df["pnl"] > 0).sum()
            win_rate = wins / len(trades_df) * 100
        else:
            win_rate = 0.0

        # Maximum drawdown
        rolling_max = np.maximum.accumulate(equity)
        drawdowns = (equity - rolling_max) / rolling_max * 100
        max_drawdown = float(drawdowns.min())

        # Sharpe ratio (annualised, hourly bars → 8760 bars/year)
        returns = np.diff(equity) / equity[:-1]
        if returns.std() != 0:
            sharpe = float(returns.mean() / returns.std() * np.sqrt(8760))
        else:
            sharpe = 0.0

        return BacktestResult(
            total_return_pct=round(total_return, 4),
            win_rate_pct=round(win_rate, 2),
            max_drawdown_pct=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe, 4),
            num_trades=len(trade_records),
            trades=trades_df,
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @staticmethod
    def report(result: BacktestResult) -> None:
        """Print a human-readable backtest summary to stdout."""
        print("=" * 40)
        print("Backtest Results")
        print("=" * 40)
        print(f"  Total return : {result.total_return_pct:.2f}%")
        print(f"  Win rate     : {result.win_rate_pct:.2f}%")
        print(f"  Max drawdown : {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe ratio : {result.sharpe_ratio:.4f}")
        print(f"  # trades     : {result.num_trades}")
        print("=" * 40)
