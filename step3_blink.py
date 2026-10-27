import time, cv2, mediapipe as mp
from mediapipe.tasks import python as P
from mediapipe.tasks.python import vision
L = [33, 160, 158, 133, 153, 144]
R = [362, 385, 387, 263, 373, 380]
TH, MIN = 0.20, 3          # nguong EAR, so frame lien tiep
def ear(p, i):
    a, b, c, d, e, f = (p[k] for k in i)
    g = lambda u, v: ((u[0]-v[0])**2 + (u[1]-v[1])**2) ** 0.5
    return (g(b, f) + g(c, e)) / (2 * g(a, d) + 1e-6)
o = vision.FaceLandmarkerOptions(
    base_options=P.BaseOptions(model_asset_path="models/face_landmarker.task"),
    running_mode=vision.RunningMode.VIDEO, num_faces=1)
m = vision.FaceLandmarker.create_from_options(o)
cap = cv2.VideoCapture(0)
t0 = time.time(); last = -1; below = 0; blinks = 0
while True:
    ok, f = cap.read()
    if not ok: break
    f = cv2.flip(f, 1); h, w = f.shape[:2]
    ts = int((time.time() - t0) * 1000)
    if ts <= last: ts = last + 1
    last = ts
    r = m.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB)), ts)
    if r.face_landmarks:
        p = [(int(q.x * w), int(q.y * h)) for q in r.face_landmarks[0]]
        e = max(ear(p, L), ear(p, R))   # max: ca 2 mat phai duoi nguong
        if e < TH:
            below += 1
            if below == MIN: blinks += 1
        else: below = 0
        cv2.putText(f, f"EAR {e:.3f}   BLINK {blinks}", (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 0, 255) if e < TH else (0, 255, 0), 2)
    cv2.imshow("Buoc 3 - Blink", f)
    if cv2.waitKey(1) & 0xFF in (27, ord("q")): break
cap.release(); cv2.destroyAllWindows(); m.close()
print("blinks:", blinks)
