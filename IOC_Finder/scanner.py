"""
scanner.py — IOC-Finder core scanning engine.
Covers: file enumeration (threaded), YARA, MD5/SHA1/SHA256, grep, process memory,
        ZIP archive deep-scan, and the ScannerPipeline orchestrator.
"""

from __future__ import annotations
import gc
import hashlib
import io
import os
import queue
import re
import sys
import threading
import time
import zipfile
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

# Optional heavy dependencies
try:
    import yara as _yara
    YARA_OK = True
except ImportError:
    _yara = None           # type: ignore
    YARA_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    psutil = None          # type: ignore
    PSUTIL_OK = False

from config import rc4_cipher
from events import get_forwarder

# ── YARA helpers ───────────────────────────────────────────────────────────────

def compile_yara_rules(yara_paths: List[str], rc4_key: str = "") -> Optional[object]:
    """Compile YARA rules from local files, directories, or URLs."""
    if not YARA_OK:
        _log_err("yara-python not installed — pip install yara-python")
        return None

    import requests

    sources: Dict[str, str] = {}   # namespace → rule text
    loaded = 0

    for path in yara_paths:
        path = path.strip()
        if not path:
            continue

        # Expand directories to .yar/.yara files
        candidates: List[str] = []
        if path.startswith(("http://", "https://")):
            candidates = [path]
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for fn in files:
                    if fn.endswith((".yar", ".yara")):
                        candidates.append(os.path.join(root, fn))
        elif os.path.isfile(path):
            candidates = [path]

        for c in candidates:
            try:
                if c.startswith(("http://", "https://")):
                    raw = requests.get(c, timeout=30).content
                    ns  = os.path.splitext(os.path.basename(c))[0]
                else:
                    with open(c, "rb") as fh:
                        raw = fh.read()
                    ns = os.path.splitext(os.path.basename(c))[0]

                # Decrypt if ciphered
                if rc4_key and b"rule" not in raw:
                    raw = rc4_cipher(raw, rc4_key)

                sources[ns] = raw.decode("utf-8", errors="replace")
                loaded += 1
            except Exception as exc:
                _log_err(f"Could not load YARA rule {c}: {exc}")

    if not sources:
        _log_err("No YARA rules loaded — check configuration paths")
        return None

    try:
        rules = _yara.compile(sources=sources)
        _log_info(f"Compiled {loaded} YARA rule file(s)")
        return rules
    except Exception as exc:
        _log_err(f"YARA compilation failed: {exc}")
        return None


def yara_scan(data: bytes, rules: object) -> List[dict]:
    """
    Run compiled YARA rules against a byte buffer.
    Returns list of match dicts: {namespace, rule, strings}.
    """
    if rules is None or not YARA_OK:
        return []
    try:
        matches = rules.match(data=data)
        return [
            {
                "namespace": m.namespace,
                "rule":      m.rule,
                "strings":   [
                    {"name": s.identifier, "offset": s.instances[0].offset}
                    for s in m.strings if s.instances
                ],
            }
            for m in matches
        ]
    except Exception:
        return []


# ── Hash helpers ───────────────────────────────────────────────────────────────

