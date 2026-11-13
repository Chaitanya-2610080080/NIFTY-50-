#!/usr/bin/env python3
"""
NIFTY 50 Two-Indicator 5-Minute Scalping Model (VWAP + RSI)
AstraQuant X-2026 | Problem 15
Production-ready quantitative trading model with walk-forward validation & live signal scanning.
"""

import sys
import argparse
import itertools
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Default Strategy Configuration
DEFAULT_CFG = dict(
    rsi_len=7,
    rsi_low=35,               # long trigger: RSI crosses UP through this
    rsi_high=65,              # short trigger: RSI crosses DOWN through this
    stop_pct=0.0030,          # 0.30% stop-loss
    target_pct=0.0060,        # 0.60% target  -> risk:reward = 1:2
    max_hold_bars=12,         # time stop (12 x 5min = 1 hour)
    no_entry_before="09:30",  # skip noisy opening 15 minutes
    no_entry_after="14:45",
    max_trades_per_day=3,     # per stock
    daily_loss_limit=1500,    # Rs per stock per day, stop trading after this
    square_off="15:15",
    capital_per_trade=100_000,# Rs per trade
    initial_capital=1_000_000,# for Sharpe / drawdown %
    slippage_pct=0.0001,      # 0.01% per side
)

DEFAULT_SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN"]
GRID_PARAMS = dict(
    rsi_len=[5, 7, 9],
    rsi_low=[25, 30, 35, 40],
    stop_pct=[0.002, 0.003, 0.004],
    rr=[1.5, 2.0, 3.0]
)


def load_csv(sym: str, data_dir: Path) -> pd.DataFrame:
    csv_path = data_dir / f"{sym}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["datetime"], index_col="datetime")
    return df[["open", "high", "low", "close", "volume"]].sort_index()


def load_yf(sym: str) -> pd.DataFrame:
    import yfinance as yf
    if sym in ["NIFTY50", "NIFTY_50", "NIFTY", "^NSEI"]:
        ticker = "^NSEI"
    elif sym.startswith("^") or sym.endswith(".NS"):
        ticker = sym
    else:
        ticker = f"{sym}.NS"

    df = yf.download(ticker, period="60d", interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0.0
    return df[["open", "high", "low", "close", "volume"]].sort_index()


def get_data(sym: str, data_dir: Path, use_yf: bool = True) -> pd.DataFrame:
    csv_path = data_dir / f"{sym}.csv"
    if csv_path.exists():
        return load_csv(sym, data_dir)
    if use_yf:
        try:
            return load_yf(sym)
        except Exception as e:
            print(f"Warning: Failed to fetch live data for {sym}: {e}", file=sys.stderr)
    raise RuntimeError(f"Could not load data for symbol {sym}")


def add_indicators(df: pd.DataFrame, rsi_len: int) -> pd.DataFrame:
    df = df.copy()
    df["date"] = df.index.date
    # Indicator 1: Intraday VWAP (resets daily)
    tp = (df.high + df.low + df.close) / 3
    if (df.volume > 0).any():
        pv = (tp * df.volume).groupby(df["date"]).cumsum()
        vv = df.volume.groupby(df["date"]).cumsum()
        df["vwap"] = np.where(vv > 0, pv / vv, tp.groupby(df["date"]).expanding().mean().values)
    else:
        df["vwap"] = tp.groupby(df["date"]).expanding().mean()

    # Indicator 2: RSI with Wilder smoothing
    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / rsi_len, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / rsi_len, adjust=False).mean()
    df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return df


def add_signals(df: pd.DataFrame, c: dict) -> pd.DataFrame:
    prev = df.rsi.shift(1)
    long_ = (df.close > df.vwap) & (prev < c["rsi_low"]) & (df.rsi >= c["rsi_low"])
    short_ = (df.close < df.vwap) & (prev > c["rsi_high"]) & (df.rsi <= c["rsi_high"])
    df["signal"] = np.where(long_, 1, np.where(short_, -1, 0))
    return df


def charges(buy_val: float, sell_val: float) -> float:
    brokerage = min(20.0, 0.0003 * buy_val) + min(20.0, 0.0003 * sell_val)
    stt = 0.00025 * sell_val
    exch = 0.0000297 * (buy_val + sell_val)
    sebi = 0.000001 * (buy_val + sell_val)
    stamp = 0.00003 * buy_val
    gst = 0.18 * (brokerage + exch + sebi)
    return brokerage + stt + exch + sebi + stamp + gst


