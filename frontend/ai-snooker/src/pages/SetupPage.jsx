import { ModelSettings } from "../components/ModelSettings";
import { TrialLayout } from "../components/TrialLayout";
import { CameraSetup } from "../components/CameraSetup";
import { Button, Field } from "../components/ui";
import { Guide } from "../components/Guide";
import { SettingsImport } from "../components/SettingsImport";
import { Calibration } from "../components/Calibration";
export default function SetupPage({ user, status, exerciseId, active, choose, catalog, exercise, criteriaId, setCriteriaId, setPage, config, setConfig, setAdvanced, advanced, busy, connected, run, checkReady, prepared, fingerprint, criteria, startSession, frame, setPrepared, setError }) {
  return (<>
            <div className="heading">
              <h1>ตั้งค่าก่อนฝึก</h1>
              <p className="muted">เลือกแบบฝึกและตรวจสอบกล้องก่อนเริ่มบันทึก</p>
            </div>
            <div className="columns">
              <section className="panel">
                <Field label="แบบฝึก">
                  <select
                    value={exerciseId}
                    disabled={active}
                    onChange={(e) =>
                      choose(
                        catalog.find((x) => String(x.id) === e.target.value),
                      )
                    }
                  >
                    {catalog.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.module} — {e.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <p>{exercise?.instructions}</p>
                <Field label="เกณฑ์ประเมิน">
                  <select
                    value={criteriaId}
                    disabled={active}
                    onChange={(e) => setCriteriaId(e.target.value)}
                  >
                    {exercise?.criteria.map((c) => (
                      <option key={c.id} value={c.id}>
                        รุ่น {c.version} —{" "}
                        {c.approved ? "ยืนยันเกณฑ์แล้ว" : "ยังไม่ยืนยันเกณฑ์"}
                      </option>
                    ))}
                  </select>
                </Field>
                <Button secondary onClick={() => setPage("criteria")}>
                  ดูเกณฑ์ประเมิน
                </Button>
                <Field label="ประเภทของรอบ">
                  <select disabled={active} value={config.purpose || 'PILOT'} onChange={e=>setConfig({...config,purpose:e.target.value})}>
                    <option value="PILOT">นำร่อง — เก็บค่าการวัด</option><option value="ASSESSMENT">ประเมิน — ต้องมีเกณฑ์และแผน N</option>
                  </select>
                </Field>
                {config.purpose==='ASSESSMENT' && <p className="notice">ใช้ LIVE และเกณฑ์ยืนยันที่กำหนด N กับอัตราผ่านแล้ว หากยังไม่มีให้สร้างเกณฑ์รุ่นใหม่</p>}
                <Field label="โหมดการฝึก">
                  <select
                    disabled={active}
                    value={config.mode}
                    onChange={(e) =>
                      setConfig({ ...config, mode: e.target.value })
                    }
                  >
                    <option value="DEMO">DEMO — ทดสอบการทำงาน</option>
                    <option value="LIVE">LIVE — กล้องจริง</option>
                  </select>
                </Field>
                <Field label="ช่วงเก็บท่าตั้งต้น (วินาที)">
                  <input type="number" min="0.5" max="10" step="0.5" disabled={active} value={config.baseline_seconds ?? 1} onChange={e=>setConfig({...config,baseline_seconds:Number(e.target.value)})}/>
                </Field>
                <Field label="มือที่ถนัด">
                  <select
                    disabled={active}
                    value={config.hand}
                    onChange={(e) =>
                      setConfig({ ...config, hand: e.target.value })
                    }
                  >
                    <option value="RIGHT">ขวา</option>
                    <option value="LEFT">ซ้าย</option>
                  </select>
                </Field>
              </section>
              <section className="panel">
                <h2>กล้องและการตรวจจับ</h2>
                {[
                  ["side_source", "กล้องด้านข้าง"],
                  ["top_source", "กล้องด้านบน"],
                ].map(([key, label]) => (
                  <Field label={label} key={key}>
                    <input
                      disabled={active}
                      value={config[key]}
                      onChange={(e) =>
                        setConfig({ ...config, [key]: e.target.value })
                      }
                    />
                  </Field>
                ))}
                <SettingsImport disabled={active} onImport={value=>{try{setAdvanced(JSON.stringify({...JSON.parse(advanced),...JSON.parse(value)},null,2));setPrepared('')}catch(e){setError(e.message)}}}/>
                <details>
                  <summary>การตั้งค่าการวัดเพิ่มเติม (JSON)</summary>
                  <p className="muted">
                    LIVE ด้านข้างต้องมีโมเดลท่าทาง ด้านบนเลือก HSV (ลูกขาว/แดง) หรือ YOLO และต้องสอบเทียบโต๊ะ
                  </p>
                  <textarea
                    aria-label="การตั้งค่าเพิ่มเติม"
                    value={advanced}
                    disabled={active}
                    onChange={(e) => setAdvanced(e.target.value)}
                    rows={8}
                    spellCheck={false}
                  />
                </details>
                <p className="notice">
                  {config.mode === "DEMO"
                    ? "DEMO ใช้ข้อมูลจำลอง ผลจะเป็น “ประเมินไม่ได้” และไม่ใช้ยืนยันทักษะ"
                    : "ใช้กล้องที่เชื่อมต่อกับเครื่อง Backend และจัดตำแหน่งลูกตามคำแนะนำของแบบฝึก"}
                </p>
                {status.error && <p className="error">{status.error}</p>}
                <div className="actions">
                  <Button
                    secondary
                    disabled={busy || active || !connected || !exercise}
                    onClick={() => run(checkReady)}
                  >
                    ตรวจความพร้อม
                  </Button>
                  <Button
                    disabled={
                      busy ||
                      active ||
                      !connected ||
                      !status.ready ||
                      prepared !== fingerprint ||
                      !criteria
                    }
                    onClick={() => run(startSession)}
                  >
                    เริ่มรอบฝึก
                  </Button>
                </div>
                <p className="muted">
                  {prepared === fingerprint && connected && status.ready
                    ? "พร้อมเริ่มรอบฝึก"
                    : !connected ? "ยังไม่เชื่อมต่อข้อมูลสดกับ Backend"
                    : prepared !== fingerprint ? "ต้องตรวจความพร้อมหลังเปลี่ยนการตั้งค่า"
                    : "กล้องเปิดแล้ว กำลังรอข้อมูลตรวจจับครบก่อนเริ่ม"}
                </p>
                {prepared === fingerprint && connected && !active && <div aria-live="polite">
                  {frame.image && <img src={`data:image/jpeg;base64,${frame.image}`} alt="ภาพตรวจความพร้อมก่อนเริ่มฝึก" style={{width:'100%',borderRadius:8}}/>}
                  {!status.ready && <ul className="notice">{(status.readiness_issues?.length ? status.readiness_issues : ['กำลังรอภาพและผลตรวจจับจากกล้อง']).map(issue=><li key={issue}>{issue}</li>)}</ul>}
                  {config.mode==='LIVE' && exercise?.module_id===1 && <p className="muted">ถอยกล้องให้เห็นถึงข้อเท้าทั้งสองข้าง พร้อมศีรษะ ไหล่ ศอก ข้อมือ และสะโพก กล้องที่เห็นเฉพาะใบหน้าจะยังเริ่มโมดูลนี้ไม่ได้</p>}
                </div>}
              </section>
            </div>
            <Guide exercise={exercise}/>
            <TrialLayout exercise={exercise} advanced={advanced}/>
            <ModelSettings advanced={advanced} onChange={value=>{setAdvanced(value);setPrepared('')}} disabled={active || busy}/>
            <CameraSetup config={config} setConfig={setConfig} advanced={advanced} onAdvanced={setAdvanced} status={status} disabled={active || busy || !connected} onReset={()=>setPrepared('')} accountKey={`snooker-settings-${user.username}`}/>
            <Calibration previewImage={frame.preview_camera==='top' ? frame.image : null} disabled={active} onApply={values=>{try{const current=JSON.parse(advanced);if(!current || Array.isArray(current) || typeof current!=='object')throw new Error('การตั้งค่าเพิ่มเติมต้องเป็น JSON object');setAdvanced(JSON.stringify({...current,...values},null,2));setPrepared('')}catch(e){setError(e.message)}}}/>
          </>);
}
