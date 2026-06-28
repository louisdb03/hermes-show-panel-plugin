"""Jarvis show_panel plugin.

A display-only tool that lets the Jarvis speech profile intentionally render
Hermes Panels HUD cards without abusing unrelated data/action tools.
"""

from __future__ import annotations

import json
from typing import Any

_MAX_TITLE = 120
_MAX_BODY = 800
_MAX_ITEM = 160
_MAX_CODE = 6000
_MAX_COLUMNS = 5
_MAX_ROWS = 8
_MAX_CAROUSEL_ITEMS = 8
_MAX_ACTIONS = 2
_MAX_STATS = 6
_MAX_SPARKLINE_POINTS = 24


def _text(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:limit]


def _stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)[:160]
    return json.dumps(value, default=str)[:160]


def _normalize_items(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items[:8]:
        text = _text(item, _MAX_ITEM)
        if text:
            normalized.append(text)
    return normalized


def _normalize_columns(columns: Any, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if isinstance(columns, list):
        for col in columns[:_MAX_COLUMNS]:
            if isinstance(col, str):
                key = col
                label = col.replace("_", " ").title()
            elif isinstance(col, dict):
                key = col.get("key")
                label = col.get("label") or key
            else:
                continue
            key = _text(key, 60)
            label = _text(label, 80)
            if key:
                normalized.append({"key": key, "label": label or key})
    if normalized:
        return normalized

    key_order: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in key_order:
                key_order.append(str(key))
    return [{"key": key, "label": key.replace("_", " ").title()} for key in key_order[:_MAX_COLUMNS]]


def _normalize_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [row for row in rows[:_MAX_ROWS] if isinstance(row, dict)]


def _normalize_link_url(url: Any) -> str:
    value = _text(url, 500)
    if value.startswith(("https://", "http://")):
        return value
    return ""



def _normalize_color(value: Any) -> str:
    text = _text(value, 40)
    if text.startswith("#") and 4 <= len(text) <= 9:
        return text
    if text.startswith(("rgb(", "rgba(", "hsl(", "hsla(")):
        return text
    return ""


def _normalize_carousel_actions(actions: Any) -> list[dict[str, str]]:
    if not isinstance(actions, list):
        return []
    normalized: list[dict[str, str]] = []
    for idx, action in enumerate(actions[:_MAX_ACTIONS]):
        if isinstance(action, str):
            label = _text(action, 40)
            action_id = str(idx)
            variant = "secondary"
        elif isinstance(action, dict):
            label = _text(action.get("label"), 40)
            action_id = _text(action.get("id") or idx, 60)
            variant = _text(action.get("variant") or "secondary", 20)
        else:
            continue
        if label:
            normalized.append({"id": action_id or str(idx), "label": label, "variant": variant})
    return normalized


def _normalize_carousel_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items[:_MAX_CAROUSEL_ITEMS]):
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name") or item.get("title") or item.get("label") or item.get("content"), _MAX_ITEM)
        if not name:
            continue
        normalized_item: dict[str, Any] = {
            "id": _text(item.get("id") or idx, 80) or str(idx),
            "name": name,
            "subtitle": _text(item.get("subtitle") or item.get("description"), 160),
            "image": _normalize_link_url(item.get("image") or item.get("image_url") or item.get("thumbnail")),
            "color": _normalize_color(item.get("color")),
            "actions": _normalize_carousel_actions(item.get("actions")),
        }
        normalized.append({key: value for key, value in normalized_item.items() if value not in ("", [], None)})
    return normalized


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _normalize_stat_format(value: Any, stat: dict[str, Any] | None = None) -> dict[str, Any]:
    stat = stat or {}
    if isinstance(value, str):
        value = {"kind": value}
    elif value is None and isinstance(stat.get("format"), str):
        value = {"kind": stat.get("format")}
    if not isinstance(value, dict):
        return {}
    kind = _text(value.get("kind") or value.get("type") or stat.get("format"), 20)
    if kind not in {"text", "number", "currency", "percent"}:
        return {}
    normalized: dict[str, Any] = {"kind": kind}
    if kind == "currency":
        normalized["currency"] = _text(value.get("currency") or stat.get("currency") or "USD", 8) or "USD"
    decimals = value.get("decimals", stat.get("decimals"))
    if isinstance(decimals, int):
        normalized["decimals"] = max(0, min(int(decimals), 4))
    compact = value.get("compact", stat.get("compact"))
    if isinstance(compact, bool):
        normalized["compact"] = bool(compact)
    basis = value.get("basis", stat.get("basis"))
    if kind == "percent" and basis in {"fraction", "unit"}:
        normalized["basis"] = basis
    return normalized


def _normalize_stat_diff(value: Any, stat: dict[str, Any] | None = None) -> dict[str, Any] | None:
    stat = stat or {}
    if not isinstance(value, dict):
        numeric = _number(value)
        if numeric is None:
            return None
        value = {"value": numeric}
    diff_value = _number(value.get("value"))
    if diff_value is None:
        return None
    normalized: dict[str, Any] = {"value": diff_value}
    decimals = value.get("decimals", stat.get("diffDecimals"))
    if isinstance(decimals, int):
        normalized["decimals"] = max(0, min(int(decimals), 4))
    up_is_positive = value.get("upIsPositive", stat.get("upIsPositive"))
    if isinstance(up_is_positive, bool):
        normalized["upIsPositive"] = bool(up_is_positive)
    label = _text(value.get("label") or stat.get("diffLabel"), 40)
    if label:
        normalized["label"] = label
    return normalized


def _normalize_sparkline(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        return None
    data: list[float] = []
    for point in value["data"][:_MAX_SPARKLINE_POINTS]:
        numeric = _number(point)
        if numeric is not None:
            data.append(numeric)
    if len(data) < 2:
        return None
    normalized: dict[str, Any] = {"data": data}
    color = _normalize_color(value.get("color"))
    if color:
        normalized["color"] = color
    return normalized


def _normalize_stats(stats: Any) -> list[dict[str, Any]]:
    if not isinstance(stats, list):
        return []
    normalized: list[dict[str, Any]] = []
    for idx, stat in enumerate(stats[:_MAX_STATS]):
        if not isinstance(stat, dict):
            continue
        label = _text(stat.get("label") or stat.get("name") or stat.get("key"), 80)
        if not label or "value" not in stat:
            continue
        raw_value = stat.get("value")
        numeric_value = _number(raw_value)
        if numeric_value is None:
            value: Any = _text(raw_value, 80)
        else:
            value = numeric_value
        item: dict[str, Any] = {
            "key": _text(stat.get("key") or idx, 80) or str(idx),
            "label": label,
            "value": value,
        }
        fmt = _normalize_stat_format(stat.get("format"), stat)
        if fmt:
            item["format"] = fmt
        diff = _normalize_stat_diff(stat.get("diff"), stat)
        if diff:
            item["diff"] = diff
        sparkline = _normalize_sparkline(stat.get("sparkline"))
        if sparkline:
            item["sparkline"] = sparkline
        normalized.append(item)
    return normalized

def _with_panel_id(payload: dict[str, Any], panel_id: str) -> dict[str, Any]:
    if panel_id:
        payload["panel_id"] = panel_id
    return payload


def _normalize_payload(args: dict[str, Any]) -> dict[str, Any]:
    remove_panel_id = _text(args.get("remove_panel_id"), 120)
    if remove_panel_id:
        return {
            "ok": True,
            "source": "assistant_presentation",
            "remove_panel_id": remove_panel_id,
        }

    panel_id = _text(args.get("panel_id") or args.get("id"), 120)
    panel = _text(args.get("panel") or args.get("type"), 40)
    title = _text(args.get("title"), _MAX_TITLE)

    if panel == "note":
        body = _text(args.get("body") or args.get("message") or args.get("text"), _MAX_BODY)
        items = _normalize_items(args.get("items"))
        if not body and not items:
            raise ValueError("note panel needs body or items")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "note",
            "title": title or "Note",
            "body": body,
            "items": items,
            "tone": _text(args.get("tone") or "info", 20),
        }, panel_id)

    if panel == "data_table":
        rows = _normalize_rows(args.get("rows"))
        columns = _normalize_columns(args.get("columns"), rows)
        if not rows or not columns:
            raise ValueError("data_table panel needs rows and columns")
        string_rows = [{col["key"]: _stringify_cell(row.get(col["key"])) for col in columns} for row in rows]
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "data_table",
            "title": title or "Details",
            "columns": columns,
            "rows": string_rows,
            "row_count": len(rows),
        }, panel_id)

    if panel == "link_preview":
        url = _normalize_link_url(args.get("url"))
        if not url:
            raise ValueError("link_preview panel needs an http(s) url")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "link_preview",
            "url": url,
            "title": title or url,
            "description": _text(args.get("description"), 280),
            "domain": _text(args.get("domain"), 100),
            "image": _normalize_link_url(args.get("image")),
        }, panel_id)

    if panel == "stats":
        stats = _normalize_stats(args.get("stats") or args.get("items"))
        if not stats:
            raise ValueError("stats panel needs stats/items with label and value")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "stats",
            "title": title or "Stats",
            "description": _text(args.get("description") or args.get("body"), 280),
            "stats": stats,
            "locale": _text(args.get("locale") or "en", 20),
        }, panel_id)

    if panel == "item_carousel":
        carousel_items = _normalize_carousel_items(args.get("items"))
        if not carousel_items:
            raise ValueError("item_carousel panel needs items with names")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "item_carousel",
            "title": title or "Items",
            "description": _text(args.get("description") or args.get("body"), 280),
            "items": carousel_items,
        }, panel_id)

    if panel == "code_block":
        code = _text(args.get("code"), _MAX_CODE)
        if not code:
            raise ValueError("code_block panel needs code")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "code_block",
            "title": title or "Code",
            "path": _text(args.get("path"), 180),
            "language": _text(args.get("language") or "text", 40),
            "code": code,
        }, panel_id)

    raise ValueError("unsupported panel type")