def backtest(df: pd.DataFrame, sym: str, c: dict) -> pd.DataFrame:
    trades = []
    for day, g in df.groupby("date"):
        o, h, l, cl = g.open.values, g.high.values, g.low.values, g.close.values
        sig, times, idx = g.signal.values, g.index.strftime("%H:%M").values, g.index
        n, j = len(g), 0
        day_trades, day_pnl = 0, 0.0
        while j < n - 1:
            if (sig[j] == 0 or times[j] > c["no_entry_after"] or times[j] < c["no_entry_before"]
                    or day_trades >= c["max_trades_per_day"] or day_pnl <= -c["daily_loss_limit"]):
                j += 1
                continue
            side = int(sig[j])
            entry_i = j + 1
            entry = o[entry_i] * (1 + c["slippage_pct"] * side)
            sl = entry * (1 - side * c["stop_pct"])
            tp = entry * (1 + side * c["target_pct"])
            exit_px, reason, k = None, None, entry_i
            for k in range(entry_i, n):
                hit_sl = l[k] <= sl if side == 1 else h[k] >= sl
                hit_tp = h[k] >= tp if side == 1 else l[k] <= tp
                if hit_sl:
                    exit_px, reason = sl, "SL"; break
                if hit_tp:
                    exit_px, reason = tp, "TP"; break
                if times[k] >= c["square_off"] or k == n - 1:
                    exit_px, reason = cl[k], "EOD"; break
                if k - entry_i + 1 >= c["max_hold_bars"]:
                    exit_px, reason = cl[k], "TIME"; break
            exit_px *= (1 - c["slippage_pct"] * side)
            qty = max(int(c["capital_per_trade"] / entry), 1)
            gross = side * (exit_px - entry) * qty
            buy_val = (entry if side == 1 else exit_px) * qty
            sell_val = (exit_px if side == 1 else entry) * qty
            cost = charges(buy_val, sell_val)
            trades.append(dict(symbol=sym, date=day, entry_time=idx[entry_i], exit_time=idx[k],
                               side="LONG" if side == 1 else "SHORT", entry=entry, exit=exit_px,
                               qty=qty, gross_pnl=gross, costs=cost, net_pnl=gross - cost, reason=reason))
            day_trades += 1
            day_pnl += gross - cost
            j = k + 1
    return pd.DataFrame(trades)


def metrics(tr: pd.DataFrame, c: dict) -> dict:
    if tr.empty:
        return {"trades": 0, "net_pnl": 0.0, "win_rate_%": 0.0, "sharpe": 0.0, "max_drawdown_%": 0.0}
    wins, losses = tr[tr.net_pnl > 0], tr[tr.net_pnl <= 0]
    daily = tr.groupby("date").net_pnl.sum()
    daily_ret = daily / c["initial_capital"]
    sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(252) if daily_ret.std() > 0 else 0.0
    eq = tr.sort_values("exit_time").net_pnl.cumsum()
    dd = eq - eq.cummax().clip(lower=0)
    avg_w = wins.net_pnl.mean() if len(wins) else 0.0
    avg_l = abs(losses.net_pnl.mean()) if len(losses) else 0.0
    return {
        "trades": len(tr),
        "gross_pnl": round(float(tr.gross_pnl.sum()), 2),
        "total_costs": round(float(tr.costs.sum()), 2),
        "net_pnl": round(float(tr.net_pnl.sum()), 2),
        "win_rate_%": round(float(100 * len(wins) / len(tr)), 2),
        "avg_win": round(float(avg_w), 2),
        "avg_loss": round(float(-avg_l), 2) if avg_l else 0.0,
        "risk_reward": round(float(avg_w / avg_l), 2) if avg_l else 0.0,
        "profit_factor": round(float(wins.net_pnl.sum() / abs(losses.net_pnl.sum())), 2) if len(losses) and losses.net_pnl.sum() else 0.0,
        "sharpe": round(float(sharpe), 2),
        "max_drawdown_Rs": round(float(dd.min()), 2),
        "max_drawdown_%": round(float(100 * dd.min() / c["initial_capital"]), 2),
    }


def make_cfg(base_cfg: dict, rsi_len: int, rsi_low: int, stop_pct: float, rr: float) -> dict:
    return {
        **base_cfg,
        "rsi_len": int(rsi_len),
        "rsi_low": int(rsi_low),
        "rsi_high": int(100 - rsi_low),
        "stop_pct": float(stop_pct),
        "target_pct": float(stop_pct * rr)
    }


