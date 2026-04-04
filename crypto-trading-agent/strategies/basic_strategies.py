"""
Basic trading strategies: momentum and arbitrage.

These strategies consume OHLCV DataFrames (columns: open, high, low, close,
volume) and return a signal string: 'buy', 'sell', or 'hold'.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Momentum strategy
# ---------------------------------------------------------------------------

def momentum_signal(
    df: pd.DataFrame,
    short_window: int = 10,
    long_window: int = 30,
) -> str:
    """Generate a trading signal based on simple moving-average crossover.

    Args:
        df: OHLCV DataFrame with at least ``long_window`` rows.
        short_window: Look-back period for the short moving average.
        long_window: Look-back period for the long moving average.

    Returns:
        ``'buy'`` when the short MA crosses above the long MA,
        ``'sell'`` when it crosses below, otherwise ``'hold'``.

    Raises:
        ValueError: If *df* does not contain a ``close`` column or has
            fewer rows than *long_window*.
    """
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain a 'close' column.")
    if len(df) < long_window:
        raise ValueError(
            f"DataFrame must have at least {long_window} rows for "
            f"long_window={long_window}."
        )

    short_rolling = df["close"].rolling(short_window).mean()
    long_rolling = df["close"].rolling(long_window).mean()

    short_ma = short_rolling.iloc[-1]
    long_ma = long_rolling.iloc[-1]
    prev_short_ma = short_rolling.iloc[-2]
    prev_long_ma = long_rolling.iloc[-2]

    if prev_short_ma <= prev_long_ma and short_ma > long_ma:
        logger.debug("Momentum: bullish crossover → buy")
        return "buy"
    if prev_short_ma >= prev_long_ma and short_ma < long_ma:
        logger.debug("Momentum: bearish crossover → sell")
        return "sell"

    logger.debug("Momentum: no crossover → hold")
    return "hold"


# ---------------------------------------------------------------------------
# Arbitrage strategy
# ---------------------------------------------------------------------------

def arbitrage_signal(
    price_exchange_a: float,
    price_exchange_b: float,
    min_spread_pct: float = 0.5,
) -> dict[str, str]:
    """Detect a cross-exchange arbitrage opportunity.

    Args:
        price_exchange_a: Current ask price on exchange A.
        price_exchange_b: Current bid price on exchange B.
        min_spread_pct: Minimum spread percentage to trigger an action.

    Returns:
        A dict ``{'exchange_a': signal, 'exchange_b': signal}`` where each
        signal is ``'buy'``, ``'sell'``, or ``'hold'``.
    """
    if price_exchange_a <= 0 or price_exchange_b <= 0:
        raise ValueError("Prices must be positive.")

    spread_pct = (
        (price_exchange_b - price_exchange_a) / price_exchange_a * 100
    )

    if spread_pct >= min_spread_pct:
        # Buy on A (cheaper), sell on B (more expensive)
        logger.debug(
            "Arbitrage: spread %.2f%% ≥ threshold → buy A / sell B",
            spread_pct,
        )
        return {"exchange_a": "buy", "exchange_b": "sell"}

    if spread_pct <= -min_spread_pct:
        logger.debug(
            "Arbitrage: spread %.2f%% ≤ -threshold → sell A / buy B",
            spread_pct,
        )
        return {"exchange_a": "sell", "exchange_b": "buy"}

    logger.debug("Arbitrage: spread %.2f%% within threshold → hold", spread_pct)
    return {"exchange_a": "hold", "exchange_b": "hold"}
