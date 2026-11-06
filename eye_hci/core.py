"""Camera-independent calibration and temporal gesture recognition.

All timestamps are monotonic seconds, supplied by the caller for replay/testing.
"""
from dataclasses import dataclass, asdict
import math
import statistics

DIRECTIONS = {'PHAI': 'NEXT', 'TRAI': 'PREV', 'LEN': 'SCROLL UP', 'XUONG': 'SCROLL DOWN'}
STEPS = [('center', 'Nhìn thẳng, mở mắt'), ('left', 'Liếc sang trái, giữ đầu thẳng'),
         ('right', 'Liếc sang phải, giữ đầu thẳng'), ('up', 'Liếc lên trên'),
         ('down', 'Liếc xuống dưới'), ('open', 'Nhìn thẳng, mở mắt tự nhiên'),
         ('closed', 'Nhắm cả hai mắt và giữ đến khi nghe tiếng báo')]

@dataclass
class Sample:
    x: float
    y: float
    left: float
    right: float

@dataclass
class Profile:
    center_x: float
    center_y: float
    left: float
    right: float
    up: float
    down: float
    ear_left: float
    ear_right: float
    open_left: float
    open_right: float
    closed_left: float
    closed_right: float
    version: int = 1

    def validate(self):
        values = asdict(self)
        if self.version != 1 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values.values()):
            raise ValueError('Hồ sơ không hợp lệ.')
        if any(not 0.003 <= v <= 2 for v in (self.left, self.right, self.up, self.down)):
            raise ValueError('Ngưỡng hướng nhìn không hợp lệ.')
        for closed, threshold, opened in ((self.closed_left, self.ear_left, self.open_left),
                                           (self.closed_right, self.ear_right, self.open_right)):
            if not 0 <= closed < threshold < opened <= 2:
                raise ValueError('Ngưỡng mở/nhắm mắt không hợp lệ.')
        return self

    def direction(self, x, y):
        dx, dy = x - self.center_x, y - self.center_y
        nx = dx / (self.right if dx > 0 else self.left)
        ny = dy / (self.down if dy > 0 else self.up)
        if abs(nx) < 1 and abs(ny) < 1:
            return 'THANG'
        return ('PHAI' if nx > 0 else 'TRAI') if abs(nx) >= abs(ny) else ('XUONG' if ny > 0 else 'LEN')

class Calibration:
    SETTLE = 1.3
    COLLECT = 1.5

    def __init__(self):
        self.index = 0
        self.started = None
        self.samples = []
        self.results = {}
        self.error = ''

    @property
    def step(self):
        return STEPS[self.index]

    def interrupt(self):
        self.started = None
        self.samples = []

    def progress(self, now):
        return 0 if self.started is None else min(1, (now-self.started)/(self.SETTLE+self.COLLECT))

    def feed(self, sample, now):
        if self.started is None:
            self.started = now
        elapsed = now-self.started
        if elapsed >= self.SETTLE:
            self.samples.append(sample)
        if elapsed < self.SETTLE+self.COLLECT:
            return None
        if len(self.samples) < 8:
            self.error = 'Quá ít mẫu. Giữ tư thế để thử lại bước này.'
            self.interrupt()
            return None
        fields = ('x', 'y', 'left', 'right')
        med = Sample(*(statistics.median(getattr(s, f) for s in self.samples) for f in fields))
        # Reject shaky gaze; closed eyes need only stable EAR, not stable iris.
        checked = fields if self.step[0] != 'closed' else ('left', 'right')
        if any(statistics.median(abs(getattr(s,f)-getattr(med,f)) for s in self.samples) >
               (0.035 if f in ('x', 'y') else 0.04) for f in checked):
            self.error = 'Mẫu chưa ổn định. Giữ đầu yên và thử lại bước này.'
            self.interrupt()
            return None
        self.results[self.step[0]] = med
        self.error = ''
        if self.index < len(STEPS)-1:
            self.index += 1
            self.interrupt()
            return None
        return self.build()

    def build(self):
        r = self.results
        c, o, closed = r['center'], r['open'], r['closed']
        spans = (c.x-r['left'].x, r['right'].x-c.x, c.y-r['up'].y, r['down'].y-c.y)
        if any(v < 0.008 for v in spans):
            raise ValueError('Chưa phân biệt được các hướng. Hiệu chuẩn lại, liếc rõ hơn và giữ đầu thẳng.')
        if min(o.left-closed.left, o.right-closed.right) < 0.04:
            raise ValueError('Chưa phân biệt rõ mở/nhắm cả hai mắt. Hãy hiệu chuẩn lại.')
        return Profile(c.x, c.y, *(max(0.003, v*0.5) for v in spans),
                       (o.left+closed.left)/2, (o.right+closed.right)/2,
                       o.left, o.right, closed.left, closed.right).validate()

class Controller:
    DWELL = 0.4
    BLINK_MIN = 0.23
    BLINK_MAX = 0.5
    COOLDOWN = 0.5

    def __init__(self):
        self.profile = None
        self.paused = True
        self.last_fire = -math.inf
        self.last_sample = None
        self.reset()

    def reset(self):
        self.hold = ''
        self.hold_since = None
        self.closed_since = None
        self.armed = False  # Requires neutral, open eyes after any interruption.
        self.progress = 0
        self.direction = 'THANG'

    def set_profile(self, profile):
        self.profile = profile.validate()
        self.paused = True
        self.reset()

    def feed(self, sample, now):
        gap = self.last_sample is not None and now-self.last_sample > 0.25
        self.last_sample = now
        if gap:
            self.reset()
        if sample is None or self.paused or self.profile is None:
            self.reset()
            return None
        p = self.profile
        closed = sample.left < p.ear_left and sample.right < p.ear_right
        partly_closed = sample.left < p.ear_left or sample.right < p.ear_right
        if partly_closed:
            self.hold, self.hold_since, self.progress = '', None, 0
            if closed and self.closed_since is None and self.armed:
                self.closed_since = now
            elif not closed:
                self.closed_since = None
            return None
        if self.closed_since is not None:
            duration = now-self.closed_since
            self.closed_since = None
            if self.BLINK_MIN <= duration <= self.BLINK_MAX and self.armed and now-self.last_fire >= self.COOLDOWN:
                self.last_fire = now
                self.armed = False
                return 'SELECT'
        self.direction = p.direction(sample.x, sample.y)
        if self.direction == 'THANG':
            self.armed = True
            self.hold, self.hold_since, self.progress = '', None, 0
            return None
        if self.direction != self.hold:
            self.hold, self.hold_since = self.direction, now
        self.progress = min(1, (now-self.hold_since)/self.DWELL) if self.armed else 0
        if self.armed and now-self.hold_since >= self.DWELL and now-self.last_fire >= self.COOLDOWN:
            self.last_fire = now
            self.armed = False
            return DIRECTIONS[self.direction]
        return None
