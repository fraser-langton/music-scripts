#!/usr/bin/env python3
import sys
import csv
import struct
import datetime
from cratedigger.util.io import InputStream

def parse_adat(content):
    offset = 0
    fields = {}
    while offset < len(content):
        try:
            if offset + 8 > len(content):
                break
            field_id = int.from_bytes(content[offset:offset+4], 'big')
            offset += 4
            val_len = int.from_bytes(content[offset:offset+4], 'big')
            offset += 4
            
            if offset + val_len > len(content):
                break
            
            value = content[offset:offset+val_len]
            offset += val_len
            fields[field_id] = value
        except:
            break
    return fields

def decode_string(bytes_val):
    try:
        return bytes_val.decode('utf-16-be').strip('\x00')
    except:
        return ""

def decode_int(bytes_val):
    try:
        return int.from_bytes(bytes_val, 'big')
    except:
        return 0

def parse_session_to_csv(path, output_csv):
    print(f"Parsing {path} to {output_csv}...")
    
    entries = []
    
    with open(path, 'rb') as f:
        stream = InputStream(f)
        
        # Skip header until first oent
        f.read()
        f.seek(0)
        content = f.read()
        start_idx = content.find(b'oent')
        if start_idx == -1:
            print("No entries found.")
            return
            
        f.seek(start_idx)
        
        # We need to re-wrap in InputStream at the correct position?
        # InputStream buffers, so we can't just seek underlying file easily if we already read.
        # Let's just open a new handle or assume we can use the stream if we haven't read from it yet.
        # Actually, let's just do the seek and then create InputStream.
        
    with open(path, 'rb') as f:
        f.seek(start_idx)
        stream = InputStream(f)
        
        while True:
            try:
                tag = stream.read_string(4)
                length = stream.read_int()
                
                if tag == 'oent':
                    continue
                
                content = stream.read(length)
                if tag == 'adat':
                    fields = parse_adat(content)
                    
                    # Extract relevant fields
                    track_path = decode_string(fields.get(2, b''))
                    start_ts = decode_int(fields.get(28, b'\x00'*4))
                    end_ts = decode_int(fields.get(29, b'\x00'*4))
                    
                    start_time = ""
                    end_time = ""
                    duration = 0
                    
                    if start_ts > 0:
                        try:
                            dt = datetime.datetime.fromtimestamp(start_ts)
                            start_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                            
                    if end_ts > 0:
                        try:
                            dt = datetime.datetime.fromtimestamp(end_ts)
                            end_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                            
                    if end_ts > start_ts:
                        duration = end_ts - start_ts

                    if track_path:
                        entries.append({
                            'path': track_path,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration_seconds': duration
                        })
                        
            except ValueError:
                break
                
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['start_time', 'end_time', 'duration_seconds', 'path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)
            
    print(f"Successfully wrote {len(entries)} entries to {output_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        input_file = "music-scripts/2272.session"
    else:
        input_file = sys.argv[1]
        
    output_file = input_file + ".csv"
    parse_session_to_csv(input_file, output_file)




