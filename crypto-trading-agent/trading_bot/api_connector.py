"""
Exchange API connector built on top of the ``ccxt`` library.

Provides a thin wrapper that:
- Initialises an exchange from ``config.json`` credentials.
- Fetches OHLCV (candlestick) data as a pandas DataFrame.
- Retrieves real-time ticker prices.
- Places market/limit orders.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import pandas as pd

try:
    import ccxt  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ccxt is required. Install it with: pip install ccxt"
    ) from exc

logger = logging.getLogger(__name__)


class APIConnector:
    """Wraps a ``ccxt`` exchange object with convenience methods.

    Configuration priority:
    1. Constructor arguments.
    2. Environment variables ``EXCHANGE_API_KEY`` / ``EXCHANGE_API_SECRET``.
    3. Values from ``config.json`` passed via *config*.

    Args:
        exchange_id: ccxt exchange identifier, e.g. ``'binance'``.
        api_key: Public API key.
        api_secret: Private API secret.
        sandbox: When ``True``, use the exchange sandbox / testnet.
        config: Optional dict with extra exchange options (e.g. ``password``
            for OKX).  Values from this dict are merged into the ccxt options.
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
        config: Optional[dict] = None,
    ) -> None:
        self.exchange_id = exchange_id

        resolved_key = (
            api_key
            or os.getenv("EXCHANGE_API_KEY", "")
        )
        resolved_secret = (
            api_secret
            or os.getenv("EXCHANGE_API_SECRET", "")
        )

        options: dict = {
            "apiKey": resolved_key,
            "secret": resolved_secret,
            "enableRateLimit": True,
        }
        if config:
            options.update(config)

        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(
                f"Exchange '{exchange_id}' is not supported by ccxt."
            )

        self._exchange: ccxt.Exchange = exchange_class(options)

        if sandbox:
            self._exchange.set_sandbox_mode(True)
            logger.info("Sandbox mode enabled for %s", exchange_id)

        logger.info("APIConnector initialised for %s", exchange_id)

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair, e.g. ``'BTC/USDT'``.
            timeframe: Candle timeframe supported by the exchange (``'1m'``,
                ``'5m'``, ``'1h'``, ``'1d'``, …).
            limit: Maximum number of candles to retrieve.
            since: Optional start timestamp in milliseconds.

        Returns:
            DataFrame with columns ``timestamp``, ``open``, ``high``,
            ``low``, ``close``, ``volume`` and the timestamp as the index.
        """
        logger.debug(
            "Fetching %d %s candles for %s", limit, timeframe, symbol
        )
        raw = self._exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, limit=limit, since=since
        )
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def fetch_ticker(self, symbol: str) -> dict:
        """Return the current ticker for *symbol*.

        Args:
            symbol: Trading pair, e.g. ``'ETH/USDT'``.

        Returns:
            ccxt ticker dict containing ``last``, ``bid``, ``ask``, etc.
        """
        return self._exchange.fetch_ticker(symbol)

    def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Return the current order book for *symbol*.

        Args:
            symbol: Trading pair.
            limit: Depth of the order book (number of price levels).

        Returns:
            Dict with ``bids`` and ``asks`` lists.
        """
        return self._exchange.fetch_order_book(symbol, limit=limit)

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    def place_market_order(
        self, symbol: str, side: str, amount: float
    ) -> dict:
        """Place a market order.

        Args:
            symbol: Trading pair.
            side: ``'buy'`` or ``'sell'``.
            amount: Quantity of the base currency.

        Returns:
            ccxt order response dict.
        """
        logger.info(
            "Placing market %s order: %s × %f", side, symbol, amount
        )
        return self._exchange.create_market_order(symbol, side, amount)

    def place_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> dict:
        """Place a limit order.

        Args:
            symbol: Trading pair.
            side: ``'buy'`` or ``'sell'``.
            amount: Quantity of the base currency.
            price: Limit price.

        Returns:
            ccxt order response dict.
        """
        logger.info(
            "Placing limit %s order: %s × %f @ %f", side, symbol, amount, price
        )
        return self._exchange.create_limit_order(symbol, side, amount, price)

    def cancel_order(self, order_id: str, symbol: str) -> dict:
        """Cancel an open order.

        Args:
            order_id: Exchange order ID.
            symbol: Trading pair (required by some exchanges).

        Returns:
            ccxt cancellation response dict.
        """
        logger.info("Cancelling order %s for %s", order_id, symbol)
        return self._exchange.cancel_order(order_id, symbol)

    def fetch_balance(self) -> dict:
        """Return the current account balance."""
        return self._exchange.fetch_balance()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def sleep(self, seconds: float) -> None:
        """Respect rate limits by sleeping for *seconds*."""
        time.sleep(seconds)
