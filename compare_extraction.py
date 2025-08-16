#!/usr/bin/env python3
"""
Quick comparison script to show filename vs ID3 tag extraction statistics
"""

import sys
import subprocess

def main():
    print("🔍 Running song info extractor to compare filename parsing with ID3 tags...")
    print("=" * 80)
    
    try:
        # Run the extractor and capture output
        result = subprocess.run(['python3', 'song_info_extractor.py'], 
                              capture_output=True, text=True, timeout=300)
        
        # Extract just the statistics section
        output = result.stdout
        stats_start = output.find("📊 EXTRACTION STATISTICS")
        
        if stats_start != -1:
            stats_section = output[stats_start:]
            print(stats_section)
        else:
            print("❌ Could not find statistics section in output")
            print("Full output:")
            print(output)
            
    except subprocess.TimeoutExpired:
        print("⏰ Analysis timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running extractor: {e}")

if __name__ == "__main__":
    main() 