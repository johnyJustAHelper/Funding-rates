"""
=============================================================
  CRYPTO FUNDING RATES AGGREGATOR — DAY 1 SCRIPT
  Sources: Binance, Bybit, OKX
  Auth required: NONE — all public endpoints
  Personal info required: NONE
  Cost: $0
=============================================================

HOW TO RUN:
  1. Install dependencies:
       pip install requests pandas tabulate

  2. Run the script:
       python funding_rates.py

  OUTPUT:
  - Prints a live table in your terminal
  - Saves funding_rates.json  (becomes your public feed on Day 2)
  - Saves funding_rates.csv   (easy to open in Excel / Sheets)
  - Flags any extreme rates automatically
=============================================================
"""

import requests
import pandas as pd
import json
from datetime import datetime, timezone
from tabulate import tabulate

# ── CONFIG ────────────────────────────────────────────────
# Add or remove any symbols you want to track.
# These are the top perpetual futures pairs by volume.
SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "DOGE", "AVAX", "LINK", "ARB", "OP"
]

# Alert thresholds (in %)
# Rates above HIGH or below LOW are flagged automatically.
ALERT_HIGH =  0.10   # 0.10% = bullish extreme, longs paying a lot
ALERT_LOW  = -0.05   # -0.05% = bearish extreme, shorts paying


