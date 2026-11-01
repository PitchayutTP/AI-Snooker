import {CameraSetup} from '../components/CameraSetup';
import {Calibration} from '../components/Calibration';
import {M1Setup} from '../components/M1Setup';
import {Button,Field,Table} from '../components/ui';
import {TrialLayout} from '../components/TrialLayout';
import {Guide} from '../components/Guide';
import {labels} from '../lib/labels';
import {isPrototypeCriteria} from '../lib/moduleSettings';

export default function SetupPage(props) {
  const {exercise,exerciseId,catalog,choose,criteria,criteriaId,setCriteriaId,setPage,config,setConfig,
    advanced,setAdvanced,status,frame,active,busy,connected,prepared,fingerprint,run,checkReady,startSession,setPrepared,setError}=props;
  const moduleId=exercise?.module_id;
  if(moduleId===1)return <M1Setup {...props}/>;
  const disabled=active || busy;
  const cameras=moduleId===2 ? ['side','top'] : ['top'];
  const selected=isPrototypeCriteria(criteria) ? criteria : null;
  const plan=selected?.protocol || {required_valid_attempts:5,minimum_pass_rate:.8};
  const rules=selected?.rules || (moduleId===2 ? {
    cue_deviation_ratio:{max:.03},head_motion_ratio:{max:.03},bridge_motion_ratio:{max:.03},center_aim_ratio:{max:.03},follow_through_ratio:{min:.1},
  } : {fraction_error:{max:.1}});
  function apply(values) {
    try {
      const current=JSON.parse(advanced);
      if(!current || Array.isArray(current) || typeof current!=='object')throw new Error('การตั้งค่าต้องเป็น JSON object');
      setAdvanced(JSON.stringify({...current,...values},null,2));setPrepared('');
    } catch(e){setError(e.message);}
  }
  return <>
    <div className="heading"><h1>เตรียมฝึก M{moduleId}</h1><p>{moduleId===2 ? 'เลือกกล้อง มาร์กเกอร์ และจุดลูกขาว แล้วเริ่มฝึกแทงตรง' : 'เลือกเหลี่ยม กล้อง และสีลูก แล้วสอบเทียบโต๊ะ'}</p></div>
    <section className="panel"><h2>อุปกรณ์และแบบฝึก</h2>
      {moduleId===3 && <Field label="เหลี่ยมที่ต้องการฝึก"><select value={exerciseId} disabled={disabled} onChange={e=>choose(catalog.find(ex=>String(ex.id)===e.target.value))}>{catalog.filter(ex=>ex.module_id===3).map(ex=><option key={ex.id} value={ex.id}>{ex.name}</option>)}</select></Field>}
      {moduleId===2 && <Field label="มือที่ถนัด"><select disabled={disabled} value={config.hand} onChange={e=>setConfig({...config,hand:e.target.value})}><option value="RIGHT">ขวา</option><option value="LEFT">ซ้าย</option></select></Field>}
      {cameras.map(camera=><Field key={camera} label={camera==='side' ? 'หมายเลขกล้องด้านข้าง' : 'หมายเลขกล้องด้านบน'}><input disabled={disabled} value={config[`${camera}_source`]} onChange={e=>setConfig({...config,[`${camera}_source`]:e.target.value})}/></Field>)}
      <p className="notice">{moduleId===2 ? 'ใช้สองกล้อง ติดมาร์กเกอร์สองสีบนคิว เลือกสีด้านปลาย/ท้ายคิวและศูนย์กลางลูกขาวจากภาพข้าง จากนั้นเลือกสีลูกขาวและสอบเทียบภาพบน ไม่ต้องมีลูกแดงหรือลงหลุม' : 'ใช้กล้องบนตัวเดียว เลือกสีลูกขาวและลูกแดงจากภาพจริง แล้วสอบเทียบพื้นที่เล่น'}</p>
    </section>
    <CameraSetup key={moduleId} moduleId={moduleId} cameras={cameras} config={config} setConfig={setConfig} advanced={advanced} onAdvanced={setAdvanced} status={status} disabled={disabled || !connected} onReset={()=>setPrepared('')}/>
    <Calibration previewImage={frame.preview_camera==='top' ? frame.image : null} disabled={disabled} onApply={apply}/>
    <section className="panel"><h2>เกณฑ์ M{moduleId}</h2>
      <Field label="เกณฑ์ประเมิน"><select disabled={disabled} value={selected ? criteriaId : ''} onChange={e=>setCriteriaId(e.target.value)}><option value="">เกณฑ์ต้นแบบ — 5 ครั้ง ผ่านอย่างน้อย 4 ครั้ง</option>{exercise?.criteria.filter(isPrototypeCriteria).map(c=><option key={c.id} value={c.id}>รุ่น {c.version} — ยืนยันแล้ว</option>)}</select></Field>
      <Table headings={['ตัวชี้วัด','ต่ำสุด','สูงสุด','หน่วย']}>
        {Object.entries(rules).map(([key,rule])=><tr key={key}><td>{labels[key] || key}</td><td>{rule.min ?? '—'}</td><td>{rule.max ?? '—'}</td><td>{key.endsWith('_ratio') || key==='fraction_error' || key==='contact_fraction' ? 'สัดส่วน' : 'พิกเซล'}</td></tr>)}
      </Table>
      <p>ผ่านอย่างน้อย {Math.ceil(plan.required_valid_attempts*plan.minimum_pass_rate-1e-9)} จาก {plan.required_valid_attempts} ครั้งที่ประเมินได้ ข้อมูลไม่ครบไม่นับ {moduleId===3 ? 'ต้องผ่านครบเต็มใบ, 3/4, 1/2 และ 1/4 จึงครบ M3' : 'ต้องอยู่ในเกณฑ์ทั้งห้าข้อ ใช้ระยะเทียบระยะมาร์กเกอร์ในภาพ'}</p>
      <p className="muted">เป็นเกณฑ์ต้นแบบ ไม่ใช่มาตรฐานสากลหรือการรับรองทักษะ</p>
      <Button secondary disabled={disabled} onClick={()=>setPage('criteria')}>ดูหรือแก้ไขเกณฑ์</Button>
    </section>
    <section className="panel"><h2>ตรวจและเริ่มฝึก</h2>
      <p>ระบบตั้ง LIVE การประเมิน และค่าประมวลผลให้แล้ว {moduleId===2 ? 'ช่วงฐานและความไวเริ่มเคลื่อนลูกใช้ค่าตั้งต้นให้โดยอัตโนมัติ ต้องตรวจการจับลูกนิ่งและลูกเคลื่อนก่อนเก็บผลจริง' : 'ขนาดพื้นที่เล่นมาตรฐานและรัศมีลูกเติมไว้แล้ว แต่ยังต้องเลือกจุดสอบเทียบจากภาพจริง'}</p>
      {status.error && <p className="error">{status.error}</p>}
      <div className="actions"><Button secondary disabled={disabled || !connected || !exercise} onClick={()=>run(checkReady)}>ตรวจความพร้อมและใช้เกณฑ์ต้นแบบ</Button><Button disabled={disabled || !connected || !status.ready || prepared!==fingerprint || !criteria} onClick={()=>run(startSession)}>เริ่มรอบฝึก</Button></div>
      <p>{!connected ? 'กำลังเชื่อมต่อ Backend' : prepared!==fingerprint ? 'เตรียมอุปกรณ์แล้วกดตรวจความพร้อม' : status.ready ? 'พร้อมเริ่มรอบฝึก' : 'กำลังรอผลตรวจจับครบ'}</p>
      {prepared===fingerprint && connected && !active && <div aria-live="polite">{frame.image && <img src={`data:image/jpeg;base64,${frame.image}`} alt="ภาพตรวจความพร้อม" style={{width:'100%'}}/>}{!status.ready && <ul>{(status.readiness_issues || []).map(issue=><li key={issue}>{issue}</li>)}</ul>}</div>}
    </section>
    <details className="panel"><summary>วิธีทำแบบฝึกและการจัดลูก</summary><Guide exercise={exercise}/><TrialLayout exercise={exercise} advanced={advanced}/></details>
  </>;
}
