#!/usr/bin/env python3
"""
Retro Archive UI - A graphical interface for compress.py and verify.py
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Resolve script paths relative to this file ─────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
COMPRESS_SCRIPT = os.path.join(_HERE, "compress.py")
VERIFY_SCRIPT   = os.path.join(_HERE, "verify.py")

# ── Colour palette ──────────────────────────────────────────────────────────
BG        = "#1a1b26"
BG2       = "#24253a"
BG3       = "#2e3050"
ACCENT    = "#7aa2f7"
ACCENT2   = "#bb9af7"
GREEN     = "#9ece6a"
RED       = "#f7768e"
YELLOW    = "#e0af68"
FG        = "#c0caf5"
FG2       = "#565f89"
FONT      = ("Inter", 10)
FONT_BOLD = ("Inter", 10, "bold")
MONO      = ("JetBrains Mono", 9) if sys.platform != "win32" else ("Consolas", 9)


# ── Helpers ─────────────────────────────────────────────────────────────────
def browse_file(var, filetypes=None):
    path = filedialog.askopenfilename(filetypes=filetypes or [("All files", "*.*")])
    if path:
        var.set(path)

def browse_dir(var):
    path = filedialog.askdirectory()
    if path:
        var.set(path)

def browse_save(var, defaultext=".json"):
    path = filedialog.asksaveasfilename(defaultextension=defaultext,
                                        filetypes=[("JSON", "*.json"), ("Log", "*.log"), ("All", "*.*")])
    if path:
        var.set(path)


class RetroArchiveUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Retro Archive")
        self.geometry("900x700")
        self.minsize(760, 560)
        self.configure(bg=BG)
        self._apply_style()
        self._build_ui()
        self._running_process = None

    # ── Styling ─────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".", background=BG, foreground=FG, font=FONT,
                    fieldbackground=BG2, troughcolor=BG2, borderwidth=0,
                    selectbackground=ACCENT, selectforeground=BG)

        s.configure("TNotebook", background=BG, tabmargins=[2, 4, 2, 0])
        s.configure("TNotebook.Tab", background=BG3, foreground=FG2,
                    padding=[16, 6], font=FONT_BOLD)
        s.map("TNotebook.Tab",
              background=[("selected", BG2)],
              foreground=[("selected", ACCENT)])

        s.configure("TFrame", background=BG2)
        s.configure("Card.TFrame", background=BG3, relief="flat")

        s.configure("TLabel", background=BG2, foreground=FG, font=FONT)
        s.configure("Dim.TLabel", background=BG2, foreground=FG2, font=("Inter", 9))
        s.configure("Header.TLabel", background=BG2, foreground=ACCENT,
                    font=("Inter", 12, "bold"))
        s.configure("Section.TLabel", background=BG2, foreground=ACCENT2,
                    font=("Inter", 9, "bold"))

        s.configure("TEntry", fieldbackground=BG3, foreground=FG,
                    insertcolor=FG, relief="flat", padding=6)

        s.configure("TCheckbutton", background=BG2, foreground=FG,
                    indicatorcolor=BG3, font=FONT)
        s.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)])

        s.configure("TRadiobutton", background=BG2, foreground=FG, font=FONT)
        s.map("TRadiobutton", indicatorcolor=[("selected", ACCENT)])

        s.configure("TCombobox", fieldbackground=BG3, foreground=FG,
                    selectbackground=BG3, selectforeground=FG)

        s.configure("TScale", background=BG2, troughcolor=BG3)

        # Buttons
        s.configure("Run.TButton", background=ACCENT, foreground=BG,
                    font=("Inter", 10, "bold"), padding=[20, 8], relief="flat")
        s.map("Run.TButton",
              background=[("active", "#92b0ff"), ("disabled", BG3)],
              foreground=[("disabled", FG2)])

        s.configure("Stop.TButton", background=RED, foreground=BG,
                    font=("Inter", 10, "bold"), padding=[20, 8], relief="flat")
        s.map("Stop.TButton", background=[("active", "#ff9090")])

        s.configure("Browse.TButton", background=BG3, foreground=ACCENT,
                    font=FONT, padding=[8, 4], relief="flat")
        s.map("Browse.TButton", background=[("active", "#3a3d5c")])

        s.configure("TSeparator", background=BG3)
        s.configure("TProgressbar", troughcolor=BG3, background=ACCENT, thickness=4)

    # ── Main layout ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # Title bar
        header = tk.Frame(self, bg=BG, pady=12)
        header.pack(fill="x", padx=20)
        tk.Label(header, text="⬡ Retro Archive", font=("Inter", 16, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(header, text="compress & verify your ROM collection",
                 font=("Inter", 10), bg=BG, fg=FG2).pack(side="left", padx=12)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=0)

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=16, pady=10)

        self._compress_tab = CompressTab(nb, self)
        self._verify_tab   = VerifyTab(nb, self)

        nb.add(self._compress_tab, text="  Compress  ")
        nb.add(self._verify_tab,   text="  Verify  ")

        # Output panel
        out_frame = tk.Frame(self, bg=BG, pady=4)
        out_frame.pack(fill="both", expand=False, padx=16, pady=(0, 12))

        hdr = tk.Frame(out_frame, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="OUTPUT", font=("Inter", 8, "bold"),
                 bg=BG, fg=FG2).pack(side="left")
        tk.Button(hdr, text="Clear", font=("Inter", 8), bg=BG, fg=FG2,
                  bd=0, cursor="hand2", activebackground=BG, activeforeground=ACCENT,
                  command=self._clear_output).pack(side="right")

        self.output_text = tk.Text(out_frame, height=14, bg="#13131f", fg=FG,
                                   font=MONO, relief="flat", bd=0,
                                   insertbackground=FG, wrap="word",
                                   selectbackground=ACCENT, selectforeground=BG)
        self.output_text.pack(fill="both", expand=True)
        self.output_text.tag_configure("ok",   foreground=GREEN)
        self.output_text.tag_configure("err",  foreground=RED)
        self.output_text.tag_configure("warn", foreground=YELLOW)
        self.output_text.tag_configure("info", foreground=ACCENT)
        self.output_text.tag_configure("dim",  foreground=FG2)

        sb = ttk.Scrollbar(out_frame, command=self.output_text.yview)
        self.output_text["yscrollcommand"] = sb.set
        sb.pack(side="right", fill="y")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self._progress = ttk.Progressbar(self, mode="indeterminate", style="TProgressbar")
        self._progress.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(self, textvariable=self.status_var, font=("Inter", 9),
                 bg=BG, fg=FG2, anchor="w").pack(fill="x", padx=16, pady=(0, 6))

    # ── Output helpers ───────────────────────────────────────────────────────
    def _clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")

    def append_output(self, line: str):
        self.output_text.configure(state="normal")
        lower = line.lower()
        if "[✓]" in line or "successfully" in lower or "healthy" in lower:
            tag = "ok"
        elif "[x]" in line or "error" in lower or "failed" in lower or "corrupt" in lower:
            tag = "err"
        elif "[!]" in line or "warn" in lower or "skipping" in lower:
            tag = "warn"
        elif "---" in line or "===" in line or "overview" in lower:
            tag = "info"
        elif line.startswith("Progress"):
            # overwrite progress line in place
            self.output_text.delete("end-2l", "end-1l")
            tag = "dim"
        else:
            tag = None

        self.output_text.insert("end", line + "\n", tag)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    # ── Process management ───────────────────────────────────────────────────
    def run_command(self, cmd: list, on_finish=None):
        if self._running_process:
            messagebox.showwarning("Busy", "A process is already running.")
            return

        self._clear_output()
        self.append_output(f"$ {' '.join(cmd)}\n")
        self.status_var.set("Running…")
        self._progress.start(10)

        def _worker():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                self._running_process = proc
                for line in proc.stdout:
                    self.after(0, self.append_output, line.rstrip())
                proc.wait()
                rc = proc.returncode
            except Exception as e:
                self.after(0, self.append_output, f"[x] Failed to start process: {e}")
                rc = -1
            finally:
                self._running_process = None
                self.after(0, self._on_process_done, rc, on_finish)

        threading.Thread(target=_worker, daemon=True).start()

    def stop_command(self):
        if self._running_process:
            self._running_process.terminate()

    def _on_process_done(self, rc, on_finish):
        self._progress.stop()
        if rc == 0:
            self.status_var.set("✓ Finished successfully")
        elif rc == 1:
            self.status_var.set("⚠ Finished with errors")
        else:
            self.status_var.set(f"✗ Process exited with code {rc}")
        if on_finish:
            on_finish(rc)


# ── Reusable widgets ─────────────────────────────────────────────────────────
class PathRow(ttk.Frame):
    """Label + Entry + Browse button in one row."""
    def __init__(self, parent, label, var, browse_fn, width=42):
        super().__init__(parent, style="TFrame")
        ttk.Label(self, text=label, width=16, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Entry(self, textvariable=var, width=width).pack(side="left", expand=True, fill="x")
        ttk.Button(self, text="Browse", style="Browse.TButton",
                   command=browse_fn).pack(side="left", padx=(4, 0))


class Section(ttk.Frame):
    """A card-like section with a title."""
    def __init__(self, parent, title):
        super().__init__(parent, style="TFrame", padding=10)
        ttk.Label(self, text=title.upper(), style="Section.TLabel").pack(anchor="w", pady=(0, 6))


# ══ Compress Tab ══════════════════════════════════════════════════════════════
class CompressTab(ttk.Frame):
    def __init__(self, parent, app: RetroArchiveUI):
        super().__init__(parent, padding=16)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Compress to 7Z", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        # Input
        inp = Section(self, "Input")
        inp.pack(fill="x", pady=(0, 8))

        self._input_mode = tk.StringVar(value="file")
        self._file_var = tk.StringVar()
        self._dir_var  = tk.StringVar()

        mode_row = ttk.Frame(inp, style="TFrame")
        mode_row.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(mode_row, text="Single File", variable=self._input_mode,
                        value="file", command=self._toggle_input).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mode_row, text="Directory", variable=self._input_mode,
                        value="directory", command=self._toggle_input).pack(side="left")

        self._file_row = PathRow(inp, "File", self._file_var,
                                 lambda: browse_file(self._file_var))
        self._file_row.pack(fill="x", pady=2)

        self._dir_row = PathRow(inp, "Directory", self._dir_var,
                                lambda: browse_dir(self._dir_var))
        self._dir_row.pack(fill="x", pady=2)

        self._toggle_input()

        # Options
        opts = Section(self, "Options")
        opts.pack(fill="x", pady=(0, 8))

        # File types
        ft_row = ttk.Frame(opts, style="TFrame")
        ft_row.pack(fill="x", pady=2)
        ttk.Label(ft_row, text="File Types", width=16, anchor="e").pack(side="left", padx=(0, 6))
        self._file_type_var = tk.StringVar()
        ttk.Entry(ft_row, textvariable=self._file_type_var, width=30).pack(side="left")
        ttk.Label(ft_row, text="  e.g.  .iso .bin  (blank = all)",
                  style="Dim.TLabel").pack(side="left", padx=8)

        # Level
        lvl_row = ttk.Frame(opts, style="TFrame")
        lvl_row.pack(fill="x", pady=6)
        ttk.Label(lvl_row, text="Level", width=16, anchor="e").pack(side="left", padx=(0, 6))
        self._level_var = tk.IntVar(value=5)
        scale = ttk.Scale(lvl_row, from_=0, to=9, orient="horizontal",
                          variable=self._level_var, length=180)
        scale.pack(side="left")
        ttk.Label(lvl_row, textvariable=self._level_var, width=3).pack(side="left", padx=6)
        ttk.Label(lvl_row, text="0 = store  9 = ultra", style="Dim.TLabel").pack(side="left")

        # Checkboxes
        chk_row = ttk.Frame(opts, style="TFrame")
        chk_row.pack(fill="x", pady=2)
        self._delete_var = tk.BooleanVar()
        ttk.Checkbutton(chk_row, text="Delete originals after compression",
                        variable=self._delete_var).pack(side="left")

        # Output
        out = Section(self, "Output")
        out.pack(fill="x", pady=(0, 8))

        self._out_dir_var = tk.StringVar()
        PathRow(out, "Output Dir", self._out_dir_var,
                lambda: browse_dir(self._out_dir_var)).pack(fill="x", pady=2)

        self._result_var = tk.StringVar()
        PathRow(out, "Stats JSON", self._result_var,
                lambda: browse_save(self._result_var)).pack(fill="x", pady=2)

        self._log_var = tk.StringVar()
        PathRow(out, "Log File", self._log_var,
                lambda: browse_save(self._log_var, ".log")).pack(fill="x", pady=2)

        # Buttons
        btn_row = ttk.Frame(self, style="TFrame")
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="▶  Run Compression", style="Run.TButton",
                   command=self._run).pack(side="left")
        ttk.Button(btn_row, text="■  Stop", style="Stop.TButton",
                   command=self.app.stop_command).pack(side="left", padx=8)

    def _toggle_input(self):
        if self._input_mode.get() == "file":
            self._file_row.pack(fill="x", pady=2)
            self._dir_row.pack_forget()
        else:
            self._file_row.pack_forget()
            self._dir_row.pack(fill="x", pady=2)

    def _run(self):
        cmd = [sys.executable, COMPRESS_SCRIPT]

        if self._input_mode.get() == "file":
            if not self._file_var.get():
                messagebox.showerror("Missing Input", "Please select a file to compress.")
                return
            cmd += ["--file", self._file_var.get()]
        else:
            if not self._dir_var.get():
                messagebox.showerror("Missing Input", "Please select a directory to compress.")
                return
            cmd += ["--directory", self._dir_var.get()]

        ft = self._file_type_var.get().strip()
        if ft:
            cmd += ["--file-type"] + ft.split()

        cmd += ["--level", str(self._level_var.get())]

        if self._delete_var.get():
            cmd.append("--delete")
        if self._out_dir_var.get():
            cmd += ["--output-dir", self._out_dir_var.get()]
        if self._result_var.get():
            cmd += ["--result", self._result_var.get()]
        if self._log_var.get():
            cmd += ["--log-file", self._log_var.get()]

        self.app.run_command(cmd)


# ══ Verify Tab ════════════════════════════════════════════════════════════════
class VerifyTab(ttk.Frame):
    def __init__(self, parent, app: RetroArchiveUI):
        super().__init__(parent, padding=16)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Verify ROMs / Archives", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        # Input
        inp = Section(self, "Input")
        inp.pack(fill="x", pady=(0, 8))

        self._input_mode = tk.StringVar(value="file")
        self._file_var = tk.StringVar()
        self._dir_var  = tk.StringVar()

        mode_row = ttk.Frame(inp, style="TFrame")
        mode_row.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(mode_row, text="Single File", variable=self._input_mode,
                        value="file", command=self._toggle_input).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mode_row, text="Directory", variable=self._input_mode,
                        value="directory", command=self._toggle_input).pack(side="left")

        self._file_row = PathRow(inp, "File", self._file_var,
                                 lambda: browse_file(self._file_var))
        self._file_row.pack(fill="x", pady=2)

        self._dir_row = PathRow(inp, "Directory", self._dir_var,
                                lambda: browse_dir(self._dir_var))
        self._dir_row.pack(fill="x", pady=2)
        self._toggle_input()

        # Command
        cmd_frame = Section(self, "Command")
        cmd_frame.pack(fill="x", pady=(0, 8))

        self._command = tk.StringVar(value="redump")
        cmd_row = ttk.Frame(cmd_frame, style="TFrame")
        cmd_row.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(cmd_row, text="Redump verification", variable=self._command,
                        value="redump", command=self._toggle_command).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(cmd_row, text="Integrity check", variable=self._command,
                        value="integrity-check", command=self._toggle_command).pack(side="left")

        # Redump options (shown/hidden)
        self._redump_frame = ttk.Frame(cmd_frame, style="TFrame")
        self._redump_frame.pack(fill="x")

        self._dat_var = tk.StringVar()
        PathRow(self._redump_frame, "DAT File", self._dat_var,
                lambda: browse_file(self._dat_var, [("DAT files", "*.dat"), ("XML", "*.xml"), ("All", "*.*")])
                ).pack(fill="x", pady=2)

        self._archived_rom_var = tk.BooleanVar()
        ttk.Checkbutton(self._redump_frame,
                        text="--archived-rom  (stream-verify ROMs inside ZIP/7Z archives)",
                        variable=self._archived_rom_var).pack(anchor="w", pady=4)

        # Output
        out = Section(self, "Output")
        out.pack(fill="x", pady=(0, 8))

        self._result_var = tk.StringVar()
        PathRow(out, "Result JSON", self._result_var,
                lambda: browse_save(self._result_var)).pack(fill="x", pady=2)

        self._log_var = tk.StringVar()
        PathRow(out, "Log File", self._log_var,
                lambda: browse_save(self._log_var, ".log")).pack(fill="x", pady=2)

        # Buttons
        btn_row = ttk.Frame(self, style="TFrame")
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="▶  Run Verification", style="Run.TButton",
                   command=self._run).pack(side="left")
        ttk.Button(btn_row, text="■  Stop", style="Stop.TButton",
                   command=self.app.stop_command).pack(side="left", padx=8)

    def _toggle_input(self):
        if self._input_mode.get() == "file":
            self._file_row.pack(fill="x", pady=2)
            self._dir_row.pack_forget()
        else:
            self._file_row.pack_forget()
            self._dir_row.pack(fill="x", pady=2)

    def _toggle_command(self):
        if self._command.get() == "redump":
            self._redump_frame.pack(fill="x")
        else:
            self._redump_frame.pack_forget()

    def _run(self):
        cmd = [sys.executable, VERIFY_SCRIPT]

        if self._input_mode.get() == "file":
            if not self._file_var.get():
                messagebox.showerror("Missing Input", "Please select a file to verify.")
                return
            cmd += ["--file", self._file_var.get()]
        else:
            if not self._dir_var.get():
                messagebox.showerror("Missing Input", "Please select a directory to verify.")
                return
            cmd += ["--directory", self._dir_var.get()]

        if self._log_var.get():
            cmd += ["--log-file", self._log_var.get()]

        sub = self._command.get()
        cmd.append(sub)

        if sub == "redump":
            if self._dat_var.get():
                cmd += ["--dat", self._dat_var.get()]
            if self._result_var.get():
                cmd += ["--result", self._result_var.get()]
            if self._archived_rom_var.get():
                cmd.append("--archived-rom")

        self.app.run_command(cmd)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = RetroArchiveUI()
    app.mainloop()
