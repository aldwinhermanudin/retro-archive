#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import xml.etree.ElementTree as ET

try:
    from retroarchive import verify
except ImportError:
    print("Error: Could not import retroarchive. Please ensure you are in the correct directory.", file=sys.stderr)
    sys.exit(1)

__version__ = "0.1.0"

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
        results = verify.run_integrity_check(files_to_verify)
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
        
        results = verify.run_redump_check(files_to_verify, dat_root, args.archived_rom)

    if args.result:
        verify.save_json_report(results, args.result)
