import sys
import time, cv2, mediapipe as mp
from mediapipe.tasks import python as P
from mediapipe.tasks.python import vision
LI=range(468,473); RI=range(473,478); LC=(33,133); RC=(362,263)
EL=[33,160,158,133,153,144]; ER=[362,385,387,263,373,380]
REAL = "--real" in sys.argv
py = None
if REAL:
    import pyautogui as py
    py.FAILSAFE = True
A,AV=0.35,0.32; DZX,DZU,DZD=0.08,0.02,0.035
ETH,DW,CD=0.20,12,0.5
CMD={"PHAI":"NEXT","TRAI":"PREV","LEN":"SCROLL UP","XUONG":"SCROLL DOWN"}
def ear(p,i):
    a,b,c,d,e,f=(p[k] for k in i)
    g=lambda u,v:((u[0]-v[0])**2+(u[1]-v[1])**2)**.5
    return (g(b,f)+g(c,e))/(2*g(a,d)+1e-6)
def rt(p,ir,c):
    ix=sum(p[k][0] for k in ir)/5; iy=sum(p[k][1] for k in ir)/5
    x1,x2=p[c[0]][0],p[c[1]][0]; y0=(p[c[0]][1]+p[c[1]][1])/2; w=abs(x2-x1)+1e-6
    return (ix-min(x1,x2))/w,(iy-y0)/w
def cls(dx,dy):
    dz=DZD if dy>0 else DZU
    if abs(dx)<DZX and abs(dy)<dz: return "THANG"
    if abs(dx)/DZX>=abs(dy)/dz: return "PHAI" if dx>0 else "TRAI"
    return "XUONG" if dy>0 else "LEN"
def act(cmd):
    print("[ACT] " if REAL else "[DRY] ", cmd)
    if not REAL: return
    {"NEXT": lambda: py.press("right"),
     "PREV": lambda: py.press("left"),
     "SCROLL UP": lambda: py.scroll(3),
     "SCROLL DOWN": lambda: py.scroll(-3),
     "SELECT": lambda: py.click()}[cmd]()
o=vision.FaceLandmarkerOptions(base_options=P.BaseOptions(
  model_asset_path="models/face_landmarker.task"),
  running_mode=vision.RunningMode.VIDEO,num_faces=1)
lm=vision.FaceLandmarker.create_from_options(o)
cap=cv2.VideoCapture(0); t0=time.time(); last=-1
g=v=c0=c1=0.0; n=0; bel=0; hold=""; hn=0; fire=-9; armed=True
while True:
    ok,f=cap.read()
    if not ok: break
    f=cv2.flip(f,1); h,w2=f.shape[:2]
    ts=int((time.time()-t0)*1000)
    if ts<=last: ts=last+1
    last=ts
    r=lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
      data=cv2.cvtColor(f,cv2.COLOR_BGR2RGB)),ts)
    now=time.time(); d="THANG"
    if r.face_landmarks:
        p=[(int(q.x*w2),int(q.y*h)) for q in r.face_landmarks[0]]
        ax,ay=rt(p,LI,LC); bx,by=rt(p,RI,RC); mx,my=(ax+bx)/2,(ay+by)/2
        if n==0: g,v=mx,my
        g=A*mx+(1-A)*g; v=AV*my+(1-AV)*v; n+=1
        if n==45: c0,c1=g,v
        dx,dy=g-c0,v-c1; d=cls(dx,dy)
        el=ear(p,EL); er2=ear(p,ER)
        if max(el,er2)<ETH:
            bel+=1
        else:
            if 7<=bel<=15 and now-fire>CD:
                fire=now; act("SELECT"); print(f"[CMD] SELECT (blink {bel}f)")
            bel=0
        if d=="THANG": hold=""; hn=0; armed=True
        elif d==hold:
            hn+=1
            if hn==DW and armed and now-fire>CD: fire=now; hn=0; armed=False; act(CMD[d]); print("[CMD]",CMD[d],d)
        else: hold=d; hn=1
        cv2.putText(f,f"{d} dx{dx:+.2f} dy{dy:+.2f}",(15,50),
          cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)
    cv2.imshow("Buoc 6",f)
    k=cv2.waitKey(1)&0xFF
    if k in (27,ord("q")): break
    if k==ord("c") and r.face_landmarks and n>30: c0,c1=g,v
cap.release(); cv2.destroyAllWindows(); lm.close()