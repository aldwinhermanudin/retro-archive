#!/usr/bin/env python3
import os
import sys
import inquirer
import logging
import time

from retroarchive import compress
from retroarchive import verify

__version__ = "0.1.0"

def setup_logging():
    log_handlers = [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=log_handlers
    )

def compress_interactive():
    print("\n--- Batch Compression ---")
    
    questions = [
        inquirer.Text('input_path', message="Enter the file or directory to compress"),
        inquirer.Text('output_dir', message="Enter output directory (leave blank for same directory)"),
        inquirer.List('level',
                      message="Select compression level",
                      choices=['0 (Store)', '1', '3', '5 (Normal)', '7', '9 (Ultra)'],
                      default='5 (Normal)'),
        inquirer.Confirm('delete_orig', message="Delete original files after successful compression?", default=False),
        inquirer.Text('report_dir', message="Enter directory to save JSON report (leave blank to skip)"),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return
        
    input_path = answers['input_path'].strip()
    if not input_path or not os.path.exists(input_path):
        print(f"Error: Path not found -> {input_path}")
        return
        
    output_dir = answers['output_dir'].strip() or None
    level_str = answers['level'].split()[0]
    level = int(level_str)
    delete_orig = answers['delete_orig']
    report_dir = answers['report_dir'].strip() or None

    files_to_compress = []
    if os.path.isfile(input_path):
        files_to_compress.append(input_path)
    elif os.path.isdir(input_path):
        for root_dir, _, files in os.walk(input_path):
            for f in files:
                if not f.lower().endswith('.7z'):
                    files_to_compress.append(os.path.join(root_dir, f))

    if not files_to_compress:
        print("No files found to compress.")
        return

    results = compress.run_batch_compression(files_to_compress, output_dir, level, delete_orig)
    
    if report_dir:
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(report_dir, f"compress_report_{timestamp}.json")
        compress.save_json_report(results, len(files_to_compress), json_path)


def verify_interactive():
    print("\n--- ROM Verification ---")
    
    questions = [
        inquirer.List('mode',
                      message="Select verification mode",
                      choices=['Redump Verify', 'Integrity Check (ZIP/7Z)']),
        inquirer.Text('input_path', message="Enter the file or directory to verify"),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return
        
    mode = answers['mode']
    input_path = answers['input_path'].strip()
    
    if not input_path or not os.path.exists(input_path):
        print(f"Error: Path not found -> {input_path}")
        return

    dat_root = None
    archived = False

    if mode == 'Redump Verify':
        redump_q = [
            inquirer.Text('dat_file', message="Enter path to Redump DAT (XML) file (leave blank to skip matching)"),
            inquirer.Confirm('archived', message="Verify files inside ZIP/7z archives?", default=False),
        ]
        redump_a = inquirer.prompt(redump_q)
        if not redump_a:
            return
            
        dat_file = redump_a['dat_file'].strip()
        archived = redump_a['archived']
        
        if dat_file:
            if not os.path.isfile(dat_file):
                print(f"Error: DAT file not found -> {dat_file}")
                return
            import xml.etree.ElementTree as ET
            print(f"Loading Redump database: {dat_file}...")
            try:
                tree = ET.parse(dat_file)
                dat_root = tree.getroot()
            except ET.ParseError as e:
                print(f"Error parsing DAT file: {e}")
                return
                
    report_q = [
        inquirer.Text('report_dir', message="Enter directory to save JSON report (leave blank to skip)"),
    ]
    report_a = inquirer.prompt(report_q)
    if not report_a:
        return
    report_dir = report_a['report_dir'].strip() or None

    files_to_verify = []
    if os.path.isfile(input_path):
        files_to_verify.append(input_path)
    elif os.path.isdir(input_path):
        for root_dir, _, files in os.walk(input_path):
            for f in files:
                if mode == 'Integrity Check (ZIP/7Z)':
                    if f.lower().endswith(('.zip', '.7z')):
                        files_to_verify.append(os.path.join(root_dir, f))
                else:
                    if f.lower().endswith(('.iso', '.zip', '.bin', '.7z')):
                        files_to_verify.append(os.path.join(root_dir, f))

    if not files_to_verify:
        print("No valid files found to verify.")
        return

    if mode == 'Integrity Check (ZIP/7Z)':
        results = verify.run_integrity_check(files_to_verify)
    else:
        results = verify.run_redump_check(files_to_verify, dat_root, archived)

    if report_dir:
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(report_dir, f"verify_report_{timestamp}.json")
        verify.save_json_report(results, json_path)


def main():
    setup_logging()
    
    print(f"Retro Archive Interactive CLI v{__version__}")
    print("=" * 40)
    
    while True:
        questions = [
            inquirer.List('action',
                          message="What would you like to do?",
                          choices=['Batch Compression', 'ROM Verification', 'Exit']),
        ]
        
        answer = inquirer.prompt(questions)
        if not answer or answer['action'] == 'Exit':
            print("Exiting...")
            break
            
        action = answer['action']
        
        if action == 'Batch Compression':
            compress_interactive()
        elif action == 'ROM Verification':
            verify_interactive()
            
        print("\n")

if __name__ == "__main__":
    main()
