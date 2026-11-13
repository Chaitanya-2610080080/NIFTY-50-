#!/usr/bin/env python3
"""
Interactive Trading Dashboard Generator for NIFTY 50 Scalping Model
Generates a standalone, fully-featured, zero-dependency interactive dashboard
with HTML5 canvas candlestick charting, live parameter simulator, trade inspector,
and multi-stock screener.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def build_dashboard():
    base_dir = Path("C:/Users/Admin/.gemini/antigravity/scratch/nifty50_scalping")
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"
    output_nb_dir = base_dir / "output_niftybees"
    artifact_dir = Path("C:/Users/Admin/.gemini/antigravity/brain/95e9cea9-b1cc-4ed8-b61a-66d2d352f2a4")

    symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "NIFTYBEES"]
    
    market_data = {}
    screener_data = []

    for sym in symbols:
        df = pd.read_csv(data_dir / f"{sym}.csv", parse_dates=["datetime"], index_col="datetime").sort_index()
        
        # Calculate daily VWAP
        tp = (df["high"] + df["low"] + df["close"]) / 3
        dates = df.index.date
        if (df["volume"] > 0).any():
            pv = (tp * df["volume"]).groupby(dates).cumsum()
            vv = df["volume"].groupby(dates).cumsum()
            vwap = np.where(vv > 0, pv / vv, tp.groupby(dates).expanding().mean().values)
        else:
            vwap = tp.groupby(dates).expanding().mean().values

        # Calculate RSI 9
        delta = df["close"].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/9, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/9, adjust=False).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

        df["vwap"] = np.round(vwap, 2)
        df["rsi"] = np.round(rsi.fillna(50), 2)

        # Screener row based on latest bar
        last_row = df.iloc[-1]
        prev_rsi = df.iloc[-2]["rsi"] if len(df) > 1 else 50
        signal = "HOLD"
        if last_row["close"] > last_row["vwap"] and prev_rsi < 35 and last_row["rsi"] >= 35:
            signal = "BUY"
        elif last_row["close"] < last_row["vwap"] and prev_rsi > 65 and last_row["rsi"] <= 65:
            signal = "SELL"

        change_pct = ((last_row["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100) if len(df) > 1 else 0.0

        screener_data.append({
            "symbol": sym,
            "last_time": df.index[-1].strftime("%H:%M"),
            "price": float(round(last_row["close"], 2)),
            "change_pct": float(round(change_pct, 2)),
            "vwap": float(round(last_row["vwap"], 2)),
            "rsi": float(round(last_row["rsi"], 2)),
            "signal": signal
        })

        # Filter from Oct 08 for chart
        sub = df[df.index >= "2026-10-08"].copy()
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

    # Load trades
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

    print(f"Loaded {len(market_data)} symbols, {len(trades)} trades")

    # Serialize to JSON strings
    market_data_json = json.dumps(market_data)
    trades_json = json.dumps(trades)
    screener_json = json.dumps(screener_data)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NIFTY 50 Scalping Terminal — Interactive Workstation</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      background-color: #0b0f19;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      user-select: none;
    }}
    .custom-scroll::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scroll::-webkit-scrollbar-track {{
      background: #0f172a;
    }}
    .custom-scroll::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 3px;
    }}
    .custom-scroll::-webkit-scrollbar-thumb:hover {{
      background: #475569;
    }}
    .slider-thumb {{
      -webkit-appearance: none;
      appearance: none;
      height: 14px;
      width: 14px;
      border-radius: 50%;
      background: #3b82f6;
      cursor: pointer;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col p-4 space-y-4">

  <!-- Top App Navigation Bar -->
  <header class="bg-[#111827] border border-[#1f2937] rounded-xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-lg">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
        N50
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-bold text-white tracking-wide">NIFTY 50 Scalping Terminal</h1>
          <span class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            5-MIN INTRADAY
          </span>
          <span class="px-2 py-0.5 text-xs font-semibold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
            VWAP + RSI
          </span>
        </div>
        <p class="text-xs text-slate-400 mt-0.5">Real 60-Day Tick Dataset &bull; Interactive Backtest & Strategy Simulator</p>
      </div>
    </div>

    <!-- Active Stock Selector Buttons -->
    <div class="flex flex-wrap items-center gap-1.5" id="symbol-buttons">
      <!-- Populated via JS -->
    </div>
  </header>

  <!-- Main Grid: Left Workspace (Chart & Controls) & Right Workspace (Watchlist, Simulator, Trades) -->
  <div class="grid grid-cols-1 xl:grid-cols-12 gap-4 flex-1">
    
    <!-- LEFT COLUMN: Chart + Indicators HUD (8 Columns) -->
    <div class="xl:col-span-8 flex flex-col space-y-4">
      
      <!-- Chart Container Card -->
      <div class="bg-[#111827] border border-[#1f2937] rounded-xl p-4 flex flex-col shadow-lg flex-1">
        
        <!-- Chart Controls Header & HUD -->
        <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#1f2937]">
          <div class="flex items-center gap-3">
            <span class="text-xl font-bold text-white" id="hud-symbol">RELIANCE</span>
            <span class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono" id="hud-time">--:--</span>
            <span class="text-base font-semibold" id="hud-price">₹--</span>
            <span class="text-xs font-semibold" id="hud-change">--%</span>
          </div>

          <!-- OHLCV & Indicator Readout HUD -->
          <div class="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-300 bg-[#0b0f19] px-3 py-1.5 rounded-lg border border-[#1f2937]">
            <span>O: <span class="text-white" id="hud-o">--</span></span>
            <span>H: <span class="text-emerald-400" id="hud-h">--</span></span>
            <span>L: <span class="text-rose-400" id="hud-l">--</span></span>
            <span>C: <span class="text-white" id="hud-c">--</span></span>
            <span class="border-l border-slate-700 pl-2">VWAP: <span class="text-amber-400 font-semibold" id="hud-vwap">--</span></span>
            <span>RSI: <span class="text-blue-400 font-semibold" id="hud-rsi">--</span></span>
          </div>

          <!-- Chart Zoom / Navigation Buttons -->
          <div class="flex items-center gap-1.5">
            <button onclick="setZoom(40)" class="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition">40 Bars</button>
            <button onclick="setZoom(100)" class="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition">100 Bars</button>
            <button onclick="setZoom(250)" class="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition">250 Bars</button>
            <button onclick="resetZoom()" class="px-2 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 text-white font-medium transition shadow-sm">Latest</button>
          </div>
        </div>

        <!-- Interactive HTML5 Canvas Chart -->
        <div class="relative w-full mt-3 flex-1 min-h-[460px]" id="canvas-wrapper">
          <canvas id="trading-chart" class="w-full h-full cursor-crosshair rounded-lg block"></canvas>
          <div class="absolute bottom-2 left-3 pointer-events-none flex items-center gap-4 text-[11px] text-slate-400 font-sans">
            <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-amber-400 inline-block"></span> Intraday VWAP</span>
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-emerald-500 rounded-full inline-block"></span> Long Entry (▲)</span>
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-rose-500 rounded-full inline-block"></span> Short Entry (▼)</span>
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full border border-emerald-400 inline-block"></span> Take-Profit</span>
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full border border-rose-400 inline-block"></span> Stop-Loss</span>
          </div>
        </div>
      </div>

      <!-- Strategy Performance KPI Summary Strip -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Total Trades</div>
          <div class="text-xl font-bold text-white mt-1" id="kpi-trades">0</div>
          <div class="text-[11px] text-slate-500 mt-0.5" id="kpi-trades-sub">Filtered range</div>
        </div>
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Win Rate</div>
          <div class="text-xl font-bold text-amber-400 mt-1" id="kpi-winrate">0.0%</div>
          <div class="text-[11px] text-slate-500 mt-0.5" id="kpi-winrate-sub">0 Wins / 0 Losses</div>
        </div>
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Gross P&L</div>
          <div class="text-xl font-bold mt-1" id="kpi-gross">₹0</div>
          <div class="text-[11px] text-slate-500 mt-0.5">Before friction</div>
        </div>
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Friction Costs</div>
          <div class="text-xl font-bold text-rose-400 mt-1" id="kpi-costs">₹0</div>
          <div class="text-[11px] text-slate-500 mt-0.5">Slippage & Brokerage</div>
        </div>
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Net P&L</div>
          <div class="text-xl font-bold mt-1" id="kpi-net">₹0</div>
          <div class="text-[11px] text-slate-500 mt-0.5" id="kpi-net-sub">Fixed ₹1L sizing</div>
        </div>
        <div class="bg-[#111827] border border-[#1f2937] p-3 rounded-xl shadow">
          <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Profit Factor</div>
          <div class="text-xl font-bold text-blue-400 mt-1" id="kpi-pf">0.00</div>
          <div class="text-[11px] text-slate-500 mt-0.5">Gross Win / Gross Loss</div>
        </div>
      </div>
    </div>

    <!-- RIGHT COLUMN: Simulator, Screener & Trade Log (4 Columns) -->
    <div class="xl:col-span-4 flex flex-col space-y-4">
      
      <!-- Interactive Strategy Parameter Sandbox -->
      <div class="bg-[#111827] border border-[#1f2937] rounded-xl p-4 shadow-lg space-y-4">
        <div class="flex items-center justify-between border-b border-[#1f2937] pb-2.5">
          <div>
            <h2 class="text-sm font-bold text-white flex items-center gap-2">
              <span>⚙️</span> Interactive Strategy Simulator
            </h2>
            <p class="text-xs text-slate-400">Tweak rules & live backtest on current stock</p>
          </div>
          <button onclick="resetParams()" class="text-xs text-blue-400 hover:text-blue-300 font-medium">Reset</button>
        </div>

        <!-- Simulator Sliders -->
        <div class="space-y-3 text-xs">
          <div>
            <div class="flex justify-between text-slate-300 mb-1">
              <span>RSI Period:</span>
              <span class="font-mono text-blue-400 font-bold" id="val-rsi-len">9</span>
            </div>
            <input type="range" id="param-rsi-len" min="5" max="14" step="1" value="9" 
                   oninput="onParamChange()" class="w-full accent-blue-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-slate-300 mb-1">
              <span>RSI Oversold (Long Trigger):</span>
              <span class="font-mono text-emerald-400 font-bold" id="val-rsi-low">25</span>
            </div>
            <input type="range" id="param-rsi-low" min="20" max="40" step="5" value="25" 
                   oninput="onParamChange()" class="w-full accent-emerald-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-slate-300 mb-1">
              <span>Stop Loss (%):</span>
              <span class="font-mono text-rose-400 font-bold" id="val-stop-pct">0.20%</span>
            </div>
            <input type="range" id="param-stop-pct" min="0.10" max="0.80" step="0.05" value="0.20" 
                   oninput="onParamChange()" class="w-full accent-rose-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-slate-300 mb-1">
              <span>Risk:Reward Ratio (Target):</span>
              <span class="font-mono text-amber-400 font-bold" id="val-rr">1.5x</span>
            </div>
            <input type="range" id="param-rr" min="1.0" max="3.0" step="0.1" value="1.5" 
                   oninput="onParamChange()" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div class="pt-2 border-t border-[#1f2937] flex items-center justify-between">
            <label class="flex items-center gap-2 cursor-pointer text-slate-300">
              <input type="checkbox" id="param-friction" checked onchange="onParamChange()" class="accent-blue-500 rounded">
              <span>Apply Brokerage & STT (₹82/trade)</span>
            </label>
            <button onclick="runSimulation()" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium shadow-sm transition">
              Simulate ⚡
            </button>
          </div>
        </div>
      </div>

      <!-- Multi-Stock Watchlist & Screener -->
      <div class="bg-[#111827] border border-[#1f2937] rounded-xl p-4 shadow-lg flex-1 flex flex-col">
        <div class="flex items-center justify-between pb-2.5 border-b border-[#1f2937] mb-2">
          <h2 class="text-sm font-bold text-white flex items-center gap-1.5">
            <span>📡</span> Live Market Screener
          </h2>
          <span class="text-[11px] text-slate-400">Click stock to inspect</span>
        </div>
        <div class="overflow-x-auto custom-scroll flex-1">
          <table class="w-full text-left text-xs">
            <thead class="text-slate-400 uppercase text-[10px] border-b border-[#1f2937] bg-[#0b0f19]">
              <tr>
                <th class="py-2 px-2.5">Symbol</th>
                <th class="py-2 px-2">Price</th>
                <th class="py-2 px-2">VWAP</th>
                <th class="py-2 px-2">RSI</th>
                <th class="py-2 px-2 text-right">Signal</th>
              </tr>
            </thead>
            <tbody id="screener-table-body" class="divide-y divide-[#1f2937] font-mono">
              <!-- Populated via JS -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Trade History Log with Click-to-Inspect -->
      <div class="bg-[#111827] border border-[#1f2937] rounded-xl p-4 shadow-lg flex-1 flex flex-col max-h-[340px]">
        <div class="flex items-center justify-between pb-2.5 border-b border-[#1f2937] mb-2">
          <div>
            <h2 class="text-sm font-bold text-white flex items-center gap-1.5">
              <span>📋</span> Trade Execution Log
            </h2>
            <span class="text-[11px] text-slate-400">Click any trade to jump on chart</span>
          </div>
          <div class="flex items-center gap-1">
            <button onclick="filterTrades('ALL')" class="px-2 py-0.5 text-[11px] rounded bg-slate-800 text-slate-300 font-medium hover:bg-slate-700">All</button>
            <button onclick="filterTrades('WIN')" class="px-2 py-0.5 text-[11px] rounded bg-emerald-500/20 text-emerald-400 font-medium hover:bg-emerald-500/30">Wins</button>
            <button onclick="filterTrades('LOSS')" class="px-2 py-0.5 text-[11px] rounded bg-rose-500/20 text-rose-400 font-medium hover:bg-rose-500/30">Losses</button>
          </div>
        </div>
        <div class="overflow-y-auto custom-scroll flex-1">
          <table class="w-full text-left text-xs">
            <thead class="text-slate-400 uppercase text-[10px] border-b border-[#1f2937] bg-[#0b0f19] sticky top-0">
              <tr>
                <th class="py-2 px-2">Time</th>
                <th class="py-2 px-2">Side</th>
                <th class="py-2 px-2">Entry</th>
                <th class="py-2 px-2">Exit</th>
                <th class="py-2 px-2 text-right">Net P&L</th>
                <th class="py-2 px-2 text-center">Tag</th>
              </tr>
            </thead>
            <tbody id="trades-table-body" class="divide-y divide-[#1f2937] font-mono">
              <!-- Populated via JS -->
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>

  <!-- Raw Data Payload from Python -->
  <script>
    const RAW_MARKET_DATA = {market_data_json};
    const INITIAL_TRADES = {trades_json};
    const SCREENER_DATA = {screener_json};

    // Application State
    let currentSymbol = "RELIANCE";
    let activeTrades = [...INITIAL_TRADES];
    let tradeFilter = "ALL";
    let selectedTradeIndex = null;

    // Viewport / Chart State
    let visibleBarCount = 75;
    let rightOffset = 0; // 0 means stick to newest bar
    let isDragging = false;
    let dragStartX = 0;
    let dragStartOffset = 0;
    let hoverIndex = null;

    // Strategy Parameters
    let params = {{
      rsiLen: 9,
      rsiLow: 25,
      stopPct: 0.0020,
      rr: 1.5,
      friction: true
    }};

    // DOM Elements
    const canvas = document.getElementById("trading-chart");
    const ctx = canvas.getContext("2d");
    const wrapper = document.getElementById("canvas-wrapper");

    // Initialize UI
    window.addEventListener("DOMContentLoaded", () => {{
      initSymbolButtons();
      renderScreenerTable();
      initCanvasEvents();
      resizeCanvas();
      selectSymbol("RELIANCE");
      window.addEventListener("resize", () => {{
        resizeCanvas();
        drawChart();
      }});
    }});

    function initSymbolButtons() {{
      const container = document.getElementById("symbol-buttons");
      container.innerHTML = "";
      Object.keys(RAW_MARKET_DATA).forEach(sym => {{
        const btn = document.createElement("button");
        btn.id = "btn-" + sym;
        btn.className = "px-3 py-1 text-xs font-semibold rounded-lg transition border " + 
          (sym === currentSymbol 
            ? "bg-blue-600 border-blue-500 text-white shadow-sm" 
            : "bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700");
        btn.innerText = sym;
        btn.onclick = () => selectSymbol(sym);
        container.appendChild(btn);
      }});
    }}

    function selectSymbol(sym) {{
      currentSymbol = sym;
      document.querySelectorAll("#symbol-buttons button").forEach(b => {{
        if (b.id === "btn-" + sym) {{
          b.className = "px-3 py-1 text-xs font-semibold rounded-lg transition border bg-blue-600 border-blue-500 text-white shadow-sm";
        }} else {{
          b.className = "px-3 py-1 text-xs font-semibold rounded-lg transition border bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700";
        }}
      }});
      rightOffset = 0;
      selectedTradeIndex = null;
      updateHUD();
      renderTradesTable();
      updateKPISummary();
      drawChart();
    }}

    function renderScreenerTable() {{
      const tbody = document.getElementById("screener-table-body");
      tbody.innerHTML = "";
      SCREENER_DATA.forEach(row => {{
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/50 cursor-pointer transition " + (row.symbol === currentSymbol ? "bg-slate-800/60" : "");
        tr.onclick = () => selectSymbol(row.symbol);

        const changeClass = row.change_pct >= 0 ? "text-emerald-400" : "text-rose-400";
        const signalBadge = row.signal === "BUY" 
          ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">BUY</span>'
          : row.signal === "SELL"
          ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">SELL</span>'
          : '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">HOLD</span>';

        tr.innerHTML = `
          <td class="py-2 px-2.5 font-sans font-bold text-white">${{row.symbol}}</td>
          <td class="py-2 px-2 font-mono">${{row.price.toLocaleString("en-IN", {{minimumFractionDigits: 2}})}}</td>
          <td class="py-2 px-2 text-slate-400">${{row.vwap.toFixed(1)}}</td>
          <td class="py-2 px-2 text-blue-400">${{row.rsi.toFixed(1)}}</td>
          <td class="py-2 px-2 text-right">${{signalBadge}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function renderTradesTable() {{
      const tbody = document.getElementById("trades-table-body");
      tbody.innerHTML = "";
      const symbolTrades = activeTrades.filter(t => t.symbol === currentSymbol);

      let filtered = symbolTrades;
      if (tradeFilter === "WIN") filtered = symbolTrades.filter(t => t.net_pnl > 0);
      if (tradeFilter === "LOSS") filtered = symbolTrades.filter(t => t.net_pnl <= 0);

      if (filtered.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-500">No trades found for ${{currentSymbol}} with current filter.</td></tr>`;
        return;
      }}

      filtered.forEach((trade, idx) => {{
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/60 cursor-pointer transition text-slate-300";
        tr.onclick = () => jumpToTrade(trade);

        const sideBadge = trade.side === "LONG"
          ? '<span class="text-emerald-400 font-bold">LONG</span>'
          : '<span class="text-rose-400 font-bold">SHORT</span>';
        
        const pnlClass = trade.net_pnl >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
        const reasonBadge = trade.reason === "TP"
          ? '<span class="px-1 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-400">TP</span>'
          : trade.reason === "SL"
          ? '<span class="px-1 py-0.2 rounded text-[9px] bg-rose-500/20 text-rose-400">SL</span>'
          : '<span class="px-1 py-0.2 rounded text-[9px] bg-slate-800 text-slate-400">TIME</span>';

        tr.innerHTML = `
          <td class="py-2 px-2 text-[11px] text-slate-400">${{trade.entry_time.slice(5)}}</td>
          <td class="py-2 px-2">${{sideBadge}}</td>
          <td class="py-2 px-2">${{trade.entry.toFixed(1)}}</td>
          <td class="py-2 px-2">${{trade.exit.toFixed(1)}}</td>
          <td class="py-2 px-2 text-right ${{pnlClass}}">${{trade.net_pnl >= 0 ? "+" : ""}}₹${{trade.net_pnl.toFixed(0)}}</td>
          <td class="py-2 px-2 text-center">${{reasonBadge}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function filterTrades(type) {{
      tradeFilter = type;
      renderTradesTable();
    }}

    function jumpToTrade(trade) {{
      const bars = RAW_MARKET_DATA[currentSymbol];
      if (!bars) return;
      const targetTime = trade.entry_time;
      const foundIdx = bars.findIndex(b => b[0] === targetTime || b[0].startsWith(targetTime.slice(0, 16)));
      if (foundIdx !== -1) {{
        visibleBarCount = 80;
        rightOffset = Math.max(0, bars.length - 1 - foundIdx - 30);
        selectedTradeIndex = foundIdx;
        drawChart();
      }}
    }}

    function updateKPISummary() {{
      const symbolTrades = activeTrades.filter(t => t.symbol === currentSymbol);
      const totalTrades = symbolTrades.length;
      const wins = symbolTrades.filter(t => t.net_pnl > 0).length;
      const losses = totalTrades - wins;
      const winRate = totalTrades > 0 ? (wins / totalTrades * 100).toFixed(1) : "0.0";
      
      const grossPnl = symbolTrades.reduce((acc, t) => acc + t.gross_pnl, 0);
      const costs = symbolTrades.reduce((acc, t) => acc + t.costs, 0);
      const netPnl = symbolTrades.reduce((acc, t) => acc + t.net_pnl, 0);

      const grossWins = symbolTrades.filter(t => t.gross_pnl > 0).reduce((acc, t) => acc + t.gross_pnl, 0);
      const grossLosses = Math.abs(symbolTrades.filter(t => t.gross_pnl < 0).reduce((acc, t) => acc + t.gross_pnl, 0));
      const pf = grossLosses > 0 ? (grossWins / grossLosses).toFixed(2) : (grossWins > 0 ? "∞" : "0.00");

      document.getElementById("kpi-trades").innerText = totalTrades;
      document.getElementById("kpi-trades-sub").innerText = totalTrades > 0 ? `${{wins}}W / ${{losses}}L` : "No trades";

      document.getElementById("kpi-winrate").innerText = winRate + "%";
      document.getElementById("kpi-winrate-sub").innerText = `${{wins}} Won / ${{losses}} Lost`;

      const grossEl = document.getElementById("kpi-gross");
      grossEl.innerText = (grossPnl >= 0 ? "+₹" : "-₹") + Math.abs(grossPnl).toLocaleString("en-IN", {{maximumFractionDigits: 0}});
      grossEl.className = "text-xl font-bold mt-1 " + (grossPnl >= 0 ? "text-emerald-400" : "text-rose-400");

      document.getElementById("kpi-costs").innerText = "₹" + costs.toLocaleString("en-IN", {{maximumFractionDigits: 0}});

      const netEl = document.getElementById("kpi-net");
      netEl.innerText = (netPnl >= 0 ? "+₹" : "-₹") + Math.abs(netPnl).toLocaleString("en-IN", {{maximumFractionDigits: 0}});
      netEl.className = "text-xl font-bold mt-1 " + (netPnl >= 0 ? "text-emerald-400" : "text-rose-400");

      document.getElementById("kpi-pf").innerText = pf;
    }}

    function updateHUD(barIndex = null) {{
      const bars = RAW_MARKET_DATA[currentSymbol];
      if (!bars || bars.length === 0) return;

      const idx = barIndex !== null ? barIndex : bars.length - 1;
      const b = bars[idx];
      if (!b) return;

      document.getElementById("hud-symbol").innerText = currentSymbol;
      document.getElementById("hud-time").innerText = b[0];
      document.getElementById("hud-price").innerText = "₹" + b[4].toLocaleString("en-IN", {{minimumFractionDigits: 2}});
      
      const prevBar = idx > 0 ? bars[idx - 1] : b;
      const chg = ((b[4] - prevBar[4]) / prevBar[4] * 100);
      const chgEl = document.getElementById("hud-change");
      chgEl.innerText = (chg >= 0 ? "+" : "") + chg.toFixed(2) + "%";
      chgEl.className = "text-xs font-semibold " + (chg >= 0 ? "text-emerald-400" : "text-rose-400");

      document.getElementById("hud-o").innerText = b[1].toFixed(1);
      document.getElementById("hud-h").innerText = b[2].toFixed(1);
      document.getElementById("hud-l").innerText = b[3].toFixed(1);
      document.getElementById("hud-c").innerText = b[4].toFixed(1);
      document.getElementById("hud-vwap").innerText = b[6].toFixed(1);
      document.getElementById("hud-rsi").innerText = b[7].toFixed(1);
    }}

    // Canvas & Chart Rendering Logic
    function resizeCanvas() {{
      const rect = wrapper.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.scale(dpr, dpr);
    }}

    function setZoom(count) {{
      visibleBarCount = count;
      drawChart();
    }}

    function resetZoom() {{
      visibleBarCount = 75;
      rightOffset = 0;
      drawChart();
    }}

    function initCanvasEvents() {{
      wrapper.addEventListener("mousedown", (e) => {{
        isDragging = true;
        dragStartX = e.clientX;
        dragStartOffset = rightOffset;
      }});

      window.addEventListener("mouseup", () => {{
        isDragging = false;
      }});

      wrapper.addEventListener("mousemove", (e) => {{
        const rect = wrapper.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        if (isDragging) {{
          const dx = e.clientX - dragStartX;
          const bars = RAW_MARKET_DATA[currentSymbol];
          const barWidth = (rect.width - 60) / visibleBarCount;
          const shiftBars = Math.round(dx / barWidth);
          rightOffset = Math.max(0, Math.min(bars.length - visibleBarCount, dragStartOffset + shiftBars));
          drawChart();
          return;
        }}

        // Hover Crosshair
        const chartW = rect.width - 65;
        if (mouseX >= 0 && mouseX <= chartW) {{
          const bars = RAW_MARKET_DATA[currentSymbol];
          const totalBars = bars.length;
          const startIdx = Math.max(0, totalBars - visibleBarCount - rightOffset);
          const barWidth = chartW / visibleBarCount;
          const hoveredBarIdx = startIdx + Math.floor(mouseX / barWidth);
          if (hoveredBarIdx >= 0 && hoveredBarIdx < totalBars) {{
            hoverIndex = hoveredBarIdx;
            updateHUD(hoveredBarIdx);
            drawChart(mouseX, mouseY);
          }}
        }} else {{
          hoverIndex = null;
          drawChart();
        }}
      }});

      wrapper.addEventListener("mouseleave", () => {{
        hoverIndex = null;
        updateHUD();
        drawChart();
      }});

      wrapper.addEventListener("wheel", (e) => {{
        e.preventDefault();
        const delta = Math.sign(e.deltaY);
        if (delta > 0) {{
          visibleBarCount = Math.min(300, visibleBarCount + 10);
        }} else {{
          visibleBarCount = Math.max(20, visibleBarCount - 10);
        }}
        drawChart();
      }}, {{ passive: false }});
    }}

    function drawChart(mouseX = null, mouseY = null) {{
      const rect = wrapper.getBoundingClientRect();
      const W = rect.width;
      const H = rect.height;
      if (W <= 0 || H <= 0) return;

      ctx.clearRect(0, 0, W, H);

      const bars = RAW_MARKET_DATA[currentSymbol];
      if (!bars || bars.length === 0) return;

      const totalBars = bars.length;
      const startIdx = Math.max(0, totalBars - visibleBarCount - rightOffset);
      const endIdx = Math.min(totalBars, startIdx + visibleBarCount);
      const viewBars = bars.slice(startIdx, endIdx);
      const N = viewBars.length;
      if (N === 0) return;

      // Layout Geometry
      const rightPadding = 65;
      const chartW = W - rightPadding;
      const topHeight = H * 0.72;
      const bottomTop = topHeight + 20;
      const bottomHeight = H - bottomTop - 20;

      // Calculate High / Low
      let minPrice = Infinity;
      let maxPrice = -Infinity;
      let maxVol = 0;

      viewBars.forEach(b => {{
        if (b[2] > maxPrice) maxPrice = b[2];
        if (b[3] < minPrice) minPrice = b[3];
        if (b[5] > maxVol) maxVol = b[5];
      }});

      const priceRange = (maxPrice - minPrice) || 1;
      const paddedMin = minPrice - priceRange * 0.05;
      const paddedMax = maxPrice + priceRange * 0.05;
      const priceSpan = paddedMax - paddedMin;

      function yPrice(p) {{
        return topHeight - ((p - paddedMin) / priceSpan) * topHeight;
      }}

      function yRsi(rsi) {{
        return bottomTop + bottomHeight - (rsi / 100) * bottomHeight;
      }}

      // Background Grid Lines
      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 1;
      ctx.setLineDash([]);

      const gridSteps = 6;
      for (let i = 0; i <= gridSteps; i++) {{
        const p = paddedMin + (priceSpan / gridSteps) * i;
        const y = yPrice(p);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(chartW, y);
        ctx.stroke();

        ctx.fillStyle = "#64748b";
        ctx.font = "10px -apple-system, BlinkMacSystemFont, monospace";
        ctx.textAlign = "left";
        ctx.fillText(p.toFixed(1), chartW + 8, y + 3);
      }}

      // RSI Grid Lines (30, 70, 50)
      ctx.strokeStyle = "#1f2937";
      [30, 50, 70].forEach(level => {{
        const y = yRsi(level);
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.moveTo(0, y);
        ctx.lineTo(chartW, y);
        ctx.stroke();

        ctx.fillStyle = level === 50 ? "#64748b" : (level === 70 ? "#ef4444" : "#10b981");
        ctx.fillText(level.toString(), chartW + 8, y + 3);
      }});
      ctx.setLineDash([]);

      // Draw Candlesticks & Volume Bars
      const candleSlot = chartW / N;
      const candleWidth = Math.max(1, candleSlot * 0.72);

      viewBars.forEach((b, i) => {{
        const xCenter = i * candleSlot + candleSlot / 2;
        const openY = yPrice(b[1]);
        const highY = yPrice(b[2]);
        const lowY = yPrice(b[3]);
        const closeY = yPrice(b[4]);
        const isUp = b[4] >= b[1];

        // Volume Bar
        const volHeight = maxVol > 0 ? (b[5] / maxVol) * (topHeight * 0.18) : 0;
        ctx.fillStyle = isUp ? "rgba(16, 185, 129, 0.18)" : "rgba(244, 63, 94, 0.18)";
        ctx.fillRect(xCenter - candleWidth / 2, topHeight - volHeight, candleWidth, volHeight);

        // Candle Wick
        ctx.strokeStyle = isUp ? "#10b981" : "#f43f5e";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(xCenter, highY);
        ctx.lineTo(xCenter, lowY);
        ctx.stroke();

        // Candle Body
        ctx.fillStyle = isUp ? "#10b981" : "#f43f5e";
        const bodyTop = Math.min(openY, closeY);
        const bodyH = Math.max(1.5, Math.abs(closeY - openY));
        ctx.fillRect(xCenter - candleWidth / 2, bodyTop, candleWidth, bodyH);
      }});

      // Draw Intraday VWAP Curve (respect daily breaks)
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      let started = false;

      viewBars.forEach((b, i) => {{
        const xCenter = i * candleSlot + candleSlot / 2;
        const y = yPrice(b[6]);

        if (i > 0 && b[0].slice(0, 10) !== viewBars[i - 1][0].slice(0, 10)) {{
          started = false; // reset VWAP drawing across days
        }}

        if (!started) {{
          ctx.moveTo(xCenter, y);
          started = true;
        }} else {{
          ctx.lineTo(xCenter, y);
        }}
      }});
      ctx.stroke();

      // Draw RSI Oscillator Line
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      viewBars.forEach((b, i) => {{
        const xCenter = i * candleSlot + candleSlot / 2;
        const y = yRsi(b[7]);
        if (i === 0) ctx.moveTo(xCenter, y);
        else ctx.lineTo(xCenter, y);
      }});
      ctx.stroke();

      // Draw Trade Markers
      const symbolTrades = activeTrades.filter(t => t.symbol === currentSymbol);
      symbolTrades.forEach(trade => {{
        const entryIdx = viewBars.findIndex(b => b[0] === trade.entry_time || b[0].startsWith(trade.entry_time.slice(0, 16)));
        const exitIdx = viewBars.findIndex(b => b[0] === trade.exit_time || b[0].startsWith(trade.exit_time.slice(0, 16)));

        if (entryIdx !== -1) {{
          const x = entryIdx * candleSlot + candleSlot / 2;
          const isLong = trade.side === "LONG";
          const y = isLong ? yPrice(viewBars[entryIdx][3]) + 14 : yPrice(viewBars[entryIdx][2]) - 14;

          // Draw Entry Arrow
          ctx.fillStyle = isLong ? "#10b981" : "#ef4444";
          ctx.beginPath();
          if (isLong) {{
            ctx.moveTo(x, y - 8);
            ctx.lineTo(x - 6, y + 2);
            ctx.lineTo(x + 6, y + 2);
          }} else {{
            ctx.moveTo(x, y + 8);
            ctx.lineTo(x - 6, y - 2);
            ctx.lineTo(x + 6, y - 2);
          }}
          ctx.closePath();
          ctx.fill();
        }}

        if (exitIdx !== -1) {{
          const x = exitIdx * candleSlot + candleSlot / 2;
          const y = yPrice(trade.exit);

          ctx.fillStyle = trade.net_pnl >= 0 ? "#10b981" : "#ef4444";
          ctx.beginPath();
          ctx.arc(x, y, 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1;
          ctx.stroke();
        }}
      }});

      // Draw Crosshair Tooltip
      if (mouseX !== null && mouseY !== null && mouseX <= chartW) {{
        ctx.strokeStyle = "rgba(148, 163, 184, 0.4)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);

        // Vertical
        ctx.beginPath();
        ctx.moveTo(mouseX, 0);
        ctx.lineTo(mouseX, H);
        ctx.stroke();

        // Horizontal
        ctx.beginPath();
        ctx.moveTo(0, mouseY);
        ctx.lineTo(chartW, mouseY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Hover Time Label Box
        if (hoverIndex !== null && bars[hoverIndex]) {{
          const timeText = bars[hoverIndex][0];
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(mouseX - 55, H - 18, 110, 18);
          ctx.strokeStyle = "#475569";
          ctx.strokeRect(mouseX - 55, H - 18, 110, 18);
          ctx.fillStyle = "#ffffff";
          ctx.font = "10px monospace";
          ctx.textAlign = "center";
          ctx.fillText(timeText, mouseX, H - 5);
        }}
      }}
    }}

    // Parameter Sandbox & Interactive Backtesting Engine in JS
    function onParamChange() {{
      params.rsiLen = parseInt(document.getElementById("param-rsi-len").value);
      params.rsiLow = parseInt(document.getElementById("param-rsi-low").value);
      params.stopPct = parseFloat(document.getElementById("param-stop-pct").value) / 100;
      params.rr = parseFloat(document.getElementById("param-rr").value);
      params.friction = document.getElementById("param-friction").checked;

      document.getElementById("val-rsi-len").innerText = params.rsiLen;
      document.getElementById("val-rsi-low").innerText = params.rsiLow;
      document.getElementById("val-stop-pct").innerText = (params.stopPct * 100).toFixed(2) + "%";
      document.getElementById("val-rr").innerText = params.rr.toFixed(1) + "x";

      runSimulation();
    }}

    function resetParams() {{
      document.getElementById("param-rsi-len").value = 9;
      document.getElementById("param-rsi-low").value = 25;
      document.getElementById("param-stop-pct").value = 0.20;
      document.getElementById("param-rr").value = 1.5;
      document.getElementById("param-friction").checked = true;
      onParamChange();
    }}

    function runSimulation() {{
      const bars = RAW_MARKET_DATA[currentSymbol];
      if (!bars || bars.length < 50) return;

      // Recompute RSI for selected symbol with new length
      const closePrices = bars.map(b => b[4]);
      const rsiArr = computeRSI(closePrices, params.rsiLen);

      // Run Intraday Scalping Simulation
      const simulatedTrades = [];
      let inTrade = null;
      let dayTradeCount = 0;
      let currentDay = "";

      for (let i = 1; i < bars.length; i++) {{
        const b = bars[i];
        const barDate = b[0].slice(0, 10);
        const barTime = b[0].slice(11, 16);

        if (barDate !== currentDay) {{
          currentDay = barDate;
          dayTradeCount = 0;
          if (inTrade) {{
            // EOD square off
            closeSimTrade(inTrade, b, "TIME", simulatedTrades);
            inTrade = null;
          }}
        }}

        // Check active trade
        if (inTrade) {{
          const isLong = inTrade.side === "LONG";
          const high = b[2];
          const low = b[3];
          inTrade.barsHeld++;

          if (isLong) {{
            if (high >= inTrade.target) {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: inTrade.target }}, "TP", simulatedTrades);
              inTrade = null;
            }} else if (low <= inTrade.stop) {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: inTrade.stop }}, "SL", simulatedTrades);
              inTrade = null;
            }} else if (inTrade.barsHeld >= 12 || barTime >= "15:15") {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: b[4] }}, "TIME", simulatedTrades);
              inTrade = null;
            }}
          }} else {{
            if (low <= inTrade.target) {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: inTrade.target }}, "TP", simulatedTrades);
              inTrade = null;
            }} else if (high >= inTrade.stop) {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: inTrade.stop }}, "SL", simulatedTrades);
              inTrade = null;
            }} else if (inTrade.barsHeld >= 12 || barTime >= "15:15") {{
              closeSimTrade(inTrade, {{ ...b, exitPrice: b[4] }}, "TIME", simulatedTrades);
              inTrade = null;
            }}
          }}
          continue;
        }}

        // Entry Signal Check
        if (dayTradeCount >= 3 || barTime < "09:30" || barTime > "14:45") continue;

        const prevRsi = rsiArr[i - 1];
        const currRsi = rsiArr[i];
        const close = b[4];
        const vwap = b[6];

        // Long trigger: Close > VWAP & RSI crosses up through rsiLow
        if (close > vwap && prevRsi < params.rsiLow && currRsi >= params.rsiLow) {{
          const targetDist = close * (params.stopPct * params.rr);
          const stopDist = close * params.stopPct;
          inTrade = {{
            symbol: currentSymbol,
            side: "LONG",
            entryTime: b[0],
            entryPrice: close,
            qty: Math.floor(100000 / close),
            target: close + targetDist,
            stop: close - stopDist,
            barsHeld: 0
          }};
          dayTradeCount++;
        }}
        // Short trigger: Close < VWAP & RSI crosses down through (100 - rsiLow)
        else if (close < vwap && prevRsi > (100 - params.rsiLow) && currRsi <= (100 - params.rsiLow)) {{
          const targetDist = close * (params.stopPct * params.rr);
          const stopDist = close * params.stopPct;
          inTrade = {{
            symbol: currentSymbol,
            side: "SHORT",
            entryTime: b[0],
            entryPrice: close,
            qty: Math.floor(100000 / close),
            target: close - targetDist,
            stop: close + stopDist,
            barsHeld: 0
          }};
          dayTradeCount++;
        }}
      }}

      // Merge simulated trades with activeTrades
      activeTrades = activeTrades.filter(t => t.symbol !== currentSymbol).concat(simulatedTrades);
      updateKPISummary();
      renderTradesTable();
      drawChart();
    }}

    function closeSimTrade(trade, bar, reason, list) {{
      const exitPrice = bar.exitPrice || bar[4];
      const isLong = trade.side === "LONG";
      const grossPnl = isLong 
        ? (exitPrice - trade.entryPrice) * trade.qty 
        : (trade.entryPrice - exitPrice) * trade.qty;

      const buyVal = trade.entryPrice * trade.qty;
      const sellVal = exitPrice * trade.qty;
      let costs = 0;
      if (params.friction) {{
        const brok = Math.min(20, 0.0003 * buyVal) + Math.min(20, 0.0003 * sellVal);
        const stt = 0.00025 * sellVal;
        const exch = 0.0000297 * (buyVal + sellVal);
        const gst = 0.18 * (brok + exch);
        const slippage = 0.0002 * (buyVal + sellVal);
        costs = brok + stt + exch + gst + slippage;
      }}
      const netPnl = grossPnl - costs;

      list.push({{
        symbol: trade.symbol,
        date: bar[0].slice(0, 10),
        entry_time: trade.entryTime,
        exit_time: bar[0],
        side: trade.side,
        entry: trade.entryPrice,
        exit: exitPrice,
        qty: trade.qty,
        gross_pnl: grossPnl,
        costs: costs,
        net_pnl: netPnl,
        reason: reason
      }});
    }}

    function computeRSI(prices, period) {{
      const rsi = new Array(prices.length).fill(50);
      if (prices.length <= period) return rsi;

      let gain = 0;
      let loss = 0;
      for (let i = 1; i <= period; i++) {{
        const diff = prices[i] - prices[i - 1];
        if (diff >= 0) gain += diff;
        else loss -= diff;
      }}
      let avgGain = gain / period;
      let avgLoss = loss / period;

      for (let i = period + 1; i < prices.length; i++) {{
        const diff = prices[i] - prices[i - 1];
        const g = diff > 0 ? diff : 0;
        const l = diff < 0 ? -diff : 0;
        avgGain = (avgGain * (period - 1) + g) / period;
        avgLoss = (avgLoss * (period - 1) + l) / period;
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        rsi[i] = 100 - (100 / (1 + rs));
      }}
      return rsi;
    }}
  </script>
</body>
</html>
"""

    # Save to scratch directory
    scratch_dest = base_dir / "dashboard.html"
    scratch_dest.write_text(html_template, encoding="utf-8")
    print(f"Saved interactive dashboard to: {scratch_dest}")

    # Save to brain artifact directory
    artifact_dest = artifact_dir / "trading_dashboard.html"
    artifact_dest.write_text(html_template, encoding="utf-8")
    print(f"Saved artifact dashboard to: {artifact_dest}")

if __name__ == "__main__":
    build_dashboard()
