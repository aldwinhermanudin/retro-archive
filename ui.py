#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
import time

# Import from our existing modules
import compress
import verify

class StdoutRedirector:
    def __init__(self, text_widget, progress_callback=None):
        self.text_widget = text_widget
        self.progress_callback = progress_callback
        
    def write(self, string):
        self.text_widget.after(0, self._write, string)
        
    def _write(self, string):
        import re
        if self.progress_callback and '\rProgress' in string:
            match = re.search(r'Progress(?: \[([^\]]+)\])?:\s*\[([\d\.]+)%\]', string)
            if match:
                filename = match.group(1) or ""
                try:
                    percent = float(match.group(2))
                    self.progress_callback(filename, percent)
                except ValueError:
                    pass

        self.text_widget.configure(state='normal')
        for char in string:
            if char == '\r':
                self.text_widget.mark_set("insert", "insert linestart")
                self.text_widget.delete("insert", "insert lineend")
            else:
                self.text_widget.insert("insert", char)
        self.text_widget.see('end')
        self.text_widget.configure(state='disabled')
        
    def flush(self):
        pass

class RedirectHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._write, msg + "\n")

    def _write(self, string):
        self.text_widget.configure(state='normal')
        self.text_widget.insert('end', string)
        self.text_widget.see('end')
        self.text_widget.configure(state='disabled')

class RetroArchiveUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Retro Archive Tool")
        self.root.geometry("800x600")
        
        self.is_running = False
        self.create_widgets()
        self.setup_logging()
        
    def setup_logging(self):
        sys.stdout = StdoutRedirector(self.log_text, self.update_progress)
        sys.stderr = StdoutRedirector(self.log_text)
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(RedirectHandler(self.log_text))
        
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.compress_frame = ttk.Frame(self.notebook)
        self.verify_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.compress_frame, text="Compress")
        self.notebook.add(self.verify_frame, text="Verify")
        
        self.setup_compress_tab()
        self.setup_verify_tab()
        
        # Progress Section
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Idle")
        self.progress_label.pack(side='top', anchor='w')
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill='x', expand=True, pady=2)
        
        # Total Progress Section
        total_progress_frame = ttk.Frame(self.root)
        total_progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.total_progress_label = ttk.Label(total_progress_frame, text="Total Progress: 0/0 (0%)")
        self.total_progress_label.pack(side='top', anchor='w')
        
        self.total_progress_bar = ttk.Progressbar(total_progress_frame, orient='horizontal', mode='determinate')
        self.total_progress_bar.pack(fill='x', expand=True, pady=2)
        
        # Global Options Section
        global_opts_frame = ttk.LabelFrame(self.root, text="Reports Output")
        global_opts_frame.pack(fill='x', padx=10, pady=5)
        
        self.report_dir_var = tk.StringVar(value=os.getcwd())
        ttk.Label(global_opts_frame, text="Directory:").pack(side='left', padx=5)
        ttk.Entry(global_opts_frame, textvariable=self.report_dir_var).pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(global_opts_frame, text="Browse", command=lambda: self.report_dir_var.set(filedialog.askdirectory())).pack(side='left', padx=5)
        
        # Log Output Section
        log_frame = ttk.LabelFrame(self.root, text="Log Output")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(fill='x', padx=5, pady=0)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Current Task", command=self.stop_task, state='disabled')
        self.stop_btn.pack(side='right')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=10, bg='black', fg='white', font=('Courier', 10))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_compress_tab(self):
        # Input selection
        input_frame = ttk.LabelFrame(self.compress_frame, text="Input")
        input_frame.pack(fill='x', padx=10, pady=5)
        
        self.comp_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.comp_input_var).pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse File", command=lambda: self.comp_input_var.set(filedialog.askopenfilename())).pack(side='left', padx=2)
        ttk.Button(input_frame, text="Browse Dir", command=lambda: self.comp_input_var.set(filedialog.askdirectory())).pack(side='left', padx=2)
        
        # Options
        options_frame = ttk.LabelFrame(self.compress_frame, text="Options")
        options_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(options_frame, text="Level (0-9):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.comp_level_var = tk.IntVar(value=5)
        ttk.Spinbox(options_frame, from_=0, to=9, textvariable=self.comp_level_var, width=5).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        self.comp_delete_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Delete Original after compression", variable=self.comp_delete_var).grid(row=0, column=2, padx=10, pady=5, sticky='w')

        ttk.Label(options_frame, text="Output Dir (Optional):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.comp_output_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.comp_output_var, width=30).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')
        ttk.Button(options_frame, text="Browse", command=lambda: self.comp_output_var.set(filedialog.askdirectory())).grid(row=1, column=3, padx=5, pady=5)
        
        # Run button
        ttk.Button(self.compress_frame, text="Start Compression", command=self.run_compression).pack(pady=10)

    def setup_verify_tab(self):
        # Input selection
        input_frame = ttk.LabelFrame(self.verify_frame, text="Input")
        input_frame.pack(fill='x', padx=10, pady=5)
        
        self.ver_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.ver_input_var).pack(side='left', fill='x', expand=True, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse File", command=lambda: self.ver_input_var.set(filedialog.askopenfilename())).pack(side='left', padx=2)
        ttk.Button(input_frame, text="Browse Dir", command=lambda: self.ver_input_var.set(filedialog.askdirectory())).pack(side='left', padx=2)
        
        # Options
        options_frame = ttk.LabelFrame(self.verify_frame, text="Options")
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.ver_mode_var = tk.StringVar(value="redump")
        ttk.Radiobutton(options_frame, text="Redump Verify", variable=self.ver_mode_var, value="redump").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Radiobutton(options_frame, text="Integrity Check (ZIP/7Z)", variable=self.ver_mode_var, value="integrity").grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(options_frame, text="DAT File (for Redump):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.ver_dat_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.ver_dat_var, width=30).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')
        ttk.Button(options_frame, text="Browse", command=lambda: self.ver_dat_var.set(filedialog.askopenfilename(filetypes=[("DAT files", "*.dat"), ("XML files", "*.xml"), ("All files", "*.*")]))).grid(row=1, column=3, padx=5, pady=5)
        
        self.ver_archived_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Verify inside Archives (ZIP/7z)", variable=self.ver_archived_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        
        # Run button
        ttk.Button(self.verify_frame, text="Start Verification", command=self.run_verification).pack(pady=10)

    def log_clear(self):
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

    def update_progress(self, filename, percent):
        text = f"Processing: {filename} ({percent:.1f}%)" if filename else f"Processing... ({percent:.1f}%)"
        self.progress_label.config(text=text)
        self.progress_bar['value'] = percent

    def update_total_progress(self, current, total):
        percent = (current / total) * 100 if total > 0 else 0
        text = f"Total Progress: {current}/{total} ({percent:.1f}%)"
        self.root.after(0, self._set_total_progress, text, percent)

    def _set_total_progress(self, text, percent):
        self.total_progress_label.config(text=text)
        self.total_progress_bar['value'] = percent
        
    def reset_progress(self):
        self.progress_label.config(text="Idle")
        self.progress_bar['value'] = 0
        self.total_progress_label.config(text="Total Progress: 0/0 (0.0%)")
        self.total_progress_bar['value'] = 0

    def stop_task(self):
        if self.is_running:
            compress.STOP_REQUESTED = True
            verify.STOP_REQUESTED = True
            logging.warning("\n[!] Stop requested. Aborting current operation...")
            self.stop_btn.configure(state='disabled')

    def run_compression(self):
        if self.is_running:
            messagebox.showwarning("Task Running", "A task is already running. Please wait for it to finish before starting a new one.")
            return

        input_path = self.comp_input_var.get().strip()
        if not input_path:
            messagebox.showerror("Error", "Please select an input file or directory.")
            return
            
        level = self.comp_level_var.get()
        delete_orig = self.comp_delete_var.get()
        output_dir = self.comp_output_var.get().strip()
        
        self.log_clear()
        self.reset_progress()
        self.is_running = True
        compress.STOP_REQUESTED = False
        verify.STOP_REQUESTED = False
        compress.TOTAL_PROGRESS_CALLBACK = self.update_total_progress
        verify.TOTAL_PROGRESS_CALLBACK = self.update_total_progress
        self.stop_btn.configure(state='normal')
        threading.Thread(target=self._compress_task, args=(input_path, output_dir, level, delete_orig), daemon=True).start()

    def _compress_task(self, input_path, output_dir, level, delete_orig):
        try:
            files_to_compress = []
            if os.path.isfile(input_path):
                files_to_compress.append(input_path)
            elif os.path.isdir(input_path):
                for root_dir, _, files in os.walk(input_path):
                    for f in files:
                        if not f.lower().endswith('.7z'):
                            files_to_compress.append(os.path.join(root_dir, f))
                            
            if not files_to_compress:
                logging.info("No files found to compress.")
                return

            results = compress.run_batch_compression(files_to_compress, output_dir, level, delete_orig)
            
            report_dir = self.report_dir_var.get().strip() or os.getcwd()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            json_path = os.path.join(report_dir, f"compress_report_{timestamp}.json")
            compress.save_json_report(results, len(files_to_compress), json_path)
            
            log_path = os.path.join(report_dir, f"compress_log_{timestamp}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get(1.0, tk.END))
            logging.info(f"\nSaved log to: {log_path}")
        except Exception as e:
            if str(e) != "AbortRequested":
                logging.error(f"Error during compression: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.stop_btn.configure(state='disabled'))
            self.root.after(0, self.reset_progress)

    def run_verification(self):
        if self.is_running:
            messagebox.showwarning("Task Running", "A task is already running. Please wait for it to finish before starting a new one.")
            return

        input_path = self.ver_input_var.get().strip()
        if not input_path:
            messagebox.showerror("Error", "Please select an input file or directory.")
            return
            
        mode = self.ver_mode_var.get()
        dat_file = self.ver_dat_var.get().strip()
        archived = self.ver_archived_var.get()
        
        self.log_clear()
        self.reset_progress()
        self.is_running = True
        compress.STOP_REQUESTED = False
        verify.STOP_REQUESTED = False
        compress.TOTAL_PROGRESS_CALLBACK = self.update_total_progress
        verify.TOTAL_PROGRESS_CALLBACK = self.update_total_progress
        self.stop_btn.configure(state='normal')
        threading.Thread(target=self._verify_task, args=(input_path, mode, dat_file, archived), daemon=True).start()

    def _verify_task(self, input_path, mode, dat_file, archived):
        try:
            files_to_verify = []
            if os.path.isfile(input_path):
                files_to_verify.append(input_path)
            elif os.path.isdir(input_path):
                for root_dir, _, files in os.walk(input_path):
                    for f in files:
                        if mode == 'integrity':
                            if f.lower().endswith(('.zip', '.7z')):
                                files_to_verify.append(os.path.join(root_dir, f))
                        else:
                            if f.lower().endswith(('.iso', '.zip', '.bin', '.7z')):
                                files_to_verify.append(os.path.join(root_dir, f))

            if not files_to_verify:
                logging.info("No valid files found to verify.")
                return
                
            dat_root = None
            if mode == 'redump' and dat_file:
                logging.info(f"Loading DAT file: {dat_file}")
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(dat_file)
                    dat_root = tree.getroot()
                except Exception as e:
                    logging.error(f"Error parsing DAT file: {e}")
                    return

            logging.info(f"Starting verification ({mode}) for {len(files_to_verify)} files...")
            
            if mode == 'integrity':
                results = verify.run_integrity_check(files_to_verify)
            else:
                results = verify.run_redump_check(files_to_verify, dat_root, archived)

            report_dir = self.report_dir_var.get().strip() or os.getcwd()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            json_path = os.path.join(report_dir, f"verify_report_{timestamp}.json")
            verify.save_json_report(results, json_path)
            
            log_path = os.path.join(report_dir, f"verify_log_{timestamp}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get(1.0, tk.END))
            logging.info(f"\nSaved log to: {log_path}")
        except Exception as e:
            if str(e) != "AbortRequested":
                logging.error(f"Error during verification: {e}")
        finally:
            logging.info("\nVerification task complete.")
            self.is_running = False
            self.root.after(0, lambda: self.stop_btn.configure(state='disabled'))
            self.root.after(0, self.reset_progress)

if __name__ == "__main__":
    root = tk.Tk()
    app = RetroArchiveUI(root)
    root.mainloop()