def show_panel(args: dict[str, Any], **kwargs) -> str:
    """Validate and echo a display-only panel payload as JSON."""
    del kwargs
    try:
        return json.dumps(_normalize_payload(args), ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


SHOW_PANEL_SCHEMA = {
    "name": "show_panel",
    "description": (
        "Display a visual HUD card in Hermes Panels. Display-only: does not run actions or fetch facts. "
        "Use this to intentionally present structured visual details after you already know the content. "
        "For live facts, first call the appropriate lookup tool, then use show_panel to present a concise summary. "
        "Keep spoken replies short when using this tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "panel": {
                "type": "string",
                "enum": ["note", "data_table", "link_preview", "code_block", "item_carousel", "stats"],
                "description": "Visual card type to render. Omit only when using remove_panel_id.",
            },
            "panel_id": {
                "type": "string",
                "description": "Stable ID for this persistent presentation panel. Reusing the same ID replaces the previous card.",
            },
            "remove_panel_id": {
                "type": "string",
                "description": "Remove a persistent presentation panel by ID. When provided, no panel payload is required.",
            },
            "title": {"type": "string", "description": "Short card title."},
            "body": {"type": "string", "description": "Note card body text."},
            "items": {
                "type": "array",
                "items": {"anyOf": [{"type": "string"}, {"type": "object"}]},
                "description": "Short bullet items for note cards, item objects for item_carousel, or stat objects for stats.",
            },
            "stats": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Stats card items with label, value, optional format, diff, and sparkline.",
            },
            "columns": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Data table columns: {key,label}.",
            },
            "rows": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Data table rows keyed by column keys.",
            },
            "url": {"type": "string", "description": "HTTP(S) URL for link preview."},
            "description": {"type": "string", "description": "Short link description."},
            "domain": {"type": "string", "description": "Optional link domain."},
            "image": {"type": "string", "description": "Optional HTTP(S) image URL."},
            "language": {"type": "string", "description": "Code language for code_block."},
            "code": {"type": "string", "description": "Code text for code_block."},
            "path": {"type": "string", "description": "Optional filename/path label for code_block."},
            "tone": {
                "type": "string",
                "enum": ["info", "success", "warning", "danger"],
                "description": "Visual tone for note cards.",
            },
        },
    },
}


def register(ctx):
    ctx.register_tool(
        name="show_panel",
        toolset="show_panel",
        schema=SHOW_PANEL_SCHEMA,
        handler=show_panel,
        description="Display a visual HUD card in Hermes Panels.",
    )
