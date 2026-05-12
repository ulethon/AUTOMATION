"""
config.py — IOC-Finder configuration loader.
Handles YAML parsing, RC4 decryption, path normalisation, and dataclass definitions.
"""

from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

# ── RC4 cipher (decrypt legacy configs / YARA rules) ──────────────────────────

BUILDER_RC4_KEY = ">Õ°ªKb{¡§ÌB$lMÕ±9l.tòÑé¦Ø¿"


def rc4_cipher(data: bytes, key: str) -> bytes:
    k = key.encode()
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + k[i % len(k)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) % 256])
    return bytes(out)


# ── Dataclasses mirroring the YAML schema ─────────────────────────────────────

@dataclass
class ContentConfig:
    grep:     List[str] = field(default_factory=list)
    yara:     List[str] = field(default_factory=list)
    checksum: List[str] = field(default_factory=list)


@dataclass
class InputConfig:
    path:    List[str]    = field(default_factory=list)
    content: ContentConfig = field(default_factory=ContentConfig)
    # populated at runtime when all paths are direct filesystem paths
    direct_paths: List[str] = field(default_factory=list)


@dataclass
class OptionsConfig:
    contentMatchDependsOnPathMatch: bool = False
    findInHardDrives:               bool = True
    findInRemovableDrives:          bool = True
    findInNetworkDrives:            bool = False
    findInCDRomDrives:              bool = False
    findInMemory:                   bool = False


@dataclass
class OutputConfig:
    copyMatchingFiles: bool = False
    base64Files:       bool = False
    filesCopyPath:     str  = "./"


@dataclass
class AdvancedConfig:
    yaraRC4Key:                        str = ""
    maxScanFilesize:                   int = 2048
    cleanMemoryIfFileGreaterThanSize:  int = 512


@dataclass
class HTTPConfig:
    enabled:          bool         = False
    url:              str          = ""
    ssl_verify:       bool         = True
    timeout_seconds:  int          = 10
    headers:          dict         = field(default_factory=dict)
    retry_count:      int          = 3


@dataclass
class FileOutputConfig:
    enabled:          bool = False
    directory_path:   str  = "./logs"
    rotate_minutes:   int  = 60
    max_file_size_mb: int  = 10
    retain_files:     int  = 10


@dataclass
class EventFilters:
    event_types: List[str] = field(
        default_factory=lambda: ["alert", "error", "warning", "info"]
    )


@dataclass
class EventForwardingConfig:
    enabled:             bool              = False
    buffer_size:         int               = 100
    flush_time_seconds:  int               = 10
    http:    HTTPConfig                    = field(default_factory=HTTPConfig)
    file:    FileOutputConfig              = field(default_factory=FileOutputConfig)
    filters: EventFilters                  = field(default_factory=EventFilters)


@dataclass
class Configuration:
    input:              InputConfig          = field(default_factory=InputConfig)
    options:            OptionsConfig        = field(default_factory=OptionsConfig)
    output:             OutputConfig         = field(default_factory=OutputConfig)
    advancedparameters: AdvancedConfig       = field(default_factory=AdvancedConfig)
    eventforwarding:    EventForwardingConfig = field(default_factory=EventForwardingConfig)


# ── Loader ─────────────────────────────────────────────────────────────────────

