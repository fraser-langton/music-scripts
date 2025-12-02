#!/usr/bin/env python3
"""
Simple script to convert all Serato crates to Rekordbox using DJ Data Converter.
"""

import subprocess
from pathlib import Path
import shutil


def main():
    # Paths
    serato_dir = Path.home() / "Music" / "_Serato_"
    crates_dir = serato_dir / "Subcrates"
    rekordbox_dir = Path.home() / "Music" / "rekordbox"
    
    # Find DJ Data Converter
    dj_data_converter = shutil.which("dj-data-converter")
    if not dj_data_converter:
        # Try local path
        local_path = Path.home() / "Music" / "dj-data-converter"
        if local_path.exists():
            dj_data_converter = str(local_path)
        else:
            print("Error: DJ Data Converter not found in PATH or local directory")
            return
    
    # Check if crates directory exists
    if not crates_dir.exists():
        print(f"Error: Serato crates directory not found: {crates_dir}")
        return
    
    # Get all crate files
    crate_files = list(crates_dir.glob("*.crate"))
    if not crate_files:
        print("No Serato crates found")
        return
    
    print(f"Found {len(crate_files)} crates to convert")
    
    # Convert each crate
    successful = 0
    for crate_file in crate_files:
        crate_name = crate_file.stem
        print(f"Converting: {crate_name}")
        
        try:
            cmd = [dj_data_converter, str(crate_file)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✓ {crate_name}")
                successful += 1
            else:
                print(f"✗ {crate_name}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"✗ {crate_name}: Timeout")
        except Exception as e:
            print(f"✗ {crate_name}: {e}")
    
    print(f"\nConversion complete: {successful}/{len(crate_files)} successful")


if __name__ == "__main__":
    main()
