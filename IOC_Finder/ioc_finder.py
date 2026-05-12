#!/usr/bin/env python3
"""
ioc_finder.py — IOC-Finder main entry point.
Handles: CLI parsing, structured logging, Rich TUI, scan orchestration,
         drive selection, triage (watchdog) mode, and file copy output.
"""

from __future__ import annotations
import argparse
import base64
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ── Optional: Rich TUI ────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt
    from rich import box
    RICH_OK = True
except ImportError:
    RICH_OK = False

# ── Optional: Watchdog (triage mode) ─────────────────────────────────────────
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False

from config import (
    Configuration, load_configuration, convert_glob_to_regex
)
from events import init_forwarding, stop_forwarding, get_forwarder
from scanner import (
    ScannerPipeline, compile_yara_rules, scan_file, scan_memory,
    enumerate_drives, file_sha256, set_logger,
    DRIVE_FIXED, DRIVE_REMOVABLE, DRIVE_REMOTE, DRIVE_CDROM,
)

TOOL_NAME    = "IOC-Finder"
TOOL_VERSION = "3.6.0"
YARA_VERSION = "4.5.5"

# ── Logger ─────────────────────────────────────────────────────────────────────

# Global verbosity: 1=alert 2=warning 3=error 4=info 5=verbose
_verbosity: int = 4
_log_file:  Optional[object] = None

# Rich console (used when not in full TUI)
_console = Console(stderr=False) if RICH_OK else None

# TUI log buffers (filled when Rich live layout is active)
_tui_active    = False
_buf_matches:  List[str] = []
_buf_errors:   List[str] = []
_buf_log:      List[str] = []

_LEVEL_RANK = {"alert": 1, "warning": 2, "error": 3, "info": 4, "verbose": 5}


def log(level: str, *parts) -> None:
    msg   = " ".join(str(p) for p in parts)
    rank  = _LEVEL_RANK.get(level, 4)
    ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    stamp = f"[{ts}] {msg}"

    # Always forward to event subsystem
    fwd = get_forwarder()
    if fwd and level in ("alert", "warning", "error", "info"):
        fwd.forward(level, "high" if level == "alert" else "medium" if level == "error" else "low", msg)

    if rank > _verbosity:
        _write_log_file(stamp)
        return

    if _tui_active:
        # Route to the correct TUI buffer
        if level == "alert":
            _buf_matches.append(stamp)
        elif level in ("error", "warning"):
            _buf_errors.append(stamp)
        else:
            _buf_log.append(stamp)
    else:
        # Plain / Rich console output
        if RICH_OK and _console:
            colour = {"alert": "red", "warning": "yellow", "error": "bold red",
                      "info": "cyan", "verbose": "dim"}.get(level, "white")
            _console.print(f"[{colour}]{stamp}[/{colour}]")
        else:
            print(stamp, file=sys.stderr if level in ("error", "warning") else sys.stdout)

    _write_log_file(stamp)


def _write_log_file(msg: str) -> None:
    global _log_file
    if _log_file:
        try:
            _log_file.write(msg + "\n")
            _log_file.flush()
        except OSError:
            pass


def set_verbosity(v: int) -> None:
    global _verbosity
    _verbosity = max(0, min(5, v))


def open_log_file(path: str) -> None:
    global _log_file
    _log_file = open(path, "a", encoding="utf-8")


# Inject logger into scanner module
set_logger(log)


# ── System helpers ─────────────────────────────────────────────────────────────

def get_hostname() -> str:
    return socket.gethostname()


def get_username() -> str:
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"


def file_copy(src: str, dst_dir: str, b64: bool) -> str:
    """Copy src into dst_dir with a timestamped name. Base64-encode if requested."""
    ts   = int(time.time())
    name = f"{ts}_{Path(src).name}.iocfinder"
    dest = Path(dst_dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as fh:
        data = fh.read()
    if b64:
        data = base64.b64encode(data)
    with open(dest, "wb") as fh:
        fh.write(data)
    return str(dest)


def _check_single_instance() -> bool:
    """Create a platform-specific lock to prevent duplicate instances."""
    env = os.environ.get("IOC_FINDER_DISABLE_MUTEX", "")
    if env == "1":
        log("info", "(INIT) Single-instance lock disabled (IOC_FINDER_DISABLE_MUTEX=1)")
        return True

    if sys.platform == "win32":
        import ctypes
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, "ioc-finder")
        err    = ctypes.windll.kernel32.GetLastError()
        return err != 183   # ERROR_ALREADY_EXISTS
    else:
        lock_path = Path("/tmp/ioc-finder.lock")
        try:
            pid_str = lock_path.read_text() if lock_path.exists() else ""
            if pid_str:
                try:
                    os.kill(int(pid_str), 0)
                    return False   # process is alive → already running
                except (ProcessLookupError, ValueError):
                    pass  # stale lock
            lock_path.write_text(str(os.getpid()))
            return True
        except OSError:
            return True  # can't create lock — proceed anyway


