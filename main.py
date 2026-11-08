import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import core

try:
    from rich.console import Console
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

BANNER = """  ██╗  ██╗ █████╗ ██╗  ██╗██████╗  ██████╗  ██████╗
  ██║  ██║██╔══██╗╚██╗██╔╝██╔══██╗██╔═══██╗██╔════╝
  ███████║███████║ ╚███╔╝ ██║  ██║██║   ██║██║  ███╗
  ██╔══██║██╔══██║ ██╔██╗ ██║  ██║██║   ██║██║   ██║
  ██║  ██║██║  ██║██╔╝ ██╗██████╔╝╚██████╔╝╚██████╔╝
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝"""


def cmd_username(value, as_json):
    res = core.run_checks("username", value, render_ui=not as_json)
    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))


def cmd_email(value, as_json):
    res = core.run_checks("email", value, render_ui=not as_json)
    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))


def cmd_list():
    core.list_modules()


EPILOG = """
examples:
  python main.py --username test
  python main.py --username test --json
  python main.py --email test@example.com
  python main.py --email test@example.com --json
  python main.py --list
"""


def build_parser():
    p = argparse.ArgumentParser(
        prog="haxdog",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--username", metavar="USER", help="search by username")
    g.add_argument("--email", metavar="EMAIL", help="search by email")
    g.add_argument("--list", action="store_true", help="list all available modules")
    p.add_argument("--json", action="store_true", help="output as JSON")
    return p


def main():
    if len(sys.argv) == 1:
        build_parser().print_help()
        sys.exit(0)
        
    args = build_parser().parse_args()
    
    if not args.json:
        if HAS_RICH:
            console = Console()
            console.print(f"[bold red]{BANNER}[/bold red]")
            console.print("[grey50]                     v1.0[/grey50]\n")
        else:
            print(BANNER)
            print("                     v1.0\n")

    if args.username:
        cmd_username(args.username, args.json)
    elif args.email:
        cmd_email(args.email, args.json)
    elif args.list:
        cmd_list()


if __name__ == "__main__":
    main()
