import { number } from '../lib/api';

export function QualityReport({ attempt }) {
  const q=attempt.quality,timing=attempt.display_timing;
  if(!q && !timing)return null;
  return <div className="quality-report"><h4>คุณภาพข้อมูล</h4>
    {q && <p>ตัวอย่าง {q.samples ?? '—'} เฟรม · ช่วงบันทึก {number(q.duration_s)} วินาที · เฟรมข้อมูลไม่พร้อม {q.not_ready_frames ?? '—'} · เวลาอ่านและประมวลผลเฉลี่ย {number(q.processing_ms?.mean)} ms</p>}
    {timing && <p>เวลาจากเริ่มรับภาพถึง image load ในเบราว์เซอร์ (ประมาณ): median {number(timing.median_ms)} ms · P95 {number(timing.p95_ms)} ms · จำนวน {timing.n} · ความไม่แน่นอนจากการเทียบเวลา ±{number(timing.clock_uncertainty_ms)} ms</p>}
    <p className="muted">เวลานี้รวมการอ่าน/ประมวลผล/ส่งภาพและโหลดภาพ ไม่ใช่เวลาจาก sensor หรือการยืนยันว่าจอวาดภาพเสร็จ และข้อมูลฝั่งเบราว์เซอร์เป็นการรายงานจากไคลเอนต์</p>
  </div>
}