def _banner() -> str:
    return (
        "\n"
        "██╗  ██████╗  ██████╗    ███████╗██╗███╗   ██╗██████╗ ███████╗██████╗ \n"
        "██║██╔═══██╗██╔════╝    ██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔══██╗\n"
        "██║██║   ██║██║         █████╗  ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝\n"
        "██║██║   ██║██║         ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗\n"
        "██║╚██████╔╝╚██████╗    ███████╗██║██║ ╚████║██████╔╝███████╗██║  ██║\n"
        "╚═╝ ╚═════╝  ╚═════╝    ╚══════╝╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝\n"
        "\n"
        f"  {TOOL_NAME} v{TOOL_VERSION}  ·  YARA v{YARA_VERSION}\n"
        "  Incident Response  ·  Threat Hunting  ·  Live Forensics\n"
        "  github.com/nycthunter\n"
    )


# ── Rich TUI ───────────────────────────────────────────────────────────────────

def _run_tui(config: Configuration, config_path: str,
             triage: bool, root_path: str, verbosity: int) -> None:
    """Run the scan inside a Rich Live three-panel TUI dashboard."""
    global _tui_active
    _tui_active = True

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="errors",  ratio=1),
        Layout(name="matches", ratio=1),
        Layout(name="log",     ratio=2),
    )

    def _render():
        layout["header"].update(
            Panel(
                Text(f"{TOOL_NAME} v{TOOL_VERSION}  ·  YARA v{YARA_VERSION}  |  "
                     "Incident Response · Threat Hunting · Live Forensics",
                     justify="center"),
                style="bold yellow", box=box.HORIZONTALS,
            )
        )
        layout["errors"].update(
            Panel("\n".join(_buf_errors[-30:]),
                  title="[red]Errors & Warnings[/red]", border_style="red")
        )
        layout["matches"].update(
            Panel("\n".join(_buf_matches[-30:]),
                  title="[yellow]Matches & Alerts[/yellow]", border_style="yellow")
        )
        layout["log"].update(
            Panel("\n".join(_buf_log[-50:]),
                  title="[cyan]Execution Log[/cyan]", border_style="cyan")
        )
        layout["footer"].update(
            Panel("[grey50]Ctrl+C to exit[/grey50]", box=box.HORIZONTALS)
        )
        return layout

    import threading
    done = threading.Event()

    def _scan_thread():
        _main_routine(config, config_path, triage, verbosity, root_path)
        done.set()

    t = threading.Thread(target=_scan_thread, daemon=True)
    t.start()

    console = Console()
    with Live(_render(), console=console, refresh_per_second=4, screen=True) as live:
        while not done.is_set():
            live.update(_render())
            time.sleep(0.25)
        live.update(_render())
        time.sleep(1)

    _tui_active = False


# ── Config file picker (no-TUI fallback) ──────────────────────────────────────

def _pick_config_file() -> str:
    """Interactive file picker when no -c flag is provided (plain console)."""
    cwd = Path.cwd()
    yamls = sorted(cwd.rglob("*.yaml")) + sorted(cwd.rglob("*.yml"))
    if not yamls:
        print("No YAML files found in the current directory.")
        sys.exit(1)
    print("\nAvailable configuration files:")
    for i, p in enumerate(yamls):
        print(f"  [{i}] {p.relative_to(cwd)}")
    try:
        choice = int(input("\nSelect a file by number: "))
        return str(yamls[choice])
    except (ValueError, IndexError, KeyboardInterrupt):
        print("No file selected. Exiting.")
        sys.exit(1)


# ── Core scan orchestration ────────────────────────────────────────────────────

