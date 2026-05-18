# YARA Rule Generator ◈

![YARA Rule Generator Screenshot](assets/gui_screenshot.png)

A powerful, cross-platform toolkit for automatically generating high-quality YARA rules for threat intelligence, malware analysis, and digital forensics. This project provides both a rich **Command-Line Interface (CLI)** and a modern **Graphical User Interface (GUI)**.

---

## 🌟 Features

- **Dual Interfaces:** Use the native OS styled GUI for visual rule building, or the scriptable CLI for automation.
- **DFIR & Incident Response Mode:** A dedicated GUI profile that unlocks advanced forensics capabilities like MITRE ATT&CK tagging, IMPHASH conditions, Max Filesize limits, Memory-Safe scan toggles, and Inline String Comments.
- **Cross-Platform:** Runs flawlessly on Windows, Linux, and macOS.
- **Malware & Forensics Templates:** Built-in templates for quickly generating rules for Ransomware, RATs, Process Injection, Web Shells, PowerShell Obfuscation, and Cobalt Strike Beacons.
- **Append & Multi-Rule Support:** Build massive YARA rulesets by appending multiple rules together and inserting global DFIR Rule Set headers automatically.
- **Automated Hash Rules:** Pass a suspicious file to the tool, and it will automatically calculate MD5, SHA-1, and SHA-256 hashes to generate a complete YARA rule.
- **Interactive Wizard (CLI):** Step-by-step terminal wizard to guide you through rule creation.

---

## 📦 Installation

1. **Clone or download the repository** to your local machine.
2. **Install requirements:**
   While the core logic only requires standard Python libraries, the CLI utilizes `rich` and `colorama` for enhanced terminal styling.

   ```powershell
   pip install -r requirements.txt
   ```

---

## 🖥️ Graphical User Interface (GUI) Guide

The GUI provides a highly professional, native-themed interface to generate YARA rules without typing commands.

**To launch the GUI:**
```powershell
python yara_gen_gui.py
```

### 🔀 Global Profile Modes
At the top right of the GUI, you can switch between two profiles:
- **Normal Use:** A clean, stripped-down interface for fast and simple malware rule generation.
- **Incident Response (DFIR):** Unlocks advanced forensic metadata (Case ID, Malware Family, MITRE ATT&CK), forensic string categories (`pdb`, `pipe`, `api`, `wmi`), and advanced condition helpers (IMPHASH, Max Filesize, Memory Scan compatibility).

### Tab 1: Builder ✏️
- **Rule Identity & Metadata:** Fill out the rule name, tags, author, and description. In DFIR mode, track your Case ID and MITRE ATT&CK mappings.
- **Strings Panel:** Add strings one by one. Select specific Identifiers (e.g., `domain`, `ip`, `mutex`), add modifiers, and include **Inline Comments** for documentation. The engine automatically handles variable numbering.
- **Advanced Conditions:** Choose a preset (`any of them`, `all of them`) or use the UI inputs to automatically generate `filesize < X` and `pe.imphash() == "..."` logic without writing code.
- **Generation & Appending:** Click "Generate New Rule" to create a single rule, or build multiple rules in a row and click **"Append to Output"** to create a complete Rule Set. You can also insert standard DFIR global headers.

### Tab 2: Templates 📦
Select a category (e.g., Ransomware, Web Shell, Cobalt Strike). The engine will automatically populate common strings and heuristics for that category.

### Tab 3: Hash Rule 🔐
Browse for a file on your local system (e.g., `suspicious.exe`). The tool will ingest the file, calculate its cryptographic hashes, and output a YARA rule designed to match that exact file hash.

---

## 💻 Command-Line Interface (CLI) Guide

The CLI is perfect for fast generation and automation pipelines.

**To view the help menu:**
```powershell
python yara_gen_cli.py --help
```

### 1. Interactive Wizard
If you prefer terminal prompts to guide you step-by-step:
```powershell
python yara_gen_cli.py --interactive
```

### 2. Generate from Built-in Templates
First, check what templates are available:
```powershell
python yara_gen_cli.py --list-templates
```
Generate a rule using the Ransomware template and save it to a file:
```powershell
python yara_gen_cli.py --template "Ransomware" --name "Detect_Ransomware" --author "SOC Team" --out "ransomware.yar"
```

### 3. Generate from File Hashes
Instantly create a rule based on a malware sample's hashes:
```powershell
python yara_gen_cli.py --file "C:\path\to\malware.exe" --name "MalwareHash" --out "hash_rule.yar"
```

### 4. Quick String Rules
You can generate a rule directly from a list of suspicious strings:
```powershell
python yara_gen_cli.py --strings "evil.exe" "c2.domain.com" --name "C2_Rule" --tags "malware" "c2"
```

### 5. Batch Generation via JSON
Create a `rules.json` file defining multiple rules, then generate them all at once:
```powershell
python yara_gen_cli.py --batch rules.json --out batch_output.yar
```
*(Example JSON structure would include a list of dictionaries with keys like `name`, `tags`, `meta`, `strings`, and `condition`)*.

---

## 📂 Project Structure

- `yara_engine.py`: The core generation logic. Handles validation, string formatting, and standardized YARA rendering. Used by both interfaces.
- `yara_gen_cli.py`: The terminal entry point and argument parser.
- `yara_gen_gui.py`: The `tkinter`-based graphical interface application.
- `requirements.txt`: Python dependencies.

---

*Generated rules are 100% standard YARA syntax and can be deployed to any engine (VirusTotal, FireEye, CrowdStrike, open-source scanners, etc).*
