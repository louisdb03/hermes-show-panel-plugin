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

    if panel == "message_draft":
        channel = _text(args.get("channel") or "email", 20)
        body = _text(args.get("body"), 4000)
        if not body:
            raise ValueError("message_draft panel needs body")
        draft: dict[str, Any] = {
            "ok": True,
            "source": "assistant_presentation",
            "panel": "message_draft",
            "channel": channel if channel in ("email", "slack") else "email",
            "body": body,
        }
        if channel == "email":
            subject = _text(args.get("subject"), 200)
            if subject:
                draft["subject"] = subject
            for field in ("to", "cc", "bcc"):
                recipients = args.get(field)
                if isinstance(recipients, list):
                    draft[field] = [_text(r, 200) for r in recipients[:20]]
        elif channel == "slack":
            target_type = _text(args.get("target_type") or "channel", 20)
            target_name = _text(args.get("target_name"), 120)
            if target_name:
                draft["target_type"] = target_type if target_type in ("channel", "dm") else "channel"
                draft["target_name"] = target_name
        return _with_panel_id(draft, panel_id)

    if panel == "chart":
        data = args.get("data")
        series = args.get("series")
        x_key = _text(args.get("x_key") or args.get("xKey"), 60)
        if not isinstance(data, list) or not isinstance(series, list) or not x_key:
            raise ValueError("chart panel needs data, series, and x_key")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "chart",
            "title": title or "Chart",
            "description": _text(args.get("description"), 280),
            "chart_type": _text(args.get("chart_type") or args.get("type") or "bar", 10),
            "data": data[:50],
            "x_key": x_key,
            "series": series[:6],
            "show_legend": bool(args.get("show_legend")),
            "show_grid": bool(args.get("show_grid")),
        }, panel_id)

    if panel == "image":
        src = _text(args.get("src") or args.get("url"), 500)
        if not src.startswith(("https://", "http://")):
            raise ValueError("image panel needs a valid HTTP(S) src")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "image",
            "url": src,
            "alt": _text(args.get("alt") or title, 200),
            "title": title,
            "description": _text(args.get("description"), 280),
            "domain": _text(args.get("domain"), 100),
            "ratio": _text(args.get("ratio") or "auto", 10),
        }, panel_id)

    if panel == "image_gallery":
        raw_images = args.get("images")
        if not isinstance(raw_images, list) or not raw_images:
            raise ValueError("image_gallery panel needs images")
        images = []
        for idx, img in enumerate(raw_images[:6]):
            if not isinstance(img, dict):
                continue
            src = _text(img.get("src") or img.get("url"), 500)
            if not src.startswith(("https://", "http://")):
                continue
            images.append({
                "id": _text(img.get("id") or str(idx), 80),
                "src": src,
                "alt": _text(img.get("alt") or img.get("title") or "", 200),
                "title": _text(img.get("title") or "", 120),
                "caption": _text(img.get("caption") or "", 160),
            })
        if not images:
            raise ValueError("image_gallery needs at least one valid image")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "image_gallery",
            "title": title or "Gallery",
            "description": _text(args.get("description"), 280),
            "images": images,
        }, panel_id)

    if panel == "video":
        src = _text(args.get("src") or args.get("url"), 500)
        if not src.startswith(("https://", "http://")):
            raise ValueError("video panel needs a valid HTTP(S) src")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "video",
            "url": src,
            "poster": _text(args.get("poster"), 500),
            "title": title,
            "description": _text(args.get("description"), 280),
            "ratio": _text(args.get("ratio") or "16:9", 10),
            "duration_ms": args.get("duration_ms") or args.get("durationMs") or 0,
        }, panel_id)

    if panel == "audio":
        src = _text(args.get("src") or args.get("url"), 500)
        if not src.startswith(("https://", "http://")):
            raise ValueError("audio panel needs a valid HTTP(S) src")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "audio",
            "url": src,
            "title": title,
            "description": _text(args.get("description"), 280),
            "artwork": _text(args.get("artwork"), 500),
            "duration_ms": args.get("duration_ms") or args.get("durationMs") or 0,
        }, panel_id)

    if panel == "order_summary":
        raw_items = args.get("items")
        pricing = args.get("pricing")
        if not isinstance(raw_items, list) or not isinstance(pricing, dict):
            raise ValueError("order_summary panel needs items and pricing")
        items = []
        for idx, item in enumerate(raw_items[:12]):
            if not isinstance(item, dict):
                continue
            name = _text(item.get("name"), 160)
            if not name:
                continue
            items.append({
                "id": _text(item.get("id") or str(idx), 80),
                "name": name,
                "unit_price": item.get("unit_price") or item.get("unitPrice") or 0,
                "quantity": item.get("quantity") or 1,
                "description": _text(item.get("description"), 160),
                "image_url": _text(item.get("image_url") or item.get("imageUrl"), 500),
            })
        if not items:
            raise ValueError("order_summary needs at least one item")
        return _with_panel_id({
            "ok": True,
            "source": "assistant_presentation",
            "panel": "order_summary",
            "title": title or "Order Summary",
            "items": items,
            "pricing": {
                "subtotal": pricing.get("subtotal", 0),
                "total": pricing.get("total", 0),
                "tax": pricing.get("tax", 0),
                "shipping": pricing.get("shipping", 0),
                "discount": pricing.get("discount", 0),
                "currency": _text(pricing.get("currency") or "USD", 10),
            },
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
                "enum": ["note", "data_table", "link_preview", "code_block", "item_carousel", "stats", "message_draft", "chart", "image", "image_gallery", "video", "audio", "order_summary"],
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
            "body": {"type": "string", "description": "Note card body text or message draft body."},
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
            "channel": {
                "type": "string",
                "enum": ["email", "slack"],
                "description": "Message channel for message_draft cards.",
            },
            "subject": {"type": "string", "description": "Email subject for message_draft."},
            "to": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Email recipients for message_draft.",
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CC recipients for message_draft.",
            },
            "bcc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "BCC recipients for message_draft.",
            },
            "target_type": {
                "type": "string",
                "enum": ["channel", "dm"],
                "description": "Slack target type for message_draft.",
            },
            "target_name": {"type": "string", "description": "Slack channel/DM name for message_draft."},
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line"],
                "description": "Chart type for chart cards.",
            },
            "x_key": {"type": "string", "description": "Data key for the X axis (chart cards)."},
            "series": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Chart series: [{key, label, color?}].",
            },
            "data": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Chart data rows (objects keyed by series keys + x_key).",
            },
            "show_legend": {"type": "boolean", "description": "Show legend on chart cards."},
            "show_grid": {"type": "boolean", "description": "Show grid lines on chart cards."},
            "src": {"type": "string", "description": "HTTP(S) source URL for image/video/audio cards."},
            "alt": {"type": "string", "description": "Alt text for image cards."},
            "ratio": {
                "type": "string",
                "enum": ["auto", "1:1", "4:3", "16:9", "9:16"],
                "description": "Aspect ratio for image/video cards.",
            },
            "poster": {"type": "string", "description": "Poster image URL for video cards."},
            "artwork": {"type": "string", "description": "Artwork image URL for audio cards."},
            "duration_ms": {"type": "number", "description": "Duration in milliseconds for video/audio cards."},
            "images": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Image gallery items: [{id, src, alt, title?, caption?}].",
            },
            "pricing": {
                "type": "object",
                "description": "Order summary pricing: {subtotal, total, tax?, shipping?, discount?, currency?}.",
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
