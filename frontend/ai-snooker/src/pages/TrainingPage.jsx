import { ProtocolStatus } from "../components/ProtocolStatus";
import { CameraViews } from "../components/CameraViews";
import { Button, Badge, Table } from "../components/ui";
import { Feedback } from "../components/Feedback";
import { LiveValues } from "../components/LiveValues";
import { Trajectory } from "../components/Trajectory";
import { number } from "../lib/api";
import { labels } from "../lib/labels";
import {ElbowDetail} from '../components/ElbowDetail';
export default function TrainingPage({ m1Auto,cancelM1,criteria, exercise, activeReport, onDisplayed, status, active, frame, config, busy, connected, run, finishAttempt, startAttempt, finishSession, lastAttempt, units }) {
  const recordingSeconds=status.configuration?.m1_auto_seconds || 0;
  const automatic=exercise?.module_id===1 && recordingSeconds>0;
  const autoBusy=m1Auto?.phase==='STARTING' || m1Auto?.phase==='FINISHING';
  return (<>
            <div className="heading">
              <h1>ฝึกและบันทึกผล</h1>
              <p className="muted">{automatic ? `บันทึกและสรุปผลอัตโนมัติ ${recordingSeconds} วินาที` : 'เริ่มและจบแต่ละครั้งด้วยตนเอง'}</p>
            </div>
            {!active ? (
              <p className="notice">
                ไม่มีรอบฝึกที่กำลังทำงาน กรุณาเลือกแบบฝึกเพื่อเริ่มต้น
              </p>
            ) : (
              <>
                <ProtocolStatus result={activeReport?.protocol_result}/>
                {exercise?.module_id === 1 && <section className="notice">
                  <p>{automatic ? `คงท่าให้นิ่ง เหลือประมาณ ${Math.max(0,Math.ceil(recordingSeconds-(status.attempt_elapsed_s || 0)))} วินาที ระบบจะหยุดและสรุปให้เอง` : `ตั้งท่าให้เห็นจุดร่างกายครบ นิ่งช่วงฐาน ${status.configuration?.baseline_seconds ?? config.baseline_seconds ?? 1} วินาที จากนั้นคงท่าอย่างน้อย ${criteria?.minimum_active_seconds ?? 5} วินาที ก่อนกดจบครั้ง`}</p>
                  {automatic && !status.ready && <p className="error">จุดร่างกายบางส่วนหาย กรุณากลับเข้ามุมกล้อง ข้อมูลไม่ครบจะเป็นประเมินไม่ได้</p>}
                  {automatic && m1Auto?.phase==='FINISHING' && <p role="status">ครบเวลาแล้ว กำลังบันทึกและสรุปผล…</p>}
                  <p>เกณฑ์ที่เลือก: {Object.entries(criteria?.rules || {}).map(([key, rule]) => `${labels[key] || key}: ${rule.min != null ? 'ต่ำสุด '+rule.min+' ' : ''}${rule.max != null ? 'สูงสุด '+rule.max : ''} ${units[key] || ''}`).join(' · ') || 'ยังไม่กำหนดเกณฑ์'}</p>
                  {criteria?.template_version==='m1-elbow-shooting-leg-8s-v10' && <p>ตรวจศอกและเข่าฝั่งแทง ใช้ภาพขยายดูไหล่–ศอก–ข้อมือ ไม่บังคับตรวจขาฝั่งสะพานมือ</p>}
                  <p>ผ่านหมายถึงอยู่ในเกณฑ์รุ่นนี้ ไม่ใช่การรับรองท่าสนุกเกอร์ถูกต้องทั้งหมด</p>
                </section>}
                <div className="columns training">
                  <CameraViews status={status} onDisplayed={onDisplayed}/>
                  <section className="panel">
                    <Badge value={status.mode || config.mode} />
                    <h2>ข้อมูลขณะฝึก</h2>
                    <LiveValues status={status}/>
                    <dl>
                      <dt>อัตราภาพ (FPS)</dt>
                      <dd>{number(frame.fps)}</dd>
                      <dt>ตัวอย่างที่บันทึก</dt>
                      <dd>{status.samples || 0}</dd>
                    </dl>
                    <p className="muted">
                      ค่า “—” หมายถึงไม่มีข้อมูล ไม่ใช่ค่า 0
                    </p>
                    {status.error && <p className="error">{status.error}</p>}
                    {!automatic && <div className="stack">
                      {status.attempt_id ? (
                        <>
                          <Button
                            disabled={busy || !connected}
                            onClick={() => run(() => finishAttempt(false))}
                          >
                            จบการบันทึกครั้งนี้
                          </Button>
                          <Button
                            secondary
                            disabled={busy || !connected}
                            onClick={() => run(() => finishAttempt(true))}
                          >
                            ยกเลิกครั้งนี้
                          </Button>
                        </>
                      ) : (
                        <Button
                          disabled={busy || !connected || !status.ready || activeReport?.protocol_result?.remaining===0}
                          onClick={() => run(startAttempt)}
                        >
                          เริ่มบันทึกครั้งใหม่
                        </Button>
                      )}
                      <Button
                        secondary
                        disabled={busy || !connected || !!status.attempt_id}
                        onClick={() => run(()=>finishSession(false))}
                      >
                        จบรอบและดูสรุป
                      </Button>
                      <Button secondary disabled={busy || !connected} onClick={()=>run(()=>finishSession(true))}>ยุติรอบก่อนจบแผน</Button>
                    </div>}
                    {automatic && <Button secondary disabled={busy || !connected || autoBusy} onClick={()=>run(cancelM1)}>ยกเลิกการตรวจท่าครั้งนี้</Button>}
                    {status.attempt_id && !automatic && (
                      <p className="muted">จบหรือยกเลิกครั้งนี้ก่อนจบรอบ</p>
                    )}
                  </section>
                </div>
                <Trajectory status={status}/>
                {exercise?.module_id===1 && <ElbowDetail frame={frame}/>}
                {lastAttempt && (
                  <section className="panel">
                    <h2>
                      ผลครั้งล่าสุด <Badge value={lastAttempt.status} />
                    </h2>
                    <p>{lastAttempt.reason}</p>
                    <Feedback items={lastAttempt.feedback}/>
                    <Table headings={["ตัวชี้วัด", "ค่า", "หน่วย"]}>
                      {Object.entries(lastAttempt.metrics || {}).map(
                        ([key, value]) => (
                          <tr key={key}>
                            <td>{labels[key] || key}</td>
                            <td>{number(value)}</td>
                            <td>{units[key]}</td>
                          </tr>
                        ),
                      )}
                    </Table>
                  </section>
                )}
              </>
            )}
          </>);
}
