# Retro Archive Scripts

## AI-Generated Disclaimer
These scripts are AI-generated. They have not been formally reviewed by a human developer, but it has been verified that they work as intended.

## Scripts

### 1. `redump-verify.py`
A Python command-line tool designed to verify ROM and ISO files against official Redump XML DAT databases. It calculates CRC32, MD5, and SHA-1 hashes of your local files and cross-references them with the DAT file to ensure you have perfect, unmodified dumps.

#### Features
* **Multiple Hashing Algorithms:** Calculates CRC32, MD5, and SHA-1 simultaneously.
* **Memory Efficient:** Reads files (and ZIP contents) in 4MB chunks, allowing it to process large ISOs without consuming excessive RAM.
* **Batch Processing:** Scan a single file or an entire directory of `.iso`, `.bin`, `.zip`, and `.7z` files.
* **Archive Support:** Verifies ROMs directly inside ZIP and 7z archives without extracting them to disk.
* **Redump DAT Support:** Parses official Redump XML databases to verify matches.
* **No External Dependencies Required:** Built entirely with Python's standard library. (Optional: `py7zr` for `.7z` support)

#### Usage

**Verify a single file:**
```bash
python redump-verify.py --file path/to/game.iso --dat path/to/redump.dat
```

**Verify a directory of files:**
```bash
python redump-verify.py --directory path/to/roms/ --dat path/to/redump.dat
```

**Additional Options:**
* `--log-file <path>`: Save the console output to a log file.
* `--zipped-rom`: Treat ZIP/7z files as archives and verify the `.iso` or `.bin` ROMs inside them directly.
* `--result <path>`: Output a JSON file mapping verified and failed filenames to their SHA-1 hashes.
* `--log-level <LEVEL>`: Set the logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default is `INFO`.

---

### 2. `compress_iso.py`
A Python script to compress `.iso` files into the highly efficient `.7z` archive format using the 7-Zip (`7z`) executable.

#### Features
* **Batch Compression:** Compress a single `.iso` or an entire directory automatically.
* **Space Saving:** Automatically delete the original `.iso` file after successful compression using the `--delete` flag.
* **Live Progress:** Streams 7-Zip's native progress percentage directly to your terminal.
* **JSON Statistics:** Generate detailed JSON reports containing compression ratios, bytes saved, and time taken using the `--result` flag.
* **Configurable:** Customize compression levels and output directories.

#### Requirements
* Requires the `7z` executable to be installed and available in your system's PATH (or specify its location with `--7zip`).

#### Usage

**Compress a single ISO file:**
```bash
python compress_iso.py --file /path/to/game.iso
```

**Compress a directory of ISO files and delete the originals:**
```bash
python compress_iso.py --directory /path/to/isos --delete
```

**Specify maximum compression (9) and a custom output directory:**
```bash
python compress_iso.py --directory /path/to/isos --level 9 --output-dir /path/to/output
```

**Generate a JSON statistics report of the compression batch:**
```bash
python compress_iso.py --directory /path/to/isos --result compression_stats.json
```

## System Requirements
* Python 3.6 or higher
* Optional: `py7zr` package for `.7z` verification support in `redump-verify.py` (`pip install -r requirements.txt`)
* Tested in Python 3.12.3