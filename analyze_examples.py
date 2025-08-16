#!/usr/bin/env python3
"""
Analyze specific examples of filename vs ID3 tag differences
"""

import subprocess
import re

def main():
    print("🎵 ANALYZING FILENAME vs ID3 TAG DIFFERENCES")
    print("=" * 60)
    
    # Run extractor and capture output
    result = subprocess.run(['python3', 'song_info_extractor.py'], 
                          capture_output=True, text=True, timeout=300)
    
    output = result.stdout
    
    # Find examples of different patterns
    examples = []
    
    # Look for files with mismatches
    lines = output.split('\n')
    current_file = None
    filename_artist = None
    filename_title = None
    id3_artist = None
    id3_title = None
    
    for line in lines:
        if line.startswith('📁 '):
            current_file = line[3:]
        elif 'Artist (filename):' in line:
            filename_artist = line.split('Artist (filename): ')[1]
        elif 'Title (filename):' in line:
            filename_title = line.split('Title (filename): ')[1]
        elif 'Artist (ID3):' in line:
            id3_artist = line.split('Artist (ID3): ')[1]
        elif 'Title (ID3):' in line:
            id3_title = line.split('Title (ID3): ')[1]
        elif '✅ Artist match: No' in line or '✅ Title match: No' in line:
            if current_file and (filename_artist or filename_title):
                examples.append({
                    'file': current_file,
                    'filename_artist': filename_artist,
                    'filename_title': filename_title,
                    'id3_artist': id3_artist,
                    'id3_title': id3_title
                })
                # Reset for next file
                current_file = None
                filename_artist = None
                filename_title = None
                id3_artist = None
                id3_title = None
    
    # Show interesting examples
    print(f"\n📋 Found {len(examples)} files with mismatches")
    print("\n🔍 INTERESTING EXAMPLES:")
    print("-" * 60)
    
    for i, example in enumerate(examples[:10]):  # Show first 10
        print(f"\n{i+1}. {example['file']}")
        if example['filename_artist']:
            print(f"   Filename Artist: {example['filename_artist']}")
        if example['id3_artist']:
            print(f"   ID3 Artist:      {example['id3_artist']}")
        if example['filename_title']:
            print(f"   Filename Title:  {example['filename_title']}")
        if example['id3_title']:
            print(f"   ID3 Title:       {example['id3_title']}")
    
    # Analyze patterns
    print(f"\n📊 PATTERN ANALYSIS:")
    print("-" * 60)
    
    # Count different types of mismatches
    artist_only_mismatch = 0
    title_only_mismatch = 0
    both_mismatch = 0
    
    for example in examples:
        has_artist_mismatch = (example['filename_artist'] and example['id3_artist'] and 
                              example['filename_artist'] != example['id3_artist'])
        has_title_mismatch = (example['filename_title'] and example['id3_title'] and 
                             example['filename_title'] != example['id3_title'])
        
        if has_artist_mismatch and has_title_mismatch:
            both_mismatch += 1
        elif has_artist_mismatch:
            artist_only_mismatch += 1
        elif has_title_mismatch:
            title_only_mismatch += 1
    
    print(f"Artist-only mismatches: {artist_only_mismatch}")
    print(f"Title-only mismatches:  {title_only_mismatch}")
    print(f"Both mismatches:        {both_mismatch}")
    
    # Show common patterns
    print(f"\n🎯 COMMON PATTERNS:")
    print("-" * 60)
    
    # Look for remix patterns
    remix_examples = [e for e in examples if 'remix' in e['id3_title'].lower() or 'remix' in e['filename_title'].lower()]
    print(f"Remix-related mismatches: {len(remix_examples)}")
    
    # Look for featuring patterns
    feat_examples = [e for e in examples if (e['filename_artist'] and 'feat' in e['filename_artist'].lower()) or 
                    (e['id3_artist'] and 'feat' in e['id3_artist'].lower())]
    print(f"Featuring-related mismatches: {len(feat_examples)}")
    
    # Look for SoundCloud account vs actual artist
    sc_account_examples = [e for e in examples if e['id3_artist'] and 'soundcloud' in e['id3_artist'].lower()]
    print(f"SoundCloud account as artist: {len(sc_account_examples)}")

if __name__ == "__main__":
    main() 