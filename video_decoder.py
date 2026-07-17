# video_decoder.py
import cv2
import numpy as np
from ecc import decode_color_grid

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

def closest_color_id(bgr_pixel):
    min_dist = float('inf')
    best_id = 0
    # bgr_pixel is a numpy array [B, G, R]
    for idx, color in enumerate(COLOR_PALETTE):
        # Calculate Euclidean distance in color space
        dist = np.sum((np.array(bgr_pixel, dtype=np.int32) - np.array(color, dtype=np.int32)) ** 2)
        if dist < min_dist:
            min_dist = dist
            best_id = idx
    return best_id

def decode_image(image, grid_width=8, block_size=120):
    """
    Processes perspective-corrected color frames, mapping each block 
    to its closest color ID (0-7) to form a 7x8 color grid.
    """
    # Ensure it's a color image
    if len(image.shape) != 3:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
    img_h, img_w, _ = image.shape
    
    target_width = grid_width * block_size
    block_size_approx = img_w / float(grid_width)
    num_rows = round(img_h / block_size_approx)
    if num_rows < 1: 
        num_rows = 1
    target_height = int(num_rows * block_size)
    
    aligned_grid = cv2.resize(image, (target_width, target_height))
    
    img_height, img_width, _ = aligned_grid.shape
    grid_height = img_height // block_size
    
    color_grid = []
    
    for row in range(grid_height):
        row_ids = []
        for col in range(grid_width):
            center_x = (col * block_size) + (block_size // 2)
            center_y = (row * block_size) + (block_size // 2)
            
            if center_y < img_height and center_x < img_width:
                # Sample the center pixel (BGR)
                pixel_value = aligned_grid[center_y, center_x]
                color_id = closest_color_id(pixel_value)
                row_ids.append(color_id)
        color_grid.append(row_ids)
                    
    if len(color_grid) == 7:
        return color_grid
            
    return None

def decode_video(video_path, grid_width=8, block_size=120, headless=False):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not read source {video_path}")
        return None

    print(f"Scanning target video tracking stream from '{video_path}'...")
    
    frame_count = 0
    decoded_chunks = {}
    
    # Initialize ArUco tracking parameters
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 23
    parameters.adaptiveThreshWinSizeStep = 10
    parameters.minMarkerPerimeterRate = 0.03
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray_frame)
        
        if ids is not None and len(ids) == 4:
            ids = ids.flatten()
            corner_map = {int(ids[i]): corners[i][0] for i in range(len(ids))}
            
            if all(i in corner_map for i in [0, 1, 2, 3]):
                src_pts = np.float32([corner_map[0][0], corner_map[1][1], corner_map[2][2], corner_map[3][3]])
                
                measured_w = np.linalg.norm(corner_map[1][1] - corner_map[0][0])
                measured_h = (np.linalg.norm(corner_map[3][3] - corner_map[0][0]) + np.linalg.norm(corner_map[2][2] - corner_map[1][1])) / 2.0
                
                target_w = 150 + (grid_width * block_size) + 150
                target_h = int(target_w * (measured_h / measured_w)) if measured_w > 0 else target_w
                dst_pts = np.float32([[0, 0], [target_w, 0], [target_w, target_h], [0, target_h]])
                
                # Execute spatial homography un-warping mapping on the COLOR frame
                matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                warped_img = cv2.warpPerspective(frame, matrix, (target_w, target_h))
                
                # Strip out corner bounds
                cropped_grid = warped_img[150:target_h-150, 150:target_w-150]
                
                scanned_color_grid = decode_image(cropped_grid, grid_width, block_size)
                
                if scanned_color_grid is not None:
                    # PASS DATA MATRIX TO THE REED-SOLOMON ENGINE
                    corrected_char, char_idx, ber = decode_color_grid(scanned_color_grid)
                    
                    if corrected_char is not None:
                        if '\x04' in corrected_char:
                            if not headless:
                                print(f"Frame {frame_count:03d} -> End of Transmission received. (BER: {ber}/168 bits)")
                            # Extract everything up to the EOF
                            corrected_char = corrected_char.split('\x04')[0]
                            if corrected_char and char_idx not in decoded_chunks:
                                decoded_chunks[char_idx] = corrected_char
                            break
                            
                        if char_idx not in decoded_chunks:
                            decoded_chunks[char_idx] = corrected_char
                            if not headless:
                                print(f"Frame {frame_count:03d} [Chunk {char_idx}] -> Decoded: '{repr(corrected_char)}' | BER: {ber}/168 bits")
        
        if not headless:
            cv2.imshow("Decoder Scanning Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    if not headless:
        cv2.destroyAllWindows()
        
    # Reassemble total transmission chunks cleanly 
    if decoded_chunks:
        sorted_keys = sorted(decoded_chunks.keys())
        final_decoded_text = "".join([decoded_chunks.get(i, '[MISSING]') for i in range(max(sorted_keys) + 1)])
        print(f"\n[SCAN COMPLETE] Decoded Output Payload:\n{final_decoded_text}\n")
        return "", final_decoded_text
    
    print("\n[FAILED] Could not decode tracking structures.")
    return "", ""

if __name__ == "__main__":
    decode_video("animated_video.mp4", grid_width=8, block_size=120, headless=False)