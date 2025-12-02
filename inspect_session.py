#!/usr/bin/env python3
import os
import sys
import struct
from cratedigger.util.io import InputStream

def parse_adat(content):
    # Content is bytes
    # Try to parse as a sequence of fields
    # Format hypothesis: ID (4 bytes), Length (4 bytes), Value (Length bytes)
    offset = 0
    fields = {}
    while offset < len(content):
        try:
            # Read ID
            if offset + 8 > len(content):
                break
            field_id = int.from_bytes(content[offset:offset+4], 'big')
            offset += 4
            
            # Read Length
            val_len = int.from_bytes(content[offset:offset+4], 'big')
            offset += 4
            
            if offset + val_len > len(content):
                # print(f"    [!] Field {field_id} length {val_len} exceeds remaining size")
                break
            
            value = content[offset:offset+val_len]
            offset += val_len
            
            fields[field_id] = value
            
            # Try to interpret value
            val_display = value.hex()
            if field_id == 2: # Path
                try:
                    val_display = value.decode('utf-16-be')
                except:
                    pass
            elif field_id in [1, 3, 4, 5]: # Integers?
                if len(value) == 4:
                    val_display = int.from_bytes(value, 'big')
            
            print(f"    Field {field_id}: {val_display}")
            
        except Exception as e:
            print(f"    Error parsing fields: {e}")
            break

def inspect_session(path):
    print(f"Inspecting {path}...")
    try:
        with open(path, 'rb') as f:
            stream = InputStream(f)
            
            # Header
            try:
                stream.skip_string('vrsn')
                stream.skip_bytes(b'\x00\x00')
                version = stream.read_string(8, 'utf-16-be')
                print(f"Version: {version}")
            except Exception as e:
                print(f"Header parse error: {e}")
            
            # Scan for the first 'oent' tag
            found_start = False
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                idx = chunk.find(b'oent')
                if idx != -1:
                    # Found it. Seek to that position.
                    current_pos = f.tell()
                    f.seek(current_pos - len(chunk) + idx)
                    found_start = True
                    break
            
            if not found_start:
                print("Could not find 'oent' tag")
                return

            while True:
                try:
                    tag = stream.read_string(4)
                except ValueError:
                    break # End of file
                
                try:
                    length = stream.read_int()
                except ValueError:
                    print(f"Tag {tag} has no length")
                    break
                
                print(f"Tag: {tag}, Length: {length}")
                
                if tag == 'oent':
                    print("  (Container tag, continuing to parse children)")
                    continue
                
                # For other tags, read the content
                try:
                    content = stream.read(length)
                    if tag == 'adat':
                        # Parse adat fields
                        parse_adat(content)

                except ValueError:
                    print(f"  Could not read {length} bytes")
                    break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <session_file>")
        sys.exit(1)
    
    inspect_session(sys.argv[1])




