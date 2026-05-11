#!/usr/bin/env python3
import os
import sys
import zlib
import signal
import hashlib
import argparse
import logging
import json
import xml.etree.ElementTree as ET
import zipfile

try:
    import py7zr
    from py7zr.io import Py7zIO, WriterFactory
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
    Py7zIO = object
    WriterFactory = object

__version__ = "0.1.0"

def calculate_hashes_from_stream(f, file_size: int, filename: str):
    """Calculates CRC32, MD5, and SHA-1 hashes for a given file stream."""
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()
    crc32_hash = 0
    
    processed = 0
    
    logging.info(f"Calculating hashes for: {filename}")
    logging.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
    
    # Read in 4MB chunks to keep memory usage low
    for chunk in iter(lambda: f.read(4096 * 1024), b""):
        if globals().get('STOP_REQUESTED', False):
            raise Exception("AbortRequested")
        md5_hash.update(chunk)
        sha1_hash.update(chunk)
        crc32_hash = zlib.crc32(chunk, crc32_hash)
        
        processed += len(chunk)
        if file_size > 0:
            percent = (processed / file_size) * 100
            sys.stdout.write(f"\rProgress: [{percent:.1f}%] {processed/(1024*1024):.1f}MB")
            sys.stdout.flush()
            
    logging.info("\nHash calculation complete!\n")
    
    return {
        "crc32": format(crc32_hash & 0xFFFFFFFF, '08x'),
        "md5": md5_hash.hexdigest(),
        "sha1": sha1_hash.hexdigest(),
        "size": str(file_size)
    }

class HashCalculationIO(Py7zIO):
    def __init__(self, filename, size_expected):
        self.filename = filename
        self.size_expected = size_expected
        self.processed = 0
        self.md5_hash = hashlib.md5()
        self.sha1_hash = hashlib.sha1()
        self.crc32_hash = 0

    def write(self, s):
        if globals().get('STOP_REQUESTED', False):
            raise Exception("AbortRequested")
        self.md5_hash.update(s)
        self.sha1_hash.update(s)
        self.crc32_hash = zlib.crc32(s, self.crc32_hash)
        
        self.processed += len(s)
        if self.size_expected > 0:
            percent = (self.processed / self.size_expected) * 100
            sys.stdout.write(f"\rProgress [{self.filename}]: [{percent:.1f}%] {self.processed/(1024*1024):.1f}MB")
            sys.stdout.flush()
        return len(s)

    def flush(self):
        pass

    def read(self, length=-1):
        return b""

    def seek(self, offset, whence=0):
        return 0

    def size(self):
        return self.size_expected

    def close(self):
        sys.stdout.write("\n")
        sys.stdout.flush()

    def get_hashes(self):
        return {
            "crc32": format(self.crc32_hash & 0xFFFFFFFF, '08x'),
            "md5": self.md5_hash.hexdigest(),
            "sha1": self.sha1_hash.hexdigest(),
            "size": str(self.size_expected)
        }

class HashWriterFactory(WriterFactory):
    def __init__(self, file_sizes):
        self.file_sizes = file_sizes
        self.io_objects = {}

    def create(self, filename):
        size = self.file_sizes.get(filename, 0)
        obj = HashCalculationIO(filename, size)
        self.io_objects[filename] = obj
        return obj

def calculate_hashes(filepath: str):
    """Calculates CRC32, MD5, and SHA-1 hashes for a given file."""
    file_size = os.path.getsize(filepath)
    with open(filepath, "rb") as f:
        return calculate_hashes_from_stream(f, file_size, os.path.basename(filepath))

def check_redump_dat(dat_root, file_hashes: dict) -> dict:
    """Searches for matching hashes in the parsed Redump XML DAT root."""
    for game in dat_root.findall('game'):
        for rom in game.findall('rom'):
            rom_sha1 = rom.get('sha1', '').lower()
            rom_md5 = rom.get('md5', '').lower()
            
            # SHA-1 is standard for checking against collisions, but checking both is safest
            if rom_sha1 == file_hashes['sha1'] or rom_md5 == file_hashes['md5']:
                return {
                    "game_name": game.get('name', 'Unknown'),
                    "rom_name": rom.get('name', 'Unknown'),
                    "status": "Match"
                }
                
    return None

def _handle_signal(signum, frame):
    sig_name = "SIGTERM" if signum == signal.SIGTERM else "Ctrl+C"
    sys.stdout.write("\n")
    logging.error(f"[!] Interrupted by user ({sig_name}). Exiting...")
    sys.exit(1)

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

def run_integrity_check(files_to_verify):
    if not files_to_verify:
        logging.info("No valid files found to verify.")
        return {"healthy": [], "corrupted": []}

    results = {"healthy": [], "corrupted": []}
    total_files = len(files_to_verify)
    for i, filepath in enumerate(files_to_verify):
        cb = globals().get('TOTAL_PROGRESS_CALLBACK')
        if cb:
            cb(i, total_files)
            
        if globals().get('STOP_REQUESTED', False):
            logging.warning("\n[!] Integrity check aborted by user.")
            break

        logging.info(f"\n--- Checking Integrity: {filepath} ---")
        is_zip = filepath.lower().endswith('.zip')
        is_7z = filepath.lower().endswith('.7z')
        
        if is_zip:
            try:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    bad_file = zf.testzip()
                    if bad_file is not None:
                        logging.error(f"[x] CORRUPTED: Bad file found inside ZIP: {bad_file}")
                        results["corrupted"].append({"file": filepath, "reason": f"Bad file: {bad_file}"})
                    else:
                        logging.info("[✓] HEALTHY: ZIP archive is intact.")
                        results["healthy"].append(filepath)
            except zipfile.BadZipFile:
                logging.error(f"[x] CORRUPTED: Invalid ZIP file -> {filepath}")
                results["corrupted"].append({"file": filepath, "reason": "BadZipFile"})
                
        elif is_7z:
            if not HAS_PY7ZR:
                logging.error(f"[x] SKIPPED: py7zr module is required for .7z files. Install with 'pip install py7zr'")
                continue
            try:
                with py7zr.SevenZipFile(filepath, 'r') as zf:
                    zf.test()
                logging.info("[✓] HEALTHY: 7Z archive is intact.")
                results["healthy"].append(filepath)
            except py7zr.exceptions.Bad7zFile:
                logging.error(f"[x] CORRUPTED: Invalid 7z file -> {filepath}")
                results["corrupted"].append({"file": filepath, "reason": "Bad7zFile"})
            except Exception as e:
                logging.error(f"[x] CORRUPTED: Error testing 7z file -> {e}")
                results["corrupted"].append({"file": filepath, "reason": str(e)})

    cb = globals().get('TOTAL_PROGRESS_CALLBACK')
    if cb and not globals().get('STOP_REQUESTED', False):
        cb(total_files, total_files)

    logging.info("\n" + "=" * 40)
    logging.info("INTEGRITY CHECK OVERVIEW")
    logging.info("=" * 40)
    logging.info(f"Total archives checked: {len(files_to_verify)}")
    logging.info(f"Healthy archives:       {len(results['healthy'])}")
    logging.info(f"Corrupted archives:     {len(results['corrupted'])}")
    if results['corrupted']:
        logging.info("\nCorrupted Files:")
        for f in results['corrupted']:
            logging.info(f"  - {f['file']} ({f['reason']})")
            
    return results

