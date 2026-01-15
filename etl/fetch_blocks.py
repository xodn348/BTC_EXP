"""
Script to collect block data from blockchain.info API
"""
import argparse
import pathlib
import pandas as pd
import requests
import time
from datetime import datetime
from tqdm import tqdm

RAW_BLOCKS_DIR = pathlib.Path("data/raw/blocks")
RAW_BLOCKS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_block(block_height, retries=3, delay=1):
    """Fetch a single block."""
    url = f"https://blockchain.info/block-height/{block_height}?format=json"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'blocks' in data and len(data['blocks']) > 0:
                block = data['blocks'][0]
                return {
                    'height': block['height'],
                    'block_timestamp': datetime.fromtimestamp(block['time']).strftime('%Y-%m-%d %H:%M:%S'),
                    'total_fees_sat': block.get('fee', 0),
                    'total_vbytes': block.get('size', 0) // 4,  # vbytes approximation
                    'avg_sat_per_vb': block.get('fee', 0) / (block.get('size', 1) // 4) if block.get('size', 0) > 0 else 0,
                    'tx_count': block.get('n_tx', 0),
                    'size': block.get('size', 0),
                    'weight': block.get('weight', 0),
                    'timestamp': block['time']
                }
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise e
    
    return None


def fetch_blocks_range(start_height, end_height, output_file=None, resume_from=None, log_file=None):
    """Collect a range of blocks."""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_BLOCKS_DIR / f"blocks_blockchain_com_{start_height}_{end_height}_{timestamp}.csv"
    else:
        output_file = pathlib.Path(output_file)
    
    # Resume from existing file if present
    existing_heights = set()
    missing_blocks = []
    if output_file.exists() and resume_from is None:
        try:
            df_existing = pd.read_csv(output_file)
            existing_heights = set(df_existing['height'].values)
            print(f"Found {len(existing_heights)} blocks in existing file.")
            
            # Find missing blocks (from 790000 to max)
            if existing_heights:
                min_height = min(existing_heights)
                max_height = max(existing_heights)
                missing_blocks = [h for h in range(min_height, max_height + 1) if h not in existing_heights]
                if missing_blocks:
                    print(f"Found {len(missing_blocks)} missing blocks: {missing_blocks[:10]}{'...' if len(missing_blocks) > 10 else ''}")
            
            start_height = max(existing_heights) + 1
        except:
            pass
    
    if resume_from:
        # Still need to find missing blocks even with resume_from
        if output_file.exists():
            try:
                df_existing = pd.read_csv(output_file)
                existing_heights = set(df_existing['height'].values)
                min_height = min(existing_heights) if existing_heights else 790000
                max_height = max(existing_heights) if existing_heights else resume_from
                missing_blocks = [h for h in range(min_height, max_height + 1) if h not in existing_heights]
                if missing_blocks:
                    print(f"Found {len(missing_blocks)} missing blocks: {missing_blocks[:10]}{'...' if len(missing_blocks) > 10 else ''}")
            except:
                missing_blocks = []
        start_height = resume_from
    
    blocks_data = []
    failed_blocks = []
    total_blocks = end_height - start_height + 1
    
    # Calculate full range (progress based on 790000-890000)
    full_start = 790000
    full_end = 890000
    full_total = full_end - full_start + 1  # 100001
    
    start_msg = f"Starting collection from block {start_height} to {end_height}...\n"
    print(start_msg, end='')
    
    log_fp = None
    if log_file:
        log_fp = open(log_file, 'a')
        log_fp.write(start_msg)
        log_fp.flush()
    
    try:
        # Progress based on full range
        initial_progress = start_height - full_start  # Already collected blocks
        with tqdm(total=full_total, initial=initial_progress, desc="Fetching blocks") as pbar:
            # First collect missing blocks
            if missing_blocks:
                print(f"Collecting {len(missing_blocks)} missing blocks first...")
                for height in missing_blocks:
                    try:
                        block_data = fetch_block(height)
                        if block_data:
                            blocks_data.append(block_data)
                            pbar.update(1)
                            
                            # Save every 10 blocks
                            if len(blocks_data) >= 10:
                                df_new = pd.DataFrame(blocks_data)
                                if output_file.exists():
                                    df_existing = pd.read_csv(output_file)
                                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                                else:
                                    df_combined = df_new
                                df_combined.to_csv(output_file, index=False)
                                
                                if log_fp:
                                    log_fp.write(f"Progress: {len(df_combined)} blocks collected, {len(failed_blocks)} failed (saved to {output_file})\n")
                                    log_fp.flush()
                                
                                blocks_data = []
                        else:
                            failed_blocks.append(height)
                            pbar.update(1)
                    except Exception as e:
                        failed_blocks.append(height)
                        error_msg = f"Error fetching block {height}: {e}\n"
                        if log_fp:
                            log_fp.write(error_msg)
                            log_fp.flush()
                        pbar.update(1)
                        time.sleep(2)
            
            # Collect normal range
            for height in range(start_height, end_height + 1):
                try:
                    block_data = fetch_block(height)
                    if block_data:
                        blocks_data.append(block_data)
                        pbar.update(1)
                        
                        # Save every 10 blocks (save frequently)
                        if len(blocks_data) >= 10:
                            df_new = pd.DataFrame(blocks_data)
                            if output_file.exists():
                                df_existing = pd.read_csv(output_file)
                                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                            else:
                                df_combined = df_new
                            df_combined.to_csv(output_file, index=False)
                            
                            if log_fp:
                                log_fp.write(f"Progress: {len(df_combined)} blocks collected, {len(failed_blocks)} failed (saved to {output_file})\n")
                                log_fp.flush()
                            
                            blocks_data = []
                    else:
                        failed_blocks.append(height)
                        pbar.update(1)
                        
                except Exception as e:
                    failed_blocks.append(height)
                    error_msg = f"Error fetching block {height}: {e}\n"
                    if log_fp:
                        log_fp.write(error_msg)
                        log_fp.flush()
                    pbar.update(1)
                    time.sleep(2)  # Wait briefly after error
        
        # Save remaining data
        if blocks_data:
            df_new = pd.DataFrame(blocks_data)
            if output_file.exists():
                df_existing = pd.read_csv(output_file)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new
            df_combined.to_csv(output_file, index=False)
        
        print(f"\nComplete! Total {len(df_combined)} blocks collected")
        if failed_blocks:
            print(f"Failed blocks: {len(failed_blocks)}")
        
    finally:
        if log_fp:
            log_fp.close()
    
    return output_file


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


def main():
    parser = argparse.ArgumentParser(description="Block data collection")
    parser.add_argument("--start", type=int, default=790000, help="Start block height")
    parser.add_argument("--end", type=int, default=890000, help="End block height")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    parser.add_argument("--resume-from", type=int, default=None, help="Resume from this block")
    parser.add_argument("--log", type=str, default="block_collection.log", help="Log file path")
    parser.add_argument("--auto-resume", action="store_true", help="Enable auto-resume (auto-restart on process termination)")
    parser.add_argument("--max-retries", type=int, default=None, help="Maximum retry count (with --auto-resume, default: infinite)")
    
    args = parser.parse_args()
    
    # Auto-resume mode
    if args.auto_resume:
        retry_count = 0
        while True:
            # Automatically determine resume position
            current_resume = args.resume_from
            if current_resume is None and args.output:
                last_height = get_last_height_from_csv(args.output)
                if last_height is not None and last_height >= args.start:
                    current_resume = last_height + 1
                    print(f"\n{'='*60}")
                    print(f"Auto-resume: Starting after last block {last_height}")
                    print(f"Resume position: {current_resume}")
                    print(f"{'='*60}\n")
            
            # Check if target reached
            if current_resume and current_resume > args.end:
                print(f"\nComplete! All blocks up to {args.end} have been collected.")
                break
            
            try:
                fetch_blocks_range(
                    args.start, 
                    args.end, 
                    output_file=args.output,
                    resume_from=current_resume,
                    log_file=args.log
                )
                # Normal completion
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Block collection complete!")
                break
            except KeyboardInterrupt:
                print("\n\nInterrupted by user.")
                raise
            except Exception as e:
                retry_count += 1
                if args.max_retries is not None and retry_count >= args.max_retries:
                    print(f"\nMaximum retry count ({args.max_retries}) reached. Terminating.")
                    raise
                
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error occurred: {e}")
                print(f"Retry {retry_count}... Auto-restart in 10 seconds.\n")
                time.sleep(10)
    else:
        # Original behavior (no auto-resume)
        fetch_blocks_range(
            args.start, 
            args.end, 
            output_file=args.output,
            resume_from=args.resume_from,
            log_file=args.log
        )


if __name__ == "__main__":
    main()
