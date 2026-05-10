#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import subprocess
import time

__version__ = "0.1.0"

def compress_file(input_path: str, output_path: str, sevenzip_path: str, compression_level: int):
    """Compresses a single .iso file to .7z using 7zip."""
    # -t7z: format 7z
    # -mx=<level>: compression level (0-9)
    # -bsp1: force progress output to stdout
    cmd = [
        sevenzip_path, 
        "a", 
        "-t7z", 
        f"-mx={compression_level}", 
        "-bsp1", 
        output_path, 
        input_path
    ]
    logging.info(f"Running: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        # Run 7z and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            
        process.wait()
        end_time = time.time()
        
        if process.returncode == 0:
            duration = end_time - start_time
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            time_str = f"{int(h)}h {int(m)}m {int(s)}s" if h > 0 else f"{int(m)}m {int(s)}s"
            logging.info(f"\n[✓] Successfully compressed: {os.path.basename(output_path)} in {time_str}")
            return True
        else:
            logging.error(f"\n[x] Failed to compress: {os.path.basename(input_path)} (Return code: {process.returncode})")
            return False
            
    except FileNotFoundError:
        logging.error(f"\n[x] Error: '7z' executable not found at '{sevenzip_path}'. Please install it (e.g., 'sudo apt install p7zip-full') or provide the path.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"\n[x] An error occurred: {e}")
        return False

if __name__ == "__main__":
    desc = "Compress .iso files to .7z using 7zip."
    epilog = """
Examples:
  Compress a single ISO file:
    %(prog)s --file /path/to/game.iso

  Compress a directory of ISO files and delete the originals to save space:
    %(prog)s --directory /path/to/isos --delete

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
    group.add_argument("--file", help="Path to a single .iso file to compress")
    group.add_argument("--directory", help="Path to a directory containing .iso files to compress")
    
    parser.add_argument("--output-dir", help="Path to the output directory for .7z files (defaults to same as input)", required=False)
    parser.add_argument("--7zip", dest="sevenzip", help="Path to the 7z executable (default: 7z)", default="7z")
    parser.add_argument("--level", type=int, choices=range(0, 10), default=5, help="Compression level from 0 (store) to 9 (ultra). Default is 5.")
    parser.add_argument("--delete", action="store_true", help="Delete the original .iso file after successful compression.")
    parser.add_argument("--log-file", help="Path to a log file to save the output", required=False)
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    
    args = parser.parse_args()
    
    log_handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
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
        for root_dir, _, files in os.walk(args.directory):
            for f in files:
                if f.lower().endswith('.iso'):
                    files_to_compress.append(os.path.join(root_dir, f))
                    
    if not files_to_compress:
        logging.info("No valid .iso files found to compress.")
        sys.exit(0)
        
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    results = {"success": [], "failed": []}
    
    logging.info(f"Found {len(files_to_compress)} files to compress.")
    
    total_start_time = time.time()
    
    for filepath in files_to_compress:
        logging.info(f"\n--- Compressing: {filepath} ---")
        
        filename = os.path.basename(filepath)
        name, _ = os.path.splitext(filename)
        output_filename = f"{name}.7z"
        
        if args.output_dir:
            output_path = os.path.join(args.output_dir, output_filename)
        else:
            output_path = os.path.join(os.path.dirname(filepath), output_filename)
            
        if os.path.exists(output_path):
            logging.warning(f"Output file already exists, skipping: {output_path}")
            continue
            
        success = compress_file(filepath, output_path, args.sevenzip, args.level)
        if success:
            results["success"].append(filepath)
            if args.delete:
                try:
                    os.remove(filepath)
                    logging.info(f"Deleted original file: {filepath}")
                except Exception as e:
                    logging.error(f"Failed to delete original file {filepath}: {e}")
        else:
            results["failed"].append(filepath)

    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    tm, ts = divmod(total_duration, 60)
    th, tm = divmod(tm, 60)
    total_time_str = f"{int(th)}h {int(tm)}m {int(ts)}s" if th > 0 else f"{int(tm)}m {int(ts)}s"

    logging.info("\n" + "=" * 40)
    logging.info("COMPRESSION OVERVIEW")
    logging.info("=" * 40)
    logging.info(f"Total time taken:        {total_time_str}")
    logging.info(f"Total files processed:   {len(files_to_compress)}")
    logging.info(f"Successfully compressed: {len(results['success'])}")
    logging.info(f"Failed compression:      {len(results['failed'])}")
    
    if results['failed']:
        logging.info("\nFailed Files:")
        for f in results['failed']:
            logging.info(f"  - {f}")
