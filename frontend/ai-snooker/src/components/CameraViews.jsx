import { useEffect, useRef } from 'react';

export function CameraViews({ status,onDisplayed }) {
  const frame=status.frame || {};
  const images=Object.entries(frame.images || {});
  const rendered=useRef(new Map());
  useEffect(()=>{rendered.current.clear()},[status.attempt_id]);
  if(!images.length)return <div className="video">{frame.image ? <img src={`data:image/jpeg;base64,${frame.image}`} alt="ภาพกล้องฝึก"/> : <p>{status.mode==='DEMO' ? 'โหมดสาธิต ไม่มีภาพจริง' : 'กำลังรอภาพกล้อง'}</p>}</div>;
  return <div className="camera-views">{images.map(([camera,image])=><figure key={camera}><figcaption>{camera==='side' ? 'ด้านข้าง' : 'ด้านบน'} · {frame.image_sizes?.[camera]?.join(' × ')} px</figcaption><img key={`${camera}:${frame.t}`} alt={`ภาพกล้อง${camera}`} src={`data:image/jpeg;base64,${image}`} onLoad={()=>{const key=`${status.attempt_id}:${frame.t}`;const loaded=rendered.current.get(key) || new Set();if(loaded.has(camera))return;loaded.add(camera);rendered.current.set(key,loaded);if(loaded.size===images.length)onDisplayed?.(frame);if(rendered.current.size>6000)rendered.current.clear()}}/></figure>)}</div>
}
