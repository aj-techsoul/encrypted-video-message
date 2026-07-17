import os
import base64
import numpy as np
import cv2
import uuid
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Import our mathematical error-corrected extraction and generation logic hooks
from video_decoder import decode_image
from video_generator import create_animated_video
from ecc import decode_color_grid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Keep your original styling and layout configuration perfectly intact
INDEX_HTML = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Vortex | Encoder & Decoder (Reed-Solomon)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-color: #0f172a;
      --panel-bg: rgba(30, 41, 59, 0.7);
      --text-color: #f8fafc;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
    }
    body { 
      font-family: 'Inter', sans-serif; margin: 0; background: var(--bg-color); 
      background-image: radial-gradient(circle at top right, #1e1b4b, transparent 40%),
                        radial-gradient(circle at bottom left, #0f172a, transparent 40%);
      color: var(--text-color); min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 40px 20px;
    }
    h1, h2 { text-align: center; margin-top: 0; font-weight: 800; background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .container { width: 100%; max-width: 600px; background: var(--panel-bg); padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 30px; transition: transform 0.3s ease; }
    .container:hover { transform: translateY(-5px); }
    p { color: #94a3b8; font-size: 14px; margin-bottom: 20px; text-align: center; }
    input[type=file], textarea { width: 100%; padding: 12px; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; color: var(--text-color); margin-bottom: 20px; box-sizing: border-box; font-family: 'Inter', sans-serif; }
    textarea { resize: vertical; min-height: 100px; }
    textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3); }
    button { width: 100%; padding: 14px 20px; border: none; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; margin-bottom: 10px; transition: all 0.2s ease; background: var(--accent); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2); }
    button:hover { background: var(--accent-hover); transform: translateY(-2px); box-shadow: 0 6px 12px rgba(59, 130, 246, 0.3); }
    .btn-success { background: var(--success); }
    .btn-success:hover { background: #059669; box-shadow: 0 6px 12px rgba(16, 185, 129, 0.3); }
    .btn-warning { background: var(--warning); color: #000; }
    .btn-warning:hover { background: #d97706; box-shadow: 0 6px 12px rgba(245, 158, 11, 0.3); }
    .btn-danger { background: var(--danger); }
    .btn-danger:hover { background: #dc2626; box-shadow: 0 6px 12px rgba(239, 68, 68, 0.3); }
    #videoContainer { position: relative; width: 100%; border-radius: 8px; margin-bottom: 20px; display: none; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid rgba(255, 255, 255, 0.1); }
    #videoElement { width: 100%; display: block; }
    .result-box { margin-top: 15px; font-weight: 600; padding: 15px; border-radius: 8px; display: none; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; word-break: break-all; }
    .spinner { display: none; width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 1s ease-in-out infinite; margin: 0 auto; }
    @keyframes spin { to { transform: rotate(360deg); } }
    #generatedVideoContainer { display: none; margin-top: 20px; }
    #generatedVideoPlayer { width: 100%; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }
  </style>
</head>
<body>

  <!-- GENERATOR SECTION -->
  <div class="container">
    <h1>Encode Message</h1>
    <p>Generate a Reed-Solomon mathematically protected matrix tracking video.</p>
    <textarea id="encodeText" placeholder="Enter your secret message here..."></textarea>
    <button id="generateBtn" class="btn-success">
      <span id="genBtnText">Generate Video</span>
      <div id="genSpinner" class="spinner"></div>
    </button>
    <div id="generatedVideoContainer">
      <video id="generatedVideoPlayer" controls playsinline></video>
      <a id="downloadLink" download="secret_matrix.mp4" style="text-decoration:none;">
        <button class="btn-success">Download Video</button>
      </a>
    </div>
  </div>

  <!-- DECODER UPLOAD SECTION -->
  <div class="container">
    <h2>Upload to Decode</h2>
    <p>Upload a Matrix video to let the server reconstruct the message using ECC.</p>
    <form id="uploadDecodeForm">
      <input type="file" name="file" accept="video/mp4,video/quicktime,video/webm" required>
      <button type="submit" class="btn-success">Decode Video File</button>
    </form>
    <div id="uploadResult" class="result-box"></div>
  </div>

  <!-- LIVE WEBRTC SCAN SECTION -->
  <div class="container">
    <h2>Live WebRTC Scan</h2>
    <p>Scan directly from your browser camera with server-side Reed-Solomon verification.</p>
    <div id="videoContainer">
      <video id="videoElement" autoplay playsinline></video>
    </div>
    <canvas id="canvasElement" style="display:none;"></canvas>
    <button type="button" id="startCameraBtn">Turn On Camera</button>
    <button type="button" id="startDecodeBtn" class="btn-success" style="display: none;">Start Decoding</button>
    <button type="button" id="stopDecodeBtn" class="btn-warning" style="display: none;">Stop Decoding</button>
    <button type="button" id="stopCameraBtn" class="btn-danger" style="display: none;">Turn Off Camera</button>
    <div id="result" class="result-box"></div>
  </div>

  <script>
    // --- GENERATOR BINDINGS ---
    const generateBtn = document.getElementById('generateBtn');
    const genBtnText = document.getElementById('genBtnText');
    const genSpinner = document.getElementById('genSpinner');
    const encodeText = document.getElementById('encodeText');
    const generatedVideoContainer = document.getElementById('generatedVideoContainer');
    const generatedVideoPlayer = document.getElementById('generatedVideoPlayer');
    const downloadLink = document.getElementById('downloadLink');

    generateBtn.addEventListener('click', async () => {
        const text = encodeText.value.trim();
        if (!text) { alert("Please enter a message to encode."); return; }
        genBtnText.style.display = 'none'; genSpinner.style.display = 'block';
        generateBtn.disabled = true; generatedVideoContainer.style.display = 'none';
        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            if (!response.ok) throw new Error("Generation failed");
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            generatedVideoPlayer.src = url; downloadLink.href = url;
            generatedVideoContainer.style.display = 'block';
        } catch (err) { alert("Error: " + err.message); }
        finally { genBtnText.style.display = 'block'; genSpinner.style.display = 'none'; generateBtn.disabled = false; }
    });

    // --- FILE UPLOAD DECODER ---
    document.getElementById('uploadDecodeForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const box = document.getElementById('uploadResult');
        box.style.display = 'block'; box.innerHTML = "Processing video file frames on server...";
        box.style.color = '#fbbf24'; box.style.background = 'rgba(245, 158, 11, 0.1)';
        const formData = new FormData(e.target);
        try {
            const response = await fetch('/decode', { method: 'POST', body: formData });
            const data = await response.json();
            if(data.success) {
                box.innerHTML = `<strong>Decoded Message:</strong><br><br>${data.text.replace(/\n/g, '<br>')}`;
                box.style.color = '#34d399'; box.style.background = 'rgba(16, 185, 129, 0.1)';
            } else {
                box.innerHTML = `Error: ${data.error}`;
                box.style.color = '#ef4444'; box.style.background = 'rgba(239, 68, 68, 0.1)';
            }
        } catch (err) { box.innerHTML = "Server connection lost."; box.style.color = '#ef4444'; }
    });

    // --- WEBRTC LIVE STREAM SCAN LOGIC ---
    const videoContainer = document.getElementById('videoContainer');
    const video = document.getElementById('videoElement');
    const canvas = document.getElementById('canvasElement');
    const startCameraBtn = document.getElementById('startCameraBtn');
    const startDecodeBtn = document.getElementById('startDecodeBtn');
    const stopDecodeBtn = document.getElementById('stopDecodeBtn');
    const stopCameraBtn = document.getElementById('stopCameraBtn');
    const resultDiv = document.getElementById('result');
    let stream;
    let scanInterval;
    let isDecoding = false;
    let decodedMessageMap = {};
    let expectedTotalChars = null;

    startCameraBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } } 
            });
            video.srcObject = stream; videoContainer.style.display = 'block';
            startCameraBtn.style.display = 'none'; startDecodeBtn.style.display = 'block'; stopCameraBtn.style.display = 'block';
            resultDiv.style.display = 'none';
        } catch (err) { alert("Camera acquisition error: " + err.message); }
    });

    startDecodeBtn.addEventListener('click', () => {
        startDecodeBtn.style.display = 'none'; stopDecodeBtn.style.display = 'block';
        resultDiv.style.display = 'block'; resultDiv.innerHTML = "Initializing tracking matrix components...";
        resultDiv.style.color = '#fbbf24'; resultDiv.style.background = 'rgba(245, 158, 11, 0.1)';
        decodedMessageMap = {}; isDecoding = true; expectedTotalChars = null;
        captureFrameLoop();
    });

    stopDecodeBtn.addEventListener('click', () => {
        isDecoding = false;
        startDecodeBtn.style.display = 'block'; stopDecodeBtn.style.display = 'none';
        const indices = Object.keys(decodedMessageMap).map(Number).sort((a,b)=>a-b);
        if (indices.length > 0) {
            let maxIdx = indices[indices.length - 1];
            let msg = '';
            for(let i = 0; i <= maxIdx; i++) {
                msg += decodedMessageMap[i] !== undefined ? decodedMessageMap[i] : '?';
            }
            resultDiv.innerHTML = "<strong>Assembled Output Stream:</strong><br><br>" + msg.replace(/\n/g, '<br>');
            resultDiv.style.color = '#34d399'; resultDiv.style.background = 'rgba(16, 185, 129, 0.1)';
        } else {
            resultDiv.innerHTML = "Scanning interrupted. No complete ECC segments extracted.";
        }
    });

    stopCameraBtn.addEventListener('click', () => {
        isDecoding = false;
        if (stream) stream.getTracks().forEach(t => t.stop());
        videoContainer.style.display = 'none'; startCameraBtn.style.display = 'block';
        startDecodeBtn.style.display = 'none'; stopDecodeBtn.style.display = 'none'; stopCameraBtn.style.display = 'none';
    });

    async function captureFrameLoop() {
        if (!isDecoding) return;
        await captureFrame();
        if (isDecoding) {
            setTimeout(captureFrameLoop, 50);
        }
    }

    async function captureFrame() {
        if (video.videoWidth === 0 || !isDecoding) return;
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
        
        try {
            const response = await fetch('/decode_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: dataUrl, frame_num: Object.keys(decodedMessageMap).length * 15 }) 
            });
            const data = await response.json();
            if (!isDecoding) return;
            
            if (data.success) {
                if (data.is_end) {
                    expectedTotalChars = data.char_index;
                }
                if (data.char || data.is_end) {
                    // Map character sequence slot inside the frontend layer
                    if (data.char) decodedMessageMap[data.char_index] = data.char;
                }
                let maxIdx = expectedTotalChars !== null ? expectedTotalChars : Math.max(-1, ...Object.keys(decodedMessageMap).map(Number));
                
                let gridHtml = '<div style="display:flex; flex-wrap:wrap; gap:5px; margin-top:15px; justify-content:center; font-family:monospace;">';
                let capturedCount = 0;
                
                let totalExpected = expectedTotalChars !== null ? expectedTotalChars + 1 : maxIdx + 1;
                for(let i = 0; i < totalExpected; i++) {
                    if (decodedMessageMap[i] !== undefined) {
                        capturedCount++;
                        let charDisplay = decodedMessageMap[i].replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        if (charDisplay.trim() === '') charDisplay = '&nbsp;';
                        gridHtml += `<div style="padding: 0 8px; height:30px; background:var(--success); color:white; display:flex; align-items:center; justify-content:center; border-radius:4px; font-weight:bold; box-shadow:0 2px 4px rgba(0,0,0,0.3);">${charDisplay}</div>`;
                    } else {
                        gridHtml += `<div style="width:30px; height:30px; background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.2); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; border-radius:4px; font-weight:bold;">?</div>`;
                    }
                }
                gridHtml += '</div>';
                
                let berHtml = data.ber !== undefined ? `<div style="margin-top:10px; font-size:13px; color:#f59e0b;">Current Frame Environmental Bit Errors: ${data.ber}/168 bits (${((data.ber/168)*100).toFixed(1)}%)</div>` : '';

                let statusText = `Extracting payload stream... Chunks: ${capturedCount}`;
                if (expectedTotalChars !== null) {
                    statusText += ` / ${totalExpected}`;
                    if (capturedCount >= totalExpected) {
                        resultDiv.innerHTML = "<strong>Transmission Complete!</strong><br>" + statusText + gridHtml + berHtml;
                        resultDiv.style.color = '#34d399'; resultDiv.style.background = 'rgba(16, 185, 129, 0.1)';
                        setTimeout(() => stopDecodeBtn.click(), 1000);
                        return;
                    }
                }
                
                resultDiv.innerHTML = statusText + gridHtml + berHtml;
                resultDiv.style.color = '#60a5fa'; resultDiv.style.background = 'rgba(59, 130, 246, 0.1)';
            } else if (data.text) {
                // Ensure we don't overwrite the grid if we just have a temporary alignment message
                if (Object.keys(decodedMessageMap).length === 0) {
                    resultDiv.innerHTML = data.text;
                }
            }
        } catch (err) { console.error("Transmission glitch:", err); }
    }
  </script>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return INDEX_HTML