def run_all(raw_data: dict, cfg: dict, day_filter: set) -> pd.DataFrame:
    out = []
    for sym, r in raw_data.items():
        df = add_signals(add_indicators(r, cfg["rsi_len"]), cfg)
        df = df[df.date.isin(day_filter)]
        res = backtest(df, sym, cfg)
        if not res.empty:
            out.append(res)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def plot_equity_and_drawdown(tr: pd.DataFrame, out_path: Path):
    if tr.empty:
        return
    t = tr.sort_values("exit_time")
    eq = t.net_pnl.cumsum().values
    dd = eq - np.maximum.accumulate(np.maximum(eq, 0))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    a1.plot(eq, color="#1f77b4", lw=1.5)
    a1.set_title("NIFTY 50 5-Min Model: Cumulative Net P&L (Rs)")
    a1.grid(True, linestyle="--", alpha=0.5)
    a2.fill_between(range(len(dd)), dd, color="#d62728", alpha=0.4)
    a2.plot(dd, color="#d62728", lw=1.0)
    a2.set_title("Drawdown Curve (Rs)")
    a2.set_xlabel("Completed Trades")
    a2.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    plt.close()


def scan_current_signal(sym: str, raw_df: pd.DataFrame, cfg: dict) -> dict:
    df = add_signals(add_indicators(raw_df, cfg["rsi_len"]), cfg)
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2] if len(df) > 1 else last_row
    last_time = df.index[-1]

    action = "HOLD"
    entry_price = float(last_row.close)
    sl = 0.0
    tp = 0.0
    if last_row.signal == 1:
        action = "BUY (LONG)"
        sl = entry_price * (1 - cfg["stop_pct"])
        tp = entry_price * (1 + cfg["target_pct"])
    elif last_row.signal == -1:
        action = "SELL (SHORT)"
        sl = entry_price * (1 + cfg["stop_pct"])
        tp = entry_price * (1 - cfg["target_pct"])

    return {
        "symbol": sym,
        "last_bar_time": str(last_time),
        "close": round(float(last_row.close), 2),
        "vwap": round(float(last_row.vwap), 2),
        "rsi": round(float(last_row.rsi), 2),
        "prev_rsi": round(float(prev_row.rsi), 2),
        "action": action,
        "stop_loss": round(sl, 2) if sl else "N/A",
        "target": round(tp, 2) if tp else "N/A",
    }


