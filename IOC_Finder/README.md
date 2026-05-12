# IOC-Finder

<div align="center">

```
██╗  ██████╗  ██████╗    ███████╗██╗███╗   ██╗██████╗ ███████╗██████╗ 
██║██╔═══██╗██╔════╝    ██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔══██╗
██║██║   ██║██║         █████╗  ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝
██║██║   ██║██║         ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
██║╚██████╔╝╚██████╗    ██      ██║██║ ╚████║██████╔╝███████╗██║  ██║
╚═╝ ╚═════╝  ╚═════╝    ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝
```

**Lightweight Incident Response & Threat Hunting Tool**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-brightgreen?style=flat-square)](#installation)
[![YARA](https://img.shields.io/badge/YARA-4.5.5-orange?style=flat-square)](https://virustotal.github.io/yara/)
[![License](https://img.shields.io/badge/License-AGPL-purple?style=flat-square)](LICENSE)
[![Author](https://img.shields.io/badge/Author-nycthunter-red?style=flat-square)](https://github.com/nycthunter)

</div>

---

## 📖 Overview

**IOC-Finder** is a fast, portable incident response tool built for cybersecurity professionals. It scans filesystems, running process memory, and archives for **Indicators of Compromise (IOCs)** using multiple detection engines — all driven by a simple YAML configuration file.

Designed to be dropped onto a live system with zero dependencies (using the standalone build), it gives analysts immediate triage capability during active incidents.

### 🎯 Use Cases

- **Incident Response** — Rapidly triage endpoints for known malware artifacts
- **Threat Hunting** — Proactively search for attacker TTPs across your environment  
- **Forensic Triage** — Scan mounted disk images or evidence directories
- **SOC Automation** — Run silently with event forwarding to your SIEM

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Path Matching** | Glob wildcards, regex patterns, environment variable expansion |
| #️⃣ **Hash Verification** | MD5, SHA1, SHA256 checksum matching |
| 📝 **Content Grep** | Literal string search inside file content |
| 🛡️ **YARA Scanning** | Local files, directories, or remote URL rule loading |
| 🗜️ **Archive Deep-Scan** | Scan inside ZIP archives file-by-file |
| 🧠 **Process Memory** | Dump and scan running process memory (Windows & Linux) |
| 👁️ **Triage Mode** | Continuous filesystem watch — scan files as they change |
| 📡 **Event Forwarding** | Stream results to HTTP endpoints or rotating JSONL log files |
| 🖥️ **Rich TUI** | Live 3-panel dashboard (Matches / Errors / Log) |
| 🔒 **RC4 Config Decrypt** | Support for encrypted configuration and YARA rule files |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Configuration File

```yaml
# my_scan.yaml
input:
  path:
    - '%TEMP%\*.exe'
    - '%APPDATA%\*.dll'
  content:
    grep:
      - "cmd.exe /c"
      - "powershell -enc"
    yara:
      - "./rules/my_rules.yar"
    checksum:
      - "44d88612fea8a8f36de82e1278abb02f"  # MD5
options:
  findInHardDrives: true
  findInMemory: false
output:
  copyMatchingFiles: false
```

### 3. Run

```bash
python ioc_finder.py -c my_scan.yaml
```

---

## 🖥️ Usage

```
python ioc_finder.py [OPTIONS]
```

### CLI Options

| Flag | Description | Default |
|---|---|---|
| `-c`, `--configuration` | Path or URL to a YAML configuration file | — |
| `-r`, `--root` | Scan a specific directory (skip drive enumeration) | — |
| `-v`, `--verbosity` | Log level: `1`=alerts · `2`=+warn · `3`=+err · `4`=+info · `5`=debug | `4` |
| `-t`, `--triage` | Continuous watch mode — scan files as they are written | `off` |
| `-l`, `--logfile` | Write all log output to a file | — |
| `-s`, `--silent` | Suppress all console output (event forwarding still works) | `off` |
| `--no-tui` | Use plain console output instead of the Rich TUI dashboard | `off` |
| `-h`, `--help` | Show help | — |

### Examples

```bash
# Standard scan with full debug output
python ioc_finder.py -c config.yaml -v 5

# Scan a specific directory instead of all drives
python ioc_finder.py -c config.yaml -r /mnt/evidence

# Alerts only, write to log file
python ioc_finder.py -c config.yaml -v 1 -l /tmp/findings.log

# Continuous triage mode (watch for new/modified files)
python ioc_finder.py -c config.yaml -t

# Silent background scan — forward events to SIEM only
python ioc_finder.py -c config.yaml -s

# Plain console (no Rich TUI)
python ioc_finder.py -c config.yaml --no-tui
```

> 💡 **Tip**: Run with administrative/root privileges for full system access including process memory and protected directories.

---

## 📂 Project Structure

```
IOC-Finder/
│
├── ioc_finder.py        ← Entry point · CLI · TUI · orchestration · logging
├── scanner.py           ← YARA · hash · grep · archive · process memory · pipeline
├── events.py            ← HTTP & JSONL event forwarding
├── config.py            ← YAML configuration loader · dataclasses · RC4 decrypt
├── requirements.txt     ← Python dependencies
│
├── examples/            ← Ready-to-use scan configurations & YARA rules
│   ├── example_configuration_windows.yaml
│   ├── example_configuration_linux.yaml
│   ├── example_configuration_api_triage.yaml
│   ├── example_configuration_docker_triage.yaml
│   ├── example_rule_windows.yar
│   ├── example_rule_linux.yar
│   ├── CISA-AA21-259A/   ← ManageEngine CVE-2021-40539 threat hunt
│   ├── React2Shell/      ← React2Shell webshell detection
│   ├── linux-fontonlake/ ← FontOnLake Linux rootkit detection
│   ├── log4j_vuln_checker/ ← Log4Shell (CVE-2021-44228) detection
│   └── proxyshell/       ← ProxyShell (CVE-2021-34473) detection
│
└── tests/               ← Test fixture configs and YARA rules
```

---

## ⚙️ Configuration Reference

Full YAML schema with all available options:

```yaml
input:
  path:
    # Glob wildcards
    - '%TEMP%\*.exe'
    - 'C:\Users\*\AppData\*.dll'
    # Regex (wrap in /slashes/)
    - '/(?i)\\system32\\.+\.ps1$/'
    # Direct file paths
    - 'C:\Windows\System32\notepad.exe'

  content:
    grep:
      - "eval("           # Case-sensitive literal string search
      - "base64_decode"
    
    yara:
      - "./rules/malware.yar"             # Relative to config file
      - "/absolute/path/to/rules/"        # Directory of .yar files
      - "https://example.com/rule.yar"    # Remote URL
    
    checksum:
      - "44d88612fea8a8f36de82e1278abb02f"          # MD5
      - "3395856ce81f2b7382dee72602f798b642f14d3"   # SHA1
      - "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"  # SHA256

options:
  # When true: grep only runs on files whose path already matched a pattern
  # YARA and checksums always evaluate regardless of this flag
  contentMatchDependsOnPathMatch: false

  findInHardDrives:      true   # Scan local fixed drives
  findInRemovableDrives: false  # Scan USB/removable drives
  findInNetworkDrives:   false  # Scan network/SMB mounts
  findInCDRomDrives:     false  # Scan CD-ROM / mounted ISOs
  findInMemory:          false  # Scan running process memory

output:
  copyMatchingFiles: false     # Copy every matched file to filesCopyPath
  base64Files:       false     # Base64-encode files before copying
  filesCopyPath:     './'      # Destination directory for copies

advancedparameters:
  yaraRC4Key:                       ''    # RC4 key for encrypted YARA rules
  maxScanFilesize:                  2048  # Skip files larger than N MB
  cleanMemoryIfFileGreaterThanSize: 512   # Free heap after scanning large files (MB)

eventforwarding:
  enabled:             true
  buffer_size:         100    # Flush after N events
  flush_time_seconds:  10     # Also flush every N seconds

  http:
    enabled:          false
    url:              "https://your-siem.example.com/api/events"
    ssl_verify:       true
    timeout_seconds:  10
    headers:
      Authorization:  "Bearer YOUR_API_KEY"
    retry_count:      3

  file:
    enabled:          true
    directory_path:   "./logs"
    rotate_minutes:   60        # Rotate log file every N minutes
    max_file_size_mb: 10        # Also rotate when file exceeds N MB
    retain_files:     10        # Keep N most recent log files

  filters:
    event_types:
      - "alert"     # IOC matches
      - "error"     # Scan errors
      - "warning"   # Non-fatal warnings
      - "info"      # General operational events
```

---

## 🔍 Path Pattern Reference

| Pattern Type | Example | Matches |
|---|---|---|
| Literal | `C:\Windows\notepad.exe` | Exact path |
| Glob `*` | `%TEMP%\*.exe` | Any `.exe` in TEMP |
| Glob `?` | `cmd?.exe` | `cmd1.exe`, `cmds.exe`, etc. |
| Regex | `/(?i)\\system32\\.+\.ps1$/` | Case-insensitive regex |
| Env Var | `%APPDATA%\*.dll` | Expanded automatically |

> ⚠️ **Notes:**
> - Path patterns are always **case-insensitive**
> - Grep content search is always **case-sensitive**
> - Backslashes must be **escaped** in YAML: `\\` (except inside `/regex/`)

---

## 📦 Dependencies

| Package | Purpose | Version |
|---|---|---|
| `yara-python` | YARA rule compilation and scanning | ≥ 4.3.0 |
| `pyyaml` | YAML configuration parsing | ≥ 6.0 |
| `rich` | Terminal UI dashboard and colored output | ≥ 13.0 |
| `requests` | HTTP event forwarding + remote YARA/config loading | ≥ 2.31 |
| `psutil` | Process enumeration, drive detection (cross-platform) | ≥ 5.9 |
| `watchdog` | Filesystem event watching for triage mode | ≥ 3.0 |

Install all at once:

```bash
pip install -r requirements.txt
```

> **Windows note**: `yara-python` may require Microsoft Visual C++ Build Tools.  
> Pre-compiled wheels are available at: https://pypi.org/project/yara-python/#files

---

## 🌐 Event Forwarding

IOC-Finder can stream scan events in real-time to external systems.

### HTTP (SIEM / Webhook)

```yaml
eventforwarding:
  enabled: true
  http:
    enabled: true
    url: "https://your-siem.example.com/api/ingest"
    headers:
      Authorization: "Bearer eyJ..."
    retry_count: 3
```

Each event is sent as a JSON POST:

```json
{
  "timestamp": "2026-05-12T06:30:00.000000Z",
  "hostname":  "WORKSTATION-01",
  "event_type": "alert",
  "severity":   "high",
  "message":    "YARA match: Cobalt_Strike_Beacon in C:\\Temp\\update.exe",
  "metadata": {
    "rule_name":  "Cobalt_Strike_Beacon",
    "file_path":  "C:\\Temp\\update.exe",
    "file_size":  "204800"
  }
}
```

### File Output (JSONL)

```yaml
eventforwarding:
  enabled: true
  file:
    enabled: true
    directory_path: "./logs"
    rotate_minutes: 60
    retain_files: 10
```

Produces rotating `YYYYMMDDHHMM_ioc_finder_logs.jsonl` files — one JSON event per line, compatible with Splunk, Elastic, and standard log shippers.

---

## 🧪 Testing

Run with one of the included example configs to verify your installation:

```bash
# Test YARA scanning (Linux)
python ioc_finder.py -c examples/example_configuration_linux.yaml --no-tui -v 5

# Test YARA scanning (Windows)
python ioc_finder.py -c examples/example_configuration_windows.yaml --no-tui -v 5
```

Use the test fixtures in `tests/` to verify config loading and rule parsing:

```bash
# Verify the test config loads correctly
python -c "from config import load_configuration; c = load_configuration('tests/config_test_standard.yml'); print('OK:', c)"
```

---

## 📡 Threat Hunting Examples

The `examples/` directory contains ready-to-use threat hunt configurations for real-world vulnerabilities:

| Folder | CVE / Campaign | Description |
|---|---|---|
| `CISA-AA21-259A/` | CVE-2021-40539 | ManageEngine ADSelfService Plus exploitation |
| `React2Shell/` | — | React2Shell webshell detection |
| `linux-fontonlake/` | — | FontOnLake Linux rootkit & backdoor |
| `log4j_vuln_checker/` | CVE-2021-44228 | Log4Shell vulnerability scanning |
| `proxyshell/` | CVE-2021-34473 | Microsoft Exchange ProxyShell |

Run any example:

```bash
python ioc_finder.py -c examples/CISA-AA21-259A/CISA-AA21-259A.yaml -v 1
```

---

## 🤝 Contributing

Contributions are welcome — bug reports, feature requests, and pull requests.

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Commit** your changes: `git commit -m "Add my feature"`
4. **Push**: `git push origin feature/my-feature`
5. **Open** a Pull Request

---

## 📜 License

This project is licensed under the **AGPL License** — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**nycthunter**  
🔗 [github.com/nycthunter](https://github.com/nycthunter)

---

<div align="center">

*Built for incident responders, by incident responders.*  
**IOC-Finder** — Fast. Portable. Reliable.

![GitHub stars](https://img.shields.io/github/stars/nycthunter/ioc-finder?style=social)
![GitHub forks](https://img.shields.io/github/forks/nycthunter/ioc-finder?style=social)

</div>
