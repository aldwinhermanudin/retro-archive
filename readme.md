# Retro Archive Scripts

## AI-Generated Disclaimer
These scripts are AI-generated. They have not been formally reviewed by a human developer, but it has been verified that they work as intended.

## Scripts

### 1. `verify.py`
A Python command-line tool designed to verify ROM and ISO files against official Redump XML DAT databases, and to check the integrity of ZIP and 7Z archives.

#### Features
* **Multiple Verification Commands:** Includes `redump` for DAT-based verification and `integrity-check` for archive testing.
* **Multiple Hashing Algorithms:** Calculates CRC32, MD5, and SHA-1 simultaneously for Redump verification.
* **Memory Efficient:** Reads plain files in 4MB chunks. For archives, decompressed data is streamed directly into the hash calculator — no temp files, no disk writes.
* **Batch Processing:** Scan a single file or an entire directory.
* **Archive Support:** Verifies ROMs inside ZIP and 7Z archives by streaming decompressed data directly into the hash calculator — no temp files, no disk writes.
* **Signal Handling:** Gracefully handles Ctrl+C and SIGTERM with a clean exit message.
* **No External System Dependencies:** Built entirely with Python. Uses `py7zr >= 1.0` for `.7z` support.

#### Usage

**Verify a single file against a Redump DAT:**
```bash
python3 verify.py --file path/to/game.iso redump --dat path/to/redump.dat
```

**Verify a directory of files against Redump:**
```bash
python3 verify.py --directory path/to/roms/ redump --dat path/to/redump.dat
```

**Verify ROMs inside 7Z/ZIP archives against Redump:**
```bash
python3 verify.py --directory path/to/roms/ redump --dat path/to/redump.dat --archived-rom
```

**Check the integrity of archives in a directory:**
```bash
python3 verify.py --directory path/to/roms/ integrity-check
```

**Additional Options:**
* `--log-file <path>`: Save the console output to a log file.
* `--log-level <LEVEL>`: Set the logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default is `INFO`.
* `--archived-rom`: (for `redump` command) Verify the ROMs inside ZIP/7z archives by streaming decompressed data directly into the hash calculator — no temp files, no disk writes.
* `--result <path>`: (for `redump` command) Output a JSON file mapping verified and failed filenames to their SHA-1 hashes.

---

### 2. `compress.py`
A Python script to compress files into the highly efficient `.7z` archive format natively using the `py7zr` library.

#### Features
* **Batch Compression:** Compress a single file or an entire directory automatically.
* **Custom File Types:** Use `--file-type` to specify which files to compress when scanning a directory (e.g. `.iso .bin`). If omitted, all files in the directory will be compressed (existing `.7z` archives are automatically ignored).
* **Integrity Check on Existing Archives:** If an output `.7z` already exists, it is tested for integrity before being skipped. Corrupted archives are automatically overwritten.
* **Space Saving:** Automatically delete the original file after successful compression using the `--delete` flag.
* **Live Progress:** Displays a live progress bar during compression.
* **JSON Statistics:** Generate detailed JSON reports containing compression ratios, bytes saved, and time taken using the `--result` flag.
* **Configurable:** Customize compression levels and output directories.
* **Signal Handling:** Gracefully handles Ctrl+C and SIGTERM, deleting any partial `.7z` file before exiting.

#### Requirements
* Requires the `py7zr` Python package (`pip install py7zr`).

#### Usage

**Compress a single file:**
```bash
python3 compress.py --file /path/to/game.iso
```

**Compress a directory of specific files and delete the originals:**
```bash
python3 compress.py --directory /path/to/isos --delete --file-type .iso .bin
```

**Compress all files in a directory:**
```bash
python3 compress.py --directory /path/to/isos
```

**Specify maximum compression (9) and a custom output directory:**
```bash
python3 compress.py --directory /path/to/isos --level 9 --output-dir /path/to/output
```

**Generate a JSON statistics report of the compression batch:**
```bash
python3 compress.py --directory /path/to/isos --result compression_stats.json
```

### 3. `ui.py`
A graphical user interface built with Python's built-in `tkinter` that wraps the functionality of `compress.py` and `verify.py`.

#### Features
* **Cross-Platform UI:** Works on Windows, macOS, and Linux without requiring additional UI frameworks.
* **Unified Interface:** Tabbed interface to access both Compression and Verification tools in one place.
* **Direct Integration:** Imports and executes batch processing functions directly from the core tools, eliminating subprocess overhead.
* **Real-time Logging:** Intercepts standard output and logging calls to display command-line progress bars and logs directly in a scrolling text widget.
* **Non-blocking Execution:** Runs operations in background threads to keep the UI responsive during long-running tasks.

#### Usage

Launch the graphical interface:
```bash
python3 ui.py
```

---

## System Requirements
* Python 3.10 or higher
* Required: `py7zr >= 1.0` for `.7z` verification and compression support (`pip install -r requirements.txt`)
* Tested in Python 3.12+ and 3.14