def run_redump_check(files_to_verify, dat_root, archived_rom):
    if not files_to_verify:
        logging.info("No valid files found to verify.")
        return {"matched": [], "failed": [], "unverified": []}

    results = {"matched": [], "failed": [], "unverified": []}

    def process_match(filepath_display, file_hashes):
        logging.info(f"CRC32: {file_hashes['crc32']}")
        logging.info(f"MD5:   {file_hashes['md5']}")
        logging.info(f"SHA-1: {file_hashes['sha1']}")
        logging.info("-" * 40)
        
        if dat_root is not None:
            match = check_redump_dat(dat_root, file_hashes)
            if match:
                logging.info("[✓] VERIFIED: Perfect match found in Redump database!")
                logging.info(f"Game: {match['game_name']}")
                logging.info(f"ROM:  {match['rom_name']}")
                results["matched"].append({"file": filepath_display, "sha1": file_hashes['sha1']})
            else:
                logging.info("[x] FAILED: No match found in the provided DAT file. This might be a bad dump.")
                results["failed"].append({"file": filepath_display, "sha1": file_hashes['sha1'], "reason": "NO_MATCH"})
        else:
            results["unverified"].append(filepath_display)

    total_files = len(files_to_verify)
    for i, filepath in enumerate(files_to_verify):
        cb = globals().get('TOTAL_PROGRESS_CALLBACK')
        if cb:
            cb(i, total_files)

        if globals().get('STOP_REQUESTED', False):
            logging.warning("\n[!] Verification aborted by user.")
            break

        is_zip = filepath.lower().endswith('.zip')
        is_7z = filepath.lower().endswith('.7z')
        if archived_rom and (is_zip or is_7z):
            if is_7z:
                if not HAS_PY7ZR:
                    logging.error(f"[x] FAILED: py7zr module is required for .7z files. Install with 'pip install py7zr'")
                    results["failed"].append({"file": filepath, "sha1": "", "reason": "MISSING_PY7ZR"})
                    continue
                try:
                    with py7zr.SevenZipFile(filepath, 'r') as zf:
                        all_files = zf.list()
                        targets = [
                            zinfo.filename for zinfo in all_files
                            if not zinfo.is_directory and zinfo.filename.lower().endswith(('.iso', '.bin'))
                        ]
                        file_sizes = {
                            zinfo.filename: zinfo.uncompressed for zinfo in all_files
                            if zinfo.filename in targets
                        }

                        if not targets:
                            continue

                        logging.info(f"\n--- Verifying inside 7Z: {filepath} ---")
                        factory = HashWriterFactory(file_sizes)
                        zf.extractall(factory=factory)
                        for target in targets:
                            if target not in factory.io_objects:
                                continue
                            logging.info(f"\nResults for 7Z target: {target}")
                            hashes = factory.io_objects[target].get_hashes()
                            process_match(f"{filepath}/{target}", hashes)

                except py7zr.exceptions.Bad7zFile:
                    logging.error(f"[x] FAILED: Invalid 7z file -> {filepath}")
                    results["failed"].append({"file": filepath, "sha1": "", "reason": "INVALID_7Z"})
            elif is_zip:
                try:
                    with zipfile.ZipFile(filepath, 'r') as zf:
                        for zinfo in zf.infolist():
                            if zinfo.is_dir() or not zinfo.filename.lower().endswith(('.iso', '.bin')):
                                continue
                            logging.info(f"\n--- Verifying inside ZIP: {filepath} -> {zinfo.filename} ---")
                            with zf.open(zinfo) as f:
                                hashes = calculate_hashes_from_stream(f, zinfo.file_size, zinfo.filename)
                            process_match(f"{filepath}/{zinfo.filename}", hashes)
                except zipfile.BadZipFile:
                    logging.error(f"[x] FAILED: Invalid ZIP file -> {filepath}")
                    results["failed"].append({"file": filepath, "sha1": "", "reason": "INVALID_ZIP"})
        else:
            logging.info(f"\n--- Verifying: {filepath} ---")
            hashes = calculate_hashes(filepath)
            process_match(filepath, hashes)

    cb = globals().get('TOTAL_PROGRESS_CALLBACK')
    if cb and not globals().get('STOP_REQUESTED', False):
        cb(total_files, total_files)

    logging.info("\n" + "=" * 40)
    logging.info("VERIFICATION OVERVIEW")
    logging.info("=" * 40)
    logging.info(f"Total files processed: {len(files_to_verify)}")
    if dat_root is not None:
        logging.info(f"Successfully verified: {len(results['matched'])}")
        logging.info(f"Failed verification:   {len(results['failed'])}")
        if results['failed']:
            logging.info("\nFailed Files:")
            for f in results['failed']:
                logging.info(f"  - {f['file']}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ROMs/ISOs.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-file", help="Path to a log file to save the output", required=False)
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single file (.iso/.bin/.zip/.7z) to verify")
    group.add_argument("--directory", help="Path to a directory containing files to verify")
    
    subparsers = parser.add_subparsers(dest='command', required=True, help="Verification commands")
    
    redump_parser = subparsers.add_parser('redump', help="Verify a ROM/ISO against a Redump DAT file")
    redump_parser.add_argument("--dat", help="Path to the Redump .dat (XML) file", required=False)
    redump_parser.add_argument("--result", help="Path to output a JSON file containing verified and failed filenames with their SHA-1 hashes", required=False)
    redump_parser.add_argument("--archived-rom", action="store_true", help="Treat files as ZIP/7z archives and verify their contents", required=False)
    
    integrity_parser = subparsers.add_parser('integrity-check', help="Check integrity of ZIP and 7Z archives")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()

    if args.command not in ['redump', 'integrity-check']:
        sys.exit(0)
    
    log_handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
        log_dir = os.path.dirname(os.path.abspath(args.log_file))
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error: Could not create log directory '{log_dir}': {e}", file=sys.stderr)
                sys.exit(1)
        log_handlers.append(logging.FileHandler(args.log_file, encoding='utf-8'))
        
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(message)s',
        handlers=log_handlers
    )

    files_to_verify = []
    if args.file:
        if not os.path.isfile(args.file):
            logging.error(f"Error: File not found -> {args.file}")
            sys.exit(1)
        files_to_verify.append(args.file)
    elif args.directory:
        if not os.path.isdir(args.directory):
            logging.error(f"Error: Directory not found -> {args.directory}")
            sys.exit(1)
        for root_dir, _, files in os.walk(args.directory):
            for f in files:
                if args.command == 'integrity-check':
                    if f.lower().endswith(('.zip', '.7z')):
                        files_to_verify.append(os.path.join(root_dir, f))
                else:
                    if f.lower().endswith(('.iso', '.zip', '.bin', '.7z')):
                        files_to_verify.append(os.path.join(root_dir, f))
                    
    if not files_to_verify:
        logging.info("No valid files found to verify.")
        sys.exit(0)

    if args.command == 'integrity-check':
        results = run_integrity_check(files_to_verify)
        if results.get('corrupted'):
            sys.exit(1)
        sys.exit(0)

    elif args.command == 'redump':
        dat_root = None
        if args.dat:
            logging.info(f"Loading Redump database: {args.dat}...")
            try:
                tree = ET.parse(args.dat)
                dat_root = tree.getroot()
            except ET.ParseError as e:
                logging.error(f"Error parsing DAT file: {e}")
                sys.exit(1)
        
        results = run_redump_check(files_to_verify, dat_root, args.archived_rom)

    if args.result:
        json_output = {
            "matched": {os.path.basename(item["file"]): item["sha1"] for item in results["matched"]},
            "failed": {
                os.path.basename(item["file"]): {"sha1": item["sha1"], "reason": item["reason"]} for item in results["failed"]
            }
        }
        try:
            with open(args.result, "w", encoding="utf-8") as f:
                json.dump(json_output, f, indent=4)
            logging.info(f"\nSaved verified results to JSON: {args.result}")
        except Exception as e:
            logging.error(f"\nFailed to save results to JSON: {e}")
