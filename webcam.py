import time
import threading
from flask import Flask, Response, render_template_string, jsonify
import cv2

app = Flask(__name__)

# HTML content as a string
html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Phone Camera Feed</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background-color: #f0f0f0; }
        h1 { color: #333; }
        .controls { margin: 20px; }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; }
        img { width: 80%; max-width: 720px; }
    </style>
    <script>
        function toggleCamera() {
            fetch('/toggle_camera')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('camera-status').innerText = data.status ? 'ON' : 'OFF';
                });
        }

        function rotateCamera(direction) {
            fetch('/rotate_camera?direction=' + direction)
                .then(response => response.json())
                .then(data => {
                    // No action needed on the client side
                });
        }
    </script>
</head>
<body>
    <h1>Phone Camera Feed</h1>
    <div class="controls">
        <button onclick="toggleCamera()">Toggle Camera</button>
        <button onclick="rotateCamera('vertical')">Rotate Vertical</button>
        <button onclick="rotateCamera('horizontal')">Rotate Horizontal</button>
        <p>Camera is <span id="camera-status">ON</span></p>
    </div>
    <img src="{{ url_for('video_feed') }}" id="video-feed">
</body>
</html>
'''

camera_on = True
rotate_vertical = False
rotate_horizontal = False

@app.route('/')
def index():
    return render_template_string(html_template)

@app.route('/toggle_camera')
def toggle_camera():
    global camera_on
    camera_on = not camera_on
    return jsonify(status=camera_on)

@app.route('/rotate_camera')
def rotate_camera():
    global rotate_vertical, rotate_horizontal
    direction = request.args.get('direction')
    if direction == 'vertical':
        rotate_vertical = not rotate_vertical
    elif direction == 'horizontal':
        rotate_horizontal = not rotate_horizontal
    return jsonify(success=True)

class VideoCamera:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.frame = None
        self.grabbed = False
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            if camera_on:
                self.grabbed, self.frame = self.cap.read()

    def get_frame(self):
        frame = self.frame
        if frame is not None:
            if rotate_vertical:
                frame = cv2.flip(frame, 0)  # Flip vertically
            if rotate_horizontal:
                frame = cv2.flip(frame, 1)  # Flip horizontally
        return self.grabbed, frame

camera = VideoCamera('http://192.168.1.38:8080/video')

def gen(camera):
    while True:
        grabbed, frame = camera.get_frame()
        if not grabbed:
            break

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        time.sleep(0.03)  # Adjust the sleep time as needed

@app.route('/video_feed')
def video_feed():
    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
