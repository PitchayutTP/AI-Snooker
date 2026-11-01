import { Badge } from './ui';
import { number } from '../lib/api';

export function ProtocolStatus({ result }) {
  if(!result)return null;
  const requiredPasses = result.required_valid_attempts && result.minimum_pass_rate
    ? Math.ceil(result.required_valid_attempts * result.minimum_pass_rate - 1e-9) : null;
  return <section className="panel"><h3>ผลตามแผนรายรอบ <Badge value={result.status}/></h3>
    {result.validation_scope==='PROTOTYPE' && <p className="notice">ประเมินตามเกณฑ์ต้นแบบของโครงงาน ไม่ใช่มาตรฐานสากลหรือการรับรองทักษะ หากใช้ HSV ผลนี้ไม่ใช่ผลทดสอบ YOLO ตามรายงาน</p>}
    {result.purpose==='ASSESSMENT' && requiredPasses != null && <p>เป้าหมาย: ผ่านอย่างน้อย {requiredPasses} จาก {result.required_valid_attempts} ครั้งที่ประเมินได้ ไม่จำเป็นต้องติดต่อกัน เมื่อครบจึงสรุปผลตามแผน</p>}
    {result.status==='READY_TO_FINISH' && <p className="notice">ครบจำนวนแล้ว พร้อมสรุปผลผ่าน/ไม่ผ่านรายรอบ</p>}
    {result.purpose==='ASSESSMENT' ? <><p>ผลที่ประเมินได้ {result.valid_attempts}/{result.required_valid_attempts} ครั้ง · เหลือ {result.remaining} ครั้ง · ข้อมูลไม่ครบ {result.invalid_attempts} ครั้ง</p><p>อัตราผ่าน {result.pass_rate==null ? '—' : number(result.pass_rate*100)+'%'} · เกณฑ์ขั้นต่ำ {number(result.minimum_pass_rate*100)}%</p><p className="muted">นับเฉพาะ PASS/FAIL จบรอบเมื่อครบ N หรือเลือกยุติรอบหากไม่ทำต่อ</p></> : <p className="muted">รอบนำร่องใช้เก็บค่าการวัด ไม่ใช้ยืนยันการผ่านบทเรียน</p>}
  </section>
}
