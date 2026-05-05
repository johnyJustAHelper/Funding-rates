# Funding Rates Tracker 


I got tired of checking Binance, Bybit and OKX separately every time I wanted to see funding rates. So I built this.

It pulls live perpetual futures funding rates across all three exchanges every hour and dumps everything into a clean JSON feed. That's it. No fluff.

---

## What it tracks

- **BTC, ETH, SOL, BNB, XRP, DOGE, AVAX, LINK, ARB, OP**
- Funding rate per exchange
- Cross-exchange spread (useful for spotting anomalies)
- Automatic flags for extreme rates

---

## Live data feed

The JSON feed updates every hour automatically:

```
https://YOUR-USERNAME.github.io/funding-rates/funding_rates.json
```

Free to use. No API key needed to read it.

---

## Why funding rates matter

Funding rates are the periodic payments between long and short traders in perpetual futures markets. When rates are high and positive, longs are paying shorts — a sign the market is heavily bullish and potentially overheated. When rates go negative, shorts are paying longs — the market is leaning bearish.

Tracking them across multiple exchanges at once gives a cleaner picture than looking at just one.

---

## How it works

A Python script runs on a cron schedule via GitHub Actions. It hits the public API endpoints on Binance, Bybit and OKX — no authentication required, all public data — aggregates everything into a single JSON file and pushes it to GitHub Pages.

Zero server cost. Zero maintenance. Runs itself.

---

## Data sources

| Exchange | Endpoint | Auth |
|----------|----------|------|
| Binance | `/fapi/v1/fundingRate` | None |
| Bybit | `/v5/market/funding/history` | None |
| OKX | `/api/v5/public/funding-rate` | None |

---

## Run it yourself

```bash
pip install requests pandas tabulate
python funding_rates.py
```

No accounts. No API keys. No cost.

---

Built for personal use. Figured someone else might find it useful.
