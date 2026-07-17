import cv2
import numpy as np

def text_to_binary(text):
    """Converts a text string into a string of 0s and 1s (8 bits per character)."""
    binary_str = ""
    for char in text:
        binary_str += format(ord(char), '08b')
    return binary_str

def draw_dashed_line(img, pt1, pt2, color, thickness, dash_length):
    import math
    dist = math.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1])
    if dist == 0: return
    dashes = int(dist / dash_length)
    if dashes == 0: dashes = 1
    for i in range(dashes):
        if i % 2 == 0:
            start = (int(pt1[0] + (pt2[0]-pt1[0])*i/dashes), int(pt1[1] + (pt2[1]-pt1[1])*i/dashes))
            end = (int(pt1[0] + (pt2[0]-pt1[0])*(i+1)/dashes), int(pt1[1] + (pt2[1]-pt1[1])*(i+1)/dashes))
            cv2.line(img, start, end, color, thickness)

def generate_encoded_matrix(text, grid_width=8, block_size=60):
    rows_data = []
    
    # 1. Start marker: Full black screen (stripe)
    rows_data.append([0] * grid_width)
    
    for char in text:
        if char == '\n':
            # 2 black stripes for line end
            rows_data.append([0] * grid_width)
            rows_data.append([0] * grid_width)
        elif char == ',':
            # 1 black stripe for comma
            rows_data.append([0] * grid_width)
        else:
            binary_str = format(ord(char), '08b')
            row = [255 if bit == '1' else 0 for bit in binary_str]
            rows_data.append(row)
            
    # Always end with a black stripe to clearly bound the data
    rows_data.append([0] * grid_width)
            
    grid_height = len(rows_data)
    
    canvas_height = grid_height * block_size
    canvas_width = grid_width * block_size
    canvas = np.zeros((canvas_height, canvas_width), dtype=np.uint8)
    
    # Draw blocks
    for r, row_data in enumerate(rows_data):
        for c, color in enumerate(row_data):
            x_start = c * block_size
            y_start = r * block_size
            canvas[y_start:y_start+block_size, x_start:x_start+block_size] = color
            
    # Draw dashed border exactly on the outer edge (overwrites a few pixels but center is safe)
    border_thickness = 4
    dashed_length = 20
    draw_dashed_line(canvas, (0, 0), (canvas_width-1, 0), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (canvas_width-1, 0), (canvas_width-1, canvas_height-1), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (canvas_width-1, canvas_height-1), (0, canvas_height-1), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (0, canvas_height-1), (0, 0), 127, border_thickness, dashed_length)

    return canvas, grid_width, grid_height

def generate_animated_frame_matrix(char, index, total_chars, grid_width=8, block_size=60):
    rows_data = []
    
    # 1. Start marker: Full black stripe
    rows_data.append([0] * grid_width)
    
    # 2. Index (8 bits)
    binary_index = format(index, '08b')
    rows_data.append([255 if bit == '1' else 0 for bit in binary_index])
    
    # 3. Total (8 bits)
    binary_total = format(total_chars, '08b')
    rows_data.append([255 if bit == '1' else 0 for bit in binary_total])
    
    # 4. Character Data (8 bits)
    binary_char = format(ord(char), '08b')
    rows_data.append([255 if bit == '1' else 0 for bit in binary_char])
    
    # 5. End marker: Full black stripe
    rows_data.append([0] * grid_width)
    
    grid_height = len(rows_data)
    
    canvas_height = grid_height * block_size
    canvas_width = grid_width * block_size
    canvas = np.zeros((canvas_height, canvas_width), dtype=np.uint8)
    
    # Draw blocks
    for r, row_data in enumerate(rows_data):
        for c, color in enumerate(row_data):
            x_start = c * block_size
            y_start = r * block_size
            canvas[y_start:y_start+block_size, x_start:x_start+block_size] = color
            
    # Draw dashed border
    border_thickness = 4
    dashed_length = 20
    draw_dashed_line(canvas, (0, 0), (canvas_width-1, 0), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (canvas_width-1, 0), (canvas_width-1, canvas_height-1), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (canvas_width-1, canvas_height-1), (0, canvas_height-1), 127, border_thickness, dashed_length)
    draw_dashed_line(canvas, (0, canvas_height-1), (0, 0), 127, border_thickness, dashed_length)

    return canvas, grid_width, grid_height

if __name__ == "__main__":
    secret_message = "HELLO,WORLD\nTEST"
    print(f"Original Message: {secret_message}")
    
    block_size = 60 
    encoded_image, cols, rows = generate_encoded_matrix(secret_message, grid_width=8, block_size=block_size)
    
    output_filename = "encoded_static_frame.png"
    cv2.imwrite(output_filename, encoded_image)
    print(f"\nSuccess! Encoded matrix saved as '{output_filename}'")
    print(f"Matrix Dimensions: {cols}x{rows} blocks (Total Image Size: {encoded_image.shape[1]}x{encoded_image.shape[0]} pixels)")