def main():
    parser = argparse.ArgumentParser(description="NIFTY 50 Scalping Model")
    parser.add_argument("--mode", choices=["train", "test", "full", "scan"], default="full")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out-dir", default="output")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Loading NIFTY 50 5-minute data for symbols: {args.symbols}...")
    raw = {}
    for s in args.symbols:
        try:
            df = get_data(s, data_dir)
            raw[s] = df
            print(f"  [OK] {s}: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        except Exception as e:
            print(f"  [ERR] {s}: {e}", file=sys.stderr)

    if not raw:
        print("Error: No data loaded. Exiting.", file=sys.stderr)
        sys.exit(1)

    if args.mode == "scan":
        print("\n================ LIVE 5-MINUTE SIGNAL SCAN ================")
        scan_results = []
        for s, df in raw.items():
            sig = scan_current_signal(s, df, DEFAULT_CFG)
            scan_results.append(sig)
        scan_df = pd.DataFrame(scan_results)
        print(scan_df.to_string(index=False))
        scan_df.to_csv(out_dir / "latest_signals.csv", index=False)
        return

    # Train / Test walk-forward split
    all_days = sorted({d for r in raw.values() for d in r.index.date})
    cut = int(len(all_days) * 0.6)
    train_days = set(all_days[:cut])
    test_days = set(all_days[cut:])
    print(f"\nTotal Trading Sessions: {len(all_days)}")
    print(f"In-Sample (Train) Sessions: {len(train_days)} | Out-Of-Sample (Test) Sessions: {len(test_days)}")

    # 1. Grid Search Optimization on TRAIN
    print("\nRunning Grid Search Optimization on TRAIN period...")
    grid_rows = []
    min_trades = 15 if len(args.symbols) <= 2 else 30
    for combo in itertools.product(*GRID_PARAMS.values()):
        p = dict(zip(GRID_PARAMS, combo))
        cfg_i = make_cfg(DEFAULT_CFG, **p)
        tr = run_all(raw, cfg_i, train_days)
        m = metrics(tr, DEFAULT_CFG)
        if m.get("trades", 0) >= min_trades:
            grid_rows.append({**p, **m})

    if not grid_rows:
        for combo in itertools.product(*GRID_PARAMS.values()):
            p = dict(zip(GRID_PARAMS, combo))
            cfg_i = make_cfg(DEFAULT_CFG, **p)
            tr = run_all(raw, cfg_i, train_days)
            m = metrics(tr, DEFAULT_CFG)
            if m.get("trades", 0) > 0:
                grid_rows.append({**p, **m})

    grid_df = pd.DataFrame(grid_rows).sort_values("net_pnl", ascending=False)
    grid_df.to_csv(out_dir / "grid_search_train.csv", index=False)

    best_p = grid_df.iloc[0][list(GRID_PARAMS)].to_dict()
    best_cfg = make_cfg(DEFAULT_CFG, **best_p)
    print("\nBest Parameters found on TRAIN:")
    for k, v in best_p.items():
        print(f"  {k}: {v}")

    # 2. Run Train vs Test Backtests
    tr_train = run_all(raw, best_cfg, train_days)
    tr_test = run_all(raw, best_cfg, test_days)

    m_train = metrics(tr_train, DEFAULT_CFG)
    m_test = metrics(tr_test, DEFAULT_CFG)

    comparison = pd.DataFrame({"IN-SAMPLE (Train)": m_train, "OUT-OF-SAMPLE (Test)": m_test})
    print("\n================ PERFORMANCE COMPARISON ================")
    print(comparison)
    comparison.to_csv(out_dir / "performance_comparison.csv")

    # 3. Per-Symbol Breakdown on Test
    per_stock = []
    for s in args.symbols:
        s_tr = tr_test[tr_test.symbol == s] if not tr_test.empty else pd.DataFrame()
        sm = metrics(s_tr, DEFAULT_CFG)
        sm["symbol"] = s
        per_stock.append(sm)
    per_stock_df = pd.DataFrame(per_stock).set_index("symbol")
    print("\n================ OUT-OF-SAMPLE PER-SYMBOL RESULTS ================")
    print(per_stock_df[["trades", "net_pnl", "win_rate_%", "risk_reward", "sharpe", "max_drawdown_%"]])
    per_stock_df.to_csv(out_dir / "per_symbol_test.csv")

    # 4. Save Trades and Plot Equity & Signals
    if not tr_test.empty:
        tr_test.to_csv(out_dir / "trades_test.csv", index=False)
        plot_equity_and_drawdown(tr_test, out_dir / "equity_curve_test.png")
        s0 = tr_test.iloc[0]
        df0 = add_signals(add_indicators(raw[s0.symbol], best_cfg["rsi_len"]), best_cfg)
        g = df0[df0.date == s0.date]
        t_day = tr_test[(tr_test.symbol == s0.symbol) & (tr_test.date == s0.date)]
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        a1.plot(g.index, g.close, label="Close", lw=1.2, color="#1f77b4")
        a1.plot(g.index, g.vwap, label="VWAP", lw=1.2, ls="--", color="#ff7f0e")
        for _, r in t_day.iterrows():
            up = r.side == "LONG"
            a1.scatter(r.entry_time, r.entry, marker="^" if up else "v", c="green" if up else "red", s=110, zorder=5)
            a1.scatter(r.exit_time, r.exit, marker="x", c="black", s=70, zorder=5)
        a1.set_title(f"{s0.symbol} {s0.date} | ^ Long Entry, v Short Entry, x Exit")
        a1.legend()
        a1.grid(True, linestyle="--", alpha=0.5)
        a2.plot(g.index, g.rsi, color="purple")
        a2.axhline(best_cfg["rsi_low"], color="g", linestyle=":")
        a2.axhline(best_cfg["rsi_high"], color="r", linestyle=":")
        a2.set_ylabel(f"RSI({best_cfg['rsi_len']})")
        a2.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(out_dir / "signals.png", dpi=130)
        plt.close()

        print(f"\nTest trades saved to: {out_dir / 'trades_test.csv'}")
        print(f"Equity curve saved to: {out_dir / 'equity_curve_test.png'}")
        print(f"Signal chart saved to: {out_dir / 'signals.png'}")
        print("\nExit Reason Breakdown:")
        print(tr_test.reason.value_counts())

    # 5. Output Current Market Signal Scan
    print("\n================ CURRENT LIVE SIGNAL SCAN ================")
    latest_signals = [scan_current_signal(s, raw[s], best_cfg) for s in args.symbols]
    latest_df = pd.DataFrame(latest_signals)
    print(latest_df.to_string(index=False))
    latest_df.to_csv(out_dir / "latest_signals.csv", index=False)
    print(f"\nModel execution complete. All artifacts saved to '{out_dir}/'.")


if __name__ == "__main__":
    main()
