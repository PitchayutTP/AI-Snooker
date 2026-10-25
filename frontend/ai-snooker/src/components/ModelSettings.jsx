import { useState } from 'react';
import { api } from '../lib/api';
import { Button,Field } from './ui';

export function ModelSettings({ advanced,onChange,disabled }) {
  const [info,setInfo]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  let settings={};try{settings=JSON.parse(advanced)}catch{/* JSON editor shows parse errors on apply */}
  function apply(patch) {
    try{const current=JSON.parse(advanced);onChange(JSON.stringify({...current,...patch},null,2));setError('');setInfo(null)}catch(e){setError(e.message)}
  }
  async function inspect() {
    setBusy(true);setError('');setInfo(null);
    try{setInfo(await api('/models/inspect',{path:settings.ball_model || 'models/snooker.pt'}))}
    catch(e){setError(e.message)}finally{setBusy(false)}
  }
  return <section className="panel"><h2>โมเดลและการกรองข้อมูลตามรายงาน</h2>
    <fieldset disabled={disabled || busy}>
      <div className="columns"><Field label="วิธีตรวจลูก"><select value={settings.ball_detector || 'HSV'} onChange={e=>apply({ball_detector:e.target.value})}><option value="HSV">HSV — นำร่องในสภาพแวดล้อมควบคุม</option><option value="YOLO">YOLOv8 — ใช้โมเดลที่ฝึกลูกสนุกเกอร์แล้ว</option></select></Field>
      <Field label="ไฟล์โมเดลลูก (ภายใน backend/models)"><input value={settings.ball_model || 'models/snooker.pt'} onChange={e=>apply({ball_model:e.target.value})}/></Field></div>
      <Button type="button" secondary onClick={inspect}>ตรวจไฟล์และคลาสของโมเดล</Button>
      <p className="muted">คลาสมาตรฐานคือ cue_ball และ target_ball หากโมเดลใช้ชื่ออื่น กำหนด ball_roles ใน JSON โมเดลทั่วไปที่ยังไม่ฝึกลูกสนุกเกอร์ไม่ถือว่าพร้อมประเมิน</p>
      <Field label="จำนวนเฟรม Moving Average (1 = ไม่กรอง)"><input type="number" min="1" max="31" step="1" value={settings.smoothing_window ?? 1} onChange={e=>apply({smoothing_window:Number(e.target.value)})}/></Field>
      <label className="check"><input type="checkbox" checked={!!settings.smoothing_for_evaluation} onChange={e=>apply({smoothing_for_evaluation:e.target.checked})}/>ใช้ค่าหลังกรองคำนวณผลประเมินด้วย (ต้องมีเหตุผลจากการนำร่อง)</label>
      <p className="muted">ค่าเริ่มต้นใช้ข้อมูลดิบประเมิน กรองเฉพาะร่างกายและคิวเพื่อแสดงผล ไม่กรองเส้นทางลูก ไม่เติมจุดที่หาย เก็บทั้งค่าดิบและค่าหลังกรองในหลักฐาน และต้องประเมินความล่าช้าที่เพิ่มขึ้น</p>
      <label className="check"><input type="checkbox" checked={!!settings.record_frames} onChange={e=>apply({record_frames:e.target.checked})}/>เก็บภาพดิบแต่ละเฟรมขณะบันทึก เพื่อทำข้อมูลอ้างอิงในเครื่องนี้</label>
      <div className="columns"><Field label="จำนวนเฟรมที่ใช้วัดได้ขั้นต่ำ"><input type="number" min="2" max="1000" value={settings.min_valid_frames ?? 5} onChange={e=>apply({min_valid_frames:Number(e.target.value)})}/></Field><Field label="สัดส่วนเฟรมที่ใช้วัดได้ขั้นต่ำ (0–1)"><input type="number" min="0.01" max="1" step="any" value={settings.min_valid_ratio ?? .7} onChange={e=>apply({min_valid_ratio:Number(e.target.value)})}/></Field></div>
      <p className="muted">ค่าขั้นต่ำเริ่มต้นเป็นพารามิเตอร์ของโปรแกรม ต้องตรวจความเหมาะสมจากการนำร่อง ไม่ใช่เกณฑ์มาตรฐานของท่าทางที่ถูกต้อง</p>
      <p className="muted">ภาพอาจใช้พื้นที่มากและเพิ่มเวลาทำงาน เปิดเฉพาะช่วงเก็บข้อมูลที่ต้องตรวจเทียบ แล้วดาวน์โหลด ZIP หลักฐานหลังจบรอบ ภาพไม่ถูกส่งไปบริการภายนอก</p>
    </fieldset>
    {busy && <p role="status">กำลังตรวจโมเดล…</p>}{error && <p className="error">{error}</p>}
    {info && <p className="notice">{info.available ? `พบโมเดล · คลาส: ${info.classes.join(', ')} · SHA256: ${info.sha256}` : info.message}</p>}
  </section>
}