def file_sha256(path: str) -> str:
    """Return the SHA-256 hex digest of a file, or '' on error."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _compute_hashes(data: bytes) -> Tuple[str, str, str]:
    return (
        hashlib.md5(data).hexdigest(),
        hashlib.sha1(data).hexdigest(),
        hashlib.sha256(data).hexdigest(),
    )


# ── Single-file content scan ───────────────────────────────────────────────────

def scan_file_content(
    path:            str,
    data:            bytes,
    patterns:        List[str],
    rules:           Optional[object],
    hash_list:       List[str],
) -> List[str]:
    """
    Scan file bytes for grep patterns, hash matches, and YARA rules.
    Returns list of matched file paths (may be path itself or archive member path).
    """
    fwd = get_forwarder()
    matched: List[str] = []
    size = len(data)

    # ── Hash check ────────────────────────────────────────────────────────────
    if hash_list:
        md5, sha1, sha256 = _compute_hashes(data)
        for h in (md5, sha1, sha256):
            if h in hash_list:
                _log_alert(f"(ALERT) Checksum match [{h}] in {path}")
                if fwd:
                    fwd.forward_checksum(h, path, size)
                if path not in matched:
                    matched.append(path)

    # ── Grep check ────────────────────────────────────────────────────────────
    if patterns:
        try:
            text  = data.decode("utf-8", errors="replace")
            lines = text.splitlines()
        except Exception:
            lines = []
        for expr in patterns:
            for lineno, line in enumerate(lines, 1):
                if expr in line:
                    _log_alert(f"(ALERT) Grep match [{expr}] in {path} at line {lineno}")
                    if fwd:
                        fwd.forward_grep(expr, path, size, {"line_number": str(lineno)})
                    if path not in matched:
                        matched.append(path)
                    break

    # ── YARA check ────────────────────────────────────────────────────────────
    if rules:
        hits = yara_scan(data, rules)
        for hit in hits:
            msg = f"(ALERT) YARA match | path: {path} | ns: {hit['namespace']} | rule: {hit['rule']}"
            _log_alert(msg)
            if fwd:
                fwd.forward_alert(hit["rule"], path, size, "", {"rule_namespace": hit["namespace"]})
            if path not in matched:
                matched.append(path)

    return matched


def scan_file(
    path:              str,
    patterns:          List[str],
    rules:             Optional[object],
    hash_list:         List[str],
    max_mb:            int,
    triage:            bool = False,
) -> List[str]:
    """Read a file and run all content checks. Returns matched paths."""
    try:
        data = open(path, "rb").read()
    except OSError:
        if triage:
            time.sleep(0.5)
            try:
                data = open(path, "rb").read()
            except OSError:
                _log_err(f"(ERROR) Cannot read: {path}")
                return []
        else:
            _log_err(f"(ERROR) Cannot read: {path}")
            return []

    if len(data) > max_mb * 1024 * 1024:
        _log_warn(f"(WARNING) Skipping {path} — exceeds {max_mb} MB")
        return []

    results = scan_file_content(path, data, patterns, rules, hash_list)

    # ── ZIP deep-scan ─────────────────────────────────────────────────────────
    try:
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                for member in zf.infolist():
                    try:
                        mdata = zf.read(member.filename)
                        mpath = f"{path}::{member.filename}"
                        for r in scan_file_content(mpath, mdata, patterns, rules, hash_list):
                            if r not in results:
                                results.append(r)
                    except Exception:
                        pass
    except Exception:
        pass

    return results


# ── Scanner pipeline (concurrent) ─────────────────────────────────────────────

@dataclass
class ScanStats:
    files_scanned:      int = 0
    matches_found:      int = 0
    errors_encountered: int = 0

    def __post_init__(self):
        self._lock = threading.Lock()

    def add_scanned(self, n: int = 1):
        with self._lock:
            self.files_scanned += n

    def add_match(self, n: int = 1):
        with self._lock:
            self.matches_found += n

    def add_error(self, n: int = 1):
        with self._lock:
            self.errors_encountered += n


class ScannerPipeline:
    """
    Concurrent pipeline: producer threads enumerate files, consumer threads scan them.
    Call run() and iterate matches via get_matches().
    """

    def __init__(self, workers: int = 8):
        self._workers     = workers
        self._file_q:     queue.Queue = queue.Queue(maxsize=2000)
        self._match_q:    queue.Queue = queue.Queue()
        self.stats        = ScanStats()
        self._seen:       Set[str]    = set()
        self._seen_lock   = threading.Lock()

    # ── Enumeration ────────────────────────────────────────────────────────────

    def _enumerate(self, base_paths: List[str], excluded: List[str]) -> None:
        for base in base_paths:
            for root, dirs, files in os.walk(base, followlinks=False):
                # Prune excluded dirs in-place
                dirs[:] = [
                    d for d in dirs
                    if not any(
                        os.path.join(root, d).startswith(ex)
                        for ex in excluded if len(ex) > 1
                    )
                ]
                for fn in files:
                    self._file_q.put(os.path.join(root, fn))
        # Signal end
        for _ in range(self._workers):
            self._file_q.put(None)

    # ── Scanning workers ───────────────────────────────────────────────────────

    def _scan_worker(
        self,
        path_patterns:    List[re.Pattern],
        patterns:         List[str],
        rules:            Optional[object],
        hash_list:        List[str],
        max_mb:           int,
        content_needs_path: bool,
    ) -> None:
        while True:
            path = self._file_q.get()
            if path is None:
                break
            self.stats.add_scanned()

            # ── Path pattern matching ─────────────────────────────────────────
            path_match = False
            if path_patterns:
                norm = path.replace("\\", "/").lower()
                path_match = any(p.search(norm) for p in path_patterns)

                if not content_needs_path and path_match:
                    _log_alert(f"(ALERT) Path match: {path}")
                    self._emit(path)

            has_content = bool(patterns or hash_list or rules)
            if has_content:
                # Skip content scan if content depends on path match but path didn't match
                if content_needs_path and path_patterns and not path_match:
                    continue
                try:
                    for m in scan_file(path, patterns, rules, hash_list, max_mb):
                        self._emit(m)
                except Exception as exc:
                    _log_err(f"(ERROR) Scan error on {path}: {exc}")
                    self.stats.add_error()
            elif path_patterns and not path_match:
                pass  # pure path scan, no match

        self._match_q.put(None)  # signal this worker is done

    def _emit(self, path: str) -> None:
        with self._seen_lock:
            if path not in self._seen:
                self._seen.add(path)
                self._match_q.put(path)
                self.stats.add_match()

    # ── Public interface ───────────────────────────────────────────────────────

    def run(
        self,
        base_paths:         List[str],
        excluded:           List[str],
        path_patterns:      List[re.Pattern],
        patterns:           List[str],
        rules:              Optional[object],
        hash_list:          List[str],
        max_mb:             int,
        content_needs_path: bool,
    ) -> List[str]:
        """
        Execute the full scan and return all matched file paths.
        Blocking — runs enumeration + scanning concurrently, waits for completion.
        """
        # Start file enumeration thread
        enum_thread = threading.Thread(
            target=self._enumerate, args=(base_paths, excluded), daemon=True
        )
        enum_thread.start()

        # Start scanner worker threads
        worker_threads = []
        for _ in range(self._workers):
            t = threading.Thread(
                target=self._scan_worker,
                args=(path_patterns, patterns, rules, hash_list, max_mb, content_needs_path),
                daemon=True,
            )
            t.start()
            worker_threads.append(t)

        # Collect matches until all workers signal done
        matches: List[str] = []
        done_workers = 0
        while done_workers < self._workers:
            item = self._match_q.get()
            if item is None:
                done_workers += 1
            else:
                matches.append(item)

        enum_thread.join()
        for t in worker_threads:
            t.join()

        return matches


# ── Process memory scan ────────────────────────────────────────────────────────

def scan_memory(rules: Optional[object], patterns: List[str]) -> List[str]:
    """
    Enumerate running processes, dump readable memory regions, and scan
    them with YARA rules and/or grep patterns.
    Returns list of match strings in the form "MEMORY:<process>:<pid>".
    """
    if not PSUTIL_OK:
        _log_err("psutil not installed — pip install psutil")
        return []

    matches: List[str] = []
    _log_info("(INIT) Starting process memory scan...")

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid  = proc.info["pid"]
            name = proc.info["name"] or "unknown"
            label = f"MEMORY:{name}:{pid}"

            dump = _read_process_memory(pid)
            if not dump:
                continue

            _log_verbose(f"(MEMORY) Scanning process: {name} (PID {pid})")
            result = scan_file_content(label, dump, patterns, rules, [])
            matches.extend(result)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        finally:
            gc.collect()

    _log_info("(INFO) Memory scan complete")
    return matches


def _read_process_memory(pid: int) -> bytes:
    """
    Attempt to read readable memory pages of a process.
    Returns a best-effort byte dump (empty on failure).
    Works on Linux (/proc/<pid>/maps + mem) and Windows (ctypes ReadProcessMemory).
    """
    if sys.platform.startswith("linux"):
        return _read_linux_proc_mem(pid)
    elif sys.platform == "win32":
        return _read_windows_proc_mem(pid)
    return b""


def _read_linux_proc_mem(pid: int) -> bytes:
    buf = bytearray()
    try:
        maps_path = f"/proc/{pid}/maps"
        mem_path  = f"/proc/{pid}/mem"
        with open(maps_path, "r") as mf, open(mem_path, "rb", 0) as memf:
            for line in mf:
                parts = line.split()
                if not parts or "r" not in parts[1]:
                    continue
                try:
                    start, end = (int(x, 16) for x in parts[0].split("-"))
                    memf.seek(start)
                    chunk = memf.read(min(end - start, 4 * 1024 * 1024))
                    buf.extend(chunk)
                except Exception:
                    pass
    except Exception:
        pass
    return bytes(buf)


def _read_windows_proc_mem(pid: int) -> bytes:
    import ctypes
    import ctypes.wintypes as wt

    PROCESS_VM_READ      = 0x0010
    PROCESS_QUERY_INFO   = 0x0400
    MEM_COMMIT           = 0x1000
    PAGE_NOACCESS        = 0x01
    PAGE_GUARD           = 0x100

    k32  = ctypes.windll.kernel32
    hProc = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pid)
    if not hProc:
        return b""

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress",       ctypes.c_void_p),
            ("AllocationBase",    ctypes.c_void_p),
            ("AllocationProtect", wt.DWORD),
            ("RegionSize",        ctypes.c_size_t),
            ("State",             wt.DWORD),
            ("Protect",           wt.DWORD),
            ("Type",              wt.DWORD),
        ]

    buf = bytearray()
    addr = 0
    mbi  = MEMORY_BASIC_INFORMATION()

    while k32.VirtualQueryEx(hProc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        readable = (
            mbi.State == MEM_COMMIT
            and not (mbi.Protect & PAGE_NOACCESS)
            and not (mbi.Protect & PAGE_GUARD)
        )
        if readable and mbi.RegionSize > 0:
            chunk = ctypes.create_string_buffer(min(mbi.RegionSize, 4 * 1024 * 1024))
            read  = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), chunk, len(chunk), ctypes.byref(read)):
                buf.extend(chunk.raw[: read.value])
        addr += mbi.RegionSize or 1
        if addr > 0x7FFFFFFFFFFF:
            break

    k32.CloseHandle(hProc)
    return bytes(buf)


# ── Drive enumeration ──────────────────────────────────────────────────────────

DRIVE_FIXED     = "fixed"
DRIVE_REMOVABLE = "removable"
DRIVE_REMOTE    = "remote"
DRIVE_CDROM     = "cdrom"


@dataclass
class DriveInfo:
    path: str
    kind: str   # fixed | removable | remote | cdrom


def enumerate_drives() -> Tuple[List[DriveInfo], List[str]]:
    """
    Return (drives, excluded_paths) for the current platform.
    """
    if sys.platform == "win32":
        return _windows_drives()
    return _linux_drives()


def _windows_drives() -> Tuple[List[DriveInfo], List[str]]:
    import ctypes
    drives: List[DriveInfo] = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    TYPE_MAP = {2: DRIVE_REMOVABLE, 3: DRIVE_FIXED, 4: DRIVE_REMOTE, 5: DRIVE_CDROM}
    for i in range(26):
        if bitmask & (1 << i):
            letter = chr(ord("A") + i) + ":\\"
            t = ctypes.windll.kernel32.GetDriveTypeW(letter)
            kind = TYPE_MAP.get(t)
            if kind:
                drives.append(DriveInfo(letter, kind))
    return drives, []


def _linux_drives() -> Tuple[List[DriveInfo], List[str]]:
    excluded = ["/dev", "/proc", "/sys", "/run", "/snap"]
    drives: List[DriveInfo] = []
    if not PSUTIL_OK:
        drives.append(DriveInfo("/", DRIVE_FIXED))
        return drives, excluded

    seen: Set[str] = set()
    for part in psutil.disk_partitions(all=False):
        mp = part.mountpoint
        if mp in seen or not os.path.isdir(mp):
            continue
        seen.add(mp)
        fs = part.fstype.lower()
        if "nfs" in fs or "smb" in fs or "cifs" in fs or "fuse.s3fs" in fs:
            drives.append(DriveInfo(mp, DRIVE_REMOTE))
        elif "iso9660" in fs or "udf" in fs:
            drives.append(DriveInfo(mp, DRIVE_CDROM))
        elif any(x in mp for x in ("/media/", "/mnt/usb", "/run/media")):
            drives.append(DriveInfo(mp, DRIVE_REMOVABLE))
        else:
            drives.append(DriveInfo(mp, DRIVE_FIXED))

    if not drives:
        drives.append(DriveInfo("/", DRIVE_FIXED))
    return drives, excluded


# ── Internal log shims (replaced by ioc_finder.py's real logger) ───────────────

def _log_alert(msg: str):   _LOGGER("alert",   msg)
def _log_warn(msg: str):    _LOGGER("warning", msg)
def _log_err(msg: str):     _LOGGER("error",   msg)
def _log_info(msg: str):    _LOGGER("info",    msg)
def _log_verbose(msg: str): _LOGGER("verbose", msg)


def _default_logger(level: str, msg: str):
    print(f"[{level.upper()}] {msg}", file=sys.stderr if level == "error" else sys.stdout)


_LOGGER: Callable[[str, str], None] = _default_logger


def set_logger(fn: Callable[[str, str], None]):
    """Allow ioc_finder.py to inject the real logger."""
    global _LOGGER
    _LOGGER = fn
