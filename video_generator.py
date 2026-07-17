# video_generator.py
import cv2
import numpy as np
from ecc import encode_chunk

# BGR Color Mapping (3 bits -> 0 to 7)
COLOR_PALETTE = [
    (0, 0, 0),       # 000: Black
    (0, 0, 255),     # 001: Red
    (0, 255, 0),     # 010: Green
    (0, 255, 255),   # 011: Yellow
    (255, 0, 0),     # 100: Blue
    (255, 0, 255),   # 101: Magenta
    (255, 255, 0),   # 110: Cyan
    (255, 255, 255)  # 111: White
]

def generate_animated_frame_matrix(grid_width=8, block_size=120):
    """
    Generates a 7-row by 8-column blank color canvas.
    """
    rows = 7
    matrix = np.ones((rows * block_size, grid_width * block_size, 3), dtype=np.uint8) * 255
    return matrix, grid_width * block_size, rows * block_size

def create_animated_video(text, output_video_path="animated_video.mp4", fps=30, display_time_per_chunk=1.0):
    if not text.endswith('\x04'):
        text += '\x04'
        
    # Split text into 9-character chunks
    chunks = [text[i:i+9] for i in range(0, len(text), 9)]
    total_chunks = len(chunks)
    frames_per_chunk = int(fps * display_time_per_chunk)
    total_frames = total_chunks * frames_per_chunk
    
    # Layout tuning metrics
    marker_size = 120
    padding = 30
    border_gap = 40
    
    grid_width_px = 8 * 120
    grid_height_px = 7 * 120
    
    full_width = grid_width_px + (2 * marker_size) + (2 * padding) + (2 * border_gap)
    full_height = grid_height_px + (2 * marker_size) + (2 * padding) + (2 * border_gap)
    
    # Generate structural ArUco framing anchors (converted to BGR)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    
    def get_color_marker(id):
        marker = cv2.aruco.generateImageMarker(aruco_dict, id, marker_size)
        return cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        
    marker_tl = get_color_marker(0)
    marker_tr = get_color_marker(1)
    marker_br = get_color_marker(2)
    marker_bl = get_color_marker(3)
    
    base_template = np.ones((full_height, full_width, 3), dtype=np.uint8) * 255
    base_template[border_gap:border_gap+marker_size, border_gap:border_gap+marker_size] = marker_tl
    base_template[border_gap:border_gap+marker_size, full_width-marker_size-border_gap:full_width-border_gap] = marker_tr
    base_template[full_height-marker_size-border_gap:full_height-border_gap, full_width-marker_size-border_gap:full_width-border_gap] = marker_br
    base_template[full_height-marker_size-border_gap:full_height-border_gap, border_gap:border_gap+marker_size] = marker_bl
    
    x_offset = marker_size + padding + border_gap
    y_offset = marker_size + padding + border_gap
    
    # AVC1/H.264 video codec configuration
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    video = cv2.VideoWriter(output_video_path, fourcc, fps, (full_width, full_height), isColor=True)
    
    print(f"Generating CSK ECC protected animated video ({full_width}x{full_height})...")
    
    for frame_idx in range(total_frames):
        chunk_idx = frame_idx // frames_per_chunk
        current_chunk = chunks[chunk_idx]
        
        frame = base_template.copy()
        
        # 1. Fetch the Reed-Solomon 7-row protection COLOR layout
        color_grid = encode_chunk(current_chunk, chunk_idx)
        
        # 2. Get standard blank grid array sizing template
        matrix, _, _ = generate_animated_frame_matrix(grid_width=8, block_size=120)
        
        # 3. Draw error-corrected payload directly into the canvas array
        for row_idx, row_colors in enumerate(color_grid):
            for col_idx, color_id in enumerate(row_colors):
                color_val = COLOR_PALETTE[color_id]
                # Apply structural bounding rectangles to array pixels
                matrix[row_idx*120:(row_idx+1)*120, col_idx*120:(col_idx+1)*120] = color_val
        
        # Paste calculated text data matrix directly into coordinates
        frame[y_offset:y_offset+grid_height_px, x_offset:x_offset+grid_width_px] = matrix
        
        # Overlay running timeline strings
        sec = frame_idx // fps
        msec = int((frame_idx % fps) * (1000/fps))
        time_text = f"T+{sec:02d}:{msec:03d} | FRAME:{frame_idx:04d} | CHUNK:{chunk_idx+1}/{total_chunks} [CSK ACTIVE]"
        
        if (frame_idx // (fps // 2)) % 2 == 0:
            cv2.circle(frame, (border_gap // 2, border_gap // 2), 8, (0,0,0), -1)
            
        cv2.putText(frame, time_text, (border_gap, border_gap // 2 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
        
        video.write(frame)
        
    video.release()
    print(f"Animated Video successfully created: {output_video_path}")

if __name__ == "__main__":
    secret_phrase = "HELLO, WORLD! THIS IS A 8-COLOR CSK HIGH DENSITY PAYLOAD TEST\n"
    create_animated_video(secret_phrase)