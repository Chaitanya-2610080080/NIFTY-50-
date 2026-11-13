#!/usr/bin/env python3
"""
Compiles template.html into index.html and dashboard.html with real market data.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def compile():
    base_dir = Path("c:/Users/Admin/.gemini/antigravity/scratch/nifty50_scalping")
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"
    output_nb_dir = base_dir / "output_niftybees"
    artifact_dir = Path("C:/Users/Admin/.gemini/antigravity/brain/f42ca97e-0197-45ed-a504-5d55308bfae7")

    symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "NIFTY50", "NIFTYBEES"]
    
    market_data = {}
    screener_data = []

    print("Reading and processing market datasets...")
    for sym in symbols:
        csv_file = data_dir / f"{sym}.csv"
        if not csv_file.exists():
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
            vwap = tp.groupby(dates).expanding().mean().values

        # Wilder's RSI (period 9)
        delta = df["close"].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/9, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/9, adjust=False).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

        df["vwap"] = np.round(vwap, 2)
        df["rsi"] = np.round(rsi.fillna(50), 2)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row
        
        signal = "HOLD"
        signal_type = "NEUTRAL"
        if last_row["close"] > last_row["vwap"] and prev_row["rsi"] < 35 and last_row["rsi"] >= 35:
            signal = "BUY"
            signal_type = "BULLISH"
        elif last_row["close"] < last_row["vwap"] and prev_row["rsi"] > 65 and last_row["rsi"] <= 65:
            signal = "SELL"
            signal_type = "BEARISH"

        change_pct = ((last_row["close"] - prev_row["close"]) / prev_row["close"] * 100) if len(df) > 1 else 0.0
        vwap_dist = ((last_row["close"] - last_row["vwap"]) / last_row["vwap"] * 100) if last_row["vwap"] > 0 else 0.0

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
            "vwap_dist": float(round(vwap_dist, 2)),
            "rsi": float(round(last_row["rsi"], 2)),
            "signal": signal,
            "signal_type": signal_type
        })

        # Chart bars (from 2026-09-15 onwards ~ 40+ sessions)
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

    # Baseline trades
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

    print(f"Loaded {len(market_data)} symbols, {len(trades)} baseline trades.")

    template_file = base_dir / "template.html"
    template_content = template_file.read_text(encoding="utf-8")

    market_data_str = json.dumps(market_data)
    trades_str = json.dumps(trades)
    screener_str = json.dumps(screener_data)

    compiled = template_content.replace("__MARKET_DATA_JSON__", market_data_str)
    compiled = compiled.replace("__TRADES_JSON__", trades_str)
    compiled = compiled.replace("__SCREENER_JSON__", screener_str)

    # Save to scratch directory
    scratch_index = base_dir / "index.html"
    scratch_dash = base_dir / "dashboard.html"
    scratch_index.write_text(compiled, encoding="utf-8")
    scratch_dash.write_text(compiled, encoding="utf-8")
    print(f"Successfully generated: {scratch_index}")
    print(f"Successfully generated: {scratch_dash}")

    # Save to artifact directory
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_index = artifact_dir / "index.html"
    artifact_index.write_text(compiled, encoding="utf-8")
    print(f"Successfully generated artifact: {artifact_index}")

if __name__ == "__main__":
    compile()
