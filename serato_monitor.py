#!/usr/bin/env uv run python
import os
import glob
import io
import time
import sys
import tty
import termios
import select
import argparse
import json
from mutagen.id3 import ID3

# Serato Session File Constants
TAG_VRSN = 'vrsn'
TAG_OENT = 'oent'
TAG_ADAT = 'adat'

def get_key_press():
    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        return sys.stdin.read(1)
    return None

def setup_terminal():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())
    except:
        pass
    return fd, old_settings

def restore_terminal(fd, old_settings):
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class SeratoSessionParser:
    def __init__(self, session_path):
        self.session_path = session_path
        self.tracks = []

    def parse(self):
        if not os.path.exists(self.session_path):
            return []
        
        with open(self.session_path, 'rb') as f:
            self._parse_chunk(f)
        
        return self.tracks

    def _read_int(self, stream, length=4):
        data = stream.read(length)
        if len(data) < length:
            raise ValueError("Unexpected EOF")
        return int.from_bytes(data, byteorder='big')

    def _read_string(self, stream, length, encoding='utf-16-be'):
        data = stream.read(length)
        try:
            # Remove null bytes which are common in Serato strings padding
            return data.replace(b'\x00', b'').decode(encoding)
        except UnicodeDecodeError:
            return data.hex()

    def _parse_chunk(self, stream, level=0):
        while True:
            try:
                tag_bytes = stream.read(4)
                if not tag_bytes or len(tag_bytes) < 4:
                    break
                
                # Try to decode tag
                try:
                    tag = tag_bytes.decode('utf-8')
                    if not tag.isprintable():
                         # If not printable, it might be a field ID (integer)
                         tag = int.from_bytes(tag_bytes, byteorder='big')
                except UnicodeDecodeError:
                    tag = int.from_bytes(tag_bytes, byteorder='big')

                length = self._read_int(stream, 4)
                content = stream.read(length)

                if tag == TAG_OENT:
                    # Object Entry - likely a track event
                    self._parse_oent(content)
                elif tag == TAG_ADAT:
                    # Associated Data - container for fields inside OENT
                    # We usually recurse into ADAT if we are inside OENT
                    pass # Handled by _parse_oent recursion
                else:
                    # Just skip other chunks
                    pass

            except ValueError:
                break

    def _parse_oent(self, content):
        # Parse the ADAT chunk inside OENT
        # OENT usually contains one ADAT chunk which contains the fields
        stream = io.BytesIO(content)
        
        # Expect ADAT tag
        tag_bytes = stream.read(4)
        if tag_bytes != b'adat':
            return
        
        length = self._read_int(stream, 4)
        adat_content = stream.read(length)
        
        # Now parse fields from adat_content
        fields = self._parse_fields(adat_content)
        if fields:
            self.tracks.append(fields)

    def _parse_fields(self, content):
        stream = io.BytesIO(content)
        fields = {}
        
        while True:
            tag_bytes = stream.read(4)
            if not tag_bytes or len(tag_bytes) < 4:
                break
            
            field_id = int.from_bytes(tag_bytes, byteorder='big')
            length = self._read_int(stream, 4)
            value_bytes = stream.read(length)
            
            fields[field_id] = value_bytes
            
        return fields

def decode_string(bytes_val):
    if not bytes_val:
        return ""
    
    # Check for Byte Order Mark
    if bytes_val.startswith(b'\xfe\xff'):
        return bytes_val.decode('utf-16-be').strip('\ufeff\x00')
    if bytes_val.startswith(b'\xff\xfe'):
        return bytes_val.decode('utf-16-le').strip('\ufeff\x00')

    # Check for null patterns characteristic of ASCII-in-UTF16
    even_nulls = sum(1 for b in bytes_val[0::2] if b == 0)
    odd_nulls = sum(1 for b in bytes_val[1::2] if b == 0)
    length = len(bytes_val)
    
    # If significant number of even bytes are null, likely Big Endian UTF-16
    if length > 2 and even_nulls / (length/2) > 0.4:
        try:
            return bytes_val.decode('utf-16-be').replace('\x00', '').strip()
        except:
            pass
            
    # If significant number of odd bytes are null, likely Little Endian UTF-16
    if length > 2 and odd_nulls / (length/2) > 0.4:
        try:
            return bytes_val.decode('utf-16-le').replace('\x00', '').strip()
        except:
            pass

    # Fallback to UTF-8 / ASCII
    try:
        # Try removing any stray nulls and decoding
        return bytes_val.replace(b'\x00', b'').decode('utf-8').strip()
    except UnicodeDecodeError:
        pass
        
    # If all else fails, try utf-16-be (e.g. purely CJK text with no nulls)
    try:
        return bytes_val.decode('utf-16-be')
    except:
        pass

    return bytes_val.hex()

