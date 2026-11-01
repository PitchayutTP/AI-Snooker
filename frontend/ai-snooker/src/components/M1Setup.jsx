import {Button,Field,Table} from './ui';
import {CameraSetup} from './CameraSetup';
import {labels} from '../lib/labels';
import {isTimedM1Criteria} from '../lib/m1AutoTrial';
import {ElbowDetail} from './ElbowDetail';

export function M1Setup({exercise,criteria,criteriaId,setCriteriaId,config,setConfig,status,frame,active,busy,connected,m1Auto,prepareM1,cancelM1,run,setPrepared,setAdvanced,setPage}) {
  const counting=m1Auto?.phase==='COUNTDOWN';
  const waiting=m1Auto?.phase==='WAITING' || counting;
  const disabled=active || busy || waiting || m1Auto?.phase==='STARTING';
  const selected=isTimedM1Criteria(criteria) ? criteria : null;
  const rules=selected?.rules || {elbow_min:{min:80},elbow_max:{max:100},knee_shooting_min:{min:160},knee_shooting_max:{max:180}};
  return <>
    <div className="heading"><h1>เตรียมฝึก M1</h1><p>เลือกมือ กล้อง และเกณฑ์ จากนั้นเริ่มตรวจท่าได้เลย</p></div>
    <section className="panel"><h2>มือที่ถนัดและหมายเลขกล้อง</h2>
      <Field label="มือที่ถนัด"><select disabled={disabled} value={config.hand} onChange={e=>setConfig({...config,hand:e.target.value})}><option value="RIGHT">ขวา</option><option value="LEFT">ซ้าย</option></select></Field>
      <Field label="หมายเลขกล้องด้านข้าง"><input disabled={disabled} value={config.side_source} onChange={e=>setConfig({...config,side_source:e.target.value})}/></Field>
    </section>
    <CameraSetup moduleId={1} cameras={['side']} config={config} setConfig={setConfig} advanced="{}" onAdvanced={setAdvanced} status={status} disabled={disabled || !connected} onReset={()=>setPrepared('')}/>
    <section className="panel"><h2>เกณฑ์ M1</h2>
      <Field label="เกณฑ์สำหรับตรวจท่า 8 วินาที"><select disabled={disabled} value={selected ? criteriaId : ''} onChange={e=>setCriteriaId(e.target.value)}><option value="">เกณฑ์ต้นแบบ — ศอก 80–100° และขาฝั่งแทง</option>{exercise?.criteria.filter(isTimedM1Criteria).map(c=><option key={c.id} value={c.id}>รุ่น {c.version} — ยืนยันแล้ว</option>)}</select></Field>
      <Table headings={['ตัวชี้วัด','ต่ำสุด','สูงสุด','หน่วย']}>
        {Object.entries(rules).map(([key,rule])=><tr key={key}><td>{labels[key] || key}</td><td>{rule.min ?? '—'}</td><td>{rule.max ?? '—'}</td><td>องศา</td></tr>)}
      </Table>
      <p>ทดลองเฉพาะศอกและขา ผ่านเมื่อค่าต่ำสุด–สูงสุดของศอกและเข่าฝั่งแทงอยู่ในช่วงทุกข้อหลังช่วงฐาน ไม่ใช้ SD ตัดสิน ต้องมีข้อมูลเพียงพอ ประเมินหนึ่งครั้งจบรอบ มุมเป็นมุมฉายในภาพและเกณฑ์ต้นแบบ ไม่ใช่มาตรฐานสากล</p>
      <Button secondary disabled={disabled} onClick={()=>setPage('criteria')}>ดูหรือแก้ไขเกณฑ์</Button>
    </section>
    <section className="panel"><h2>เริ่มฝึก</h2>
      <p className="muted">จุดที่ใช้: ไหล่–ศอก–ข้อมือฝั่งถือคิว และสะโพก–เข่า–ข้อเท้าฝั่งแทง ไม่บังคับตรวจศีรษะหรือมือสะพาน และไม่ประเมินการก้มกับคาง ระบบไม่ใช้จุดเก่าทดแทนจุดที่หาย</p>
      <p>เมื่อจุดครบต่อเนื่อง 1 วินาที จะเตรียมตัว 5 วินาที แล้วบันทึก 8 วินาทีและสรุปผลอัตโนมัติ ช่วงเตรียมตัวไม่รวมในเวลาบันทึก</p>
      <details><summary>รายละเอียดการวัดและตัวกรอง</summary>
        <p>Median 15 เฟรม + EMA 0.8 วินาที ทั้งแสดงผลและตัดสิน หน่วงโดยประมาณ 1–1.5 วินาทีที่ 10–30 FPS จุดที่หายไม่ถูกเติมทดแทน เก็บค่าดิบไว้ตรวจสอบ</p>
        <p>พักจุดบนภาพภายใน 1.5 พิกเซล และพักตัวเลขภายใน 0.25° เฉพาะหน้าจอ ผลตัดสินใช้ค่ากรองเต็มความละเอียด รีเซ็ตตัวกรองเมื่อเฟรมห่างเกิน 0.75 วินาที</p>
      </details>
      {status.error && <p className="error">{status.error}</p>}
      <Button disabled={disabled || !connected || !exercise} onClick={()=>run(prepareM1)}>เริ่มตรวจท่าอัตโนมัติ 8 วินาที</Button>
      {waiting && <>{counting ? <div className="notice" role="timer" aria-live="polite"><strong style={{fontSize:'2rem'}}>เตรียมตัว {m1Auto.remaining ?? 5} วินาที</strong><p>ยังไม่บันทึก จัดท่าให้นิ่งและอยู่ในภาพ หากจุดหายจะกลับไปรอใหม่</p></div> : <p role="status">กำลังรอจุดร่างกายครบต่อเนื่อง</p>}<Button secondary onClick={cancelM1}>ยกเลิกการรอ</Button>{frame.image && <img src={`data:image/jpeg;base64,${frame.image}`} alt="ภาพตรวจความพร้อม M1" style={{width:'100%'}}/>}{!status.ready && <ul>{(status.readiness_issues || []).map(issue=><li key={issue}>{issue}</li>)}</ul>}</>}
      {!connected && <p className="notice">กำลังเชื่อมต่อข้อมูลสดกับ Backend</p>}
    </section>
    {waiting && <ElbowDetail frame={frame}/>}
  </>;
}
