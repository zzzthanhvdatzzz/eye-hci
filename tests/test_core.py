import unittest
from eye_hci.core import Controller, Sample, Profile, Calibration

def profile():
    return Profile(.5,0,.06,.06,.02,.03,.16,.17,.3,.32,.02,.02)
def sample(x=.5,y=0,closed=False):
    return Sample(x,y,.02 if closed else .3,.02 if closed else .32)

class Gestures(unittest.TestCase):
    def active(self):
        c=Controller(); c.set_profile(profile()); c.paused=False; c.feed(sample(),0); return c
    def test_no_commands_without_profile_or_while_paused(self):
        c=Controller()
        for i in range(100): self.assertIsNone(c.feed(sample(.8),i/30))
        c.set_profile(profile())
        for i in range(100): self.assertIsNone(c.feed(sample(.8),i/30))
    def test_fps_independence(self):
        for fps in (15,30,60):
            c=self.active(); events=[]
            for i in range(1,fps+1):
                cmd=c.feed(sample(.8),i/fps)
                if cmd: events.append((i/fps,cmd))
            self.assertEqual(len(events),1)
            self.assertEqual(events[0][1],'NEXT')
            self.assertLessEqual(abs(events[0][0]-.4),2/fps)
    def test_cooldown_eventually_fires_after_dwell(self):
        c=self.active(); c.last_fire=.2
        result=[]
        for i in range(1,31):
            cmd=c.feed(sample(.8),i/30)
            if cmd: result.append(cmd)
        self.assertEqual(result,['NEXT'])
    def test_face_loss_cancels_hold_and_requires_neutral(self):
        c=self.active()
        for i in range(1,10): c.feed(sample(.8),i/30)
        c.feed(None,.31)
        for i in range(10,40): self.assertIsNone(c.feed(sample(.8),i/30))
        c.feed(sample(),1.34)
        result=[c.feed(sample(.8),1.34+i/30) for i in range(1,21)]
        self.assertEqual([v for v in result if v],['NEXT'])
    def test_blink_duration_and_no_gaze_while_closed(self):
        c=self.active()
        for i in range(1,11): self.assertIsNone(c.feed(sample(.8,closed=True),i/30))
        self.assertEqual(c.feed(sample(),.37),'SELECT')
    def test_short_and_long_blinks_do_not_click(self):
        for duration in (.1,.7):
            c=self.active()
            for i in range(1,round(duration*60)+1): c.feed(sample(closed=True),i/60)
            self.assertIsNone(c.feed(sample(),duration+1/60))
    def test_face_loss_cancels_blink(self):
        c=self.active();c.feed(sample(closed=True),.03);c.feed(None,.2)
        self.assertIsNone(c.feed(sample(),.35))
    def test_stall_does_not_complete_dwell(self):
        c=self.active();c.feed(sample(.8),.03)
        self.assertIsNone(c.feed(sample(.8),1.0))
    def test_paused_reset(self):
        c=self.active();c.feed(sample(.8),.03);c.paused=True;c.feed(sample(.8),.2)
        c.paused=False
        for i in range(7,30): self.assertIsNone(c.feed(sample(.8),i/30))

class CalibrationTests(unittest.TestCase):
    def test_calibration_and_interruption(self):
        cal=Calibration();cal.feed(sample(),0);cal.feed(sample(),1.5);cal.interrupt()
        self.assertEqual(cal.samples,[]);self.assertIsNone(cal.started)
        values=[sample(),sample(.36),sample(.64),sample(y=-.06),sample(y=.08),sample(),sample(closed=True)]
        now=2.;p=None
        for s in values:
            for i in range(90):
                result=cal.feed(s,now+i/30)
                if result: p=result;break
                if cal.started is None: break
            now+=3.1
        self.assertIsNotNone(p)
        self.assertAlmostEqual(p.left,.07)
        self.assertAlmostEqual(p.up,.03)
        self.assertEqual(p.direction(.64,0),'PHAI')
    def test_invalid_profiles(self):
        p=profile();p.up=float('nan')
        with self.assertRaises(ValueError):p.validate()
    def test_insufficient_range_rejected(self):
        cal=Calibration();cal.results={k:sample() for k in ('center','left','right','up','down','open','closed')}
        with self.assertRaises(ValueError):cal.build()

if __name__=='__main__':unittest.main()
