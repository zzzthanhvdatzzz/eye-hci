"""Bước 2 — MediaPipe FaceLandmarker: 478 điểm mốc + khoanh 2 mắt + EAR.

Chạy:
    cd ~/eye-hci
    source .venv/bin/activate
    python step2_landmarks.py

Phím: ESC hoặc q để thoát.

Yêu cầu: models/face_landmarker.task (đã tải ở Bước 5 của hướng dẫn).
"""
import os
import sys
import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_PATH = os.path.join("models", "face_landmarker.task")
CAM_INDEX = int(os.environ.get("CAM_INDEX", "0"))

# --- Chỉ số landmark của MediaPipe Face Mesh -----------------------------
# Thứ tự 6 điểm quanh mỗi mắt: p1 góc trái, p2..p5 viền trên/dưới, p6 góc phải
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
# Tâm mắt (góc mắt) để vẽ khung
LEFT_EYE_ALL = [33, 133, 159, 145]
RIGHT_EYE_ALL = [362, 263, 386, 374]


def ear(points, idx):
    """Eye Aspect Ratio: (|p2-p6| + |p3-p5|) / (2*|p1-p4|)."""
    p1, p2, p3, p4, p5, p6 = (points[i] for i in idx)
    v1 = ((p2[0] - p6[0]) ** 2 + (p2[1] - p6[1]) ** 2) ** 0.5
    v2 = ((p3[0] - p5[0]) ** 2 + (p3[1] - p5[1]) ** 2) ** 0.5
    h = ((p1[0] - p4[0]) ** 2 + (p1[1] - p4[1]) ** 2) ** 0.5
    return 0.0 if h == 0 else (v1 + v2) / (2.0 * h)


def bbox(points, idx, pad=6):
    xs = [points[i][0] for i in idx]
    ys = [points[i][1] for i in idx]
    return (max(0, min(xs) - pad), max(0, min(ys) - pad),
            max(xs) + pad, max(ys) + pad)


if not os.path.exists(MODEL_PATH):
    sys.exit(f"Thiếu model: {MODEL_PATH}\n"
             "Tải bằng:\n"
             "  mkdir -p models\n"
             "  curl -L -o models/face_landmarker.task "
             "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")

options = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
if not cap.isOpened():
    sys.exit(f"Không mở được camera {CAM_INDEX}. "
             "macOS: System Settings > Privacy & Security > Camera → bật cho Terminal rồi mở lại.")

t_base = time.time()
t_fps = t_base
last_ts = -1
fps, last_fps, frames = 0.0, 0.0, 0

print("Đang chạy... ESC/q để thoát.")
while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)          # lật gương cho tự nhiên
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    ts_ms = int((time.time() - t_base) * 1000)
    if ts_ms <= last_ts:
        ts_ms = last_ts + 1
    last_ts = ts_ms
    result = landmarker.detect_for_video(mp_image, ts_ms)

    if result.face_landmarks:
        lms = result.face_landmarks[0]
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]

        # 478 điểm
        for (x, y) in pts:
            cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

        # 2 mắt + EAR
        for idx, color, name in ((LEFT_EYE, (0, 220, 255), "L"),
                                 (RIGHT_EYE, (255, 180, 0), "R")):
            x1, y1, x2, y2 = bbox(pts, idx)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"EAR{name} {ear(pts, idx):.2f}", (x1, max(18, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(frame, f"landmarks: {len(pts)}", (15, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Không thấy mặt", (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    frames += 1
    elapsed = time.time() - t_fps
    if elapsed >= 0.5:
        last_fps = frames / elapsed
        frames, t_fps = 0, time.time()
    cv2.putText(frame, f"FPS {last_fps:.1f}", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow("Buoc 2 - Landmarks + EAR", frame)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
        break

cap.release()
cv2.destroyAllWindows()
landmarker.close()
