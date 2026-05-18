"""
yara_engine.py — Core YARA Rule Generation Engine
Cross-platform shared logic for CLI and GUI tools.
"""

import re
import hashlib
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ─────────────────────────────────────────────
#  Enums & Constants
# ─────────────────────────────────────────────

class StringType(Enum):
    TEXT   = "text"
    HEX    = "hex"
    REGEX  = "regex"

class Modifier(Enum):
    NOCASE      = "nocase"
    WIDE        = "wide"
    ASCII       = "ascii"
    FULLWORD    = "fullword"
    XOR         = "xor"
    BASE64      = "base64"
    BASE64WIDE  = "base64wide"

class ConditionOperator(Enum):
    ANY         = "any of them"
    ALL         = "all of them"
    CUSTOM      = "custom"

YARA_META_KEYS = ["author", "description", "date", "version",
                  "hash", "reference", "severity", "tlp", "os", "tags"]

SEVERITY_LEVELS = ["informational", "low", "medium", "high", "critical"]
TLP_LEVELS      = ["WHITE", "GREEN", "AMBER", "RED"]

COMMON_MALWARE_STRINGS = {
    "Ransomware": [
        "Your files have been encrypted",
        "bitcoin",
        ".locked",
        "ransom",
        "decrypt",
        "All your files",
    ],
    "RAT / Backdoor": [
        "cmd.exe",
        "powershell",
        "CreateRemoteThread",
        "VirtualAllocEx",
        "WriteProcessMemory",
        "LoadLibraryA",
    ],
    "Keylogger": [
        "GetAsyncKeyState",
        "SetWindowsHookEx",
        "WH_KEYBOARD_LL",
        "keylog",
        "GetForegroundWindow",
    ],
    "Dropper / Loader": [
        "URLDownloadToFile",
        "WinExec",
        "ShellExecute",
        "CreateProcess",
        "ExpandEnvironmentStrings",
    ],
    "Persistence": [
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "schtasks",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    ],
    "Process Injection": [
        "OpenProcess",
        "VirtualAlloc",
        "WriteProcessMemory",
        "CreateRemoteThread",
        "NtUnmapViewOfSection",
    ],
    "Network C2": [
        "InternetOpen",
        "HttpSendRequest",
        "connect",
        "WSAStartup",
        "gethostbyname",
    ],
    "Web Shell (PHP/ASP/JSP)": [
        "eval(base64_decode(",
        "Request.Item[\"cmd\"]",
        "System.Diagnostics.Process.Start",
        "cmd.exe /c",
        "WScript.Shell",
        "java.lang.Runtime.getRuntime().exec",
    ],
    "PowerShell Obfuscation": [
        "System.Convert]::FromBase64String",
        "Invoke-Expression",
        "IEX",
        "Hidden -Command",
        "Bypass -File",
        "Net.WebClient",
    ],
    "Cobalt Strike Beacon": [
        "\\\\.\\pipe\\MSSE-",
        "\\\\.\\pipe\\status_",
        "beacon.dll",
        "ReflectiveLoader",
    ],
}

# ─────────────────────────────────────────────
#  Data Models
# ─────────────────────────────────────────────

@dataclass
class YaraString:
    name:      str
    value:     str
    stype:     StringType = StringType.TEXT
    modifiers: List[str]  = field(default_factory=list)
    comment:   str        = ""

    def render(self) -> str:
        if self.stype == StringType.HEX:
            val = f"{{ {self.value.strip()} }}"
        elif self.stype == StringType.REGEX:
            val = f"/{self.value}/"
        else:
            val = f'"{self.value}"'
        mods = (" " + " ".join(self.modifiers)) if self.modifiers else ""
        comment = f" // {self.comment}" if self.comment else ""
        return f"        ${self.name} = {val}{mods}{comment}"


@dataclass
class YaraRule:
    name:        str
    tags:        List[str]         = field(default_factory=list)
    meta:        Dict[str, str]    = field(default_factory=dict)
    strings:     List[YaraString]  = field(default_factory=list)
    condition:   str               = "any of them"
    imports:     List[str]         = field(default_factory=list)
    includes:    List[str]         = field(default_factory=list)


