import { useState } from 'react';
import { api } from '../lib/api';
import { Button, Field } from './ui';
import { moduleCaptureConfig } from '../lib/moduleSettings';

function hsvAt(image, event) {
  const rect=image.getBoundingClientRect();
  const x=Math.max(0,Math.min(image.naturalWidth-1,Math.floor((event.clientX-rect.left)*image.naturalWidth/rect.width)));
  const y=Math.max(0,Math.min(image.naturalHeight-1,Math.floor((event.clientY-rect.top)*image.naturalHeight/rect.height)));
  const canvas=document.createElement('canvas'); canvas.width=canvas.height=1;
  const ctx=canvas.getContext('2d');ctx.drawImage(image,x,y,1,1,0,0,1,1);
  const [r,g,b]=Array.from(ctx.getImageData(0,0,1,1).data).map(v=>v/255);
  const max=Math.max(r,g,b),min=Math.min(r,g,b),d=max-min;
  let h=0;
  if(d)h=max===r ? ((g-b)/d)%6 : max===g ? (b-r)/d+2 : (r-g)/d+4;
  return {xy:[x,y],hsv:[Math.round(((h*60+360)%360)/2)%180,Math.round(max ? d/max*255 : 0),Math.round(max*255)]};
}

function ranges([h,s,v],white=false) {
  if(white)return [{lower:[0,0,Math.max(0,v-60)],upper:[179,Math.min(255,s+55),255]}];
  const lowS=Math.max(35,s-65),lowV=Math.max(25,v-80),lo=h-10,hi=h+10;
  if(lo<0)return [{lower:[0,lowS,lowV],upper:[hi,255,255]},{lower:[180+lo,lowS,lowV],upper:[179,255,255]}];
  if(hi>179)return [{lower:[lo,lowS,lowV],upper:[179,255,255]},{lower:[0,lowS,lowV],upper:[hi-180,255,255]}];
  return [{lower:[lo,lowS,lowV],upper:[hi,255,255]}];
}

