import os
from datetime import datetime
from flask import Flask, render_template, Response, request, redirect, url_for, send_file, flash
import cv2, numpy as np, face_recognition
import config

# Initialize app
app = Flask(__name__)
app.secret_key = 'replace_with_secure_key'

# Ensure folders and attendance file exist
os.makedirs(config.reference_folder, exist_ok=True)
if not os.path.exists(config.attendance_file):
    with open(config.attendance_file, 'w') as f:
        f.write('Name,Time\n')

# Load known faces
def load_known_faces():
    names, encodings = [], []
    for fname in os.listdir(config.reference_folder):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(config.reference_folder, fname)
            img = cv2.imread(path)
            if img is None: continue
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            enc = face_recognition.face_encodings(rgb)
            if enc:
                names.append(os.path.splitext(fname)[0])
                encodings.append(enc[0])
    return names, encodings

# Initialize global encodings
class_names, known_encodings = load_known_faces()

def refresh_known_faces():
    global class_names, known_encodings
    class_names, known_encodings = load_known_faces()

# Attendance logging
def mark_attendance(name):
    if name == 'Unknown':
        return
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = open(config.attendance_file).read().splitlines()
    existing = {line.split(',')[0] for line in lines[1:]}
    if name not in existing:
        with open(config.attendance_file, 'a') as f:
            f.write(f"{name},{now}\n")

# Video stream generator
def generate_frames(camera_idx, tol):
    cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locs)
            for enc, loc in zip(encs, locs):
                dists = face_recognition.face_distance(known_encodings, enc)
                name = 'Unknown'
                if dists.size and np.min(dists) < tol:
                    idx = np.argmin(dists)
                    name = class_names[idx]
                    mark_attendance(name)
                # draw box
                y1, x2, y2, x1 = [v*4 for v in loc]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, name, (x1, y2+25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        cap.release()

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(config.reference_folder, file.filename)
            file.save(path)
            flash(f"Uploaded {file.filename}", 'success')
            refresh_known_faces()
        else:
            flash('Invalid file type', 'danger')
        return redirect(url_for('index'))
    return render_template('index.html', tolerance=config.tolerance, camera=config.default_camera)

@app.route('/video_feed')
def video_feed():
    cam = int(request.args.get('cam', config.default_camera))
    tol = float(request.args.get('tol', config.tolerance))
    return Response(generate_frames(cam, tol), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance')
def attendance():
    lines = open(config.attendance_file).read().splitlines()[1:]
    records = [line.split(',') for line in lines]
    return render_template('attendance.html', records=records)

@app.route('/download')
def download():
    return send_file(config.attendance_file, as_attachment=True)

@app.route('/clear')
def clear():
    open(config.attendance_file, 'w').write('Name,Time\n')
    flash('Cleared attendance log', 'info')
    return redirect(url_for('attendance'))

if __name__ == '__main__':
    app.run(debug=True)