"""
AI-based trading strategy using an LSTM neural network for price prediction.

The model is trained on a sequence of closing prices and predicts whether the
next close will be higher (buy) or lower (sell) than the current close.

Dependencies: numpy, pandas, scikit-learn, tensorflow (or torch).
The implementation uses TensorFlow/Keras but falls back gracefully if the
library is unavailable (useful for environments that only have lightweight
deps installed).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Optional heavy dependency – import lazily so the module is still importable
# in environments without TensorFlow.
try:
    from tensorflow import keras  # type: ignore
    from tensorflow.keras import layers  # type: ignore

    _TF_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TF_AVAILABLE = False
    logger.warning(
        "TensorFlow is not installed. AI strategy will use a simple "
        "heuristic fallback."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_sequences(
    data: np.ndarray, look_back: int
) -> tuple[np.ndarray, np.ndarray]:
    """Slide a window over *data* to build (X, y) training pairs.

    Args:
        data: 1-D array of normalised closing prices.
        look_back: Number of time steps used as input features.

    Returns:
        Tuple of ``(X, y)`` arrays with shapes
        ``(n_samples, look_back, 1)`` and ``(n_samples,)`` respectively.
    """
    X, y = [], []
    for i in range(look_back, len(data)):
        X.append(data[i - look_back : i])
        y.append(1 if data[i] > data[i - 1] else 0)
    return np.array(X)[..., np.newaxis], np.array(y)


def _build_lstm_model(look_back: int, units: int = 64) -> "keras.Model":
    """Build and compile a small LSTM classifier.

    Args:
        look_back: Input sequence length.
        units: Number of LSTM units.

    Returns:
        Compiled Keras model.
    """
    model = keras.Sequential(
        [
            layers.LSTM(units, input_shape=(look_back, 1), return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(32, activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LSTMStrategy:
    """LSTM-based price-direction predictor.

    Usage::

        strategy = LSTMStrategy(look_back=20)
        strategy.train(df)
        signal = strategy.predict(df)

    Args:
        look_back: Number of historic candles used as input features.
        lstm_units: Number of LSTM units in the hidden layer.
        epochs: Training epochs.
        batch_size: Mini-batch size for training.
        model_path: Optional file path to save / load model weights.
    """

    def __init__(
        self,
        look_back: int = 20,
        lstm_units: int = 64,
        epochs: int = 20,
        batch_size: int = 32,
        model_path: Optional[str] = None,
    ) -> None:
        self.look_back = look_back
        self.lstm_units = lstm_units
        self.epochs = epochs
        self.batch_size = batch_size
        self.model_path = model_path
        self._model: Optional[object] = None
        self._price_min: float = 0.0
        self._price_max: float = 1.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalise(self, series: pd.Series) -> np.ndarray:
        """Min-max normalise *series* using the training range."""
        return (series.values - self._price_min) / max(
            self._price_max - self._price_min, 1e-8
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, df: pd.DataFrame) -> None:
        """Train the LSTM model on historical closing prices.

        Args:
            df: OHLCV DataFrame with a ``close`` column.  Must contain at
                least ``look_back + 1`` rows.

        Raises:
            RuntimeError: If TensorFlow is not available.
            ValueError: If *df* has too few rows.
        """
        if not _TF_AVAILABLE:
            raise RuntimeError(
                "TensorFlow is required for LSTM training. "
                "Install it with: pip install tensorflow"
            )

        if len(df) < self.look_back + 1:
            raise ValueError(
                f"Need at least {self.look_back + 1} rows to train."
            )

        close = df["close"]
        self._price_min = float(close.min())
        self._price_max = float(close.max())

        normalised = self._normalise(close)
        X, y = _create_sequences(normalised, self.look_back)

        model = _build_lstm_model(self.look_back, self.lstm_units)
        model.fit(
            X,
            y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.1,
            verbose=0,
        )
        self._model = model

        if self.model_path:
            model.save(self.model_path)
            logger.info("Model saved to %s", self.model_path)

    def load(self) -> None:
        """Load a previously saved model from *model_path*.

        Raises:
            RuntimeError: If TensorFlow is not available.
            FileNotFoundError: If *model_path* does not exist.
        """
        if not _TF_AVAILABLE:
            raise RuntimeError("TensorFlow is required to load a model.")
        if not self.model_path or not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}"
            )
        self._model = keras.models.load_model(self.model_path)
        logger.info("Model loaded from %s", self.model_path)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, df: pd.DataFrame, threshold: float = 0.55) -> str:
        """Predict the next price direction.

        If TensorFlow is unavailable the method falls back to a simple
        momentum heuristic (last close vs. rolling mean).

        Args:
            df: OHLCV DataFrame.  The last ``look_back`` rows are used as
                the prediction window.
            threshold: Probability threshold above which a 'buy' is issued.

        Returns:
            ``'buy'``, ``'sell'``, or ``'hold'``.
        """
        if not _TF_AVAILABLE or self._model is None:
            return self._heuristic_predict(df)

        if len(df) < self.look_back:
            logger.warning(
                "Not enough data for LSTM prediction; using heuristic."
            )
            return self._heuristic_predict(df)

        normalised = self._normalise(df["close"])
        window = normalised[-self.look_back :][np.newaxis, :, np.newaxis]
        prob: float = float(self._model.predict(window, verbose=0)[0][0])

        logger.debug("LSTM probability: %.4f", prob)
        if prob > threshold:
            return "buy"
        if prob < 1 - threshold:
            return "sell"
        return "hold"

    def _heuristic_predict(self, df: pd.DataFrame) -> str:
        """Simple fallback heuristic when LSTM is unavailable."""
        if len(df) < 2:
            return "hold"
        last_close = df["close"].iloc[-1]
        tail_size = min(len(df), self.look_back)
        mean_close = df["close"].tail(tail_size).mean()
        if last_close > mean_close * 1.01:
            return "buy"
        if last_close < mean_close * 0.99:
            return "sell"
        return "hold"
