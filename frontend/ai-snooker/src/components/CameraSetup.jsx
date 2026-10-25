import { useState } from 'react';
import { api } from '../lib/api';
import { Button, Field } from './ui';

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

export function CameraSetup({ config,setConfig,advanced,onAdvanced,status,disabled,onReset,accountKey }) {
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [role,setRole]=useState('cue_ball');
  const [frozen,setFrozen]=useState(null);
  const frame=status.frame || {};
  const preview=frame.preview_only ? frame : null;
  const current=frozen || preview;
  function extra() {const value=JSON.parse(advanced);if(!value || Array.isArray(value) || typeof value!=='object')throw new Error('การตั้งค่าต้องเป็น JSON object');return value;}
  function apply(patch) {onAdvanced(JSON.stringify({...extra(),...patch},null,2));onReset();}
  async function action(task) {setBusy(true);setError('');setMessage('');try{await task()}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function previewCamera(camera) {
    setFrozen(null);onReset();await api('/cameras/preview',{camera,config:{...extra(),...config}});
  }
  function pick(event) {
    if(disabled || busy || !current)return;
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
  function saved() {return JSON.stringify({version:1,config,advanced:extra()},null,2)}
  return <section className="panel camera-setup"><h2>ตั้งค่ากล้องสำหรับโต๊ะจริง</h2>
    <p className="muted">ดูภาพดิบก่อนสอบเทียบ เลือกสีจากกลางวัตถุที่ไม่มีแสงสะท้อน แล้วกดตรวจความพร้อมเมื่อเสร็จ</p>
    <fieldset disabled={disabled || busy}>
      <div className="filters">
        {[['capture_width','ความกว้างภาพ',1280],['capture_height','ความสูงภาพ',720],['capture_fps','FPS ที่ร้องขอ',30]].map(([key,label,value])=><Field key={key} label={label}><input type="number" value={config[key] ?? value} onChange={e=>{setConfig({...config,[key]:Number(e.target.value)});onReset()}}/></Field>)}
        <Field label="วิธีเปิดกล้อง"><select value={config.camera_backend || 'AUTO'} onChange={e=>{setConfig({...config,camera_backend:e.target.value});onReset()}}><option>AUTO</option><option>DSHOW</option><option>MSMF</option></select></Field>
      </div>
      <label className="check"><input type="checkbox" checked={!!config.camera_mjpeg} onChange={e=>{setConfig({...config,camera_mjpeg:e.target.checked});onReset()}}/>ร้องขอ MJPEG สำหรับเว็บแคมที่รองรับ</label>
      <div className="actions"><Button type="button" onClick={()=>action(()=>previewCamera('side'))}>ดูภาพดิบด้านข้าง</Button><Button type="button" onClick={()=>action(()=>previewCamera('top'))}>ดูภาพดิบด้านบน</Button><Button type="button" secondary onClick={()=>action(async()=>{await api('/cameras/stop',{});setFrozen(null);onReset()})}>ปิดกล้อง</Button></div>
      {current?.image && <><p>ภาพ{current.preview_camera==='side' ? 'ด้านข้าง' : 'ด้านบน'} · ขนาดจริง {current.image_size?.join(' × ')} px</p>
        <div className="actions"><Button type="button" secondary onClick={()=>setFrozen({...preview})} disabled={!preview}>หยุดภาพเพื่อเลือกจุด</Button><Button type="button" secondary onClick={()=>setFrozen(null)}>กลับภาพสด</Button>
        <a className="button secondary" download={`camera-${current.preview_camera}.jpg`} href={`data:image/jpeg;base64,${current.image}`}>ดาวน์โหลดภาพสอบเทียบ</a></div>
        <Field label="สิ่งที่จะเลือกจากภาพ"><select value={role} onChange={e=>setRole(e.target.value)}><option value="cue_ball">สีลูกขาว (ด้านบน)</option><option value="target_ball">สีลูกแดง (ด้านบน)</option><option value="marker_tip">สีมาร์กเกอร์ด้านปลายคิว (ด้านข้าง)</option><option value="marker_back">สีมาร์กเกอร์ด้านท้ายคิว (ด้านข้าง)</option><option value="center">ศูนย์กลางลูกขาว (ด้านข้าง)</option></select></Field>
        <img className="setup-preview" src={`data:image/jpeg;base64,${current.image}`} alt="คลิกเลือกสีหรือจุดบนภาพกล้องดิบ" onClick={pick}/>
      </>}
      <div className="filters">{[['ball_min_area','พื้นที่ลูกต่ำสุด (px²)',50],['ball_max_area','พื้นที่ลูกสูงสุด (px²)',5000],['ball_max_jump','ระยะเปลี่ยนตำแหน่งสูงสุดต่อเฟรม (px)',120],['motion_threshold','ระยะเริ่มเคลื่อนลูก (หน่วยโต๊ะ)',0],['contact_tolerance','ค่าคลาดเคลื่อนระยะสัมผัส (หน่วยโต๊ะ)',0]].map(([key,label,defaultValue])=>{let settings={};try{settings=extra()}catch{/* shown on apply */}return <Field key={key} label={label}><input type="number" min="0" step="any" value={settings[key] ?? defaultValue} onChange={e=>{try{apply({[key]:Number(e.target.value)})}catch(err){setError(err.message)}}}/></Field>})}</div>
      <label className="check"><input type="checkbox" checked={(()=>{try{return !!extra().delivery_ball_timing}catch{return false}})()} onChange={e=>{try{apply({delivery_ball_timing:e.target.checked})}catch(err){setError(err.message)}}}/>M2 ใช้สองกล้องเพื่อประมาณ Follow-through และแนวเล็ง (ต้องตั้งระยะเริ่มเคลื่อนลูกมากกว่าศูนย์)</label>
      <p className="muted">ศูนย์กลางลูกในภาพด้านข้างเป็นจุดตั้งต้นคงที่ ต้องจัดลูกเดิมทุกครั้ง ค่าแนวเล็งไม่ใช่จุดสัมผัสหัวคิวจริง สีและค่าพารามิเตอร์ที่คลิกเป็นค่าเริ่มต้นสำหรับปรับจากการนำร่อง</p>
      <div className="actions"><Button type="button" secondary onClick={()=>action(async()=>{localStorage.setItem(accountKey,saved());setMessage('บันทึกการตั้งค่าในเบราว์เซอร์นี้แล้ว')})}>บันทึกค่าบนเครื่องนี้</Button><Button type="button" secondary onClick={()=>action(async()=>{const savedValue=JSON.parse(localStorage.getItem(accountKey) || 'null');if(!savedValue || savedValue.version!==1)throw new Error('ยังไม่มีค่าที่บันทึก');setConfig(savedValue.config);onAdvanced(JSON.stringify(savedValue.advanced,null,2));onReset();setFrozen(null);setMessage('โหลดค่าแล้ว กดดูภาพเพื่อตรวจตำแหน่งกล้องอีกครั้ง')})}>โหลดค่าที่บันทึก</Button>
        <Button type="button" secondary onClick={()=>action(async()=>{const blob=new Blob([saved()],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='snooker-table-settings.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})}>ส่งออกค่าทั้งชุด</Button>
        <label className="button secondary">นำเข้าค่าทั้งชุด<input className="file-input" type="file" accept=".json" onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file)action(async()=>{if(file.size>64000)throw new Error('ไฟล์ใหญ่เกิน 64 KB');const value=JSON.parse(await file.text());if(value.version!==1 || !value.config || !value.advanced || Array.isArray(value.config) || Array.isArray(value.advanced))throw new Error('รูปแบบไฟล์ไม่ถูกต้อง');setConfig(value.config);onAdvanced(JSON.stringify(value.advanced,null,2));onReset();setFrozen(null)})}}/></label>
      </div>
    </fieldset>{busy && <p role="status">กำลังเปิดกล้อง/ดำเนินการ…</p>}{error && <p className="error" role="alert">{error}</p>}{message && <p className="notice">{message}</p>}
  </section>
}
