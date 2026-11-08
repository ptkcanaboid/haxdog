import importlib
import pkgutil
import re
import sys
from io import BytesIO
from urllib.parse import urlparse

import requests

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markup import escape
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DEFAULT_TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_AVATAR_RE = re.compile(r"(?:avatar(?:_url)?\s*[:=]\s*)(https?://\S+)", re.IGNORECASE)

SHOW_AVATARS = True


class _DummyResponse:
    status_code = 0
    content = b""
    text = ""
    headers = {}

    def json(self):
        return {}


def safe_request(method, url, timeout=DEFAULT_TIMEOUT, **kwargs):
    headers = kwargs.pop("headers", {}) or {}
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers)
    try:
        return _session.request(method, url, timeout=timeout, headers=merged, **kwargs)
    except requests.RequestException:
        return _DummyResponse()


def load_modules(category):
    pkg_name = f"modules.{category}"
    try:
        pkg = importlib.import_module(pkg_name)
    except ImportError:
        return []
    modules = []
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        if name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{pkg_name}.{name}")
        except Exception as e:
            print(f"[loader] failed to import {pkg_name}.{name}: {e}")
            continue
        if hasattr(mod, "check"):
            modules.append((name, mod))
    return modules


def _parse_details(details_str):
    if not details_str:
        return {}
    if isinstance(details_str, dict):
        return details_str
    parsed = {}
    parts = [p.strip() for p in details_str.split("|") if p.strip()]
    for i, p in enumerate(parts):
        if ": " in p:
            k, v = p.split(": ", 1)
            parsed[k.strip()] = v.strip()
        else:
            parsed["Info" if i == 0 and len(parts) == 1 else f"Info_{i+1}"] = p
    return parsed


def _extract_avatar(result):
    if result.get("avatar_url"):
        return result["avatar_url"]
    details = result.get("details", {})
    if isinstance(details, dict):
        return details.get("Avatar") or details.get("avatar_url")
    elif isinstance(details, str):
        m = _AVATAR_RE.search(details)
        return m.group(1).rstrip(".,;|)").strip() if m else None
    return None


def _render_avatar(url, width=16):
    if not HAS_PIL or not SHOW_AVATARS or not url or not sys.stdout.isatty():
        return None
    try:
        r = safe_request("GET", url, timeout=10)
        if r.status_code != 200 or not r.content:
            return None
        img = Image.open(BytesIO(r.content)).convert("RGB")
    except Exception:
        return None

    w = width
    h_px = int(w * img.height / img.width)
    h_px = max(2, h_px + (h_px % 2))
    try:
        img = img.resize((w, h_px), Image.LANCZOS)
    except Exception:
        return None

    lines = []
    for y in range(0, img.height, 2):
        row = ""
        for x in range(img.width):
            r1, g1, b1 = img.getpixel((x, y))
            if y + 1 < img.height:
                r2, g2, b2 = img.getpixel((x, y + 1))
            else:
                r2, g2, b2 = r1, g1, b1
            row += f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀"
        row += "\033[0m"
        lines.append(row)
    return lines


def _build_card(r, console_width):
    status = r.get("status", "?")
    site = escape(r.get("site") or r.get("module") or "?")
    url = r.get("url") or ""
    avatar_url = _extract_avatar(r)
    
    details = r.get("details", {})
    if not isinstance(details, dict):
        details = _parse_details(details)
        
    if "Avatar" in details:
        del details["Avatar"]
    if "avatar_url" in details:
        del details["avatar_url"]

    border_color = "green" if status == "Found" else "grey50"

    grid = Table.grid(padding=(0, 2), expand=True)
    grid.add_column(style="bold #7a7a85", justify="right", no_wrap=True)
    grid.add_column(style="white", overflow="fold")

    if url:
        grid.add_row("Profile:", f"[blue][link={url}]{escape(url)}[/link][/blue]")

    if not details:
        grid.add_row("", "[dim]No extra details available[/dim]")
    else:
        for k, v in details.items():
            grid.add_row(f"{escape(k)}:", escape(str(v)))

    avatar_renderable = None
    if avatar_url:
        if HAS_PIL and SHOW_AVATARS and console_width > 80:
            rendered = _render_avatar(avatar_url, width=16)
            if rendered:
                avatar_renderable = Text.from_ansi("\n".join(rendered))
        
        if not avatar_renderable:
            avatar_renderable = Text.from_markup(
                f"[link={avatar_url}] [dim]Avatar available[/dim][/link]", 
                style="magenta"
            )

    layout = Table.grid(expand=True)
    layout.add_column(ratio=1)
    if avatar_renderable:
        layout.add_column(justify="right", width=18)

    if avatar_renderable:
        layout.add_row(grid, avatar_renderable)
    else:
        layout.add_row(grid)

    title = f"[bold cyan]{site}[/bold cyan]"
    subtitle = f"[bold {'green' if status == 'Found' else 'grey50'}]{escape(status)}[/]"

    return Panel(
        layout,
        title=title,
        subtitle=subtitle,
        subtitle_align="right",
        border_style=border_color,
        box=box.ROUNDED,
        padding=(0, 1)
    )


def _merge_enrich_details(result, api_data):
    if not isinstance(api_data, dict) or not api_data:
        return
    if "details" not in result or not isinstance(result["details"], dict):
        result["details"] = _parse_details(result.get("details"))
    for k, v in api_data.items():
        if v not in (None, "", {}):
            result["details"][k] = v


def run_checks(category, value, render_ui=True):
    modules = load_modules(category)
    if not modules:
        if render_ui:
            print(f"[!] No modules in modules/{category}/")
        return []

    results = []
    if render_ui:
        print(f"[*] {len(modules)} module(s) for {category}: {value}\n")

    for name, mod in modules:
        def callback(result, _n=name, _mod=mod):
            result.setdefault("module", _n)
            result["details"] = _parse_details(result.get("details"))

            url = result.get("url", "")
            if result.get("status") == "Found" and url and hasattr(_mod, "enrich"):
                try:
                    extra = _mod.enrich(url)
                    if isinstance(extra, dict):
                        _merge_enrich_details(result, extra.get("api_data"))
                        if extra.get("avatar_url"):
                            result["avatar_url"] = extra["avatar_url"]
                except Exception as e:
                    if render_ui:
                        print(f"  \033[93m[!]\033[0m [{_n}] enrich failed: {e}")

            results.append(result)

        try:
            out = mod.check(value, callback)
            if isinstance(out, dict):
                callback(out)
            elif isinstance(out, list):
                for r in out:
                    if isinstance(r, dict):
                        callback(r)
        except Exception as e:
            if render_ui:
                print(f"  \033[91m[!]\033[0m [{name}] exception: {e}")

    if render_ui:
        if HAS_RICH:
            console = Console(highlight=False)
            for r in results:
                console.print(_build_card(r, console.width))
                console.print()
        else:
            for r in results:
                print(f"  [{r.get('status')}] {r.get('site')}: {r.get('details')}")
        print(f"[*] Done. {len(results)} hit(s).")
        
    return results


def list_modules():
    for category in ("username", "email"):
        print(f"\n{category}:")
        mods = load_modules(category)
        if not mods:
            print("  (none)")
            continue
        for name, mod in mods:
            site = getattr(mod, "SITE", name)
            mark = " [enrich]" if hasattr(mod, "enrich") else ""
            print(f"  - {site:<22} ({name}){mark}")
