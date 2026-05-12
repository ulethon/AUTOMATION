"""
events.py — IOC-Finder event forwarding.
Supports HTTP POST (with retry) and rotating JSONL file output.
"""

from __future__ import annotations
import glob
import json
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from config import EventForwardingConfig

TOOL_VERSION = "3.6.0"


# ── Event data structures ──────────────────────────────────────────────────────

@dataclass
class ScanResultsEvent:
    files_scanned:       int = 0
    matches_found:       int = 0
    errors_encountered:  int = 0
    scan_duration_seconds: int = 0


@dataclass
class IOCEvent:
    timestamp:    str               = ""
    hostname:     str               = ""
    event_type:   str               = ""   # alert | error | warning | info | scan_start | scan_complete
    severity:     str               = ""   # low | medium | high
    message:      str               = ""
    file_path:    str               = ""
    rule_name:    str               = ""
    file_size:    int               = 0
    file_hash:    str               = ""
    config_path:  str               = ""
    metadata:     Dict[str, str]    = field(default_factory=dict)
    scan_results: Optional[ScanResultsEvent] = None


def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _event_to_dict(e: IOCEvent) -> dict:
    d: dict = {
        "timestamp":  e.timestamp,
        "hostname":   e.hostname,
        "event_type": e.event_type,
        "severity":   e.severity,
        "message":    e.message,
    }
    if e.file_path:    d["file_path"]   = e.file_path
    if e.rule_name:    d["rule_name"]   = e.rule_name
    if e.file_size:    d["file_size"]   = e.file_size
    if e.file_hash:    d["file_hash"]   = e.file_hash
    if e.config_path:  d["config_path"] = e.config_path
    if e.metadata:     d["metadata"]    = e.metadata
    if e.scan_results:
        d["scan_results"] = {
            "files_scanned":        e.scan_results.files_scanned,
            "matches_found":        e.scan_results.matches_found,
            "errors_encountered":   e.scan_results.errors_encountered,
            "scan_duration_seconds": e.scan_results.scan_duration_seconds,
        }
    return d


# ── EventForwarder ─────────────────────────────────────────────────────────────

