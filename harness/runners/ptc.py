"""Supply the same PTC convenience wrapper to both JavaScript execution adapters."""

from pathlib import Path

PTC_PRELUDE = Path(__file__).with_name("ptc.js").read_text(encoding="utf-8")
