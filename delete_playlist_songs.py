#!/usr/bin/env python3
"""
Script to delete all songs from a specific SoundCloud playlist.
Usage: python delete_playlist_songs.py <playlist_name>
"""

import json
import os
import sys
import glob
from pathlib import Path

# Configuration
SC_BASE_DIR = "/Users/fraser.langton/Music/soundcloud"
SC_CACHE_DIR = f"{SC_BASE_DIR}/CACHE"
SC_PLAYLIST_DIR = f"{SC_BASE_DIR}/playlists"
SC_ARCHIVE_FILE = f"{SC_CACHE_DIR}/downloaded.txt"

def delete_playlist_songs(playlist_name):
    """Delete all songs from a specific playlist."""
    
    # Normalize playlist name (convert spaces to hyphens, lowercase)
    playlist_name_normalized = playlist_name.lower().replace(' ', '-')
    playlist_file = f"{SC_PLAYLIST_DIR}/{playlist_name_normalized}.json"
    
    print(f"🎵 Deleting all songs from playlist: {playlist_name}")
    print(f"📁 Playlist file: {playlist_file}")
    print("=" * 60)
    
    # Check if playlist file exists
    if not os.path.exists(playlist_file):
        print(f"❌ Playlist file not found: {playlist_file}")
        print("\nAvailable playlists:")
        for json_file in glob.glob(f"{SC_PLAYLIST_DIR}/*.json"):
            name = os.path.basename(json_file).replace('.json', '')
            print(f"  - {name}")
        return False
    
    # Read playlist JSON
    try:
        with open(playlist_file, 'r') as f:
            playlist_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")
        return False
    
    # Extract track IDs
    track_ids = []
    if 'entries' in playlist_data:
        for entry in playlist_data['entries']:
            if 'id' in entry:
                track_ids.append(str(entry['id']))
    
    if not track_ids:
        print("❌ No track IDs found in playlist")
        return False
    
    print(f"📊 Found {len(track_ids)} tracks in playlist")
    print()
    
    # Delete MP3 files and update archive
    deleted_files = 0
    removed_from_archive = 0
    
    for track_id in track_ids:
        # Find MP3 files for this track ID using shell command with proper escaping
        import subprocess
        try:
            # Use shell=True to handle the square brackets properly
            cmd = f"find '{SC_CACHE_DIR}' -name '\\[id={track_id}\\]*.mp3'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            matching_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            

        except Exception as e:
            print(f"DEBUG: Error for track {track_id}: {e}")
            matching_files = []
        
        if matching_files:
            for mp3_file in matching_files:
                try:
                    os.remove(mp3_file)
                    print(f"🗑️  Deleted: {os.path.basename(mp3_file)}")
                    deleted_files += 1
                except Exception as e:
                    print(f"❌ Error deleting {mp3_file}: {e}")
        else:
            print(f"⚠️  No MP3 files found for track ID: {track_id}")
    
    # Remove entries from downloaded.txt archive
    if os.path.exists(SC_ARCHIVE_FILE):
        try:
            with open(SC_ARCHIVE_FILE, 'r') as f:
                lines = f.readlines()
            
            original_count = len(lines)
            
            # Filter out lines containing the track IDs
            filtered_lines = []
            for line in lines:
                should_keep = True
                for track_id in track_ids:
                    if f" {track_id}" in line:
                        should_keep = False
                        removed_from_archive += 1
                        break
                if should_keep:
                    filtered_lines.append(line)
            
            # Write back the filtered content
            with open(SC_ARCHIVE_FILE, 'w') as f:
                f.writelines(filtered_lines)
            
            print(f"📝 Removed {removed_from_archive} entries from archive file")
            
        except Exception as e:
            print(f"❌ Error updating archive file: {e}")
    else:
        print("⚠️  Archive file not found")
    
    # Summary
    print()
    print("🎯 Deletion Complete!")
    print("====================")
    print(f"🗑️  Deleted MP3 files: {deleted_files}")
    print(f"📝 Removed from archive: {removed_from_archive}")
    print(f"📊 Total tracks processed: {len(track_ids)}")
    
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python delete_playlist_songs.py <playlist_name>")
        print("\nExamples:")
        print("  python delete_playlist_songs.py 'songs-that-get-white-people'")
        print("  python delete_playlist_songs.py '5am'")
        print("  python delete_playlist_songs.py 'boogie'")
        return
    
    playlist_name = sys.argv[1]
    delete_playlist_songs(playlist_name)

if __name__ == "__main__":
    main() 