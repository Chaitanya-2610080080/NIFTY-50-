import pandas as pd
from pathlib import Path

p = Path("data")
for f in sorted(p.glob("*.csv")):
    df = pd.read_csv(f)
    first_dt = df["datetime"].iloc[0]
    last_dt = df["datetime"].iloc[-1]
    print(f"{f.stem:12} | Rows: {len(df):4} | {first_dt} to {last_dt} | Last Close: {df['close'].iloc[-1]:.2f}")