# ─────────────────────────────────────────────
#  Validation helpers
# ─────────────────────────────────────────────

def validate_rule_name(name: str) -> Optional[str]:
    """Returns error string or None if valid."""
    if not name:
        return "Rule name cannot be empty."
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        return "Rule name must start with a letter/underscore and contain only alphanumeric/underscore chars."
    if len(name) > 128:
        return "Rule name too long (max 128 chars)."
    return None

def validate_hex_string(value: str) -> Optional[str]:
    clean = re.sub(r'\s+', '', value)
    if not re.match(r'^[0-9A-Fa-f\?\[\]\|\(\)\{\}\-]+$', clean):
        return "Invalid hex string. Use hex digits, wildcards (?), jumps ([0-3]), or alternatives (|)."
    return None

def validate_regex_string(value: str) -> Optional[str]:
    try:
        re.compile(value)
        return None
    except re.error as e:
        return f"Invalid regex: {e}"

def validate_condition(condition: str) -> Optional[str]:
    if not condition.strip():
        return "Condition cannot be empty."
    return None


# ─────────────────────────────────────────────
#  Rule Builder
# ─────────────────────────────────────────────

class YaraRuleBuilder:
    def __init__(self):
        self.rule = YaraRule(name="NewRule")
        self._string_counter = 0
        self._category_counters = {}

    def set_name(self, name: str) -> "YaraRuleBuilder":
        err = validate_rule_name(name)
        if err:
            raise ValueError(err)
        self.rule.name = name
        return self

    def set_tags(self, tags: List[str]) -> "YaraRuleBuilder":
        self.rule.tags = [t.strip() for t in tags if t.strip()]
        return self

    def set_meta(self, key: str, value: str) -> "YaraRuleBuilder":
        self.rule.meta[key] = value
        return self

    def add_string(self, value: str, stype: StringType = StringType.TEXT,
                   modifiers: List[str] = None, name: str = None, comment: str = "") -> "YaraRuleBuilder":
        """Add a string with optional category/name identifier and inline comment."""
        if stype == StringType.HEX:
            err = validate_hex_string(value)
            if err:
                raise ValueError(err)
        elif stype == StringType.REGEX:
            err = validate_regex_string(value)
            if err:
                raise ValueError(err)

        cat = name.strip().lower() if name else "str"
        # Sanitize category name to ensure it's a valid YARA variable name
        cat = re.sub(r'[^a-zA-Z0-9_]', '', cat)
        if not cat: cat = "str"
        
        self._category_counters.setdefault(cat, 0)
        self._category_counters[cat] += 1
        count = self._category_counters[cat]
        
        if cat == "str":
            sname = f"str{count}"
        else:
            sname = f"{cat}_{count}" if count > 1 else cat

        ys = YaraString(
            name=sname,
            value=value,
            stype=stype,
            modifiers=modifiers or [],
            comment=comment.strip()
        )
        self.rule.strings.append(ys)
        return self

    def set_condition(self, condition: str) -> "YaraRuleBuilder":
        err = validate_condition(condition)
        if err:
            raise ValueError(err)
        self.rule.condition = condition
        return self

    def add_import(self, module: str) -> "YaraRuleBuilder":
        if module not in self.rule.imports:
            self.rule.imports.append(module)
        return self

    def auto_fill_meta(self, author: str = "", description: str = "") -> "YaraRuleBuilder":
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if author:
            self.rule.meta.setdefault("author", author)
        if description:
            self.rule.meta.setdefault("description", description)
        self.rule.meta.setdefault("date", now)
        self.rule.meta.setdefault("version", "1.0")
        return self

    def build(self) -> YaraRule:
        return self.rule


# ─────────────────────────────────────────────
#  Renderer
# ─────────────────────────────────────────────

