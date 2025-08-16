import struct
import os
import glob

def decode_struct(data):
  ret = []
  i = 0
  while i < len(data):
    tag = data[i:i+4].decode('ascii')
    length = struct.unpack('>I', data[i+4:i+8])[0]
    value = data[i+8:i+8+length]
    value = decode(value, tag=tag)
    ret.append((tag, value))
    i += 8 + length
  return ret


def decode_unicode(data):
  return data.decode('utf-16-be')


def decode_unsigned(data):
  return struct.unpack('>I', data)[0]


def noop(data):
  return data


DECODE_FUNC_FULL = {
  None: decode_struct,
  'vrsn': decode_unicode,
  'sbav': noop,
}

DECODE_FUNC_FIRST = {
  'o': decode_struct,
  't': decode_unicode,
  'p': decode_unicode,
  'u': decode_unsigned,
  'b': noop,
}

def decode(data, tag=None):
  if tag in DECODE_FUNC_FULL:
    decode_func = DECODE_FUNC_FULL[tag]
  else:
    decode_func = DECODE_FUNC_FIRST[tag[0]]

  return decode_func(data)


def loadcrate(fname):
  with open(fname, 'rb') as f:
    return decode(f.read())


def encode_struct(data):
  """Encode structured data back to binary format"""
  result = b''
  for tag, value in data:
    encoded_value = encode_value(value, tag)
    result += tag.encode('ascii')
    result += struct.pack('>I', len(encoded_value))
    result += encoded_value
  return result


def encode_value(value, tag):
  """Encode a value based on its tag"""
  if tag in DECODE_FUNC_FULL:
    if tag == 'vrsn':
      return value.encode('utf-16-be')
    elif tag == 'sbav':
      return value
    else:
      return encode_struct(value)
  else:
    first_char = tag[0]
    if first_char == 'o':
      return encode_struct(value)
    elif first_char == 't':
      return value.encode('utf-16-be')
    elif first_char == 'p':
      return value.encode('utf-16-be')
    elif first_char == 'u':
      return struct.pack('>I', value)
    elif first_char == 'b':
      return value
    else:
      return value


def update_crate_paths(crate_data, crate_name):
  """Update crate paths and return True if any changes were made"""
  # Set SC_CACHE_DIR directly
  SC_BASE_DIR = "Users/fraser.langton/Music/soundcloud"
  SC_CACHE_DIR = f"{SC_BASE_DIR}/CACHE"
  
  changes_made = False
  unchanged_count = 0
  
  def update_path(path):
    nonlocal changes_made, unchanged_count
    # Find the soundcloud part of the path and extract just the filename
    if 'soundcloud' in path:
      # Extract the filename (the [id=...] part)
      filename = os.path.basename(path)
      new_path = os.path.join(SC_CACHE_DIR, filename)
      # Only print if the path actually changed
      if new_path != path:
        print(f"moved {path}")
        changes_made = True
        return new_path
      else:
        unchanged_count += 1
    return path
  
  def update_structure(data):
    if isinstance(data, list):
      for i, item in enumerate(data):
        if isinstance(item, tuple) and len(item) == 2:
          tag, value = item
          if isinstance(value, str) and tag == 'ptrk':  # This is a track path
            new_path = update_path(value)
            # Update the tuple in the list
            data[i] = (tag, new_path)
          elif isinstance(value, list):
            update_structure(value)
  
  update_structure(crate_data)
  
  # Print count of unchanged paths
  if unchanged_count > 0:
    print(f"{unchanged_count} paths were not changed")
  
  return changes_made


def save_crate(crate_data, filename):
  """Save the updated crate data back to file"""
  encoded_data = encode_struct(crate_data)
  with open(filename, 'wb') as f:
    f.write(encoded_data)


def main():
  # Find all .crate files in the Serato directory
  serato_dir = os.path.join(os.path.expanduser("~"), "Music", "_Serato_")
  crate_pattern = os.path.join(serato_dir, "**", "*.crate")
  all_crate_files = glob.glob(crate_pattern, recursive=True)
  
  # Filter to only include crates with "soundcloud" in the filename
  crate_files = [f for f in all_crate_files if "soundcloud" in os.path.basename(f).lower()]
  
  if not crate_files:
    return
  
  # Load and process each crate
  for crate_file in crate_files:
    try:
      crate_name = os.path.basename(crate_file)
      crate_data = loadcrate(crate_file)
      changes_made = update_crate_paths(crate_data, crate_name)
      
      # Save the updated crate back to file if changes were made
      if changes_made:
        save_crate(crate_data, crate_file)
        
    except Exception as e:
      pass  # Silently skip errors


if __name__ == "__main__":
  main()
