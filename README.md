# Vortex - Encoder & Decoder (Reed-Solomon)

This project is a secure communication server that encodes secret messages into a Matrix-style video using Reed-Solomon Error Correction Codes (ECC) and allows you to decode these messages either via file upload or live WebRTC stream.

## Prerequisites

- **Python 3.7+**
- A webcam (for the live scanning feature)

## Installation

1. Open a terminal (or command prompt) and navigate to the project directory:
   ```bash
   cd "c:\Users\Admin\Desktop\final final final"
   ```

2. Install the required Python packages. You can do this by running:
   ```bash
   pip install Flask numpy opencv-python reedsolo pyOpenSSL cryptography
   ```
   *(Note: `pyOpenSSL` and `cryptography` are required because the Flask server runs with an `adhoc` SSL context to enable secure WebRTC camera access in the browser).*

## Running the Server

1. Start the Flask server by running:
   ```bash
   python server.py
   ```

2. The server will start on `https://0.0.0.0:5000`.

3. Open your web browser and navigate to:
   **[https://localhost:5000](https://localhost:5000)** or **[https://127.0.0.1:5000](https://127.0.0.1:5000)**

   > **Important:** Because the server uses an ad-hoc (self-signed) SSL certificate, your browser will likely show a warning that the connection is not private. You will need to click on "Advanced" and choose to "Proceed to localhost (unsafe)" to view the application. HTTPS is required by modern browsers to allow webcam access.

## Features

- **Encode Message**: Type a text message to generate a `.mp4` video containing Reed-Solomon mathematically protected matrix codes.
- **Upload to Decode**: Upload an encoded `.mp4` video to decode the message.
- **Live WebRTC Scan**: Use your webcam to scan a generated video playing on another screen. The server will actively track the matrix, perform Reed-Solomon verification, and reconstruct the text.
