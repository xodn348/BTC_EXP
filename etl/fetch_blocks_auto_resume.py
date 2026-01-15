"""
Wrapper script for auto-resuming block collection

Automatically restarts when process terminates or errors occur,
and automatically detects current progress to resume.

Usage:
    python etl/fetch_blocks_auto_resume.py --start 790000 --end 890000 --output data/raw/blocks/blocks.csv
"""
import argparse
import pathlib
import pandas as pd
import subprocess
import time
import sys
from datetime import datetime


def get_last_height_from_csv(csv_file):
    """Get last block height from CSV file."""
    if not pathlib.Path(csv_file).exists():
        return None
    
    try:
        df = pd.read_csv(csv_file)
        if len(df) == 0 or 'height' not in df.columns:
            return None
        return int(df['height'].max())
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None


def run_fetch_blocks(start, end, output_file, resume_from=None, log_file="block_collection.log", max_retries=None):
    """
    Run fetch_blocks.py and automatically restart on failure.
    
    Args:
        start: Start block height
        end: End block height
        output_file: Output file path
        resume_from: Manual resume position (None for auto-detect)
        log_file: Log file path
        max_retries: Maximum retry count (None for infinite retries)
    """
    retry_count = 0
    script_path = pathlib.Path(__file__).parent / "fetch_blocks.py"
    
    while True:
        # Automatically determine resume position
        if resume_from is None:
            last_height = get_last_height_from_csv(output_file)
            if last_height is not None and last_height >= start:
                current_resume = last_height + 1
                print(f"\n{'='*60}")
                print(f"Auto-resume: Starting after last block {last_height}")
                print(f"Resume position: {current_resume}")
                print(f"{'='*60}\n")
            else:
                current_resume = start
        else:
            current_resume = resume_from
        
        # Check if target reached
        if current_resume > end:
            print(f"\nComplete! All blocks up to {end} have been collected.")
            break
        
        # Run fetch_blocks.py
        cmd = [
            sys.executable,
            str(script_path),
            "--start", str(start),
            "--end", str(end),
            "--output", output_file,
            "--resume-from", str(current_resume),
            "--log", log_file
        ]
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting block collection: {current_resume} ~ {end}")
        print(f"Command: {' '.join(cmd)}\n")
        
        try:
            # Run process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Real-time output
            for line in process.stdout:
                print(line, end='')
            
            # Wait for process termination
            return_code = process.wait()
            
            if return_code == 0:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Block collection complete!")
                break
            else:
                retry_count += 1
                if max_retries is not None and retry_count >= max_retries:
                    print(f"\nMaximum retry count ({max_retries}) reached. Terminating.")
                    sys.exit(1)
                
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process terminated with error (code: {return_code})")
                print(f"Retry {retry_count}... Auto-restart in 10 seconds.\n")
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            sys.exit(0)
        except Exception as e:
            retry_count += 1
            if max_retries is not None and retry_count >= max_retries:
                print(f"\nMaximum retry count ({max_retries}) reached. Terminating.")
                sys.exit(1)
            
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Exception occurred: {e}")
            print(f"Retry {retry_count}... Auto-restart in 10 seconds.\n")
            time.sleep(10)


def main():
    parser = argparse.ArgumentParser(
        description="Block data collection (with auto-resume)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-resume enabled (default)
  python etl/fetch_blocks_auto_resume.py --start 790000 --end 890000 --output data/raw/blocks/blocks.csv
  
  # Manual resume position
  python etl/fetch_blocks_auto_resume.py --start 790000 --end 890000 --output blocks.csv --resume-from 850000
  
  # Limit maximum retries
  python etl/fetch_blocks_auto_resume.py --start 790000 --end 890000 --output blocks.csv --max-retries 10
        """
    )
    parser.add_argument("--start", type=int, default=790000, help="Start block height")
    parser.add_argument("--end", type=int, default=890000, help="End block height")
    parser.add_argument("--output", type=str, required=True, help="Output file path")
    parser.add_argument("--resume-from", type=int, default=None, help="Manual resume position (None for auto-detect)")
    parser.add_argument("--log", type=str, default="block_collection.log", help="Log file path")
    parser.add_argument("--max-retries", type=int, default=None, help="Maximum retry count (default: infinite)")
    
    args = parser.parse_args()
    
    run_fetch_blocks(
        start=args.start,
        end=args.end,
        output_file=args.output,
        resume_from=args.resume_from,
        log_file=args.log,
        max_retries=args.max_retries
    )


if __name__ == "__main__":
    main()
