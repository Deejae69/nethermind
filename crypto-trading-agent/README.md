# AI-Powered Cryptocurrency Trading Bot

A modular, extensible Python framework for automated cryptocurrency trading using
classic quantitative strategies and AI/ML models (LSTM neural networks).

---

## Table of Contents
1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Requirements](#requirements)
4. [Setup](#setup)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Backtesting](#backtesting)
8. [Extending the Bot](#extending-the-bot)
9. [Disclaimer](#disclaimer)

---

## Features

| Category | Details |
|---|---|
| **Data collection** | Fetch live and historical OHLCV data from 100+ exchanges via [`ccxt`](https://github.com/ccxt/ccxt) |
| **Strategies** | Momentum (SMA crossover), Cross-exchange arbitrage, LSTM price-direction prediction |
| **Risk management** | Configurable stop-loss, take-profit, position sizing, and leverage |
| **Trade execution** | Market and limit orders; dry-run (paper trading) mode built-in |
| **Backtesting** | Event-driven simulator with total return, win rate, max drawdown, and Sharpe ratio |
| **Logging** | Structured console logging + CSV trade history in `data/trade_log.csv` |

---

## Project Structure

```
crypto-trading-agent/
├── data/
│   └── market_data.csv       # Sample / downloaded OHLCV data
├── strategies/
│   ├── basic_strategies.py   # Momentum and arbitrage signal generators
│   └── ai_strategy.py        # LSTM-based price-direction predictor
├── trading_bot/
│   ├── api_connector.py      # ccxt exchange wrapper
│   ├── trade_executor.py     # Main trading loop
│   └── risk_manager.py       # Stop-loss, take-profit, position sizing
├── tests/
│   └── backtesting.py        # Historical simulation framework
├── config.json               # Bot configuration (copy and edit)
├── requirements.txt          # Python dependencies
└── main.py                   # Entry point
```

---

## Requirements

- Python **3.10+**
- A supported exchange account with API credentials (Binance, Coinbase, etc.)
- (Optional) TensorFlow ≥ 2.16 for the LSTM strategy

---

## Setup

```bash
# 1. Navigate to the project directory
cd crypto-trading-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install TensorFlow for LSTM support
pip install tensorflow
```

---

## Configuration

Edit **`config.json`** in the project root (or point to a different file with `--config`).
Sensitive values (API keys) can alternatively be provided via **environment variables**,
which take precedence over the file.

| Key | Environment variable | Default | Description |
|---|---|---|---|
| `exchange` | `EXCHANGE_ID` | `"binance"` | ccxt exchange ID |
| `api_key` | `EXCHANGE_API_KEY` | `""` | Exchange public API key |
| `api_secret` | `EXCHANGE_API_SECRET` | `""` | Exchange private API secret |
| `sandbox` | — | `true` | Use exchange testnet / sandbox |
| `symbol` | — | `"BTC/USDT"` | Trading pair |
| `timeframe` | — | `"1h"` | Candle timeframe |
| `strategy` | — | `"momentum"` | `"momentum"` or `"lstm"` |
| `dry_run` | — | `true` | Log trades without executing them |
| `stop_loss_pct` | — | `2.0` | Stop-loss threshold (%) |
| `take_profit_pct` | — | `5.0` | Take-profit threshold (%) |
| `max_position_pct` | — | `10.0` | Max portfolio % per position |
| `leverage` | — | `1.0` | Position leverage multiplier |
| `poll_interval_seconds` | — | `60` | Seconds between loop iterations |

> **Security**: Never commit `config.json` with real API keys.  Use environment
> variables or a secrets manager in production.

---

## Usage

### Paper trading (default)

```bash
python main.py
```

The bot runs in dry-run mode by default – it logs every intended trade to the
console and to `data/trade_log.csv` without placing real orders.

### Live trading

Set `"dry_run": false` in `config.json` **and** provide valid API credentials,
then run:

```bash
python main.py
```

### Custom config file

```bash
python main.py --config /path/to/my_config.json
```

---

## Backtesting

Run the built-in backtest against the sample OHLCV data:

```bash
python main.py --backtest
```

Example output:

```
========================================
Backtest Results
========================================
  Total return :  3.42%
  Win rate     : 55.00%
  Max drawdown : -1.87%
  Sharpe ratio :  0.8231
  # trades     : 20
========================================
```

You can feed your own data by replacing `data/market_data.csv` with any CSV
that has the columns `timestamp, open, high, low, close, volume`.

---

## Extending the Bot

### Add a new strategy

1. Create a callable in `strategies/` that accepts a `pd.DataFrame` and returns
   `'buy'`, `'sell'`, or `'hold'`.
2. Wrap it in a class with a `predict(df) -> str` method.
3. Instantiate it in `main.py` and pass it to `TradeExecutor`.

### Add a new exchange

`ccxt` supports 100+ exchanges out of the box.  Change `"exchange"` in
`config.json` to any valid ccxt exchange ID (e.g. `"kraken"`, `"okx"`).

---

## Disclaimer

> **This software is provided for educational purposes only.**
> Cryptocurrency trading involves significant financial risk.  Past performance
> of a backtested strategy does not guarantee future results.  Never trade with
> funds you cannot afford to lose.  Always test thoroughly in sandbox/paper mode
> before deploying with real capital.  The authors accept no responsibility for
> financial losses arising from use of this software.