export function CameraSetup({ moduleId,cameras=['side','top'],config,setConfig,advanced,onAdvanced,status,disabled,onReset }) {
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [role,setRole]=useState(()=>moduleId===2 && status.frame?.preview_camera!=='top' ? 'marker_tip' : 'cue_ball');
  const [frozen,setFrozen]=useState(null);
  const frame=status.frame || {};
  const preview=frame.preview_only && cameras.includes(frame.preview_camera) ? frame : null;
  const current=frozen || preview;
  const usesTop=cameras.includes('top');
  const selectable=moduleId!==1;
  const roles=current?.preview_camera==='side'
    ? (moduleId===2 ? [['marker_tip','สีมาร์กเกอร์ด้านปลายคิว'],['marker_back','สีมาร์กเกอร์ด้านท้ายคิว'],...(usesTop ? [['center','ศูนย์กลางลูกขาว']] : [])] : [])
    : [['cue_ball','สีลูกขาว'],...(moduleId===3 ? [['target_ball','สีลูกแดง']] : [])];
  function extra() {const value=JSON.parse(advanced);if(!value || Array.isArray(value) || typeof value!=='object')throw new Error('การตั้งค่าต้องเป็น JSON object');return value;}
  function apply(patch) {onAdvanced(JSON.stringify({...extra(),...patch},null,2));onReset();}
  async function action(task) {setBusy(true);setError('');setMessage('');try{await task()}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function previewCamera(camera) {
    setFrozen(null);setRole(camera==='side' ? 'marker_tip' : 'cue_ball');onReset();await api('/cameras/preview',{camera,config:moduleCaptureConfig(moduleId,config,advanced)});
  }
  function pick(event) {
    if(disabled || busy || !current || !selectable)return;
    try {
      const picked=hsvAt(event.currentTarget,event),settings=extra(),side=current.preview_camera==='side';
      if(role==='center') {
        if(!side)throw new Error('เลือกศูนย์กลางลูกขาวจากภาพด้านข้าง');
        apply({side_ball_center:picked.xy,side_image_size:current.image_size});
      } else if(role.startsWith('marker')) {
        if(!side)throw new Error('เลือกสีมาร์กเกอร์จากภาพด้านข้าง');
        const choices=ranges(picked.hsv);
        if(choices.length!==1)throw new Error('สีนี้คร่อมช่วงแดง เลือกมาร์กเกอร์สีอื่น เช่น น้ำเงิน/เหลือง');
        const markers=settings.cue_markers?.length===2 ? [...settings.cue_markers] : [
          {lower:[90,90,60],upper:[130,255,255],min_area:10},
          {lower:[18,90,60],upper:[38,255,255],min_area:10}];
        markers[role==='marker_tip' ? 0 : 1]={...choices[0],min_area:10};
        apply({cue_markers:markers});
      } else {
        if(side)throw new Error('เลือกสีลูกจากภาพด้านบน');
        const colours=settings.ball_colours || {
          cue_ball:[{lower:[0,0,160],upper:[179,75,255]}],
          target_ball:[{lower:[0,110,70],upper:[10,255,255]},{lower:[170,110,70],upper:[179,255,255]}]};
        apply({ball_detector:'HSV',ball_colours:{...colours,[role]:ranges(picked.hsv,role==='cue_ball')}});
      }
      setMessage(`เลือกแล้ว: พิกัด ${picked.xy.join(', ')} / HSV ${picked.hsv.join(', ')} ตรวจผลจริงอีกครั้งหลังนำไปใช้`);
    } catch(e){setError(e.message)}
  }
  return <section className="panel camera-setup"><h2>ตั้งค่ากล้อง M{moduleId}</h2>
    <p className="muted">{moduleId===1 ? 'เปิดภาพด้านข้างและจัดให้เห็นจุดร่างกายครบ แล้วกดเริ่มตรวจท่าได้เลย' : 'เปิดภาพ หยุดภาพแล้วเลือกสีจากกลางวัตถุที่ไม่มีแสงสะท้อน'}</p>
    <fieldset disabled={disabled || busy}>
      <details><summary>แก้ปัญหากล้อง / ความละเอียด / DSHOW</summary>
      <div className="filters">
        {[['capture_width','ความกว้างภาพ',1280],['capture_height','ความสูงภาพ',720],['capture_fps','FPS ที่ร้องขอ',30]].map(([key,label,value])=><Field key={key} label={label}><input type="number" value={config[key] ?? value} onChange={e=>{setConfig({...config,[key]:Number(e.target.value)});onReset()}}/></Field>)}
        <Field label="วิธีเปิดกล้อง"><select value={config.camera_backend || 'AUTO'} onChange={e=>{setConfig({...config,camera_backend:e.target.value});onReset()}}><option>AUTO</option><option>DSHOW</option><option>MSMF</option></select></Field>
      </div>
      <label className="check"><input type="checkbox" checked={!!config.camera_mjpeg} onChange={e=>{setConfig({...config,camera_mjpeg:e.target.checked});onReset()}}/>ร้องขอ MJPEG สำหรับเว็บแคมที่รองรับ</label>
      </details>
      <div className="actions">{cameras.map(camera=><Button key={camera} type="button" onClick={()=>action(()=>previewCamera(camera))}>{camera==='side' ? 'ดูภาพดิบด้านข้าง' : 'ดูภาพดิบด้านบน'}</Button>)}<Button type="button" secondary onClick={()=>action(async()=>{await api('/cameras/stop',{});setFrozen(null);onReset()})}>ปิดกล้อง</Button></div>
      {current?.image && <><p>ภาพ{current.preview_camera==='side' ? 'ด้านข้าง' : 'ด้านบน'} · ขนาดจริง {current.image_size?.join(' × ')} px</p>
        {selectable && <div className="actions"><Button type="button" secondary onClick={()=>setFrozen({...preview})} disabled={!preview}>หยุดภาพเพื่อเลือกจุด</Button><Button type="button" secondary onClick={()=>setFrozen(null)}>กลับภาพสด</Button>
        <a className="button secondary" download={`camera-${current.preview_camera}.jpg`} href={`data:image/jpeg;base64,${current.image}`}>ดาวน์โหลดภาพสอบเทียบ</a></div>}
        {selectable && roles.length>0 && <Field label="สิ่งที่จะเลือกจากภาพ"><select value={role} onChange={e=>setRole(e.target.value)}>{roles.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></Field>}
        <img className="setup-preview" src={`data:image/jpeg;base64,${current.image}`} alt={selectable ? 'คลิกเลือกสีหรือจุดบนภาพกล้องดิบ' : 'ภาพกล้องด้านข้าง'} onClick={selectable ? pick : undefined}/>
      </>}
      {moduleId===2 && usesTop && <p className="muted">ศูนย์กลางลูกในภาพข้างเป็นจุดตั้งต้นคงที่ ต้องจัดลูกเดิมทุกครั้ง ค่าแนวเล็งไม่ใช่จุดสัมผัสหัวคิวจริง</p>}
    </fieldset>{busy && <p role="status">กำลังเปิดกล้อง/ดำเนินการ…</p>}{error && <p className="error" role="alert">{error}</p>}{message && <p className="notice">{message}</p>}
  </section>
}
