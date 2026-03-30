from __future__ import annotations


def parse_kv_pairs(values: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            parsed[item] = ""
            continue
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed

