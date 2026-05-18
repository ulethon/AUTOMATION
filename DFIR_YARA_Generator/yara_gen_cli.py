#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           YARA Rule Generator — CLI Edition v1.0            ║
║       Cross-platform  |  Windows & Linux  |  Python 3.8+    ║
╚══════════════════════════════════════════════════════════════╝

Usage Examples:
  python yara_gen_cli.py --interactive
  python yara_gen_cli.py --template "Ransomware" --name MyRule --author "Analyst"
  python yara_gen_cli.py --file malware.exe --name HashRule
  python yara_gen_cli.py --strings "evil.exe" "c2.domain.com" --name C2Rule --out rule.yar
"""

import argparse
import sys
import os
import json
import datetime
from pathlib import Path

# ── Optional rich output ──────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    from rich.progress import track
    from rich.theme import Theme
    RICH = True
except ImportError:
    RICH = False

# ── Optional colorama fallback (Windows safe) ─────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    from colorama import Fore, Style
    COLORAMA = True
except ImportError:
    COLORAMA = False

from yara_engine import (
    YaraRuleBuilder, YaraRuleRenderer, YaraTemplateGenerator,
    StringType, COMMON_MALWARE_STRINGS, SEVERITY_LEVELS, TLP_LEVELS,
    generate_hash_rule, make_pe_rule, validate_rule_name,
    YARA_META_KEYS
)

# ─────────────────────────────────────────────
#  Console helpers
# ─────────────────────────────────────────────

if RICH:
    custom_theme = Theme({
        "info":    "cyan",
        "warn":    "yellow",
        "error":   "bold red",
        "success": "bold green",
        "accent":  "bold magenta",
        "code":    "bright_white on grey23",
    })
    console = Console(theme=custom_theme)

    def info(msg):    console.print(f"[info]ℹ  {msg}[/info]")
    def warn(msg):    console.print(f"[warn]⚠  {msg}[/warn]")
    def error(msg):   console.print(f"[error]✖  {msg}[/error]")
    def success(msg): console.print(f"[success]✔  {msg}[/success]")

    def print_banner():
        console.print(Panel.fit(
            "[bold magenta]██╗   ██╗ █████╗ ██████╗  █████╗\n"
            "╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗\n"
            " ╚████╔╝ ███████║██████╔╝███████║\n"
            "  ╚██╔╝  ██╔══██║██╔══██╗██╔══██║\n"
            "   ██║   ██║  ██║██║  ██║██║  ██║\n"
            "   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝[/bold magenta]\n\n"
            "[bold cyan]YARA Rule Generator CLI[/bold cyan]  [dim]v1.0[/dim]\n"
            "[dim]Cross-platform Threat Intelligence Tooling[/dim]",
            title="[bold yellow]◈ YARA-GEN ◈[/bold yellow]",
            border_style="bright_blue",
            padding=(1, 4),
        ))

    def print_rule(rule_text: str):
        syntax = Syntax(rule_text, "java", theme="monokai",
                        line_numbers=True, padding=1)
        console.print(Panel(syntax, title="[bold green]Generated YARA Rule[/bold green]",
                            border_style="green"))

else:
    def _c(code, msg):
        if COLORAMA:
            return f"{code}{msg}{Style.RESET_ALL}"
        return msg

    def info(msg):    print(f"[*] {msg}")
    def warn(msg):    print(f"[!] {msg}")
    def error(msg):   print(f"[ERROR] {msg}", file=sys.stderr)
    def success(msg): print(f"[+] {msg}")

    def print_banner():
        banner = r"""
  ___   ___  ____     _____   ___  _   _
 / _ \ / _ \|  _ \   / _ \ / _ \| \ | |
| | | | | | | |_) | | | | | | | |  \| |
| |_| | |_| |  _ <  | |_| | |_| | |\  |
 \__, |\___/|_| \_\  \__, |\___/|_| \_|
    |_|                  |_|

  YARA Rule Generator CLI  v1.0
  Cross-platform | Windows & Linux
"""
        print(banner)

    def print_rule(rule_text: str):
        print("\n" + "─" * 60)
        print(rule_text)
        print("─" * 60)


# ─────────────────────────────────────────────
#  Input helpers (rich vs plain)
# ─────────────────────────────────────────────

def ask(prompt: str, default: str = "") -> str:
    if RICH:
        result = Prompt.ask(f"[bold cyan]{prompt}[/bold cyan]",
                            default=default)
        return result
    else:
        suffix = f" [{default}]" if default else ""
        val = input(f"{prompt}{suffix}: ").strip()
        return val if val else default

def ask_confirm(prompt: str, default: bool = True) -> bool:
    if RICH:
        return Confirm.ask(f"[bold yellow]{prompt}[/bold yellow]", default=default)
    else:
        suffix = " [Y/n]" if default else " [y/N]"
        val = input(f"{prompt}{suffix}: ").strip().lower()
        if not val:
            return default
        return val in ("y", "yes")

def ask_choice(prompt: str, choices: list, default: str = None) -> str:
    choices_str = ", ".join(choices)
    if RICH:
        table = Table(show_header=False, box=None, padding=(0, 2))
        for i, c in enumerate(choices, 1):
            table.add_row(f"[cyan]{i}[/cyan]", c)
        console.print(table)
        val = Prompt.ask(
            f"[bold cyan]{prompt}[/bold cyan]",
            choices=[str(i) for i in range(1, len(choices)+1)],
            default=str(choices.index(default)+1) if default and default in choices else "1"
        )
        return choices[int(val) - 1]
    else:
        print(f"\n{prompt}")
        for i, c in enumerate(choices, 1):
            print(f"  {i}. {c}")
        while True:
            val = input("Choice: ").strip()
            if val.isdigit() and 1 <= int(val) <= len(choices):
                return choices[int(val) - 1]
            print("Invalid choice, try again.")


# ─────────────────────────────────────────────
#  Interactive Wizard
# ─────────────────────────────────────────────

def interactive_wizard():
    """Step-by-step interactive YARA rule creation wizard."""
    if RICH:
        console.rule("[bold magenta]Interactive Rule Builder[/bold magenta]")
    else:
        print("\n=== Interactive Rule Builder ===\n")

    # 1. Rule name
    while True:
        name = ask("Rule name", default="DetectMalware")
        err = validate_rule_name(name)
        if err:
            error(err)
        else:
            break

    # 2. Tags
    tags_raw = ask("Tags (comma-separated)", default="malware")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # 3. Meta
    if RICH:
        console.rule("[dim]Metadata[/dim]")

    author      = ask("Author", default="")
    description = ask("Description", default="")
    severity    = ask_choice("Severity", SEVERITY_LEVELS, default="medium")
    tlp         = ask_choice("TLP", TLP_LEVELS, default="AMBER")
    reference   = ask("Reference URL", default="")

    # 4. Strings
    if RICH:
        console.rule("[dim]Strings[/dim]")
    else:
        print("\n--- Strings ---")

    info("String types: 1=Text  2=Hex  3=Regex")
    strings_data = []
    while True:
        stype_choice = ask_choice("String type", ["Text", "Hex", "Regex", "Done (no more strings)"])
        if stype_choice.startswith("Done"):
            break

        stype_map = {"Text": StringType.TEXT, "Hex": StringType.HEX, "Regex": StringType.REGEX}
        stype = stype_map[stype_choice]
        val = ask("  String value")
        if not val:
            warn("Empty string skipped.")
            continue

        # modifiers
        available_mods = ["nocase", "wide", "ascii", "fullword", "xor", "base64"]
        mods_raw = ask("  Modifiers (comma-separated, or leave blank)", default="nocase ascii")
        mods = [m.strip() for m in mods_raw.split(",") if m.strip() in available_mods]
        strings_data.append((val, stype, mods))

        if not ask_confirm("  Add another string?"):
            break

    # 5. Condition
    if RICH:
        console.rule("[dim]Condition[/dim]")
    condition_choice = ask_choice(
        "Condition preset",
        ["any of them", "all of them", "Custom condition"]
    )
    if condition_choice == "Custom condition":
        condition = ask("Enter custom condition", default="any of them")
    else:
        condition = condition_choice

    # 6. PE-specific?
    pe_mode = ask_confirm("Add PE header check (MZ magic)?", default=False)
    if pe_mode and condition in ("any of them", "all of them"):
        condition = f'uint16(0) == 0x5A4D and {condition}'

    # ── Build rule ───────────────────────────────────────────
    builder = YaraRuleBuilder()
    builder.set_name(name)
    builder.set_tags(tags)
    builder.auto_fill_meta(author=author, description=description)
    if severity:    builder.rule.meta["severity"]  = severity
    if tlp:         builder.rule.meta["tlp"]       = tlp
    if reference:   builder.rule.meta["reference"] = reference
    for val, stype, mods in strings_data:
        builder.add_string(val, stype, mods)
    builder.set_condition(condition)

    rule = builder.build()
    rule_text = YaraRuleRenderer.render(rule)

    print_rule(rule_text)

    # 7. Save?
    if ask_confirm("Save rule to file?"):
        default_fname = f"{name}.yar"
        fname = ask("Output file path", default=default_fname)
        Path(fname).parent.mkdir(parents=True, exist_ok=True)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(rule_text + "\n")
        success(f"Rule saved → {fname}")

    return rule_text


# ─────────────────────────────────────────────
#  Template Mode
# ─────────────────────────────────────────────

def template_mode(args):
    templates = YaraTemplateGenerator.available_templates()
    if args.list_templates:
        if RICH:
            t = Table("Template", "Built-in Strings", show_lines=True,
                      border_style="cyan", header_style="bold magenta")
            for cat, strs in COMMON_MALWARE_STRINGS.items():
                t.add_row(cat, "\n".join(strs[:3]) + ("..." if len(strs) > 3 else ""))
            console.print(t)
        else:
            for cat, strs in COMMON_MALWARE_STRINGS.items():
                print(f"\n  {cat}:")
                for s in strs[:3]:
                    print(f"    - {s}")
        return

    category = args.template
    if category not in templates:
        error(f"Unknown template: '{category}'. Use --list-templates to see available options.")
        sys.exit(1)

    rule_name = args.name or re.sub(r'\W+', '_', category)
    rule = YaraTemplateGenerator.from_template(
        category=category,
        rule_name=rule_name,
        author=args.author or "",
        extra_strings=args.strings or []
    )
    rule_text = YaraRuleRenderer.render(rule)
    print_rule(rule_text)
    _save_if_needed(rule_text, args)


# ─────────────────────────────────────────────
#  Hash Mode
# ─────────────────────────────────────────────

def hash_mode(args):
    filepath = args.file
    if not os.path.isfile(filepath):
        error(f"File not found: {filepath}")
        sys.exit(1)

    info(f"Computing hashes for: {filepath}")
    rule = generate_hash_rule(
        filepath=filepath,
        rule_name=args.name,
        author=args.author or ""
    )
    rule_text = YaraRuleRenderer.render(rule)
    print_rule(rule_text)
    _save_if_needed(rule_text, args)


# ─────────────────────────────────────────────
#  Quick Strings Mode
# ─────────────────────────────────────────────

def strings_mode(args):
    name = args.name or "CustomStringRule"
    err = validate_rule_name(name)
    if err:
        error(err)
        sys.exit(1)

    builder = YaraRuleBuilder()
    builder.set_name(name)
    builder.set_tags(args.tags or ["custom"])
    builder.auto_fill_meta(author=args.author or "", description=args.description or "")

    mods = args.modifiers or ["nocase", "ascii"]

    stype_map = {
        "text":  StringType.TEXT,
        "hex":   StringType.HEX,
        "regex": StringType.REGEX,
    }
    stype = stype_map.get((args.stype or "text").lower(), StringType.TEXT)

    for s in (args.strings or []):
        builder.add_string(s, stype, mods)

    # hex strings
    for h in (args.hex_strings or []):
        builder.add_string(h, StringType.HEX, [])

    # regex strings
    for r in (args.regex_strings or []):
        builder.add_string(r, StringType.REGEX, [])

    if args.pe:
        builder.add_import("pe")
        condition = f'uint16(0) == 0x5A4D and {args.condition or "any of them"}'
    else:
        condition = args.condition or "any of them"

    builder.set_condition(condition)

    if args.severity:
        builder.rule.meta["severity"] = args.severity
    if args.tlp:
        builder.rule.meta["tlp"] = args.tlp

    rule = builder.build()
    rule_text = YaraRuleRenderer.render(rule)
    print_rule(rule_text)
    _save_if_needed(rule_text, args)


# ─────────────────────────────────────────────
#  Batch / JSON mode
# ─────────────────────────────────────────────

def batch_mode(args):
    """Generate multiple rules from a JSON definition file."""
    json_path = args.batch
    if not os.path.isfile(json_path):
        error(f"JSON file not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules_list = data if isinstance(data, list) else [data]
    all_rules = []

    for i, rule_def in enumerate(rules_list):
        try:
            builder = YaraRuleBuilder()
            builder.set_name(rule_def.get("name", f"Rule_{i+1}"))
            builder.set_tags(rule_def.get("tags", []))

            for k, v in rule_def.get("meta", {}).items():
                builder.set_meta(k, v)
            builder.auto_fill_meta(
                author=rule_def.get("author", ""),
                description=rule_def.get("description", "")
            )

            for s in rule_def.get("strings", []):
                stype = {"text": StringType.TEXT, "hex": StringType.HEX,
                         "regex": StringType.REGEX}.get(s.get("type", "text"), StringType.TEXT)
                builder.add_string(s["value"], stype, s.get("modifiers", []))

            builder.set_condition(rule_def.get("condition", "any of them"))
            all_rules.append(builder.build())
            success(f"  Built rule: {builder.rule.name}")
        except Exception as e:
            error(f"  Rule #{i+1} failed: {e}")

    if all_rules:
        combined = YaraRuleRenderer.render_multiple(all_rules)
        print_rule(combined)
        _save_if_needed(combined, args)
        success(f"Total: {len(all_rules)} rule(s) generated.")


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _save_if_needed(rule_text: str, args):
    out = getattr(args, "out", None)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(rule_text + "\n")
        success(f"Saved → {out}")


# ─────────────────────────────────────────────
#  Argument Parser
# ─────────────────────────────────────────────

import re  # needed for re.sub in template_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yara_gen_cli",
        description="YARA Rule Generator — Cross-platform CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive wizard:
    python yara_gen_cli.py --interactive

  From template:
    python yara_gen_cli.py --template "Ransomware" --name MyRule --author "SOC Team"

  From strings:
    python yara_gen_cli.py --strings "evil.exe" "cmd.exe" --name C2Rule --out c2.yar

  From file hash:
    python yara_gen_cli.py --file malware.exe --name MalwareHash --out hash.yar

  Batch from JSON:
    python yara_gen_cli.py --batch rules.json --out batch_output.yar

  List templates:
    python yara_gen_cli.py --list-templates
        """
    )

    # ── Modes ──────────────────────────────────────────────
    mode_grp = parser.add_mutually_exclusive_group()
    mode_grp.add_argument("-i", "--interactive", action="store_true",
                          help="Launch interactive wizard (default if no args)")
    mode_grp.add_argument("-t", "--template", metavar="CATEGORY",
                          help="Generate rule from malware template category")
    mode_grp.add_argument("-f", "--file", metavar="PATH",
                          help="Generate hash-based rule from a file")
    mode_grp.add_argument("-b", "--batch", metavar="JSON_FILE",
                          help="Generate multiple rules from JSON definition file")
    mode_grp.add_argument("--list-templates", action="store_true",
                          help="List all available malware templates")

    # ── String inputs ───────────────────────────────────────
    str_grp = parser.add_argument_group("String inputs")
    str_grp.add_argument("-s", "--strings", nargs="+", metavar="STR",
                         help="Plain text strings to match")
    str_grp.add_argument("--hex-strings", nargs="+", metavar="HEX",
                         help='Hex byte strings e.g. "4D 5A 90 00"')
    str_grp.add_argument("--regex-strings", nargs="+", metavar="REGEX",
                         help="Regex pattern strings")
    str_grp.add_argument("--stype", choices=["text", "hex", "regex"], default="text",
                         help="String type for --strings (default: text)")
    str_grp.add_argument("--modifiers", nargs="+",
                         metavar="MOD",
                         help="Modifiers: nocase wide ascii fullword xor base64")

    # ── Rule metadata ───────────────────────────────────────
    meta_grp = parser.add_argument_group("Rule metadata")
    meta_grp.add_argument("-n", "--name", metavar="NAME",
                          help="Rule name (default: auto)")
    meta_grp.add_argument("-a", "--author", metavar="AUTHOR",
                          help="Author metadata")
    meta_grp.add_argument("-d", "--description", metavar="DESC",
                          help="Description metadata")
    meta_grp.add_argument("--tags", nargs="+", metavar="TAG",
                          help="Rule tags")
    meta_grp.add_argument("--severity", choices=SEVERITY_LEVELS,
                          help="Severity level")
    meta_grp.add_argument("--tlp", choices=TLP_LEVELS,
                          help="TLP classification")
    meta_grp.add_argument("--condition", metavar="COND",
                          help='YARA condition (default: "any of them")')

    # ── Output ──────────────────────────────────────────────
    out_grp = parser.add_argument_group("Output")
    out_grp.add_argument("-o", "--out", metavar="FILE",
                         help="Output .yar file path")
    out_grp.add_argument("--pe", action="store_true",
                         help="Add PE header check to condition")
    out_grp.add_argument("--no-banner", action="store_true",
                         help="Suppress banner")

    return parser


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.no_banner:
        print_banner()

    # ── Route ──────────────────────────────────────────────
    if args.list_templates:
        template_mode(args)

    elif args.template:
        template_mode(args)

    elif args.file:
        hash_mode(args)

    elif args.batch:
        batch_mode(args)

    elif args.strings or args.hex_strings or args.regex_strings:
        strings_mode(args)

    else:
        # Default: interactive wizard
        interactive_wizard()


if __name__ == "__main__":
    main()
