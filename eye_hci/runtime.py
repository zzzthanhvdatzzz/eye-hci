"""Single camera worker; local profile persistence and OS action adapter."""
from dataclasses import asdict
from pathlib import Path
import json
import math
import threading
import time
from .core import Calibration, Controller, Profile, Sample

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / 'profiles' / 'default.json'
EL = [33,160,158,133,153,144]
ER = [362,385,387,263,373,380]

def ear(p, indices):
    a,b,c,d,e,f = (p[k] for k in indices)
    distance = lambda u,v: math.hypot(u[0]-v[0],u[1]-v[1])
    return (distance(b,f)+distance(c,e))/(2*distance(a,d)+1e-9)

def ratio(p, iris, corners):
    x = sum(p[k][0] for k in iris)/5
    y = sum(p[k][1] for k in iris)/5
    a,b = (p[k] for k in corners)
    width = abs(b[0]-a[0])+1e-9
    return (x-min(a[0],b[0]))/width, (y-(a[1]+b[1])/2)/width

class Runtime:
    def __init__(self, camera=0):
        self.lock = threading.RLock()
        self.controller = Controller()
        self.calibration = None
        self.thread = None
        self.stop_event = threading.Event()
        self.camera = camera
        self.real = False
        self.py = None
        self.jpeg = None
        self.state = dict(running=False, status='STOPPED', message='Bật camera để bắt đầu.',
                          face=False, x=0, y=0, left=1, right=1, fps=0,
                          direction='THANG', progress=0, events=[], profile=False, real=False)
        if PROFILE.exists():
            try:
                self.controller.set_profile(Profile(**json.loads(PROFILE.read_text())).validate())
                self.state['profile'] = True
                self.state['message'] = 'Đã tải hồ sơ. Bật camera, nhìn thẳng rồi nhấn Tiếp tục.'
            except (ValueError, TypeError, OSError):
                self.state['message'] = 'Hồ sơ cũ không hợp lệ; hãy hiệu chuẩn lại.'

    def snapshot(self):
        with self.lock:
            s = dict(self.state)
            s['events'] = list(self.state['events'])
            s['real'] = self.real
            if self.calibration:
                s['calibration'] = dict(index=self.calibration.index, total=7,
                    instruction=self.calibration.step[1], progress=self.calibration.progress(time.monotonic()),
                    error=self.calibration.error)
            else:
                s['calibration'] = None
            return s

    def command(self, action, value=None):
        with self.lock:
            c = self.controller
            if action == 'start':
                if self.thread and self.thread.is_alive():
                    return
                self.stop_event.clear()
                c.paused = True
                c.reset()
                self.state.update(running=True, status='STARTING', message='Đang mở camera…')
                self.thread = threading.Thread(target=self.run, daemon=True)
                self.thread.start()
            elif action == 'stop':
                self.stop_event.set()
                c.paused = True
                c.reset()
                self.calibration = None
                self.state.update(status='STOPPED', message='Đã dừng điều khiển.')
            elif action == 'pause':
                c.paused = True
                c.reset()
                self.calibration = None
                self.state.update(status='PAUSED', message='Đã tạm dừng.')
            elif action == 'resume':
                if not self.state['running'] or not self.state['face'] or not c.profile or self.calibration:
                    raise ValueError('Cần camera, khuôn mặt và hồ sơ hiệu chuẩn hoàn tất.')
                c.paused = False
                c.reset()
                self.state.update(status='ACTIVE', message='Nhìn thẳng để sẵn sàng nhận lệnh.')
            elif action == 'calibrate':
                if not self.state['running']:
                    raise ValueError('Bật camera trước khi hiệu chuẩn.')
                c.paused = True
                c.reset()
                self.calibration = Calibration()
                self.state.update(status='CALIBRATING', message='Làm theo hướng dẫn. Mỗi bước khoảng 3 giây.')
            elif action == 'real':
                if not isinstance(value, bool):
                    raise ValueError('Chế độ không hợp lệ.')
                if value and self.py is None:
                    import pyautogui
                    pyautogui.FAILSAFE = True
                    self.py = pyautogui
                self.real = value
                c.paused = True
                c.reset()
                self.state.update(status='PAUSED', message='Đã đổi chế độ. Nhấn Tiếp tục khi sẵn sàng.')
            else:
                raise ValueError('Lệnh không hợp lệ.')

    def emit(self, cmd):
        if self.real:
            actions = {'NEXT': lambda: self.py.press('right'), 'PREV': lambda: self.py.press('left'),
                       'SCROLL UP': lambda: self.py.scroll(3), 'SCROLL DOWN': lambda: self.py.scroll(-3),
                       'SELECT': lambda: self.py.click()}
            actions[cmd]()
        self.state['events'] = [dict(command=cmd, real=self.real,
            time=time.strftime('%H:%M:%S'))] + self.state['events'][:11]

    def run(self):
        cap = landmarker = None
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python as P
            from mediapipe.tasks.python import vision
            model = ROOT / 'models' / 'face_landmarker.task'
            if not model.exists():
                raise ValueError('Thiếu models/face_landmarker.task. Xem hướng dẫn README.')
            landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
                base_options=P.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO, num_faces=1))
            cap = cv2.VideoCapture(self.camera)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
            if not cap.isOpened():
                raise ValueError('Không mở được camera. Kiểm tra quyền Camera và chỉ số --camera.')
            last_ts = -1
            previous = time.monotonic()
            smooth = None
            with self.lock:
                if not self.stop_event.is_set():
                    self.state.update(status='PAUSED', message='Camera sẵn sàng. Hiệu chuẩn hoặc dùng hồ sơ đã lưu.')
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    raise ValueError('Không đọc được camera. Hãy dừng và bật lại.')
                frame = cv2.flip(frame,1)
                h,w = frame.shape[:2]
                now = time.monotonic()
                dt = now-previous
                previous = now
                ts = max(last_ts+1,int(now*1000))
                last_ts = ts
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),ts)
                sample = None
                if result.face_landmarks:
                    p = [(q.x*w,q.y*h) for q in result.face_landmarks[0]]
                    ax,ay = ratio(p,range(468,473),(33,133))
                    bx,by = ratio(p,range(473,478),(362,263))
                    sample = Sample((ax+bx)/2,(ay+by)/2,ear(p,EL),ear(p,ER))
                small = cv2.resize(frame,(640,360))
                encoded_ok, encoded = cv2.imencode('.jpg',small,[cv2.IMWRITE_JPEG_QUALITY,75])
                with self.lock:
                    if self.stop_event.is_set():
                        break
                    if encoded_ok:
                        self.jpeg = encoded.tobytes()
                    self.state.update(face=sample is not None, fps=round(1/max(dt,0.001)))
                    c = self.controller
                    if sample is None:
                        smooth = None
                        c.feed(None,now)
                        if self.calibration:
                            self.calibration.interrupt()
                        self.state.update(status='NO_FACE', progress=0, left=1, right=1,
                            message='Không thấy mặt. Thao tác đang chờ đã được xóa.')
                        continue
                    if self.calibration:
                        # Calibration uses raw float samples, isolated from smoothing history.
                        try:
                            profile = self.calibration.feed(sample,now)
                            if profile:
                                PROFILE.parent.mkdir(exist_ok=True)
                                temp = PROFILE.with_suffix('.tmp')
                                temp.write_text(json.dumps(asdict(profile),indent=2))
                                temp.replace(PROFILE)
                                c.set_profile(profile)
                                self.calibration = None
                                smooth = None
                                self.state.update(profile=True, status='PAUSED',
                                    message='Hiệu chuẩn thành công, đã lưu hồ sơ. Mở mắt rồi nhấn Tiếp tục.')
                            else:
                                self.state.update(status='CALIBRATING', message=self.calibration.step[1])
                        except ValueError as exc:
                            self.calibration = None
                            self.state.update(status='PAUSED', message=str(exc))
                    else:
                        self.state.update(status='PAUSED' if c.paused else 'ACTIVE')
                        if self.state['message'].startswith('Không thấy mặt'):
                            self.state['message'] = 'Đã thấy mặt. Nhìn thẳng để nhận lệnh mới.'
                    profile = c.profile
                    opened_l = profile.open_left if profile else 0.30
                    opened_r = profile.open_right if profile else 0.30
                    closed_l = profile.closed_left if profile else 0.03
                    closed_r = profile.closed_right if profile else 0.03
                    self.state.update(left=max(0,min(1,(sample.left-closed_l)/max(.01,opened_l-closed_l))),
                        right=max(0,min(1,(sample.right-closed_r)/max(.01,opened_r-closed_r))))
                    # Time-aware smoothing: same response at different camera frame rates.
                    if smooth is None or dt > .25:
                        smooth = (sample.x,sample.y)
                    alpha = 1-math.exp(-dt/0.08)
                    smooth = tuple(old+alpha*(new-old) for old,new in zip(smooth,(sample.x,sample.y)))
                    filtered = Sample(*smooth,sample.left,sample.right)
                    if profile:
                        dx,dy = smooth[0]-profile.center_x,smooth[1]-profile.center_y
                        self.state.update(x=max(-1,min(1,dx/(profile.right if dx>0 else profile.left)/2)),
                                          y=max(-1,min(1,dy/(profile.down if dy>0 else profile.up)/2)))
                    else:
                        self.state.update(x=max(-1,min(1,(sample.x-.5)*6)), y=max(-1,min(1,sample.y*8)))
                    cmd = c.feed(filtered,now)
                    if cmd:
                        self.emit(cmd)
                    self.state.update(direction=c.direction, progress=c.progress)
        except Exception as exc:
            with self.lock:
                self.controller.paused = True
                self.controller.reset()
                self.calibration = None
                self.state.update(status='ERROR', message=f'{type(exc).__name__}: {exc}')
        finally:
            if cap is not None:
                cap.release()
            if landmarker is not None:
                landmarker.close()
            with self.lock:
                self.jpeg = None
                self.state.update(running=False, face=False, progress=0)
