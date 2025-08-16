#!/usr/bin/env python3
"""
Serato Crate Reader CLI Tool

Decodes and prints the contents of Serato crate files in a readable format.
"""

import struct
import os
import glob
import argparse
import sys
from pathlib import Path

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Basic colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

def colorize(text, color, use_colors=True):
    """Add color to text if colors are enabled"""
    if not use_colors or not sys.stdout.isatty():
        return text
    return f"{color}{text}{Colors.RESET}"

def decode_struct(data):
    """Decode structured data with tag-length-value format"""
    ret = []
    i = 0
    while i < len(data):
        if i + 8 > len(data):
            break
        tag = data[i:i+4].decode('ascii')
        length = struct.unpack('>I', data[i+4:i+8])[0]
        if i + 8 + length > len(data):
            break
        value = data[i+8:i+8+length]
        value = decode(value, tag=tag)
        ret.append((tag, value))
        i += 8 + length
    return ret

def decode_unicode(data):
    """Decode UTF-16 big-endian unicode string"""
    return data.decode('utf-16-be')

def decode_unsigned(data):
    """Decode unsigned 32-bit integer"""
    return struct.unpack('>I', data)[0]

def noop(data):
    """Return data as-is"""
    return data

# Mapping of tags to their decode functions
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
    """Decode data based on tag"""
    if tag in DECODE_FUNC_FULL:
        decode_func = DECODE_FUNC_FULL[tag]
    else:
        decode_func = DECODE_FUNC_FIRST[tag[0]]
    return decode_func(data)

def loadcrate(fname):
    """Load and decode a crate file"""
    with open(fname, 'rb') as f:
        return decode(f.read())

def find_crate_file(crate_name, serato_dir=None):
    """Find a crate file by name, searching common locations"""
    if serato_dir is None:
        serato_dir = os.path.join(os.path.expanduser("~"), "Music", "_Serato_")
    
    # Common crate file patterns to search for
    search_patterns = [
        # Direct match
        f"{crate_name}.crate",
        f"{crate_name}",
        # With soundcloud prefix
        f"soundcloud%%{crate_name}.crate",
        f"soundcloud%%{crate_name}",
        # Case variations
        f"{crate_name.lower()}.crate",
        f"{crate_name.upper()}.crate",
        f"soundcloud%%{crate_name.lower()}.crate",
        f"soundcloud%%{crate_name.upper()}.crate",
    ]
    
    # Search in common subdirectories
    search_dirs = [
        os.path.join(serato_dir, "Subcrates"),
        serato_dir,
    ]
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        for pattern in search_patterns:
            crate_path = os.path.join(search_dir, pattern)
            if os.path.exists(crate_path):
                return crate_path
    
    # If not found, try glob pattern matching
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        # Use glob to find files containing the crate name
        glob_pattern = os.path.join(search_dir, f"*{crate_name}*")
        matches = glob.glob(glob_pattern)
        crate_matches = [m for m in matches if m.endswith('.crate')]
        if crate_matches:
            return crate_matches[0]
    
    return None

def print_raw_contents(crate_data, crate_name, use_colors=True):
    """Print raw decoded crate contents"""
    print(f"🔍 {colorize('Raw Contents:', Colors.BRIGHT_CYAN, use_colors)} {colorize(crate_name, Colors.BRIGHT_WHITE, use_colors)}")
    print(colorize("=" * 50, Colors.DIM, use_colors))
    
    def print_structure(data, level=0):
        indent = "  " * level
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, tuple) and len(item) == 2:
                    tag, value = item
                    index_str = colorize(f"[{i}]", Colors.DIM, use_colors)
                    tag_str = colorize(f"Tag: '{tag}'", Colors.CYAN, use_colors)
                    print(f"{indent}{index_str} {tag_str}")
                    
                    if isinstance(value, (str, int, float)):
                        # For string values, show both raw and repr to handle special characters
                        if isinstance(value, str):
                            type_str = colorize("Value (str):", Colors.BLUE, use_colors)
                            value_str = colorize(repr(value), Colors.GREEN, use_colors)
                            print(f"{indent}    {type_str} {value_str}")
                            # Try to show readable version if it's a path or readable text
                            if len(value) < 200 and (value.isprintable() or '/' in value):
                                readable_str = colorize("Readable:", Colors.BLUE, use_colors)
                                readable_value = colorize(value, Colors.BRIGHT_GREEN, use_colors)
                                print(f"{indent}    {readable_str} {readable_value}")
                        else:
                            type_str = colorize("Value:", Colors.BLUE, use_colors)
                            value_str = colorize(str(value), Colors.YELLOW, use_colors)
                            print(f"{indent}    {type_str} {value_str}")
                    elif isinstance(value, bytes):
                        type_str = colorize("Value (bytes):", Colors.BLUE, use_colors)
                        bytes_preview = colorize(f"{value[:50]}{'...' if len(value) > 50 else ''}", Colors.MAGENTA, use_colors)
                        print(f"{indent}    {type_str} {bytes_preview}")
                        length_str = colorize("Length:", Colors.BLUE, use_colors)
                        length_value = colorize(f"{len(value)} bytes", Colors.YELLOW, use_colors)
                        print(f"{indent}    {length_str} {length_value}")
                    elif isinstance(value, list):
                        type_str = colorize(f"Value (list with {len(value)} items):", Colors.BLUE, use_colors)
                        print(f"{indent}    {type_str}")
                        print_structure(value, level + 2)
                    else:
                        type_str = colorize(f"Value ({type(value).__name__}):", Colors.BLUE, use_colors)
                        value_str = colorize(str(value), Colors.WHITE, use_colors)
                        print(f"{indent}    {type_str} {value_str}")
                else:
                    index_str = colorize(f"[{i}]", Colors.DIM, use_colors)
                    type_str = colorize(f"{type(item).__name__}:", Colors.BLUE, use_colors)
                    value_str = colorize(str(item), Colors.WHITE, use_colors)
                    print(f"{indent}{index_str} {type_str} {value_str}")
        else:
            type_str = colorize(f"{type(data).__name__}:", Colors.BLUE, use_colors)
            value_str = colorize(str(data), Colors.WHITE, use_colors)
            print(f"{indent}{type_str} {value_str}")
    
    print_structure(crate_data)
    print()

def print_crate_contents(crate_data, crate_name, verbose=False, use_colors=True):
    """Print crate contents in a readable format"""
    print(f"🎵 {colorize('Crate:', Colors.BRIGHT_CYAN, use_colors)} {colorize(crate_name, Colors.BRIGHT_WHITE, use_colors)}")
    print(colorize("=" * 50, Colors.DIM, use_colors))
    
    tracks = []
    metadata = {}
    
    def extract_info(data, level=0):
        if isinstance(data, list):
            for tag, value in data:
                if tag == 'ptrk':  # Track path
                    tracks.append(value)
                elif tag == 'vrsn':  # Version
                    metadata['version'] = value
                elif tag == 'sbav':  # Possibly sub-version
                    metadata['sub_version'] = value
                elif isinstance(value, list):
                    extract_info(value, level + 1)
                elif verbose:
                    tag_str = colorize(tag, Colors.CYAN, use_colors)
                    value_str = colorize(str(value), Colors.GREEN, use_colors)
                    print(f"{'  ' * level}📝 {tag_str}: {value_str}")
    
    extract_info(crate_data)
    
    # Print metadata
    if metadata:
        print(f"\n📋 {colorize('Metadata:', Colors.BRIGHT_BLUE, use_colors)}")
        for key, value in metadata.items():
            key_str = colorize(key, Colors.BLUE, use_colors)
            value_str = colorize(str(value), Colors.WHITE, use_colors)
            print(f"  {key_str}: {value_str}")
    
    # Print tracks
    if tracks:
        track_count = colorize(f"({len(tracks)} total)", Colors.YELLOW, use_colors)
        print(f"\n🎶 {colorize('Tracks', Colors.BRIGHT_GREEN, use_colors)} {track_count}:")
        for i, track in enumerate(tracks, 1):
            # Extract filename from path
            filename = os.path.basename(track)
            track_num = colorize(f"{i:2d}.", Colors.DIM, use_colors)
            track_name = colorize(filename, Colors.GREEN, use_colors)
            print(f"  {track_num} {track_name}")
            if verbose:
                path_label = colorize("Full path:", Colors.BLUE, use_colors)
                path_value = colorize(track, Colors.BRIGHT_GREEN, use_colors)
                print(f"      {path_label} {path_value}")
    else:
        print(f"\n❌ {colorize('No tracks found in this crate', Colors.RED, use_colors)}")
    
    print()

