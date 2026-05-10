# Retro Archive Scripts

## AI-Generated Disclaimer
These scripts are AI-generated. They have not been formally reviewed by a human developer, but it has been verified that they work as intended.

## Scripts

### 1. `verify.py`
A Python command-line tool designed to verify ROM and ISO files against official Redump XML DAT databases, and to check the integrity of ZIP and 7Z archives.

#### Features
* **Multiple Verification Commands:** Includes `redump` for DAT-based verification and `integrity-check` for archive testing.
* **Multiple Hashing Algorithms:** Calculates CRC32, MD5, and SHA-1 simultaneously for Redump verification.
* **Memory Efficient:** Reads files (and ZIP contents) in 4MB chunks, allowing it to process large files without consuming excessive RAM.
* **Batch Processing:** Scan a single file or an entire directory.
* **Archive Support:** Verifies ROMs directly inside ZIP and 7z archives without extracting them to disk.
* **No External System Dependencies:** Built entirely with Python. Uses the `py7zr` library for `.7z` support.

#### Usage

**Verify against a Redump DAT:**
```bash
python3 verify.py --file path/to/game.iso redump --dat path/to/redump.dat
```

**Verify a directory of files against Redump:**
```bash
python3 verify.py --directory path/to/roms/ redump --dat path/to/redump.dat
```

**Check the integrity of archives in a directory:**
```bash
python3 verify.py --directory path/to/roms/ integrity-check
```

**Additional Options:**
* `--log-file <path>`: Save the console output to a log file.
* `--archived-rom`: (for `redump` command) Treat ZIP/7z files as archives and verify the ROMs inside them directly.
* `--result <path>`: (for `redump` command) Output a JSON file mapping verified and failed filenames to their SHA-1 hashes.

---

### 2. `compress.py`
A Python script to compress files into the highly efficient `.7z` archive format natively using the `py7zr` library.

#### Features
* **Batch Compression:** Compress a single file or an entire directory automatically.
* **Custom File Types:** Use `--file-type` to specify which files to compress when scanning a directory (e.g. `.iso .bin`). If omitted, all files in the directory will be compressed (existing `.7z` archives are automatically ignored).
* **Space Saving:** Automatically delete the original file after successful compression using the `--delete` flag.
* **JSON Statistics:** Generate detailed JSON reports containing compression ratios, bytes saved, and time taken using the `--result` flag.
* **Configurable:** Customize compression levels and output directories.

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

**Specify maximum compression (9) and a custom output directory:**
```bash
python3 compress.py --directory /path/to/isos --level 9 --output-dir /path/to/output
```

**Generate a JSON statistics report of the compression batch:**
```bash
python3 compress.py --directory /path/to/isos --result compression_stats.json
```

## System Requirements
* Python 3.6 or higher
* Required: `py7zr` package for `.7z` verification and compression support (`pip install -r requirements.txt`)
* Tested in Python 3.12+ and 3.14