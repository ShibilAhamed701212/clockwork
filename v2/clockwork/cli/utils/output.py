import json
import sys
from typing import Any, Dict, List

_mode    = "standard"
_verbose = False

def set_mode(m: str):
    global _mode
    _mode = m

def set_verbose(v: bool):
    global _verbose
    _verbose = v

def banner():
    if _mode == "json":
        return
    print("+====================================================+")
    print("+          CLOCKWORK AI OS  v2.0                    +")
    print("+====================================================+")

def check_initialized():
    from pathlib import Path
    if not Path(".clockwork").exists():
        error_with_hint("Clockwork not initialized.", "Run: clockwork init")
        sys.exit(1)

def header(title: str):
    if _mode == "json":
        return
    print("=" * 52)
    print("  " + title)
    print("=" * 52)

def section(title: str):
    if _mode == "json":
        return
    print("\n" + "-" * 52)
    print("  " + title)
    print("-" * 52)

def success(msg: str):
    if _mode != "json":
        print("[OK]   " + msg)

def warn(msg: str):
    if _mode != "json":
        print("[WARN] " + msg)

def error(msg: str):
    print("[FAIL] " + msg, file=sys.stderr)

def info(msg: str):
    if _mode != "json":
        print("[INFO] " + msg)

def verbose(msg: str):
    if _verbose and _mode != "json":
        print("[DBG]  " + msg)

def result(label: str, value: Any):
    if _mode != "json":
        print("  " + str(label) + ": " + str(value))

def json_output(data: Any):
    print(json.dumps(data, indent=2, default=str))

def error_with_hint(msg: str, hint: str):
    if msg:
        error(msg)
    if _mode != "json":
        print("  Hint: " + hint)

def list_items(items: List[str], prefix: str = "  - "):
    if _mode == "json":
        print(json.dumps(items, indent=2))
        return
    for item in items:
        print(prefix + str(item))

def table(data: List[Dict], columns: List[str]):
    if _mode == "json":
        print(json.dumps(data, indent=2, default=str))
        return
    if not data:
        print("  (no data)")
        return
    widths = {c: max(len(c), max(len(str(row.get(c,""))) for row in data)) for c in columns}
    hrow = " | ".join(c.ljust(widths[c]) for c in columns)
    print(hrow)
    print("-" * len(hrow))
    for row in data:
        print(" | ".join(str(row.get(c,"")).ljust(widths[c]) for c in columns))

def decision_explain(status: str, confidence: float, risk: str, explanation: str, suggestion: str = ""):
    if _mode == "json":
        json_output({"status": status, "confidence": confidence,
                     "risk": risk, "explanation": explanation, "suggestion": suggestion})
        return
    print("-" * 52)
    print("  Decision:   " + status)
    print("  Confidence: " + str(round(confidence * 100)) + "%")
    print("  Risk:       " + risk.upper())
    print("  Reason:     " + explanation)
    if suggestion:
        print("  Fix:        " + suggestion)
    print("-" * 52)