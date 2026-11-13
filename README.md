# Two-Indicator Scalping Strategy for NIFTY 50 (VWAP + RSI)
**AstraQuant X-2026 | Problem 15**

## Project Structure
```text
nifty50_scalping/
├── scalping_vwap_rsi_notebook.ipynb   # Updated notebook configured for real 5m NIFTY 50 data
├── README.md                          # Project documentation and setup guide
└── data/                              # Real 5-minute OHLCV datasets (IST: 09:15 - 15:30)
    ├── RELIANCE.csv                   # 4,341 rows
    ├── HDFCBANK.csv                   # 4,340 rows
    ├── ICICIBANK.csv                  # 4,328 rows
    ├── INFY.csv                       # 4,334 rows
    ├── TCS.csv                        # 4,330 rows
    ├── SBIN.csv                       # 4,339 rows
    ├── NIFTY50.csv                    # 4,441 rows (^NSEI index 5m bars)
    └── NIFTYBEES.csv                  # 4,441 rows (Nifty 50 ETF with full traded volume)
```

## Key Updates Made
1. **Replaced Synthetic Demo Data**:
   - Downloaded actual, up-to-date 5-minute intraday OHLCV bars covering the full 60-day window (~40+ trading sessions).
   - Saved cleanly formatted CSV files (`datetime,open,high,low,close,volume`) with timestamps localized to IST (`Asia/Kolkata`).
2. **Automated Live Data Refresh**:
   - Enabled `USE_YFINANCE = True` by default with enhanced symbol resolution (`^NSEI`, `.NS`).
   - Added automatic flattening for multi-index columns from recent `yfinance` versions.
   - Preserved priority fallback: Local CSV -> Live yfinance -> Synthetic test generator.
3. **VWAP & Index Support**:
   - Enhanced `add_indicators()` to handle zero-volume index feeds (`^NSEI`) with TWAP fallback, while retaining true volume-weighted VWAP for stocks and ETFs (`NIFTYBEES`).
4. **Resilient Grid Search & Visualization**:
   - Added safe handling so grid search and trade plotting succeed smoothly on real market data.