# ── FETCH: BINANCE ────────────────────────────────────────
def fetch_binance(symbols):
    """
    Endpoint: GET https://fapi.binance.com/fapi/v1/fundingRate
    Auth: None — fully public
    Rate limit: 500 requests per 5 min per IP (we use 10 calls max)
    Docs: https://developers.binance.com/docs/derivatives
    """
    results = []
    base_url = "https://fapi.binance.com/fapi/v1/fundingRate"

    for sym in symbols:
        symbol = f"{sym}USDT"
        try:
            resp = requests.get(
                base_url,
                params={"symbol": symbol, "limit": 1},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data:
                entry = data[0]
                rate = float(entry["fundingRate"]) * 100  # convert to %
                results.append({
                    "asset":    sym,
                    "exchange": "Binance",
                    "rate_%":   round(rate, 6),
                    "next_funding": datetime.fromtimestamp(
                        entry["fundingTime"] / 1000, tz=timezone.utc
                    ).strftime("%H:%M UTC"),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"  [Binance] {sym} failed: {e}")

    return results


# ── FETCH: BYBIT ──────────────────────────────────────────
def fetch_bybit(symbols):
    """
    Endpoint: GET https://api.bybit.com/v5/market/funding/history
    Auth: None — fully public market data
    Rate limit: generous, no issues at our scale
    Docs: https://bybit-exchange.github.io/docs/v5/market/history-fund-rate
    """
    results = []
    base_url = "https://api.bybit.com/v5/market/funding/history"

    for sym in symbols:
        symbol = f"{sym}USDT"
        try:
            resp = requests.get(
                base_url,
                params={"category": "linear", "symbol": symbol, "limit": 1},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("list", [])

            if items:
                rate = float(items[0]["fundingRate"]) * 100
                results.append({
                    "asset":    sym,
                    "exchange": "Bybit",
                    "rate_%":   round(rate, 6),
                    "next_funding": datetime.fromtimestamp(
                        int(items[0]["fundingRateTimestamp"]) / 1000, tz=timezone.utc
                    ).strftime("%H:%M UTC"),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"  [Bybit] {sym} failed: {e}")

    return results


# ── FETCH: OKX ────────────────────────────────────────────
def fetch_okx(symbols):
    """
    Endpoint: GET https://www.okx.com/api/v5/public/funding-rate
    Auth: None — public data endpoints explicitly require no auth
    Rate limit: 20 requests per 2 seconds (we're well within this)
    Docs: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-funding-rate
    """
    results = []
    base_url = "https://www.okx.com/api/v5/public/funding-rate"

    for sym in symbols:
        inst_id = f"{sym}-USDT-SWAP"
        try:
            resp = requests.get(
                base_url,
                params={"instId": inst_id},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])

            if items:
                rate = float(items[0]["fundingRate"]) * 100
                results.append({
                    "asset":    sym,
                    "exchange": "OKX",
                    "rate_%":   round(rate, 6),
                    "next_funding": datetime.fromtimestamp(
                        int(items[0]["fundingTime"]) / 1000, tz=timezone.utc
                    ).strftime("%H:%M UTC"),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"  [OKX] {sym} failed: {e}")

    return results


# ── ALERT LOGIC ───────────────────────────────────────────
def classify_rate(rate):
    """Turn a raw rate into a human-readable signal."""
    if rate >= ALERT_HIGH:
        return "🔴 EXTREME HIGH"   # longs paying a lot — possible top signal
    elif rate >= 0.05:
        return "🟠 HIGH"           # elevated bullish sentiment
    elif rate <= ALERT_LOW:
        return "🟢 NEGATIVE"       # shorts paying — bearish sentiment
    elif rate <= -0.01:
        return "🔵 LOW NEGATIVE"   # mildly bearish
    else:
        return "⚪ NORMAL"          # nothing interesting


# ── CROSS-EXCHANGE SPREAD ─────────────────────────────────
def add_spreads(df):
    """
    Calculate the spread between exchanges for each asset.
    A big spread = potential arbitrage or data anomaly — interesting signal.
    """
    spreads = []
    for asset in df["asset"].unique():
        asset_df = df[df["asset"] == asset]
        if len(asset_df) > 1:
            spread = round(asset_df["rate_%"].max() - asset_df["rate_%"].min(), 6)
        else:
            spread = None
        for _ in range(len(asset_df)):
            spreads.append(spread)

    # Align index before assigning
    df = df.reset_index(drop=True)
    df["spread_%"] = spreads
    return df


# ── PRINT SUMMARY ─────────────────────────────────────────
def print_summary(df):
    print("\n" + "=" * 70)
    print("  CRYPTO FUNDING RATES — LIVE SNAPSHOT")
    print(f"  Fetched at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    display = df[["asset", "exchange", "rate_%", "next_funding", "signal", "spread_%"]].copy()
    display.columns = ["Asset", "Exchange", "Rate %", "Next Funding", "Signal", "Spread %"]
    display = display.sort_values(["Asset", "Exchange"])

    print(tabulate(display, headers="keys", tablefmt="rounded_outline", showindex=False))

    # Alerts section
    alerts = df[df["signal"].str.contains("EXTREME|NEGATIVE")]
    if not alerts.empty:
        print("\n⚡ ALERTS — Rates worth watching:")
        for _, row in alerts.iterrows():
            print(f"   {row['signal']}  {row['asset']} on {row['exchange']} → {row['rate_%']}%")

    # Biggest spreads
    spread_df = df.dropna(subset=["spread_%"]).drop_duplicates("asset")
    spread_df = spread_df.sort_values("spread_%", ascending=False).head(3)
    if not spread_df.empty:
        print("\n📊 BIGGEST CROSS-EXCHANGE SPREADS (arbitrage signals):")
        for _, row in spread_df.iterrows():
            print(f"   {row['asset']}: {row['spread_%']}% spread between exchanges")

    print()


# ── SAVE OUTPUT ───────────────────────────────────────────
def save_json(df):
    """
    Saves funding_rates.json — this becomes your public feed on Day 2
    when you push it to GitHub Pages.
    """
    output = {
        "meta": {
            "description": "Crypto perpetual futures funding rates aggregated from Binance, Bybit, and OKX",
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "sources": ["Binance", "Bybit", "OKX"],
            "symbols": SYMBOLS,
            "note": "Rates shown as percentages. Updated every run."
        },
        "data": df.to_dict(orient="records")
    }
    with open("funding_rates.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("  ✅ Saved: funding_rates.json")


def save_csv(df):
    """Saves a CSV — easy to open in Google Sheets or Excel."""
    df.to_csv("funding_rates.csv", index=False)
    print("  ✅ Saved: funding_rates.csv")


# ── MAIN ──────────────────────────────────────────────────
def main():
    print("\n🔄 Fetching funding rates...")
    print("   No API keys needed. No accounts needed. Pure public data.\n")

    # Fetch from all three exchanges
    print("  Fetching Binance...")
    binance = fetch_binance(SYMBOLS)

    print("  Fetching Bybit...")
    bybit = fetch_bybit(SYMBOLS)

    print("  Fetching OKX...")
    okx = fetch_okx(SYMBOLS)

    # Combine all results
    all_data = binance + bybit + okx

    if not all_data:
        print("\n❌ No data fetched. Check your internet connection.")
        return

    # Build dataframe
    df = pd.DataFrame(all_data)

    # Add signals and spreads
    df["signal"] = df["rate_%"].apply(classify_rate)
    df = add_spreads(df)

    # Print terminal summary
    print_summary(df)

    # Save outputs
    print("💾 Saving files...")
    save_json(df)
    save_csv(df)

    print(f"\n🎯 Done. {len(df)} data points across {df['exchange'].nunique()} exchanges.")
    print("   Tomorrow (Day 2): push funding_rates.json to GitHub Pages → instant public feed.\n")


if __name__ == "__main__":
    main()