class EventForwarder:
    """
    Thread-safe event forwarder that buffers IOCEvents and periodically
    flushes them to configured HTTP and/or JSONL-file outputs.
    """

    def __init__(self, config: EventForwardingConfig):
        self._cfg       = config
        self._queue:    List[IOCEvent] = []
        self._lock      = threading.Lock()
        self._file_lock = threading.Lock()
        self._stop      = threading.Event()
        self._hostname  = socket.gethostname() or "unknown"

        # File output state
        self._cur_file:      Optional[object] = None
        self._cur_file_path: str              = ""
        self._last_rotation: datetime         = datetime.utcnow()

        # Background flush thread
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    # ── Public API ─────────────────────────────────────────────────────────────

    def forward(self, event_type: str, severity: str, message: str,
                metadata: Optional[Dict] = None) -> None:
        if not self._cfg.enabled:
            return
        allowed = self._cfg.filters.event_types
        if allowed and event_type not in allowed:
            return
        ev = IOCEvent(
            timestamp  = _now_ts(),
            hostname   = self._hostname,
            event_type = event_type,
            severity   = severity,
            message    = message,
            metadata   = metadata or {},
        )
        with self._lock:
            self._queue.append(ev)
            if len(self._queue) >= self._cfg.buffer_size:
                self._flush_unlocked()

    def forward_alert(self, rule: str, path: str, size: int,
                      hash_: str, meta: Optional[Dict] = None) -> None:
        m = dict(meta or {})
        m.update({"rule_name": rule, "file_path": path, "file_size": str(size)})
        if hash_:
            m["file_hash"] = hash_
        self.forward("alert", "high", f"YARA match: {rule} in {path}", m)

    def forward_grep(self, pattern: str, path: str, size: int,
                     meta: Optional[Dict] = None) -> None:
        m = dict(meta or {})
        m.update({"grep_pattern": pattern, "file_path": path, "file_size": str(size)})
        self.forward("alert", "high", f"Grep match [{pattern}] in {path}", m)

    def forward_checksum(self, checksum: str, path: str, size: int,
                         meta: Optional[Dict] = None) -> None:
        m = dict(meta or {})
        m.update({"checksum": checksum, "file_path": path, "file_size": str(size)})
        self.forward("alert", "high", f"Checksum match [{checksum}] in {path}", m)

    def forward_scan_complete(self, scanned: int, matches: int,
                               errors: int, duration: float) -> None:
        ev = IOCEvent(
            timestamp    = _now_ts(),
            hostname     = self._hostname,
            event_type   = "scan_complete",
            severity     = "info",
            message      = f"Scan done — {scanned} files, {matches} matches",
            scan_results = ScanResultsEvent(scanned, matches, errors, int(duration)),
        )
        with self._lock:
            self._queue.append(ev)

    def stop(self) -> None:
        self._stop.set()
        self._flush()
        if self._cur_file:
            self._cur_file.close()
            self._cur_file = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _flush_loop(self) -> None:
        while not self._stop.wait(timeout=self._cfg.flush_time_seconds):
            self._flush()

    def _flush(self) -> None:
        with self._lock:
            self._flush_unlocked()

    def _flush_unlocked(self) -> None:
        if not self._queue:
            return
        batch = self._queue[:]
        self._queue.clear()

        if self._cfg.http.enabled and self._cfg.http.url:
            self._send_http(batch)
        if self._cfg.file.enabled:
            self._write_file(batch)

    def _send_http(self, batch: List[IOCEvent]) -> None:
        try:
            import requests
        except ImportError:
            return
        payload = json.dumps([_event_to_dict(e) for e in batch])
        hdrs = {
            "Content-Type": "application/json",
            "User-Agent":   f"IOC-Finder/{TOOL_VERSION}",
        }
        hdrs.update(self._cfg.http.headers)

        for attempt in range(self._cfg.http.retry_count + 1):
            try:
                resp = requests.post(
                    self._cfg.http.url, data=payload, headers=hdrs,
                    verify=self._cfg.http.ssl_verify,
                    timeout=self._cfg.http.timeout_seconds,
                )
                if resp.ok:
                    return
            except Exception:
                pass
            if attempt < self._cfg.http.retry_count:
                time.sleep(attempt + 1)

    def _write_file(self, batch: List[IOCEvent]) -> None:
        with self._file_lock:
            self._maybe_rotate()
            if self._cur_file is None:
                self._open_new_file()
            if self._cur_file:
                for ev in batch:
                    self._cur_file.write(json.dumps(_event_to_dict(ev)) + "\n")
                self._cur_file.flush()

    def _maybe_rotate(self) -> None:
        rotate = False
        now = datetime.utcnow()
        if self._cfg.file.rotate_minutes > 0:
            elapsed_min = (now - self._last_rotation).total_seconds() / 60
            if elapsed_min >= self._cfg.file.rotate_minutes:
                rotate = True
        if (not rotate and self._cfg.file.max_file_size_mb > 0
                and self._cur_file and os.path.exists(self._cur_file_path)):
            size_mb = os.path.getsize(self._cur_file_path) / (1024 * 1024)
            if size_mb >= self._cfg.file.max_file_size_mb:
                rotate = True
        if rotate:
            if self._cur_file:
                self._cur_file.close()
                self._cur_file = None
            self._clean_old_files()
            self._last_rotation = now

    def _open_new_file(self) -> None:
        os.makedirs(self._cfg.file.directory_path, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d%H%M")
        self._cur_file_path = os.path.join(
            self._cfg.file.directory_path, f"{ts}_ioc_finder_logs.jsonl"
        )
        self._cur_file = open(self._cur_file_path, "a", encoding="utf-8")

    def _clean_old_files(self) -> None:
        pattern = os.path.join(self._cfg.file.directory_path, "*_ioc_finder_logs.jsonl")
        files = sorted(glob.glob(pattern))
        keep = self._cfg.file.retain_files
        for old in files[: max(0, len(files) - keep + 1)]:
            try:
                os.remove(old)
            except OSError:
                pass


# ── Module-level singleton helpers ─────────────────────────────────────────────

_forwarder: Optional[EventForwarder] = None


def init_forwarding(config: EventForwardingConfig) -> Optional[EventForwarder]:
    global _forwarder
    if config.enabled:
        _forwarder = EventForwarder(config)
    return _forwarder


def get_forwarder() -> Optional[EventForwarder]:
    return _forwarder


def stop_forwarding() -> None:
    global _forwarder
    if _forwarder:
        _forwarder.stop()
        _forwarder = None
