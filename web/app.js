 'use strict';
let wallpaperUrl;
async function loadWallpaper(){
  try{
    const response=await fetch('/api/wallpaper');
    if(!response.ok){const data=await response.json();throw new Error(data.error||'Không đọc được hình nền.');}
    const url=URL.createObjectURL(await response.blob());
    document.documentElement.style.setProperty('--desktop-wallpaper',`url("${url}")`);
    document.documentElement.dataset.wallpaper='ready';
    if(wallpaperUrl)URL.revokeObjectURL(wallpaperUrl);
    wallpaperUrl=url;
  }catch(error){
    document.documentElement.dataset.wallpaper='unavailable';
    document.getElementById('notice').textContent=error.message+' Đang dùng nền dự phòng.';
  }
}
// Theme changes are independent of camera state and persist on this browser.
(function setupTheme(){
  const systemTheme=matchMedia('(prefers-color-scheme: dark)');
  const buttons=[...document.querySelectorAll('[data-theme-choice]')];
  function apply(choice){
    document.documentElement.dataset.preference=choice;
    if(choice==='system' && !window.irisNativeGlass)loadWallpaper();
    if(window.irisNativeGlass){
      document.documentElement.dataset.nativeGlass='true';
      window.pywebview?.api?.glass?.(choice==='system');
    }
    document.documentElement.dataset.theme=choice==='system'?(systemTheme.matches?'dark':'light'):choice;
    buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.themeChoice===choice)));
  }
  buttons.forEach(button=>button.addEventListener('click',()=>{
    const choice=button.dataset.themeChoice;
    try{localStorage.setItem('iris-theme',choice);}catch(_){}
    apply(choice);
  }));
  systemTheme.addEventListener('change',()=>{
    if(document.documentElement.dataset.preference==='system')apply('system');
  });
  apply(document.documentElement.dataset.preference||'dark');
})();
const $ = id => document.getElementById(id);
const directionNames = {THANG:'Nhìn thẳng',TRAI:'Liếc trái',PHAI:'Liếc phải',LEN:'Liếc lên',XUONG:'Liếc xuống'};
const statusNames = {STOPPED:'Camera đang tắt',STARTING:'Đang kết nối…',PAUSED:'Đang tạm dừng',ACTIVE:'Đang nhận lệnh',CALIBRATING:'Đang hiệu chuẩn',NO_FACE:'Không thấy khuôn mặt',ERROR:'Cần kiểm tra'};
let state = null, lastStep = -1, lastCal = false, busy = false;
async function control(action,value) {
  if (busy) return;
  busy = true;
  try {
    const r = await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json','X-Eye-HCI':'1'},body:JSON.stringify({action,value})});
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Không thực hiện được thao tác.');
    await refresh();
  } catch(e) { $('notice').textContent=e.message; $('notice').classList.add('error'); }
  finally {busy=false;}
}
for (const action of ['start','stop','pause','resume','calibrate']) $(action).onclick=()=>control(action);
$('real').onchange=e=>control('real',e.target.checked);
document.addEventListener('keydown',e=>{if(e.key==='Escape')control('pause');});
// A short local tone announces each calibration step, including eyes-closed completion.
let audio;
document.addEventListener('pointerdown',()=>{try{audio ||= new (window.AudioContext||window.webkitAudioContext)();audio.resume();}catch(_){}},{once:true});
function tone(){try{const o=audio.createOscillator(),g=audio.createGain();o.connect(g);g.connect(audio.destination);o.frequency.value=660;g.gain.setValueAtTime(.045,audio.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.16);o.start();o.stop(audio.currentTime+.17);}catch(_){}}
async function refresh(){
  const r=await fetch('/api/state'); if(!r.ok)throw new Error('Không đọc được trạng thái.');
  const s=await r.json(); state=s;
  $('status').textContent=statusNames[s.status]||s.status;
  $('profile').textContent=s.profile?'Hồ sơ cá nhân đã sẵn sàng':'Chưa có hồ sơ hiệu chuẩn';
  $('notice').textContent=s.message; $('notice').classList.toggle('error',s.status==='ERROR');
  $('fps').textContent=s.running?`${s.fps} FPS`:'— FPS';
  $('face-dot').classList.toggle('active',s.face);
  $('video-label').textContent=s.face?'● CAMERA TRỰC TIẾP':s.running?'ĐANG TÌM KHUÔN MẶT':'CAMERA ĐANG TẮT';
  $('start').disabled=s.running; $('stop').disabled=!s.running;
  $('calibrate').disabled=!s.running||s.status==='STARTING';
  $('resume').disabled=!s.running||!s.face||!s.profile||!!s.calibration||s.status==='ACTIVE';
  $('pause').disabled=!s.running;
  $('real').checked=s.real;
  $('mode-label').textContent=s.real?'Phát lệnh vào ứng dụng đang mở':'Đang mô phỏng lệnh';
  $('direction').textContent=s.face?(directionNames[s.direction]||'Nhìn thẳng'):'Chờ khuôn mặt';
  $('left-eye').value=s.left; $('right-eye').value=s.right;
  $('dwell-progress').style.width=`${s.progress*100}%`; $('dwell-label').textContent=`${Math.round(s.progress*100)}%`;
  const cal=s.calibration;
  if(cal){
    if(cal.index!==lastStep)tone();
    $('instruction').textContent=cal.instruction;
    $('cal-count').textContent=`BƯỚC ${cal.index+1} / ${cal.total}`;
    $('cal-help').textContent='Giữ tư thế ổn định. Chờ tiếng báo trước khi chuyển bước.';
    $('cal-progress').style.width=`${cal.progress*100}%`;
    $('cal-error').textContent=cal.error||'Mất dấu khuôn mặt sẽ bắt đầu lại bước hiện tại.';
    $('target').textContent=['◎','←','→','↑','↓','◉','—'][cal.index];
    lastStep=cal.index;
  }else{
    if(lastCal)tone();
    lastStep=-1;
    $('instruction').textContent=s.profile?'Đã lưu hồ sơ ánh nhìn':'Làm quen với ánh nhìn của bạn';
    $('cal-count').textContent=s.profile?'ĐÃ HIỆU CHUẨN':'7 BƯỚC';
    $('cal-help').textContent='Nhìn giữa, trái, phải, lên, xuống; sau đó mở và nhắm mắt. Giữ đầu thẳng trong suốt quá trình.';
    $('cal-progress').style.width=s.profile?'100%':'0%';
    $('cal-error').textContent='Hiệu chuẩn lại nếu thay đổi người dùng, vị trí ngồi hoặc camera.';
    $('target').textContent=s.profile?'✓':'✧';
  }
  lastCal=!!cal;
  [...$('steps').children].forEach((el,i)=>{el.classList.toggle('active',!!cal&&i===cal.index);el.classList.toggle('done',cal?i<cal.index:s.profile);});
  const events=$('events');
  if(s.events.length){events.replaceChildren(...s.events.map(e=>{const row=document.createElement('div');row.className='event';const name=document.createElement('strong');name.textContent=e.command;const info=document.createElement('span');info.textContent=`${e.real?'THẬT':'MÔ PHỎNG'} · ${e.time}`;row.append(name,info);return row;}));}
}
async function poll(){try{await refresh();}catch(e){$('notice').textContent='Mất kết nối Python. Kiểm tra cửa sổ Terminal.';$('notice').classList.add('error');state=null;}setTimeout(poll,100);}
poll();
let frameUrl;
async function cameraLoop(){
  try{if(state?.running){const r=await fetch('/api/frame');if(r.status===200){const blob=await r.blob();const url=URL.createObjectURL(blob);$('camera').src=url;$('camera').hidden=false;$('camera-placeholder').hidden=true;if(frameUrl)URL.revokeObjectURL(frameUrl);frameUrl=url;}}else{$('camera').hidden=true;$('camera-placeholder').hidden=false;}}catch(_){}
  setTimeout(cameraLoop,100);
}
cameraLoop();

