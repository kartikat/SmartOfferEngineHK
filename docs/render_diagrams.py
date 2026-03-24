"""
Renders Mermaid diagrams from architecture.md to PNG using mermaid.ink.
Output: docs/images/diagram_*.png

Usage: python3 docs/render_diagrams.py
"""

import base64
import re
import ssl
import urllib.request
import urllib.error
from pathlib import Path
import certifi

ARCH_MD = Path(__file__).parent / "architecture.md"
OUT_DIR = Path(__file__).parent / "images"
OUT_DIR.mkdir(exist_ok=True)

DIAGRAM_NAMES = [
    "01_system_overview",
    "02_scoring_engine",
    "03_database_schema",
    "04_ml_upgrade",
    "05_customer_stories",
]


def extract_mermaid_blocks(md_text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", md_text, re.DOTALL)


def render_to_png(mermaid_src: str, out_path: Path) -> bool:
    encoded = base64.urlsafe_b64encode(mermaid_src.encode()).decode()
    url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=white"
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers={"User-Agent": "SmartOfferEngine/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = resp.read()
        out_path.write_bytes(data)
        kb = len(data) // 1024
        print(f"  ✓  {out_path.name}  ({kb} KB)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ✗  {out_path.name}  HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"  ✗  {out_path.name}  {e}")
        return False


def main():
    md_text = ARCH_MD.read_text()
    blocks = extract_mermaid_blocks(md_text)

    if not blocks:
        print("No Mermaid blocks found in architecture.md")
        return

    print(f"Found {len(blocks)} diagrams — rendering to {OUT_DIR}/\n")

    ok = 0
    for i, (block, name) in enumerate(zip(blocks, DIAGRAM_NAMES)):
        out_path = OUT_DIR / f"{name}.png"
        if render_to_png(block, out_path):
            ok += 1

    print(f"\n{ok}/{len(blocks)} diagrams rendered successfully.")
    if ok < len(blocks):
        print("Tip: check that mermaid.ink is reachable (requires internet access).")


if __name__ == "__main__":
    main()