@app.route('/generate', methods=['POST'])
def generate_endpoint():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "No data string submitted"}), 400
    
    text = data['text']
    filename = f"generated_{uuid.uuid4().hex}.mp4"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Generate video with integrated 5-row Reed-Solomon protection matrix layout
        create_animated_video(text, output_video_path=filepath)
        return send_file(filepath, as_attachment=True, download_name="secret_matrix.mp4", mimetype="video/mp4")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/decode_frame', methods=['POST'])
def decode_frame_endpoint():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"error": "Null frame matrix payload"}), 400
        
    try:
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Inbound frame decoding crash"}), 400
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Configure tracking metrics
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        parameters.adaptiveThreshWinSizeMin = 3
        parameters.adaptiveThreshWinSizeMax = 23
        parameters.adaptiveThreshWinSizeStep = 10
        parameters.minMarkerPerimeterRate = 0.03
        
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        corners, ids, _ = detector.detectMarkers(gray)
        
        if ids is not None and len(ids) == 4:
            ids = ids.flatten()
            corner_map = {int(ids[i]): corners[i][0] for i in range(len(ids))}
            
            if all(i in corner_map for i in [0, 1, 2, 3]):
                src_pts = np.float32([corner_map[0][0], corner_map[1][1], corner_map[2][2], corner_map[3][3]])
                
                measured_w = np.linalg.norm(corner_map[1][1] - corner_map[0][0])
                measured_h = (np.linalg.norm(corner_map[3][3] - corner_map[0][0]) + np.linalg.norm(corner_map[2][2] - corner_map[1][1])) / 2.0
                
                target_w = 150 + (8 * 120) + 150
                target_h = int(target_w * (measured_h / measured_w)) if measured_w > 0 else 1260
                dst_pts = np.float32([[0, 0], [target_w, 0], [target_w, target_h], [0, target_h]])
                
                # Execute spatial homography un-warping mapping on the COLOR frame
                matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                warped_img = cv2.warpPerspective(img, matrix, (target_w, target_h))
                cropped_grid = warped_img[150:target_h-150, 150:target_w-150]
                
                scanned_color_grid = decode_image(cropped_grid, grid_width=8, block_size=120)
                
                if scanned_color_grid is not None:
                    # PASS DIRECTLY TO REED-SOLOMON CORRECTION WRAPPER
                    corrected_chunk, char_idx, ber = decode_color_grid(scanned_color_grid)
                    if corrected_chunk is not None:
                        is_end = '\x04' in corrected_chunk
                        if is_end:
                            corrected_chunk = corrected_chunk.split('\x04')[0]
                        return jsonify({
                            "success": True, 
                            "char": corrected_chunk, 
                            "char_index": char_idx,
                            "is_end": is_end,
                            "ber": ber
                        })
                    else:
                        return jsonify({"success": False, "text": "Correcting burst transmission noise..."})
                else:
                    return jsonify({"success": False, "text": "Parsing color matrix grid areas..."})
            else:
                return jsonify({"success": False, "text": "Sorting orientation boundary anchors..."})
        else:
            found_count = len(ids) if ids is not None else 0
            return jsonify({"success": False, "text": f"Align tracking frame ({found_count}/4 markers found)"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/decode', methods=['POST'])
def decode_file_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "Missing payload block file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename header"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        from video_decoder import decode_video
        # Process the entire video file on the server using our updated Reed-Solomon workflow
        _, final_decoded_text = decode_video(filepath, grid_width=8, block_size=120, headless=True)
        
        if final_decoded_text:
            return jsonify({"success": True, "text": final_decoded_text})
        else:
            return jsonify({"error": "Error count exceeded correction capabilities or tracking lost."}), 400
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    print("Starting Reed-Solomon Secure Communication Server on https://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc')