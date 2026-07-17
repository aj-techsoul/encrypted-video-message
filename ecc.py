# ecc.py
from reedsolo import RSCodec, ReedSolomonError

# We use 10 parity symbols for incredible error correction strength.
# 11 data bytes + 10 parity bytes = 21 bytes total.
# 21 bytes = 168 bits = 56 color blocks (3 bits per block) = 7x8 grid.
rs = RSCodec(10)

def encode_chunk(chunk_str, index):
    """
    Takes up to 9 characters and its sequence index, adds Reed-Solomon parity math,
    and returns a 7x8 grid of color IDs (0-7).
    """
    # Pad string to exactly 9 characters
    chunk_str = chunk_str.ljust(9, '\0')
    
    # 2 bytes for index, 9 bytes for chars = 11 bytes
    raw_bytes = index.to_bytes(2, byteorder='big') + chunk_str.encode('utf-8')[:9]
    
    # 11 data bytes + 10 parity bytes = 21 bytes
    ecc_bytes = rs.encode(raw_bytes)
    
    # Convert 21 bytes to 168 bits string
    bits_str = ''.join([format(b, '08b') for b in ecc_bytes])
    
    # Convert every 3 bits into a color ID (0-7)
    color_ids = [int(bits_str[i:i+3], 2) for i in range(0, 168, 3)]
    
    # Reshape into a 7x8 grid
    color_grid = [color_ids[r*8:(r+1)*8] for r in range(7)]
    return color_grid

def calculate_ber(corrupted_bytes, perfect_bytes):
    """Calculates the Bit Error Rate (count) between two byte arrays."""
    bit_errors = 0
    for c_byte, p_byte in zip(corrupted_bytes, perfect_bytes):
        xor_val = c_byte ^ p_byte
        bit_errors += bin(xor_val).count('1')
    return bit_errors

def decode_color_grid(color_grid):
    """
    Takes a 7x8 grid of color IDs, converts to bits, runs RS to fix noise,
    calculates the BER, and returns the original characters, index, and BER.
    """
    try:
        # Flatten the grid
        color_ids = [c for row in color_grid for c in row]
        
        # Convert color IDs to 3-bit strings
        bits_str = ''.join([format(c, '03b') for c in color_ids])
        
        # Convert 168 bits back into 21 bytes
        byte_array = bytearray([int(bits_str[i:i+8], 2) for i in range(0, 168, 8)])
        
        # Decode using Reed-Solomon
        decoded_bytes, perfect_bytes, _ = rs.decode(byte_array)
        
        # Calculate Bit Errors against the entire 21 byte transmission
        ber = calculate_ber(byte_array, perfect_bytes)
        
        # Extract index and characters
        index = int.from_bytes(decoded_bytes[0:2], byteorder='big')
        char_str = decoded_bytes[2:11].decode('utf-8').rstrip('\0')
        
        return char_str, index, ber
    except Exception:
        # Too much screen reflection or blur to recover mathematically
        return None, None, None