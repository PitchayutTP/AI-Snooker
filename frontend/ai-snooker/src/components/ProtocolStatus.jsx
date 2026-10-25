import { Badge } from './ui';
import { number } from '../lib/api';

export function ProtocolStatus({ result }) {
  if(!result)return null;
  return <section className="panel"><h3>ผลตามแผนรายรอบ <Badge value={result.status}/></h3>
    {result.purpose==='ASSESSMENT' ? <><p>ผลที่ประเมินได้ {result.valid_attempts}/{result.required_valid_attempts} ครั้ง · เหลือ {result.remaining} ครั้ง · ข้อมูลไม่ครบ {result.invalid_attempts} ครั้ง</p><p>อัตราผ่าน {result.pass_rate==null ? '—' : number(result.pass_rate*100)+'%'} · เกณฑ์ขั้นต่ำ {number(result.minimum_pass_rate*100)}%</p><p className="muted">นับเฉพาะ PASS/FAIL จบรอบเมื่อครบ N หรือเลือกยุติรอบหากไม่ทำต่อ</p></> : <p className="muted">รอบนำร่องใช้เก็บค่าการวัด ไม่ใช้ยืนยันการผ่านบทเรียน</p>}
  </section>
}
