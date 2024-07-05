import time
import threading
from flask import Flask, Response, render_template_string, jsonify, request
import cv2

app = Flask(__name__)

# HTML content as a string
html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Phone Camera Feed</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; background-color: #282c34; color: white; }
        h1 { color: #61dafb; }
        .controls { margin: 20px; display: flex; justify-content: center; align-items: center; flex-wrap: wrap; }
        .control-item { margin: 10px; }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; border: none; border-radius: 5px; background-color: #61dafb; color: #282c34; width: 180px; }
        button:hover { background-color: #21a1f1; }
        img { width: 70%; max-width: 800px; margin-top: 20px; border: 2px solid #61dafb; }
        .icon { width: 20px; height: 20px; vertical-align: middle; margin-right: 5px; }
    </style>
    <script>
        function toggleCamera() {
            fetch('/toggle_camera')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('camera-button').innerText = data.status ? 'Turn OFF' : 'Turn ON';
                    document.getElementById('camera-button').className = data.status ? 'btn-on' : 'btn-off';
                });
        }

        function rotateCamera() {
            fetch('/rotate_camera')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('rotate-button').innerText = `Rotate (${data.rotation})`;
                });
        }

        function mirrorCamera() {
            fetch('/mirror_camera')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('mirror-button').innerText = data.mirror ? 'Turn OFF' : 'Turn ON';
                    document.getElementById('mirror-button').className = data.mirror ? 'btn-on' : 'btn-off';
                });
        }
    </script>
</head>
<body>
    <h1>Phone Camera Feed</h1>
    <div class="controls">
        <div class="control-item">
            <button id="camera-button" class="btn-on" onclick="toggleCamera()">Turn OFF</button>
        </div>
        <div class="control-item">
            <button id="rotate-button" onclick="rotateCamera()">Rotate (None)</button>
        </div>
        <div class="control-item">
            <button id="mirror-button" class="btn-off" onclick="mirrorCamera()">Turn ON</button>
        </div>
    </div>
    <img src="{{ url_for('video_feed') }}" id="video-feed">
</body>
</html>
'''

camera_on = True
rotation_state = 0  # 0: None, 1: 90 degrees, 2: 180 degrees, 3: 270 degrees
mirror_state = False

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
    global rotation_state
    rotation_state = (rotation_state + 1) % 4
    rotation = "None" if rotation_state == 0 else f"{rotation_state * 90} "
    return jsonify(rotation=rotation)

@app.route('/mirror_camera')
def mirror_camera():
    global mirror_state
    mirror_state = not mirror_state
    return jsonify(mirror=mirror_state)

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
            if rotation_state != 0:
                angle = rotation_state * 90
                (h, w) = frame.shape[:2]
                center = (w / 2, h / 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                frame = cv2.warpAffine(frame, M, (w, h))
            if mirror_state:
                frame = cv2.flip(frame, 1)  # Mirror horizontally
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