def _main_routine(config: Configuration, config_path: str,
                  triage: bool, verbosity: int, root_path: str) -> None:
    """Full scan lifecycle: init → YARA compile → memory → file scan → report."""
    start_time = time.monotonic()
    total_scanned = total_matches = total_errors = 0

    # ── Init log ──────────────────────────────────────────────────────────────
    log("info", f"(INIT) {TOOL_NAME} v{TOOL_VERSION} | YARA v{YARA_VERSION}")
    log("info", f"(INIT) OS: {platform.system()} {platform.machine()}")
    log("info", f"(INIT) Host: {get_hostname()}  User: {get_username()}")
    log("info", f"(INIT) Max file size: {config.advancedparameters.maxScanFilesize} MB")
    log("info", f"(INIT) Config: {config_path}")
    sha = file_sha256(config_path)
    if sha:
        log("info", f"(INIT) Config SHA256: {sha}")

    # ── Event forwarding ──────────────────────────────────────────────────────
    fwd = None
    if config.eventforwarding.enabled:
        fwd = init_forwarding(config.eventforwarding)
        if fwd:
            fwd.forward("scan_start", "info", f"{TOOL_NAME} scan started",
                        {"config_path": config_path, "version": TOOL_VERSION})

    # ── Validate input ────────────────────────────────────────────────────────
    has_input = (config.input.path or config.input.content.grep
                 or config.input.content.checksum or config.input.content.yara)
    if not has_input:
        log("error", "(ERROR) No input criteria defined in configuration")
        sys.exit(1)

    # ── YARA compilation ──────────────────────────────────────────────────────
    rules = None
    if config.input.content.yara:
        rules = compile_yara_rules(
            config.input.content.yara,
            config.advancedparameters.yaraRC4Key,
        )

    # ── Process memory scan ───────────────────────────────────────────────────
    if config.options.findInMemory:
        mem_matches = scan_memory(rules, config.input.content.grep)
        total_matches += len(mem_matches)
        for m in mem_matches:
            log("alert", f"(MATCH) {m}")

    # ── Resolve drives / base paths ───────────────────────────────────────────
    base_paths: List[str] = []
    excluded:   List[str] = []

    if root_path:
        log("info", f"(INIT) Custom scan root: {root_path}")
        base_paths = [root_path]
    elif config.input.direct_paths:
        log("info", "(INIT) Using direct paths from configuration")
        # Scan direct files immediately without the pipeline
        for dp in config.input.direct_paths:
            if os.path.isfile(dp):
                log("info", f"(SCAN) Direct file: {dp}")
                try:
                    hits = scan_file(
                        dp,
                        config.input.content.grep,
                        rules,
                        config.input.content.checksum,
                        config.advancedparameters.maxScanFilesize,
                    )
                    total_scanned += 1
                    for h in hits:
                        log("alert", f"(MATCH) {h}")
                        if config.output.copyMatchingFiles:
                            file_copy(h, config.output.filesCopyPath,
                                      config.output.base64Files)
                    total_matches += len(hits)
                except Exception as exc:
                    log("error", f"(ERROR) {dp}: {exc}")
                    total_errors += 1
            elif os.path.isdir(dp):
                base_paths.append(dp)
    else:
        all_drives, excluded = enumerate_drives()
        want = {
            DRIVE_FIXED:     config.options.findInHardDrives,
            DRIVE_REMOVABLE: config.options.findInRemovableDrives,
            DRIVE_REMOTE:    config.options.findInNetworkDrives,
            DRIVE_CDROM:     config.options.findInCDRomDrives,
        }
        base_paths = [d.path for d in all_drives if want.get(d.kind, False)]
        if not base_paths:
            log("error", "(ERROR) No drives match the configured drive-type filters")
            sys.exit(1)
        for p in base_paths:
            log("info", f" | {p}")

    # ── Compile path regex patterns ───────────────────────────────────────────
    path_patterns = [convert_glob_to_regex(p) for p in config.input.path]

    # ── Triage (continuous watch) mode ────────────────────────────────────────
    if triage:
        if not WATCHDOG_OK:
            log("error", "(ERROR) 'watchdog' is not installed — pip install watchdog")
            sys.exit(1)
        _run_triage(config, rules, base_paths, excluded, path_patterns)
        return

    # ── One-shot scan ─────────────────────────────────────────────────────────
    for base in base_paths:
        log("info", f"(SCAN) Starting scan in: {base}")
        pipeline = ScannerPipeline(workers=8)
        matches = pipeline.run(
            base_paths         = [base],
            excluded           = excluded,
            path_patterns      = path_patterns,
            patterns           = config.input.content.grep,
            rules              = rules,
            hash_list          = config.input.content.checksum,
            max_mb             = config.advancedparameters.maxScanFilesize,
            content_needs_path = config.options.contentMatchDependsOnPathMatch,
        )

        total_scanned += pipeline.stats.files_scanned
        total_errors  += pipeline.stats.errors_encountered
        total_matches += len(matches)

        log("info", f"(INFO) Scan complete for {base}")
        if matches:
            log("alert", f"(MATCH) {len(matches)} matching file(s):")
            for m in matches:
                log("alert", f"  | {m}")
            if config.output.copyMatchingFiles:
                log("info", f"(INFO) Copying matches to {config.output.filesCopyPath}")
                for m in matches:
                    file_copy(m, config.output.filesCopyPath, config.output.base64Files)
        else:
            log("info", "(INFO) No matches found")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.monotonic() - start_time
    summary = (f"(DONE) Scan finished in {elapsed:.2f}s — "
               f"Files: {total_scanned} | Matches: {total_matches} | Errors: {total_errors}")
    log("alert", summary)

    if fwd:
        fwd.forward_scan_complete(total_scanned, total_matches, total_errors, elapsed)
        stop_forwarding()


# ── Triage mode ────────────────────────────────────────────────────────────────

def _run_triage(config: Configuration, rules, base_paths: List[str],
                excluded: List[str], path_patterns) -> None:
    """Watch configured directories indefinitely and scan new/modified files."""

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            path = event.src_path
            log("verbose", f"(TRIAGE) Change detected: {path}")
            time.sleep(0.5)
            try:
                matches = scan_file(
                    path,
                    config.input.content.grep,
                    rules,
                    config.input.content.checksum,
                    config.advancedparameters.maxScanFilesize,
                    triage=True,
                )
                for m in matches:
                    log("alert", f"(MATCH) {m}")
                    if config.output.copyMatchingFiles:
                        file_copy(m, config.output.filesCopyPath, config.output.base64Files)
            except Exception as exc:
                log("error", f"(ERROR) Triage scan failed on {path}: {exc}")

    observer = Observer()
    watch_count = 0
    for base in base_paths:
        for root, dirs, _ in os.walk(base, followlinks=False):
            dirs[:] = [d for d in dirs
                       if not any(os.path.join(root, d).startswith(ex)
                                  for ex in excluded if ex)]
            # Only watch directories that match at least one path pattern (or all if none)
            if path_patterns:
                norm = root.replace("\\", "/").lower()
                if not any(p.search(norm) for p in path_patterns):
                    continue
            observer.schedule(_Handler(), root, recursive=False)
            watch_count += 1

    log("info", f"(TRIAGE) Watching {watch_count} directories — press Ctrl+C to stop")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog        = "ioc-finder",
        description = (f"{TOOL_NAME} v{TOOL_VERSION}  ·  YARA v{YARA_VERSION}\n"
                       "Incident Response · Threat Hunting · Live Forensics"),
        formatter_class = argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-c", "--configuration", default="",
                   help="Path or URL to a YAML configuration file")
    p.add_argument("-r", "--root", default="",
                   help="Override drive enumeration — scan a specific directory")
    p.add_argument("-s", "--silent", action="store_true",
                   help="Silent mode — no console output (event forwarding still active)")
    p.add_argument("-v", "--verbosity", type=int, default=4, metavar="1-5",
                   help="Log verbosity: 1=alerts 2=+warnings 3=+errors 4=+info (default) 5=debug")
    p.add_argument("-t", "--triage", action="store_true",
                   help="Triage mode — watch paths indefinitely for new/modified files")
    p.add_argument("-l", "--logfile", default="",
                   help="Write structured log output to a file")
    p.add_argument("--no-tui", action="store_true",
                   help="Disable Rich TUI and use plain console output")
    return p


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    # ── Verbosity / logging ───────────────────────────────────────────────────
    if args.silent:
        set_verbosity(0)
    elif 1 <= args.verbosity <= 5:
        set_verbosity(args.verbosity)

    if args.logfile:
        open_log_file(args.logfile)

    # ── Single-instance guard ─────────────────────────────────────────────────
    if not _check_single_instance():
        log("error", f"(ERROR) Another {TOOL_NAME} instance is already running")
        sys.exit(1)

    # ── Config file selection ─────────────────────────────────────────────────
    config_path = args.configuration.strip()
    has_args = len(sys.argv) > 1

    if not config_path and has_args:
        log("error", "(ERROR) No configuration file specified. Use -c <config.yaml>")
        sys.exit(1)

    if not config_path:
        # No args at all → interactive picker
        if RICH_OK and not args.no_tui:
            config_path = Prompt.ask(
                "[yellow]No config specified.[/yellow] Enter path to YAML config"
            )
        else:
            config_path = _pick_config_file()

    # ── Load configuration ────────────────────────────────────────────────────
    try:
        config = load_configuration(config_path)
    except Exception as exc:
        log("error", f"(ERROR) Failed to load configuration: {exc}")
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────
    use_tui = (RICH_OK and not args.silent and not args.no_tui and bool(config_path))

    if not args.silent:
        if not use_tui:
            print(_banner())

    if use_tui:
        _run_tui(config, config_path, args.triage, args.root, args.verbosity)
    else:
        _main_routine(config, config_path, args.triage, args.verbosity, args.root)


if __name__ == "__main__":
    main()
