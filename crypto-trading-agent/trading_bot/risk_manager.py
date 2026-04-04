"""
Risk management: stop-loss, take-profit, and position sizing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Container for user-defined risk settings.

    Attributes:
        stop_loss_pct: Maximum allowable loss as a percentage of the entry
            price before a position is automatically closed (e.g. ``2.0``
            means 2 %).
        take_profit_pct: Target profit as a percentage of the entry price
            at which a position is closed (e.g. ``5.0`` means 5 %).
        max_position_pct: Maximum fraction of total portfolio value that
            may be allocated to a single position (0–100).
        leverage: Multiplier applied to the nominal position size.  Use
            ``1.0`` for spot / no leverage.
        max_open_positions: Maximum number of simultaneously open positions.
    """

    stop_loss_pct: float = 2.0
    take_profit_pct: float = 5.0
    max_position_pct: float = 10.0
    leverage: float = 1.0
    max_open_positions: int = 5


@dataclass
class Position:
    """Represents an open trading position.

    Attributes:
        symbol: Trading pair, e.g. ``'BTC/USDT'``.
        side: ``'long'`` or ``'short'``.
        entry_price: Price at which the position was opened.
        amount: Base-currency quantity.
        stop_loss_price: Price at which a stop-loss order triggers.
        take_profit_price: Price at which a take-profit order triggers.
    """

    symbol: str
    side: str
    entry_price: float
    amount: float
    stop_loss_price: float = field(init=False)
    take_profit_price: float = field(init=False)
    _params: RiskParameters = field(repr=False, compare=False, default_factory=RiskParameters)

    def __post_init__(self) -> None:
        self.stop_loss_price = _compute_stop_loss(
            self.entry_price, self.side, self._params.stop_loss_pct
        )
        self.take_profit_price = _compute_take_profit(
            self.entry_price, self.side, self._params.take_profit_pct
        )


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

def _compute_stop_loss(entry: float, side: str, pct: float) -> float:
    """Return the stop-loss trigger price."""
    if side == "long":
        return entry * (1 - pct / 100)
    return entry * (1 + pct / 100)


def _compute_take_profit(entry: float, side: str, pct: float) -> float:
    """Return the take-profit trigger price."""
    if side == "long":
        return entry * (1 + pct / 100)
    return entry * (1 - pct / 100)


def compute_position_size(
    portfolio_value: float,
    params: RiskParameters,
    entry_price: float,
) -> float:
    """Calculate the base-currency position size.

    Args:
        portfolio_value: Total portfolio value in quote currency (e.g. USDT).
        params: Risk parameters for this trade.
        entry_price: Entry price of the base asset.

    Returns:
        Position size in base currency units, adjusted for leverage.

    Raises:
        ValueError: If *entry_price* is not positive.
    """
    if entry_price <= 0:
        raise ValueError("entry_price must be positive.")

    allocated_quote = portfolio_value * (params.max_position_pct / 100)
    base_amount = (allocated_quote * params.leverage) / entry_price
    logger.debug(
        "Position size: %.6f (allocated %.2f USDT, leverage %.1f×)",
        base_amount,
        allocated_quote,
        params.leverage,
    )
    return base_amount


# ---------------------------------------------------------------------------
# RiskManager class
# ---------------------------------------------------------------------------

class RiskManager:
    """Manages open positions and enforces risk rules.

    Args:
        params: :class:`RiskParameters` governing stop/take-profit levels
            and sizing constraints.
    """

    def __init__(self, params: Optional[RiskParameters] = None) -> None:
        self.params = params or RiskParameters()
        self._positions: dict[str, Position] = {}

    # ------------------------------------------------------------------
    # Position tracking
    # ------------------------------------------------------------------

    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        portfolio_value: float,
    ) -> Position:
        """Register a new open position.

        Args:
            symbol: Trading pair.
            side: ``'long'`` or ``'short'``.
            entry_price: Fill price.
            portfolio_value: Current total portfolio value in quote currency.

        Returns:
            The created :class:`Position`.

        Raises:
            RuntimeError: If the maximum number of open positions is reached.
            ValueError: If a position for *symbol* is already open.
        """
        if symbol in self._positions:
            raise ValueError(f"Position for {symbol} is already open.")

        if len(self._positions) >= self.params.max_open_positions:
            raise RuntimeError(
                f"Maximum open positions ({self.params.max_open_positions}) reached."
            )

        amount = compute_position_size(portfolio_value, self.params, entry_price)
        pos = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            amount=amount,
            _params=self.params,
        )
        self._positions[symbol] = pos
        logger.info(
            "Opened %s position for %s: entry=%.4f, SL=%.4f, TP=%.4f, amount=%.6f",
            side,
            symbol,
            entry_price,
            pos.stop_loss_price,
            pos.take_profit_price,
            amount,
        )
        return pos

    def close_position(self, symbol: str) -> Optional[Position]:
        """Remove and return the open position for *symbol*."""
        pos = self._positions.pop(symbol, None)
        if pos:
            logger.info("Closed position for %s", symbol)
        return pos

    # ------------------------------------------------------------------
    # Exit-signal evaluation
    # ------------------------------------------------------------------

    def evaluate(self, symbol: str, current_price: float) -> str:
        """Check whether a stop-loss or take-profit has been triggered.

        Args:
            symbol: Trading pair to evaluate.
            current_price: Latest market price.

        Returns:
            ``'stop_loss'``, ``'take_profit'``, or ``'hold'``.
        """
        pos = self._positions.get(symbol)
        if pos is None:
            return "hold"

        if pos.side == "long":
            if current_price <= pos.stop_loss_price:
                logger.warning(
                    "Stop-loss triggered for %s at %.4f", symbol, current_price
                )
                return "stop_loss"
            if current_price >= pos.take_profit_price:
                logger.info(
                    "Take-profit triggered for %s at %.4f", symbol, current_price
                )
                return "take_profit"
        else:  # short
            if current_price >= pos.stop_loss_price:
                logger.warning(
                    "Stop-loss triggered for %s (short) at %.4f",
                    symbol,
                    current_price,
                )
                return "stop_loss"
            if current_price <= pos.take_profit_price:
                logger.info(
                    "Take-profit triggered for %s (short) at %.4f",
                    symbol,
                    current_price,
                )
                return "take_profit"

        return "hold"

    @property
    def open_positions(self) -> dict[str, Position]:
        """Read-only view of current open positions."""
        return dict(self._positions)