class YaraRuleRenderer:

    @staticmethod
    def render(rule: YaraRule) -> str:
        lines = []

        # imports
        for imp in rule.imports:
            lines.append(f'import "{imp}"')
        if rule.imports:
            lines.append("")

        # includes
        for inc in rule.includes:
            lines.append(f'include "{inc}"')
        if rule.includes:
            lines.append("")

        # rule header
        tags_str = (" : " + " ".join(rule.tags)) if rule.tags else ""
        lines.append(f"rule {rule.name}{tags_str}")
        lines.append("{")

        # meta
        if rule.meta:
            lines.append("    meta:")
            for k, v in rule.meta.items():
                lines.append(f'        {k} = "{v}"')
            lines.append("")

        # strings
        if rule.strings:
            lines.append("    strings:")
            for s in rule.strings:
                lines.append(s.render())
            lines.append("")

        # condition
        lines.append("    condition:")
        lines.append(f"        {rule.condition}")
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def render_multiple(rules: List[YaraRule]) -> str:
        return "\n\n".join(YaraRuleRenderer.render(r) for r in rules)


# ─────────────────────────────────────────────
#  Template Generator
# ─────────────────────────────────────────────

class YaraTemplateGenerator:
    """Generates YARA rules from predefined malware templates."""

    @staticmethod
    def from_template(category: str, rule_name: str,
                      author: str = "", extra_strings: List[str] = None) -> YaraRule:
        if category not in COMMON_MALWARE_STRINGS:
            raise ValueError(f"Unknown template category: {category}. "
                             f"Available: {list(COMMON_MALWARE_STRINGS.keys())}")

        builder = YaraRuleBuilder()
        builder.set_name(rule_name)
        builder.set_tags([re.sub(r'\W', '_', category), "template"])
        builder.auto_fill_meta(
            author=author,
            description=f"Detects {category} indicators (auto-generated template)"
        )
        builder.rule.meta["severity"] = "medium"

        for s in COMMON_MALWARE_STRINGS[category]:
            builder.add_string(s, StringType.TEXT, ["nocase", "ascii", "wide"])

        if extra_strings:
            for s in extra_strings:
                builder.add_string(s, StringType.TEXT, ["nocase"])

        builder.set_condition("any of them")
        return builder.build()

    @staticmethod
    def available_templates() -> List[str]:
        return list(COMMON_MALWARE_STRINGS.keys())


# ─────────────────────────────────────────────
#  File Hash Rule Generator
# ─────────────────────────────────────────────

def generate_hash_rule(filepath: str, rule_name: str = None,
                       author: str = "") -> YaraRule:
    """Generate a YARA rule based on file hash."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    sha1 = hashlib.sha1()

    with open(filepath, "rb") as f:
        data = f.read()
        md5.update(data)
        sha256.update(data)
        sha1.update(data)

    fname = filepath.split("/")[-1].split("\\")[-1]
    rname = rule_name or ("Hash_" + re.sub(r'\W', '_', fname))

    builder = YaraRuleBuilder()
    builder.set_name(rname)
    builder.set_tags(["hash", "file_hash"])
    builder.auto_fill_meta(
        author=author,
        description=f"Detects file by hash — {fname}"
    )
    builder.rule.meta["md5"]    = md5.hexdigest()
    builder.rule.meta["sha1"]   = sha1.hexdigest()
    builder.rule.meta["sha256"] = sha256.hexdigest()
    builder.add_import("hash")
    builder.set_condition(
        f'hash.md5(0, filesize) == "{md5.hexdigest()}" or\n'
        f'        hash.sha256(0, filesize) == "{sha256.hexdigest()}"'
    )
    return builder.build()


# ─────────────────────────────────────────────
#  Wildcard / PE Header Helpers
# ─────────────────────────────────────────────

PE_HEADER_CONDITION = 'uint16(0) == 0x5A4D'  # MZ magic

def make_pe_rule(rule_name: str, strings: List[str],
                 author: str = "", condition_prefix: bool = True) -> YaraRule:
    """PE-specific rule with MZ magic check."""
    builder = YaraRuleBuilder()
    builder.set_name(rule_name)
    builder.set_tags(["PE", "Windows"])
    builder.auto_fill_meta(author=author, description="PE-based detection rule")
    builder.add_import("pe")
    for s in strings:
        builder.add_string(s, StringType.TEXT, ["nocase", "wide", "ascii"])

    cond = f"{PE_HEADER_CONDITION} and any of them" if condition_prefix else "any of them"
    builder.set_condition(cond)
    return builder.build()
