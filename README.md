# Eye HCI - dieu khien may tinh bang mat

Webcam -> MediaPipe FaceLandmarker (478 diem) -> EAR (chop mat) +
ti le tam trong den (huong nhin) -> lenh dieu khien.

## Chay
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    mkdir -p models
    curl -L -o models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
    python step6_hci.py            # dry-run
    python step6_hci.py --real     # dieu khien that

Nhin thang ~2 giay de tu hieu chuan (frame 45). ESC de thoat.
macOS: cap quyen Camera + Accessibility cho Terminal/VS Code.

## Ban do lenh
- PHAI -> NEXT (phim phai)
- TRAI -> PREV (phim trai)
- LEN -> SCROLL UP
- XUONG -> SCROLL DOWN
- chop 2 mat 7-15 frame -> SELECT (click)

## Thong so do duoc
- Webcam 1280x720, ~30 FPS
- EAR: mo 0.30, nham 0.02
- Gaze ngang +-0.17; doc: xuong +0.08, len -0.04
- Nguong: DZX 0.08, DZU 0.02, DZD 0.035
- Wink recall 9/10, false positive 0/30 s

## Gioi han
- Rule-based + hieu chuan, KHONG huan luyen model
- Nguong theo tung nguoi, nguoi khac phai hieu chuan lai
- Quay dau lam sai gaze (chua co head-pose check)
- Gaze doc bien do nho, can lien mat ro hon
