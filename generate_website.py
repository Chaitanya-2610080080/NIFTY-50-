#!/usr/bin/env python3
"""
Comprehensive Website Generator for NIFTY 50 Intraday Scalping Model (VWAP + RSI)
AstraQuant X-2026 | Problem 15
Generates a standalone, zero-dependency, ultra-responsive interactive web application.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def generate():
    base_dir = Path("c:/Users/Admin/.gemini/antigravity/scratch/nifty50_scalping")
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"
    output_nb_dir = base_dir / "output_niftybees"
    artifact_dir = Path("C:/Users/Admin/.gemini/antigravity/brain/f42ca97e-0197-45ed-a504-5d55308bfae7")

    symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "NIFTY50", "NIFTYBEES"]
    
    market_data = {}
    screener_data = []

    print("Processing market datasets...")
    for sym in symbols:
        csv_file = data_dir / f"{sym}.csv"
        if not csv_file.exists():
            print(f"Warning: {csv_file} does not exist, skipping")
            continue
        
        df = pd.read_csv(csv_file, parse_dates=["datetime"], index_col="datetime").sort_index()
        
        # Calculate daily VWAP
        tp = (df["high"] + df["low"] + df["close"]) / 3
        dates = df.index.date
        if (df["volume"] > 0).any():
            pv = (tp * df["volume"]).groupby(dates).cumsum()
            vv = df["volume"].groupby(dates).cumsum()
            vwap = np.where(vv > 0, pv / vv, tp.groupby(dates).expanding().mean().values)
        else:
            # Index feed with 0 volume: use TWAP fallback
            vwap = tp.groupby(dates).expanding().mean().values

        # Calculate Wilder's RSI (period 9 as standard default)
        delta = df["close"].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/9, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/9, adjust=False).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

        df["vwap"] = np.round(vwap, 2)
        df["rsi"] = np.round(rsi.fillna(50), 2)

        # Screener row based on latest bar
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row
        
        # Signal evaluation
        signal = "HOLD"
        signal_type = "NEUTRAL"
        if last_row["close"] > last_row["vwap"] and prev_row["rsi"] < 35 and last_row["rsi"] >= 35:
            signal = "BUY"
            signal_type = "BULLISH"
        elif last_row["close"] < last_row["vwap"] and prev_row["rsi"] > 65 and last_row["rsi"] <= 65:
            signal = "SELL"
            signal_type = "BEARISH"

        change_pct = ((last_row["close"] - prev_row["close"]) / prev_row["close"] * 100) if len(df) > 1 else 0.0
        vwap_dist_pct = ((last_row["close"] - last_row["vwap"]) / last_row["vwap"] * 100) if last_row["vwap"] > 0 else 0.0

        # 1-day high/low
        today = df.index[-1].date()
        today_df = df[df.index.date == today]
        day_high = float(today_df["high"].max()) if not today_df.empty else float(last_row["high"])
        day_low = float(today_df["low"].min()) if not today_df.empty else float(last_row["low"])
        day_vol = int(today_df["volume"].sum()) if not today_df.empty else int(last_row["volume"])

        screener_data.append({
            "symbol": sym,
            "last_time": df.index[-1].strftime("%Y-%m-%d %H:%M"),
            "price": float(round(last_row["close"], 2)),
            "open": float(round(last_row["open"], 2)),
            "high": float(round(day_high, 2)),
            "low": float(round(day_low, 2)),
            "volume": day_vol,
            "change_pct": float(round(change_pct, 2)),
            "vwap": float(round(last_row["vwap"], 2)),
            "vwap_dist": float(round(vwap_dist_pct, 2)),
            "rsi": float(round(last_row["rsi"], 2)),
            "signal": signal,
            "signal_type": signal_type
        })

        # Keep recent trading sessions for ultra-crisp responsive charting (from 2026-09-15 onwards ~ 40+ sessions)
        sub = df[df.index >= "2026-09-15"].copy()
        if len(sub) < 500:
            sub = df.iloc[-1500:].copy()

        bars = []
        for dt, r in sub.iterrows():
            bars.append([
                dt.strftime("%Y-%m-%d %H:%M"),
                float(round(r["open"], 2)),
                float(round(r["high"], 2)),
                float(round(r["low"], 2)),
                float(round(r["close"], 2)),
                int(r["volume"]),
                float(round(r["vwap"], 2)),
                float(round(r["rsi"], 2))
            ])
        market_data[sym] = bars
        print(f"Loaded {sym}: {len(bars)} bars")

    # Load baseline trades
    trades = []
    trades_stock_path = output_dir / "trades_test.csv"
    if trades_stock_path.exists():
        tdf = pd.read_csv(trades_stock_path)
        for _, r in tdf.iterrows():
            trades.append({
                "symbol": str(r["symbol"]),
                "date": str(r["date"]),
                "entry_time": str(r["entry_time"])[:16],
                "exit_time": str(r["exit_time"])[:16],
                "side": str(r["side"]),
                "entry": float(round(r["entry"], 2)),
                "exit": float(round(r["exit"], 2)),
                "qty": int(r["qty"]),
                "gross_pnl": float(round(r["gross_pnl"], 2)),
                "costs": float(round(r["costs"], 2)),
                "net_pnl": float(round(r["net_pnl"], 2)),
                "reason": str(r["reason"])
            })

    trades_nb_path = output_nb_dir / "trades_test.csv"
    if trades_nb_path.exists():
        tdf_nb = pd.read_csv(trades_nb_path)
        for _, r in tdf_nb.iterrows():
            trades.append({
                "symbol": "NIFTYBEES",
                "date": str(r["date"]),
                "entry_time": str(r["entry_time"])[:16],
                "exit_time": str(r["exit_time"])[:16],
                "side": str(r["side"]),
                "entry": float(round(r["entry"], 2)),
                "exit": float(round(r["exit"], 2)),
                "qty": int(r["qty"]),
                "gross_pnl": float(round(r["gross_pnl"], 2)),
                "costs": float(round(r["costs"], 2)),
                "net_pnl": float(round(r["net_pnl"], 2)),
                "reason": str(r["reason"])
            })

    print(f"Total market symbols: {len(market_data)}, Total trades: {len(trades)}")

    # Write serialized payload to a separate data file or embed directly
    with open(base_dir / "market_data.json", "w", encoding="utf-8") as f:
        json.dump({"market_data": market_data, "trades": trades, "screener": screener_data}, f)
    print("Exported market_data.json")

if __name__ == "__main__":
    generate()