def decode_int(bytes_val):
    if not bytes_val:
        return 0
    return int.from_bytes(bytes_val, byteorder='big')

def get_latest_session_file(serato_dir):
    sessions_dir = os.path.join(serato_dir, "History", "Sessions")
    list_of_files = glob.glob(os.path.join(sessions_dir, "*.session"))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getmtime)

def save_pair(track1, track2):
    # Determine which song was playing first (song1) and which is newer (song2)
    if track1['start_time'] < track2['start_time']:
        song1 = track1
        song2 = track2
    else:
        song1 = track2
        song2 = track1

    filename = "good_pairs.json"
    
    # Load existing dictionary
    pairs_dict = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if content.strip():
                    # If it was a list (old format), convert or ignore? 
                    # Let's handle migration gracefully if needed, or just assume dict for now.
                    # If user just started, it might be a list from previous step.
                    loaded = json.loads(content)
                    if isinstance(loaded, dict):
                        pairs_dict = loaded
                    else:
                        # Handle migration from list to dict if necessary, or just overwrite/backup
                        # For now, let's just start fresh if it's not a dict to avoid crash
                        pass 
        except:
            pass
            
    # Use filename as key if available, otherwise "Artist - Title"
    key = song1['filename'] if song1['filename'] else f"{song1['artist']} - {song1['title']}"
    
    # Value to store
    val = {
        "artist": song2['artist'],
        "title": song2['title'],
        "filename": song2['filename'],
        "key": song2.get('key'),
        "timestamp": time.time()
    }

    if key not in pairs_dict:
        pairs_dict[key] = []
        
    # Avoid duplicates
    # Check if this filename is already in the list
    exists = False
    for existing in pairs_dict[key]:
        if existing.get('filename') == song2['filename']:
            exists = True
            break
            
    if not exists:
        pairs_dict[key].append(val)
    
    with open(filename, 'w') as f:
        json.dump(pairs_dict, f, indent=2)

def load_good_pairs():
    filename = "good_pairs.json"
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if content.strip():
                    loaded = json.loads(content)
                    if isinstance(loaded, dict):
                        return loaded
        except:
            pass
    return {}

def get_key_from_file(filename):
    """Extract key from MP3 tags (TPUB or TIT1)"""
    if not filename or not os.path.exists(filename):
        # Try decoding filename if it has odd chars?
        # print(f"DEBUG: File not found: {filename}")
        return None
    
    if ID3 is None:
        return None
        
    try:
        audio = ID3(filename)
        # Try TPUB (Publisher) where Camelot key often lives
        if 'TPUB' in audio:
            return audio['TPUB'].text[0]
        # Try TIT1 (Content Group Description)
        if 'TIT1' in audio:
            return audio['TIT1'].text[0]
        # Try TKEY (Initial Key) - standard ID3 key
        if 'TKEY' in audio:
            return audio['TKEY'].text[0]
        # Try Artist field if key is in brackets like (8A)
        if 'TPE1' in audio:
             artist = audio['TPE1'].text[0]
             # Simple heuristic for (1A) etc
             import re
             m = re.search(r'\(([0-9]+[AB])\)', artist)
             if m:
                 return m.group(1)
    except:
        pass
    return None