def _g(d: dict, *keys, default=None):
    """Safe nested dict getter."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d if d is not None else default


def load_configuration(config_path: str) -> Configuration:
    """
    Load an IOC-Finder YAML configuration from a local path or HTTP(S) URL.
    Handles RC4-encrypted configs, YARA path resolution, and environment
    variable expansion in path patterns.
    """
    config_path = config_path.strip()
    is_url = config_path.startswith(("http://", "https://"))
    config_base_dir = ""

    if not is_url:
        resolved = Path(config_path).resolve()
        config_path = str(resolved)
        config_base_dir = str(resolved.parent)

    # ── Read raw bytes ────────────────────────────────────────────────────────
    if is_url:
        import requests
        resp = requests.get(config_path, timeout=30)
        resp.raise_for_status()
        raw = resp.content
    else:
        with open(config_path, "rb") as fh:
            raw = fh.read()

    # ── Decrypt if RC4-ciphered ───────────────────────────────────────────────
    if b"input" not in raw:
        raw = rc4_cipher(raw, BUILDER_RC4_KEY)

    data: dict = yaml.safe_load(raw.decode("utf-8", errors="replace")) or {}

    cfg = Configuration()

    # ── Input ─────────────────────────────────────────────────────────────────
    inp = data.get("input") or {}
    cfg.input.path = list(_g(inp, "path", default=[]) or [])

    cnt = inp.get("content") or {}
    cfg.input.content.grep     = list(cnt.get("grep", [])     or [])
    cfg.input.content.yara     = list(cnt.get("yara", [])     or [])
    cfg.input.content.checksum = [c.lower() for c in (cnt.get("checksum", []) or [])]

    # ── Options ───────────────────────────────────────────────────────────────
    opt = data.get("options") or {}
    cfg.options.contentMatchDependsOnPathMatch = bool(opt.get("contentMatchDependsOnPathMatch", False))
    cfg.options.findInHardDrives               = bool(opt.get("findInHardDrives",      True))
    cfg.options.findInRemovableDrives          = bool(opt.get("findInRemovableDrives", True))
    cfg.options.findInNetworkDrives            = bool(opt.get("findInNetworkDrives",   False))
    cfg.options.findInCDRomDrives              = bool(opt.get("findInCDRomDrives",     False))
    cfg.options.findInMemory                   = bool(opt.get("findInMemory",          False))

    # ── Output ────────────────────────────────────────────────────────────────
    out = data.get("output") or {}
    cfg.output.copyMatchingFiles = bool(out.get("copyMatchingFiles", False))
    cfg.output.base64Files       = bool(out.get("base64Files",       False))
    cfg.output.filesCopyPath     = str( out.get("filesCopyPath", "./") or "./")
    if not cfg.output.copyMatchingFiles:
        cfg.output.base64Files   = False
        cfg.output.filesCopyPath = ""

    # ── Advanced ──────────────────────────────────────────────────────────────
    adv = data.get("advancedparameters") or {}
    cfg.advancedparameters.yaraRC4Key                       = str(adv.get("yaraRC4Key", ""))
    cfg.advancedparameters.maxScanFilesize                  = int(adv.get("maxScanFilesize", 2048) or 2048)
    cfg.advancedparameters.cleanMemoryIfFileGreaterThanSize = int(adv.get("cleanMemoryIfFileGreaterThanSize", 512) or 512)

    # ── Event forwarding ──────────────────────────────────────────────────────
    ef = data.get("eventforwarding") or {}
    cfg.eventforwarding.enabled            = bool(ef.get("enabled", False))
    cfg.eventforwarding.buffer_size        = int( ef.get("buffer_size", 100)        or 100)
    cfg.eventforwarding.flush_time_seconds = int( ef.get("flush_time_seconds", 10)  or 10)

    http = ef.get("http") or {}
    cfg.eventforwarding.http.enabled         = bool(http.get("enabled", False))
    cfg.eventforwarding.http.url             = str( http.get("url", ""))
    cfg.eventforwarding.http.ssl_verify      = bool(http.get("ssl_verify", True))
    cfg.eventforwarding.http.timeout_seconds = int( http.get("timeout_seconds", 10) or 10)
    cfg.eventforwarding.http.headers         = dict(http.get("headers", {}) or {})
    cfg.eventforwarding.http.retry_count     = int( http.get("retry_count", 3) or 3)

    fil = ef.get("file") or {}
    cfg.eventforwarding.file.enabled          = bool(fil.get("enabled", False))
    cfg.eventforwarding.file.directory_path   = str( fil.get("directory_path", "./logs") or "./logs")
    cfg.eventforwarding.file.rotate_minutes   = int( fil.get("rotate_minutes", 60)  or 60)
    cfg.eventforwarding.file.max_file_size_mb = int( fil.get("max_file_size_mb", 10) or 10)
    cfg.eventforwarding.file.retain_files     = int( fil.get("retain_files", 10)    or 10)

    flt = ef.get("filters") or {}
    cfg.eventforwarding.filters.event_types = list(
        flt.get("event_types", ["alert", "error", "warning", "info"]) or []
    )

    # ── Resolve YARA paths relative to config location ────────────────────────
    if config_base_dir:
        resolved_yara = []
        for yp in cfg.input.content.yara:
            yp = yp.strip()
            if not yp:
                continue
            if yp.startswith(("http://", "https://")) or os.path.isabs(yp):
                resolved_yara.append(yp)
            else:
                resolved_yara.append(str(Path(config_base_dir) / yp))
        cfg.input.content.yara = resolved_yara

    # ── Expand env vars and detect direct paths ───────────────────────────────
    expanded_paths = []
    direct_paths   = []
    all_direct     = True

    for p in cfg.input.path:
        p = os.path.expandvars(p)
        expanded_paths.append(p)
        is_regex    = p.startswith("/") and p.endswith("/")
        has_wildcard = any(c in p for c in ("*", "?"))
        if is_regex or has_wildcard:
            all_direct = False
        elif os.path.exists(p):
            direct_paths.append(p)
        else:
            all_direct = False

    cfg.input.path = expanded_paths

    # Separate direct file paths from direct directory paths
    direct_files = [p for p in direct_paths if os.path.isfile(p)]
    direct_dirs  = [p for p in direct_paths if os.path.isdir(p)]

    if all_direct and direct_paths:
        # Files stored separately so _main_routine can scan them directly
        cfg.input.direct_paths = direct_files + direct_dirs

    return cfg


def convert_glob_to_regex(pattern: str) -> re.Pattern:
    """
    Convert an IOC-Finder path pattern to a compiled regex.
    Supports: /regex/, glob wildcards (* ?), literal strings.
    All path separators are normalised to forward-slash before matching
    so both Windows and Linux paths work identically.
    Always case-insensitive.
    """
    if pattern.startswith("/") and pattern.endswith("/"):
        # Raw regex — user is responsible for separator handling
        return re.compile(pattern[1:-1], re.IGNORECASE)

    # Normalise separators to forward-slash (scanner does the same to test paths)
    pattern = pattern.replace("\\", "/").lower()
    escaped  = re.escape(pattern)
    # Restore glob wildcards after escaping
    escaped  = escaped.replace(r"\*", r"[^/]+")  # * = one path segment
    escaped  = escaped.replace(r"\?", r".")        # ? = single character
    return re.compile(escaped, re.IGNORECASE)