// Actual 3D ray/sphere intersections in WebGL. No downloaded model, library or CDN.
const canvas=$('eyes'),gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:false});
if(!gl){$('webgl-fallback').hidden=false;}else{
const vs=`attribute vec2 pos;void main(){gl_Position=vec4(pos,0.,1.);}`;
const fs=`precision highp float;
uniform vec2 resolution;uniform vec2 gaze;uniform vec2 openness;
vec3 shadeEye(vec3 n,vec3 local,float opening){
  float yaw=gaze.x*.50;float pitch=gaze.y*.38;
  vec3 r=vec3(cos(yaw)*n.x-sin(yaw)*n.z,n.y,sin(yaw)*n.x+cos(yaw)*n.z);
  r=vec3(r.x,cos(pitch)*r.y+sin(pitch)*r.z,-sin(pitch)*r.y+cos(pitch)*r.z);
  float rad=length(r.xy);float angle=atan(r.y,r.x);
  vec3 col=vec3(.91,.95,.93);
  float fiber=sin(angle*73.+rad*50.)*.5+sin(angle*131.-rad*30.)*.3;
  vec3 iris=mix(vec3(.10,.26,.24),vec3(.36,.61,.49),smoothstep(.07,.32,rad));
  iris+=fiber*.055;
  iris*=1.-.5*smoothstep(.29,.35,rad);
  if(r.z>0.){
    col=mix(col,iris,1.-smoothstep(.338,.353,rad));
    col=mix(col,vec3(.012,.033,.034),1.-smoothstep(.105,.12,rad));
  }
  float light=.56+.44*max(0.,dot(n,normalize(vec3(-.5,.8,1.4))));
  col*=light;
  col+=vec3(1.)*pow(max(0.,dot(n,normalize(vec3(-.3,.48,1.)))),95.)*.9;
  col+=vec3(.65,.85,.78)*pow(max(0.,dot(n,normalize(vec3(.5,-.3,1.)))),50.)*.15;
  float lid=abs(local.y+.015)-opening*.64;
  float skin=smoothstep(-.025,.025,lid);
  vec3 lidColor=vec3(.64,.76,.70)*(.67+.33*max(0.,dot(n,normalize(vec3(-.4,.9,1.)))));
  lidColor+=vec3(.08)*pow(max(0.,n.z),12.);
  col=mix(col,lidColor,skin);
  float seam=(1.-smoothstep(.006,.021,abs(local.y+.015)))*(1.-smoothstep(.01,.14,opening));
  col=mix(col,vec3(.30,.45,.39),seam*.6);
  return col;
}
void main(){
 vec2 uv=(gl_FragCoord.xy*2.-resolution)/resolution.y;
 uv*=1.9;
 vec3 ro=vec3(uv,4.);vec3 rd=vec3(0.,0.,-1.);
 vec3 color=vec3(0.);float alpha=0.;
 for(int i=0;i<2;i++){
   float cx=i==0?-.94:.94;
   vec3 center=vec3(cx,.16,0.);vec3 oc=ro-center;
   float radius=.77;float b=dot(oc,rd);float c=dot(oc,oc)-radius*radius;float disc=b*b-c;
   if(disc>0.){float t=-b-sqrt(disc);vec3 local=ro+t*rd-center;vec3 n=local/radius;
     color=shadeEye(n,local,i==0?openness.x:openness.y);alpha=smoothstep(0.,.015,disc);
   }else if(alpha==0.){
     vec2 shadow=(uv-vec2(cx,-.74))/vec2(.8,.13);
     float a=exp(-dot(shadow,shadow)*2.)*.10;
     if(a>alpha){color=vec3(.19,.35,.29);alpha=a;}
   }
 }
 gl_FragColor=vec4(color,alpha);
}`;
function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
try{
const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('WebGL link failed');gl.useProgram(program);
const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
const loc=gl.getAttribLocation(program,'pos');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
const res=gl.getUniformLocation(program,'resolution'),gazeLoc=gl.getUniformLocation(program,'gaze'),openLoc=gl.getUniformLocation(program,'openness');
let x=0,y=0,l=1,r=1,prev=performance.now();
function draw(now){
 const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);const w=Math.round(rect.width*dpr),h=Math.round(rect.height*dpr);
 if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
 const a=1-Math.exp(-(now-prev)/45);prev=now;
 const live=state?.face; x+=((live?state.x:0)-x)*a;y+=((live?state.y:0)-y)*a;
 // Mirrored camera: anatomical right eye appears on the viewer's left.
 l+=((live?state.right:1)-l)*a;r+=((live?state.left:1)-r)*a;
 gl.uniform2f(res,w,h);gl.uniform2f(gazeLoc,x,y);gl.uniform2f(openLoc,l,r);gl.drawArrays(gl.TRIANGLES,0,6);requestAnimationFrame(draw);
}requestAnimationFrame(draw);
}catch(e){$('webgl-fallback').hidden=false;console.error(e);}
}


// Native window functions are available only in the desktop launcher.
(function setupWindow(){
  let compact=false;
  const button=document.getElementById('compact-window');
  const minimize=document.getElementById('minimize-window');
  function ready(){
    document.documentElement.dataset.native='true';
    minimize.hidden=false;
    if(window.irisNativeGlass){
      document.documentElement.dataset.nativeGlass='true';
      window.pywebview.api.glass(document.documentElement.dataset.preference==='system');
    }
  }
  window.addEventListener('pywebviewready',ready);
  if(window.pywebview?.api)ready();
  button.addEventListener('click',async()=>{
    if(!window.pywebview?.api){
      document.getElementById('notice').textContent='Để dùng cửa sổ nổi, chạy: python step6_hci.py --desktop. Kéo cửa sổ bằng thanh tiêu đề.';
      return;
    }
    try{
      const next=!compact;
      await window.pywebview.api.compact(next);
      compact=next;
      document.documentElement.classList.toggle('compact',compact);
      button.textContent=compact?'⤢ Mở rộng':'▣ Thu gọn';
      button.setAttribute('aria-pressed',String(compact));
    }catch(error){document.getElementById('notice').textContent=String(error);}
  });
  minimize.addEventListener('click',()=>window.pywebview?.api.minimize());
})();