def main():
    parser_arg = argparse.ArgumentParser(description="Show currently playing tracks from Serato")
    parser_arg.add_argument("-m", "--monitor", action="store_true", help="Monitor for changes continuously")
    args = parser_arg.parse_args()

    home = os.path.expanduser("~")
    music_dir = os.path.join(home, "Music")
    serato_dir = os.path.join(music_dir, "_Serato_")
    
    last_check = {}
    
    if args.monitor:
        fd, old_settings = setup_terminal()
        print("Monitoring started. Press 'q' to quit, 'p' to pair current tracks.")

    try:
        while True:
            session_file = get_latest_session_file(serato_dir)
            if not session_file:
                print("No Serato session files found.")
                if args.monitor: restore_terminal(fd, old_settings)
                return

            current_tracks_data = None

            try:
                parser = SeratoSessionParser(session_file)
                tracks_data = parser.parse()
                
                # Process tracks
                parsed_tracks = []
                for fields in tracks_data:
                    title = decode_string(fields.get(6, b''))
                    artist = decode_string(fields.get(7, b''))
                    deck = decode_int(fields.get(31, b''))
                    start_time = decode_int(fields.get(28, b''))
                    filename = decode_string(fields.get(2, b'')) # Field 2 seems to be the full path
                    key = get_key_from_file(filename)
                    
                    if title or artist: 
                        parsed_tracks.append({
                            'artist': artist,
                            'title': title,
                            'deck': deck,
                            'start_time': start_time,
                            'filename': filename,
                            'key': key
                        })

                parsed_tracks.sort(key=lambda x: x['start_time'])

                # Get last track for each deck
                last_deck_1 = None
                last_deck_2 = None
                
                for track in reversed(parsed_tracks):
                    if track['deck'] == 1 and not last_deck_1:
                        last_deck_1 = track
                    elif track['deck'] == 2 and not last_deck_2:
                        last_deck_2 = track
                    
                    if last_deck_1 and last_deck_2:
                        break
                
                current_tracks_data = {'deck1': last_deck_1, 'deck2': last_deck_2}

                # Check if changed
                current_state = {
                    1: (last_deck_1['title'], last_deck_1['start_time']) if last_deck_1 else None,
                    2: (last_deck_2['title'], last_deck_2['start_time']) if last_deck_2 else None
                }
                
                if current_state != last_check:
                    # Load good pairs
                    pairs_db = load_good_pairs()

                    # Clear screen if monitoring
                    if args.monitor:
                        print("\033[H\033[J", end="") # ANSI clear screen
                    
                    print("-" * 40)
                    print(f"Session: {os.path.basename(session_file)}")
                    print("-" * 40)

                    current_time = time.time()

                    def print_track(label, track):
                        if not track:
                            print(f"{label}: (None)")
                            return
                        ago = int(current_time - track['start_time'])
                        time_str = f"{ago}s ago" if ago < 3600 else f"{ago//60}m ago"
                        
                        key_str = f"[{track['key']}] " if track.get('key') else ""
                        
                        print(f"{label} ({time_str}):")
                        # print(f"  Artist: {track['artist']}")
                        print(f"  {key_str}{track['title']}")
                        
                        # Check for good pairs
                        key_id = track['filename'] if track['filename'] else f"{track['artist']} - {track['title']}"
                        if key_id in pairs_db:
                            print("  \033[92mGood Pairs:\033[0m") # Green text
                            for pair in pairs_db[key_id]:
                                # Get key for pair: try from DB, otherwise look it up live
                                pair_key_val = pair.get('key')
                                if not pair_key_val and pair.get('filename'):
                                     pair_key_val = get_key_from_file(pair['filename'])
                                     
                                pair_key_str = f"[{pair_key_val}] " if pair_key_val else ""
                                print(f"    -> {pair_key_str}{pair['title']}")

                    print_track("Deck 1", last_deck_1)
                    print("-" * 20)
                    print_track("Deck 2", last_deck_2)
                    print("-" * 40)
                    
                    if args.monitor:
                        print("\nCommands: [p] Pair good mix  [q] Quit")

                    last_check = current_state

            except Exception as e:
                if not args.monitor:
                    print(f"Error: {e}")
            
            if not args.monitor:
                break
                
            # Input handling loop for monitor mode
            if args.monitor:
                start_sleep = time.time()
                while time.time() - start_sleep < 2:
                    key = get_key_press()
                    if key == 'q':
                        restore_terminal(fd, old_settings)
                        return
                    elif key == 'p':
                         if current_tracks_data and current_tracks_data['deck1'] and current_tracks_data['deck2']:
                            d1 = current_tracks_data['deck1']
                            d2 = current_tracks_data['deck2']
                            print(f"\nConfirm good pair? (y/n)")
                            print(f"  1: {d1['artist']} - {d1['title']}")
                            print(f"  2: {d2['artist']} - {d2['title']}")
                            
                            # Wait for y/n
                            while True:
                                conf = get_key_press()
                                if conf == 'y':
                                    save_pair(d1, d2)
                                    print("--> Saved to good_pairs.json!")
                                    time.sleep(1)
                                    # Force refresh
                                    last_check = {} 
                                    break
                                elif conf == 'n':
                                    print("Cancelled.")
                                    time.sleep(1)
                                    # Force refresh
                                    last_check = {}
                                    break
                                elif conf: # ignore other keys but don't loop tight
                                    pass
                                time.sleep(0.05)
                         else:
                             print("\nNeed two tracks playing to pair.")
                             time.sleep(1)

                    time.sleep(0.1)
            else:
                # Should not happen given break above
                break

    except KeyboardInterrupt:
        if args.monitor:
            restore_terminal(fd, old_settings)

if __name__ == "__main__":
    main()
