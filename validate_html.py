from pathlib import Path
import re

html_path = Path("index.html")
content = html_path.read_text(encoding="utf-8")

print(f"Total HTML file size: {len(content):,} bytes")

# Extract scripts
scripts = re.findall(r"<script>(.*?)</script>", content, re.DOTALL)
print(f"Found {len(scripts)} <script> blocks")

for i, s in enumerate(scripts):
    print(f"Script block {i}: {len(s):,} characters")
    # Check for basic JS syntax markers
    open_braces = s.count("{")
    close_braces = s.count("}")
    open_parens = s.count("(")
    close_parens = s.count(")")
    open_brackets = s.count("[")
    close_brackets = s.count("]")
    print(f"  Braces: {open_braces} open, {close_braces} close (diff: {open_braces - close_braces})")
    print(f"  Parens: {open_parens} open, {close_parens} close (diff: {open_parens - close_parens})")
    print(f"  Brackets: {open_brackets} open, {close_brackets} close (diff: {open_brackets - close_brackets})")

# Check for crucial elements
tags = ["mainChart", "tickerRibbon", "kpiActiveSym", "miniTradeTable", "journalTable", "scannerCardsContainer", "monteCarloCanvas", "equityCurveCanvas", "drawdownCanvas"]
for t in tags:
    found = f'id="{t}"' in content or f"id='{t}'" in content
    print(f"Element #{t}: {'FOUND' if found else 'MISSING'}")

print("Validation completed successfully.")