def list_available_crates(serato_dir=None, use_colors=True):
    """List all available crate files"""
    if serato_dir is None:
        serato_dir = os.path.join(os.path.expanduser("~"), "Music", "_Serato_")
    
    print(f"📁 {colorize('Available crates:', Colors.BRIGHT_CYAN, use_colors)}")
    print(colorize("-" * 30, Colors.DIM, use_colors))
    
    # Search for crate files
    search_dirs = [
        os.path.join(serato_dir, "Subcrates"),
        serato_dir,
    ]
    
    found_crates = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            crate_files = glob.glob(os.path.join(search_dir, "*.crate"))
            for crate_file in crate_files:
                crate_name = os.path.basename(crate_file)
                found_crates.append((crate_name, crate_file))
    
    if found_crates:
        for crate_name, crate_path in sorted(found_crates):
            # Show simplified name for common patterns
            display_name = crate_name
            if display_name.startswith("soundcloud%%"):
                display_name = display_name.replace("soundcloud%%", "")
            if display_name.endswith(".crate"):
                display_name = display_name[:-6]
            
            bullet = colorize("•", Colors.GREEN, use_colors)
            name = colorize(display_name, Colors.BRIGHT_GREEN, use_colors)
            full_name = colorize(f"({crate_name})", Colors.DIM, use_colors)
            print(f"  {bullet} {name} {full_name}")
    else:
        print(f"  {colorize('No crate files found', Colors.RED, use_colors)}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Decode and print Serato crate contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 5am                    # Print contents of 5am crate
  %(prog)s soundcloud%%boogie     # Print contents using full name
  %(prog)s -v bounce-inc          # Print with verbose output
  %(prog)s --raw 5am              # Dump raw decoded contents
  %(prog)s --no-color bunene      # Print without colors
  %(prog)s --list                 # List all available crates
        """
    )
    
    parser.add_argument(
        "crate_name",
        nargs="?",
        help="Name of the crate to decode (without .crate extension)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output with all metadata"
    )
    
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Dump the full raw decoded contents"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available crates"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    parser.add_argument(
        "--serato-dir",
        help="Path to Serato directory (default: ~/Music/_Serato_)"
    )
    
    args = parser.parse_args()
    
    # Determine if colors should be used
    use_colors = not args.no_color and sys.stdout.isatty()
    
    # Handle list command
    if args.list:
        list_available_crates(args.serato_dir, use_colors)
        return
    
    # Require crate name if not listing
    if not args.crate_name:
        parser.print_help()
        return
    
    # Find the crate file
    crate_file = find_crate_file(args.crate_name, args.serato_dir)
    
    if not crate_file:
        error_msg = colorize(f"❌ Crate '{args.crate_name}' not found!", Colors.RED, use_colors)
        print(error_msg)
        print(f"\n{colorize('Try one of these options:', Colors.YELLOW, use_colors)}")
        print(f"  • Use {colorize('--list', Colors.CYAN, use_colors)} to see available crates")
        print(f"  • Check the spelling")
        print(f"  • Use the full crate name (e.g., {colorize('soundcloud%%5am', Colors.GREEN, use_colors)})")
        sys.exit(1)
    
    # Load and decode the crate
    try:
        crate_data = loadcrate(crate_file)
        
        if args.raw:
            print_raw_contents(crate_data, args.crate_name, use_colors)
        else:
            print_crate_contents(crate_data, args.crate_name, args.verbose, use_colors)
    except Exception as e:
        error_msg = colorize(f"❌ Error reading crate file: {e}", Colors.RED, use_colors)
        print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main() 