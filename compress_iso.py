#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import time
import json

try:
    import py7zr
except ImportError:
    print("Error: 'py7zr' module not found. Please activate your venv (e.g. source ~/Developments/venv/bin/activate) or 'pip install py7zr'.", file=sys.stderr)
    sys.exit(1)

__version__ = "0.1.0"

def compress_file(input_path: str, output_path: str, compression_level: int):
    """Compresses a single .iso file to .7z using py7zr."""
    logging.info(f"Compressing {input_path} to {output_path} (level {compression_level})...")
    
    try:
        start_time = time.time()
        
        # Determine preset based on compression level (0-9)
        filters = [{'id': py7zr.FILTER_LZMA2, 'preset': compression_level}]
        
        with py7zr.SevenZipFile(output_path, 'w', filters=filters) as archive:
            archive.write(input_path, arcname=os.path.basename(input_path))
            
        end_time = time.time()
        duration = end_time - start_time
        
        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        time_str = f"{int(h)}h {int(m)}m {int(s)}s" if h > 0 else f"{int(m)}m {int(s)}s"
        logging.info(f"\n[✓] Successfully compressed: {os.path.basename(output_path)} in {time_str}")
        return True, duration
            
    except Exception as e:
        logging.error(f"\n[x] An error occurred: {e}")
        # Clean up output file if it was partially written
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return False, 0

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

    parser.add_argument("--level", type=int, choices=range(0, 10), default=5, help="Compression level from 0 (store) to 9 (ultra). Default is 5.")
    parser.add_argument("--delete", action="store_true", help="Delete the original .iso file after successful compression.")
    parser.add_argument("--result", help="Path to output a JSON file containing compression statistics", required=False)
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
            
        original_size = os.path.getsize(filepath)
        success, duration = compress_file(filepath, output_path, args.level)
        
        if success:
            compressed_size = os.path.getsize(output_path)
            bytes_saved = original_size - compressed_size
            compression_ratio = compressed_size / original_size if original_size > 0 else 0
            
            logging.info(f"    Original Size:   {original_size / (1024*1024):.2f} MB")
            logging.info(f"    Compressed Size: {compressed_size / (1024*1024):.2f} MB")
            logging.info(f"    Space Saved:     {bytes_saved / (1024*1024):.2f} MB ({(1 - compression_ratio) * 100:.1f}%)")
            
            results["success"].append({
                "file": filepath,
                "output": output_path,
                "compression_time_seconds": round(duration, 2),
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "bytes_saved": bytes_saved,
                "compression_ratio": round(compression_ratio, 4)
            })
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

    if args.result:
        total_original_size = sum(item["original_size_bytes"] for item in results["success"])
        total_compressed_size = sum(item["compressed_size_bytes"] for item in results["success"])
        total_bytes_saved = sum(item["bytes_saved"] for item in results["success"])
        total_compression_time = sum(item["compression_time_seconds"] for item in results["success"])
        
        num_success = len(results["success"])
        avg_original_size = total_original_size / num_success if num_success else 0
        avg_compressed_size = total_compressed_size / num_success if num_success else 0
        avg_bytes_saved = total_bytes_saved / num_success if num_success else 0
        avg_compression_time = total_compression_time / num_success if num_success else 0
        avg_compression_ratio = total_compressed_size / total_original_size if total_original_size > 0 else 0
        
        json_output = {
            "overview": {
                "total_files_processed": len(files_to_compress),
                "successful": num_success,
                "failed": len(results["failed"]),
                "total_original_size_bytes": total_original_size,
                "total_compressed_size_bytes": total_compressed_size,
                "total_bytes_saved": total_bytes_saved,
                "overall_compression_ratio": round(avg_compression_ratio, 4),
                "total_compression_time_seconds": round(total_compression_time, 2),
                "average_metrics_per_file": {
                    "original_size_bytes": round(avg_original_size, 2),
                    "compressed_size_bytes": round(avg_compressed_size, 2),
                    "bytes_saved": round(avg_bytes_saved, 2),
                    "compression_time_seconds": round(avg_compression_time, 2)
                }
            },
            "files": results["success"],
            "failed_files": results["failed"]
        }
        try:
            with open(args.result, "w", encoding="utf-8") as f:
                json.dump(json_output, f, indent=4)
            logging.info(f"\nSaved JSON results to: {args.result}")
        except Exception as e:
            logging.error(f"\nFailed to save JSON results: {e}")
