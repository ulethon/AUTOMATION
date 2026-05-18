#!/usr/bin/env python3
"""YARA Rule Generator — GUI Edition (Native ttk, cross-platform)"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import re, os
from yara_engine import (
    YaraRuleBuilder, YaraRuleRenderer, YaraTemplateGenerator,
    StringType, COMMON_MALWARE_STRINGS, SEVERITY_LEVELS, TLP_LEVELS,
    generate_hash_rule, validate_rule_name
)

class StringsPanel(ttk.Frame):
    """Manage rule strings with a Treeview for add/remove."""
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._strings = []
        self._build()

    def _build(self):
        # Top bar for adding strings
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 5))

        ttk.Label(top, text="Value:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.val_entry = ttk.Entry(top, width=30)
        self.val_entry.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(top, text="Type:").grid(row=0, column=2, padx=(0, 5))
        self.stype_var = tk.StringVar(value="text")
        stype_cb = ttk.Combobox(top, textvariable=self.stype_var, values=["text","hex","regex"], state="readonly", width=6)
        stype_cb.grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(top, text="Id:").grid(row=0, column=4, padx=(0, 5))
        self.sid_var = tk.StringVar(value="str")
        self.sid_cb = ttk.Combobox(top, textvariable=self.sid_var, values=[
            "str", "domain", "url", "ip", "filename", "mutex", 
            "registry", "ua", "marker", "config", "pdb", "pipe", 
            "wmi", "api", "email"
        ], width=8)
        self.sid_cb.grid(row=0, column=5, padx=(0, 10))

        ttk.Label(top, text="Mods:").grid(row=0, column=6, padx=(0, 5))
        self.mods_var = tk.StringVar(value="fullword ascii")
        self.mods_entry = ttk.Entry(top, textvariable=self.mods_var, width=12)
        self.mods_entry.grid(row=0, column=7, padx=(0, 10))

        ttk.Label(top, text="Comment:").grid(row=0, column=8, padx=(0, 5))
        self.cmt_var = tk.StringVar(value="")
        self.cmt_entry = ttk.Entry(top, textvariable=self.cmt_var, width=15)
        self.cmt_entry.grid(row=0, column=9, padx=(0, 10))

        ttk.Button(top, text="Add String", command=self._add).grid(row=0, column=10)

        # Treeview for displaying added strings
        tv_frame = ttk.Frame(self)
        tv_frame.pack(fill="both", expand=True)

        columns = ("Identifier", "Type", "Value", "Modifiers", "Comment")
        self.tv = ttk.Treeview(tv_frame, columns=columns, show="headings", height=5)
        self.tv.heading("Identifier", text="Id")
        self.tv.column("Identifier", width=50, anchor="center")
        self.tv.heading("Type", text="Type")
        self.tv.column("Type", width=50, anchor="center")
        self.tv.heading("Value", text="Value")
        self.tv.column("Value", width=200, anchor="w")
        self.tv.heading("Modifiers", text="Modifiers")
        self.tv.column("Modifiers", width=100, anchor="w")
        self.tv.heading("Comment", text="Comment")
        self.tv.column("Comment", width=100, anchor="w")

        sb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Bottom bar for actions
        bot = ttk.Frame(self)
        bot.pack(fill="x", pady=(5, 0))
        ttk.Button(bot, text="Remove Selected", command=self._remove).pack(side="right")

    def set_mode(self, mode):
        if mode == "Normal":
            self.sid_cb['values'] = ["str", "domain", "url", "ip", "filename", "hash"]
        else:
            self.sid_cb['values'] = ["str", "domain", "url", "ip", "filename", "mutex", "registry", "ua", "marker", "config", "pdb", "pipe", "wmi", "api", "email"]
        if self.sid_var.get() not in self.sid_cb['values']:
            self.sid_var.set("str")

    def _add(self):
        val = self.val_entry.get().strip()
        if not val:
            messagebox.showwarning("Empty", "String value cannot be empty.")
            return
        stype = self.stype_var.get()
        sid = self.sid_var.get().strip() or "str"
        mods  = [m.strip() for m in self.mods_var.get().split() if m.strip()]
        cmt = self.cmt_var.get().strip()
        
        entry = {"value": val, "type": stype, "id": sid, "modifiers": mods, "comment": cmt}
        self._strings.append(entry)
        
        self.tv.insert("", "end", values=(sid, stype, val, " ".join(mods), cmt))
        self.val_entry.delete(0, "end")
        self.cmt_entry.delete(0, "end")

    def _remove(self):
        selected = self.tv.selection()
        if not selected: return
        for item in selected:
            idx = self.tv.index(item)
            self.tv.delete(item)
            self._strings.pop(idx)

    def get_strings(self): return list(self._strings)
    def clear(self):
        self._strings.clear()
        for item in self.tv.get_children():
            self.tv.delete(item)


class YaraGenGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YARA Rule Generator")
        self.geometry("1100x750")
        self.minsize(900, 600)
        
        # Make the UI look native on Windows
        try:
            self.tk.call('source', 'azure.tcl') # fallback native
        except Exception:
            pass # Use standard native ttk Theme
        
        # Apply native theme if available (Windows defaults to 'vista' or 'winnative')
        style = ttk.Style(self)
        themes = style.theme_names()
        if 'vista' in themes: style.theme_use('vista')
        elif 'clam' in themes: style.theme_use('clam')

        self._build_ui()
        self._set_mode("Normal Use")

    def _build_ui(self):
        # Header with Mode Selection
        hdr_frame = ttk.Frame(self)
        hdr_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        ttk.Label(hdr_frame, text="YARA Rule Generator", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        mode_frame = ttk.Frame(hdr_frame)
        mode_frame.pack(side="right")
        ttk.Label(mode_frame, text="Profile Mode:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        self.mode_var = tk.StringVar(value="Normal Use")
        mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=["Normal Use", "Incident Response (DFIR)"], state="readonly", width=25)
        mode_cb.pack(side="left")
        mode_cb.bind("<<ComboboxSelected>>", lambda e: self._set_mode(self.mode_var.get()))

        # Main layout
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned)
        right_frame = ttk.Frame(main_paned)
        
        main_paned.add(left_frame, weight=1)
        main_paned.add(right_frame, weight=1)

        self._build_left(left_frame)
        self._build_right(right_frame)

    # ── Left: Tabs ────────────────────────────────────────────────
    def _build_left(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True)

        self._tab_builder(nb)
        self._tab_template(nb)
        self._tab_hash(nb)

    def _create_labeled_entry(self, parent, label_text, default=""):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text=label_text).pack(anchor="w")
        var = tk.StringVar(value=default)
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(fill="x", pady=(2, 0))
        return frame, var, entry

    def _tab_builder(self, nb):
        tab = ttk.Frame(nb, padding=5)
        nb.add(tab, text="Builder")

        # Pinned Actions at the bottom
        btn_frame = ttk.Frame(tab, padding=10)
        btn_frame.pack(side="bottom", fill="x")
        ttk.Button(btn_frame, text="Generate New Rule", command=lambda: self._generate_builder(append=False)).pack(side="left")
        ttk.Button(btn_frame, text="Append to Output", command=lambda: self._generate_builder(append=True)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self._clear_builder).pack(side="right")

        # Scrollable area for the form
        canvas = tk.Canvas(tab, highlightthickness=0)
        sb = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="top", fill="both", expand=True)

        inner = ttk.Frame(canvas, padding=10)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")
        
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        
        # Enable mouse scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Identity
        id_lf = ttk.LabelFrame(inner, text="Rule Identity", padding=10)
        id_lf.pack(fill="x", pady=(0, 10))
        
        f1, self.e_name_var, _ = self._create_labeled_entry(id_lf, "Rule Name *", "DetectMalware")
        f1.pack(fill="x", pady=(0, 5))
        
        f2, self.e_tags_var, _ = self._create_labeled_entry(id_lf, "Tags (space separated)", "malware")
        f2.pack(fill="x")

        # Metadata
        meta_lf = ttk.LabelFrame(inner, text="Metadata", padding=10)
        meta_lf.pack(fill="x", pady=(0, 10))
        
        f3, self.e_author_var, _ = self._create_labeled_entry(meta_lf, "Author")
        f3.pack(fill="x", pady=(0, 5))
        f4, self.e_desc_var, _ = self._create_labeled_entry(meta_lf, "Description")
        f4.pack(fill="x", pady=(0, 5))
        self.f_ref, self.e_ref_var, _ = self._create_labeled_entry(meta_lf, "Reference URL")
        self.f_ref.pack(fill="x", pady=(0, 5))
        
        # DFIR specific metadata fields
        self.f_case, self.e_case_var, _ = self._create_labeled_entry(meta_lf, "Case Identifier (DFIR)")
        self.f_case.pack(fill="x", pady=(0, 5))
        self.f_family, self.e_family_var, _ = self._create_labeled_entry(meta_lf, "Malware Family (DFIR)")
        self.f_family.pack(fill="x", pady=(0, 5))
        self.f_mitre, self.e_mitre_var, _ = self._create_labeled_entry(meta_lf, "MITRE ATT&CK (e.g., T1059)")
        self.f_mitre.pack(fill="x", pady=(0, 5))

        meta_row = ttk.Frame(meta_lf)
        meta_row.pack(fill="x", pady=(5, 0))
        
        ttk.Label(meta_row, text="Severity:").grid(row=0, column=0, padx=(0, 5))
        self.sev_var = tk.StringVar(value="medium")
        ttk.Combobox(meta_row, textvariable=self.sev_var, values=SEVERITY_LEVELS, state="readonly", width=12).grid(row=0, column=1, padx=(0, 15))
        
        ttk.Label(meta_row, text="TLP:").grid(row=0, column=2, padx=(0, 5))
        self.tlp_var = tk.StringVar(value="AMBER")
        ttk.Combobox(meta_row, textvariable=self.tlp_var, values=TLP_LEVELS, state="readonly", width=10).grid(row=0, column=3)

        # Strings
        str_lf = ttk.LabelFrame(inner, text="Strings", padding=10)
        str_lf.pack(fill="both", expand=True, pady=(0, 10))
        self.strings_panel = StringsPanel(str_lf)
        self.strings_panel.pack(fill="both", expand=True)

        # Condition
        cond_lf = ttk.LabelFrame(inner, text="Condition", padding=10)
        cond_lf.pack(fill="x", pady=(0, 10))
        
        self.cond_preset = tk.StringVar(value="any of them")
        cond_radios = ttk.Frame(cond_lf)
        cond_radios.pack(fill="x", pady=(0, 5))
        
        ttk.Radiobutton(cond_radios, text="Any of them", variable=self.cond_preset, value="any of them", command=self._sync_cond).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(cond_radios, text="All of them", variable=self.cond_preset, value="all of them", command=self._sync_cond).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(cond_radios, text="Custom", variable=self.cond_preset, value="custom", command=self._sync_cond).pack(side="left")

        self.e_cond_var = tk.StringVar(value="any of them")
        ttk.Entry(cond_lf, textvariable=self.e_cond_var, font=("Courier", 10)).pack(fill="x", pady=(0, 5))

        chk_frame = ttk.Frame(cond_lf)
        chk_frame.pack(fill="x", pady=(5, 0))

        self.pe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(chk_frame, text="Add PE header check (MZ magic)", variable=self.pe_var).pack(anchor="w", pady=(0, 5))

        self.mem_safe_var = tk.BooleanVar(value=True)
        self.chk_mem_safe = ttk.Checkbutton(chk_frame, text="Memory Scan Compatible (DFIR)", variable=self.mem_safe_var)
        self.chk_mem_safe.pack(anchor="w", pady=(0, 5))

        # Advanced fields (DFIR)
        self.adv_frame = ttk.Frame(cond_lf)
        self.adv_frame.pack(fill="x", pady=(5, 0))
        
        f1, self.e_filesize_var, _ = self._create_labeled_entry(self.adv_frame, "Max Filesize (e.g. 900KB)")
        f1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        f2, self.e_imphash_var, _ = self._create_labeled_entry(self.adv_frame, "IMPHASH (e.g. bb816...)")
        f2.pack(side="left", fill="x", expand=True)

    def _tab_template(self, nb):
        tab = ttk.Frame(nb, padding=15)
        nb.add(tab, text="Templates")

        ttk.Label(tab, text="Generate YARA rules from predefined malware heuristics.", font=("Segoe UI", 11)).pack(pady=(0, 15), anchor="w")

        self.cat_lf = ttk.LabelFrame(tab, text="Select Category", padding=10)
        self.cat_lf.pack(fill="x", pady=(0, 15))

        self.tmpl_var = tk.StringVar()

        opt_lf = ttk.LabelFrame(tab, text="Options", padding=10)
        opt_lf.pack(fill="x", pady=(0, 15))
        
        f1, self.tmpl_name_var, _ = self._create_labeled_entry(opt_lf, "Rule Name (leave blank to auto-generate)")
        f1.pack(fill="x", pady=(0, 5))
        f2, self.tmpl_author_var, _ = self._create_labeled_entry(opt_lf, "Author")
        f2.pack(fill="x", pady=(0, 5))
        f3, self.tmpl_extra_var, _ = self._create_labeled_entry(opt_lf, "Extra Strings (comma-separated)")
        f3.pack(fill="x")

        ttk.Button(tab, text="Generate from Template", command=self._generate_template).pack(anchor="w")

    def _tab_hash(self, nb):
        tab = ttk.Frame(nb, padding=15)
        nb.add(tab, text="Hash Rule")

        ttk.Label(tab, text="Automatically generate a rule matching a file's MD5/SHA-256 hash.", font=("Segoe UI", 11)).pack(pady=(0, 15), anchor="w")

        lf = ttk.LabelFrame(tab, text="File to Hash", padding=10)
        lf.pack(fill="x", pady=(0, 15))

        f1, self.hash_path_var, _ = self._create_labeled_entry(lf, "File Path *")
        f1.pack(fill="x", pady=(0, 5))
        ttk.Button(lf, text="Browse...", command=self._browse_hash_file).pack(anchor="w", pady=(0, 10))
        
        f2, self.hash_name_var, _ = self._create_labeled_entry(lf, "Rule Name (leave blank to auto-generate)")
        f2.pack(fill="x", pady=(0, 5))
        f3, self.hash_author_var, _ = self._create_labeled_entry(lf, "Author")
        f3.pack(fill="x")

        ttk.Button(tab, text="Generate Hash Rule", command=self._generate_hash).pack(anchor="w")


    # ── Right: Output Panel ──────────────────────────────────────
    def _build_right(self, parent):
        parent.pack_propagate(False)

        top_bar = ttk.Frame(parent)
        top_bar.pack(fill="x", pady=(0, 5))
        
        ttk.Label(top_bar, text="Generated Rule Output:", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        ttk.Button(top_bar, text="Insert DFIR Header", command=self._insert_header).pack(side="left", padx=10)
        
        ttk.Button(top_bar, text="Clear", command=self._clear_output).pack(side="right")
        ttk.Button(top_bar, text="Save As...", command=self._save_rule).pack(side="right", padx=5)
        ttk.Button(top_bar, text="Copy", command=self._copy_output).pack(side="right")

        # Use a standard text box with a native look
        text_frame = ttk.Frame(parent, borderwidth=1, relief="solid")
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.output = scrolledtext.ScrolledText(
            text_frame, font=("Consolas", 10), wrap="none",
            borderwidth=0, state="disabled"
        )
        self.output.pack(fill="both", expand=True, padx=2, pady=2)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(parent, textvariable=self.status_var, foreground="#16a34a", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(fill="x", pady=(5, 0))

    # ── Helpers ──────────────────────────────────────────────────
    def _set_mode(self, mode):
        # Update Builder Tab DFIR features
        if mode == "Normal Use":
            self.f_mitre.pack_forget()
            self.f_case.pack_forget()
            self.f_family.pack_forget()
            self.chk_mem_safe.pack_forget()
            self.adv_frame.pack_forget()
            self.mem_safe_var.set(False)
            self.strings_panel.set_mode("Normal")
        else:
            self.f_case.pack(fill="x", pady=(0, 5))
            self.f_family.pack(fill="x", pady=(0, 5))
            self.f_mitre.pack(fill="x", pady=(0, 5))
            self.chk_mem_safe.pack(anchor="w", pady=(0, 5))
            self.adv_frame.pack(fill="x", pady=(5, 0))
            self.mem_safe_var.set(True)
            self.strings_panel.set_mode("DFIR")
            
        # Update Templates Tab Options
        for widget in self.cat_lf.winfo_children():
            widget.destroy()
            
        all_cats = list(COMMON_MALWARE_STRINGS.keys())
        dfir_cats = ["Web Shell (PHP/ASP/JSP)", "PowerShell Obfuscation", "Cobalt Strike Beacon"]
        
        if mode == "Normal Use":
            cats = [c for c in all_cats if c not in dfir_cats]
        else:
            cats = [c for c in all_cats if c in dfir_cats]
            
        if cats:
            self.tmpl_var.set(cats[0])
        for i, cat in enumerate(cats):
            ttk.Radiobutton(self.cat_lf, text=cat, variable=self.tmpl_var, value=cat).grid(row=i//2, column=i%2, sticky="w", padx=20, pady=5)

    def _sync_cond(self):
        v = self.cond_preset.get()
        if v != "custom":
            self.e_cond_var.set(v)

    def _set_output(self, text: str):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.config(state="disabled")

    def _set_status(self, msg: str, is_error=False):
        self.status_var.set(msg)
        self.status_label.configure(foreground="#dc2626" if is_error else "#16a34a")

    def _get_condition(self):
        preset = self.cond_preset.get()
        cond = preset if preset != "custom" else self.e_cond_var.get().strip() or "any of them"
        
        parts = []
        if self.pe_var.get():
            parts.append("uint16(0) == 0x5A4D")
            
        fs = self.e_filesize_var.get().strip()
        if fs:
            parts.append(f"filesize < {fs}")
            
        imp = self.e_imphash_var.get().strip()
        if imp:
            parts.append(f'pe.imphash() == "{imp}"')
            self.pe_var.set(True) # Force PE logic if imphash is used
            
        if parts:
            parts_str = " and ".join(parts)
            return f"{parts_str} and\n        ( {cond} )"
        return cond

    def _insert_header(self):
        header = f"/*\nYARA Rule Set\nAuthor: {self.e_author_var.get() or 'DFIR Analyst'}\nDate: {datetime.date.today().isoformat()}\nDescription: Rule set generated via YARA Generator\n*/\n\n/* Rule Set {'-'*65} */\n\n"
        self.output.config(state="normal")
        self.output.insert("1.0", header)
        self.output.config(state="disabled")

    # ── Generator Actions ────────────────────────────────────────
    def _generate_builder(self, append=False):
        name = self.e_name_var.get().strip()
        err = validate_rule_name(name)
        if err:
            self._set_status(f"Error: {err}", True)
            return messagebox.showerror("Invalid Rule Name", err)

        tags_raw = re.split(r'[,\s]+', self.e_tags_var.get().strip())
        tags = [t for t in tags_raw if t]

        builder = YaraRuleBuilder()
        try:
            builder.set_name(name)
            builder.set_tags(tags)
            builder.auto_fill_meta(author=self.e_author_var.get().strip(), description=self.e_desc_var.get().strip())
            
            if self.sev_var.get(): builder.rule.meta["severity"] = self.sev_var.get()
            if self.tlp_var.get(): builder.rule.meta["tlp"] = self.tlp_var.get()
            if self.e_ref_var.get().strip(): builder.rule.meta["reference"] = self.e_ref_var.get().strip()
            
            # DFIR specific fields
            if self.mode_var.get() == "Incident Response (DFIR)":
                if self.e_case_var.get().strip(): builder.rule.meta["case_identifier"] = self.e_case_var.get().strip()
                if self.e_family_var.get().strip(): builder.rule.meta["malware_family"] = self.e_family_var.get().strip()
                if self.e_mitre_var.get().strip(): builder.rule.meta["mitre_attck"] = self.e_mitre_var.get().strip()
            
            if self.mem_safe_var.get(): tags.append("memory_safe")

            for s in self.strings_panel.get_strings():
                stype_map = {"text": StringType.TEXT, "hex": StringType.HEX, "regex": StringType.REGEX}
                builder.add_string(
                    value=s["value"], 
                    stype=stype_map.get(s["type"], StringType.TEXT), 
                    modifiers=s["modifiers"],
                    name=s.get("id", "str"),
                    comment=s.get("comment", "")
                )

            builder.set_condition(self._get_condition())
            if self.pe_var.get() or self.e_imphash_var.get().strip(): builder.add_import("pe")

            rule = builder.build()
            
            # Format output
            rule_text = YaraRuleRenderer.render(rule)
            
            self.output.config(state="normal")
            if append:
                # Add spacing if appending
                if self.output.get("1.0", "end-1c").strip():
                    self.output.insert("end", "\n\n")
                self.output.insert("end", rule_text)
            else:
                self.output.delete("1.0", "end")
                self.output.insert("1.0", rule_text)
            self.output.config(state="disabled")
            
            self._set_status(f"✔ Rule '{name}' generated successfully")
        except ValueError as e:
            self._set_status(f"Error: {e}", True)
            messagebox.showerror("Error", str(e))

    def _generate_template(self):
        cat = self.tmpl_var.get()
        rname = self.tmpl_name_var.get().strip() or re.sub(r'\W+','_', cat)
        err = validate_rule_name(rname)
        if err:
            self._set_status("Error: Invalid Name", True)
            return messagebox.showerror("Invalid Name", err)
            
        extra = [s.strip() for s in self.tmpl_extra_var.get().split(",") if s.strip()]
        try:
            rule = YaraTemplateGenerator.from_template(cat, rname, self.tmpl_author_var.get().strip(), extra)
            self._set_output(YaraRuleRenderer.render(rule))
            self._set_status(f"✔ Template '{cat}' applied successfully")
        except Exception as e:
            self._set_status(f"Error: {e}", True)
            messagebox.showerror("Error", str(e))

    def _generate_hash(self):
        path = self.hash_path_var.get().strip()
        if not path or not os.path.isfile(path):
            self._set_status("Error: File not found", True)
            return messagebox.showerror("Error", "Please select a valid file.")
            
        rname = self.hash_name_var.get().strip() or None
        try:
            rule = generate_hash_rule(path, rname, self.hash_author_var.get().strip())
            self._set_output(YaraRuleRenderer.render(rule))
            self._set_status("✔ Hash rule generated successfully")
        except Exception as e:
            self._set_status(f"Error: {e}", True)
            messagebox.showerror("Error", str(e))

    def _browse_hash_file(self):
        path = filedialog.askopenfilename(title="Select file to hash")
        if path:
            self.hash_path_var.set(path)
            base = os.path.basename(path)
            self.hash_name_var.set("Hash_" + re.sub(r'\W','_', os.path.splitext(base)[0]))

    def _copy_output(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            self._set_status("Error: Nothing to copy", True)
            return messagebox.showinfo("Empty", "No rule to copy.")
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("✔ Copied to clipboard")

    def _save_rule(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            self._set_status("Error: Generate a rule first", True)
            return messagebox.showinfo("Empty", "Generate a rule first.")
        path = filedialog.asksaveasfilename(
            defaultextension=".yar",
            filetypes=[("YARA Rules", "*.yar *.yara"), ("All Files", "*.*")],
            initialfile="rule.yar"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            self._set_status(f"✔ Saved to {os.path.basename(path)}")

    def _clear_builder(self):
        self.e_name_var.set("DetectMalware")
        self.e_tags_var.set("malware")
        self.e_author_var.set("")
        self.e_desc_var.set("")
        self.e_ref_var.set("")
        self.e_case_var.set("")
        self.e_family_var.set("")
        self.e_mitre_var.set("")
        self.strings_panel.clear()
        self.e_cond_var.set("any of them")
        self.pe_var.set(False)
        self.e_filesize_var.set("")
        self.e_imphash_var.set("")

    def _clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")
        self._set_status("Ready")


if __name__ == "__main__":
    app = YaraGenGUI()
    app.mainloop()
