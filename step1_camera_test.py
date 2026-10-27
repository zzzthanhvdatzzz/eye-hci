"""Bước 1 — kiểm tra camera trên macOS.

Chạy:
    cd ~/eye-hci
    source .venv/bin/activate
    python step1_camera_test.py

Kết quả mong đợi:
    OK camera 0: 1280x720, ~30.0 FPS
    Đã lưu snapshot.png

Nếu cửa sổ đen / không thấy gì:
    → System Settings > Privacy & Security > Camera > bật cho Terminal (hoặc iTerm)
      rồi THOÁT HẲN Terminal và mở lại (đóng tab là chưa đủ).
"""
import os
import sys
import time

import cv2

CAM_INDEX = int(os.environ.get("CAM_INDEX", "0"))
WIDTH, HEIGHT = 1280, 720
SNAP = "snapshot.png"


def open_camera(index: int) -> cv2.VideoCapture:
    # macOS: backend mặc định (AVFoundation) ổn định hơn, không cần chỉ định.
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    return cap


cap = open_camera(CAM_INDEX)
if not cap.isOpened():
    sys.exit(
        f"KHÔNG mở được camera index {CAM_INDEX}.\n"
        "  1) macOS: System Settings > Privacy & Security > Camera → bật cho Terminal/iTerm,\n"
        "     sau đó THOÁT HẲN app Terminal rồi mở lại.\n"
        "  2) Máy có nhiều camera: chạy lại với  CAM_INDEX=1 python step1_camera_test.py"
    )

# Bỏ 10 khung đầu: webcam thường trả khung tối/ nhiễu lúc vừa bật.
for _ in range(10):
    cap.read()

ok, frame = cap.read()
if not ok or frame is None:
    cap.release()
    sys.exit("Mở được camera nhưng không đọc được khung hình (có app khác đang chiếm camera?)")

# Đo FPS thật trong 2 giây
t0 = time.time()
n = 0
while time.time() - t0 < 2.0:
    ok, f = cap.read()
    if ok:
        n += 1
fps = n / (time.time() - t0)

h, w = frame.shape[:2]
brightness = float(frame.mean())
cv2.imwrite(SNAP, frame)
cap.release()

print(f"OK camera {CAM_INDEX}: {w}x{h}, ~{fps:.1f} FPS")
print(f"Độ sáng trung bình: {brightness:.1f}/255", end="  ")
if brightness < 15:
    print("← QUÁ TỐI: kiểm tra nắp che webcam / bật đèn phòng")
else:
    print("← ổn")
print(f"Đã lưu {SNAP} — mở lên xem có thấy mặt cậu không.")
