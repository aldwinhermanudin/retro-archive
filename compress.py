#!/usr/bin/env python3
import os
import sys
import argparse
import logging

try:
    from retroarchive import compress
except ImportError:
    print("Error: Could not import retroarchive. Please ensure you are in the correct directory.", file=sys.stderr)
    sys.exit(1)

__version__ = "0.1.0"

if __name__ == "__main__":
    desc = "Compress files to .7z using py7zr."
    epilog = """
Examples:
  Compress a single file:
    %(prog)s --file /path/to/game.iso

  Compress a directory of files and delete the originals to save space:
    %(prog)s --directory /path/to/isos --delete --file-type .iso .bin

  Specify maximum compression and a custom output directory:
    %(prog)s --directory /path/to/isos --level 9 --output-dir /path/to/output
"""
    parser = argparse.ArgumentParser(
        description=desc,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single file to compress")
    group.add_argument("--directory", help="Path to a directory containing files to compress")

    parser.add_argument("--output-dir", help="Path to the output directory for .7z files (defaults to same as input)", required=False)
    parser.add_argument("--file-type", nargs="+", default=None, help="File extensions to compress when scanning a directory (e.g. .iso .bin). Default is all files.")
    parser.add_argument("--level", type=int, choices=range(0, 10), default=5, help="Compression level from 0 (store) to 9 (ultra). Default is 5.")
    parser.add_argument("--delete", action="store_true", help="Delete the original file after successful compression.")
    parser.add_argument("--result", help="Path to output a JSON file containing compression statistics", required=False)
    parser.add_argument("--log-file", help="Path to a log file to save the output", required=False)
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")

    args = parser.parse_args()

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

    files_to_compress = []

    if args.file:
        if not os.path.isfile(args.file):
            logging.error(f"Error: File not found -> {args.file}")
            sys.exit(1)
        files_to_compress.append(args.file)

    elif args.directory:
        if not os.path.isdir(args.directory):
            logging.error(f"Error: Directory not found -> {args.directory}")
            sys.exit(1)
        if args.file_type:
            valid_exts = tuple(ext.lower() if ext.startswith('.') else f".{ext.lower()}" for ext in args.file_type)
        else:
            valid_exts = None

        for root_dir, _, files in os.walk(args.directory):
            for f in files:
                if f.lower().endswith('.7z'):
                    continue
                if valid_exts is None or f.lower().endswith(valid_exts):
                    files_to_compress.append(os.path.join(root_dir, f))

    results = compress.run_batch_compression(files_to_compress, args.output_dir, args.level, args.delete)

    if args.result:
        compress.save_json_report(results, len(files_to_compress), args.result)
