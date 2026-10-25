import { CameraViews } from "../components/CameraViews";
import { Button, Badge, Table } from "../components/ui";
import { Feedback } from "../components/Feedback";
import { LiveValues } from "../components/LiveValues";
import { Trajectory } from "../components/Trajectory";
import { number } from "../lib/api";
import { labels } from "../lib/labels";
export default function TrainingPage({ onDisplayed, status, active, frame, config, busy, connected, run, finishAttempt, startAttempt, finishSession, lastAttempt, units }) {
  return (<>
            <div className="heading">
              <h1>ฝึกและบันทึกผล</h1>
              <p className="muted">เริ่มและจบแต่ละครั้งด้วยตนเอง</p>
            </div>
            {!active ? (
              <p className="notice">
                ไม่มีรอบฝึกที่กำลังทำงาน กรุณาเลือกแบบฝึกเพื่อเริ่มต้น
              </p>
            ) : (
              <>
                <div className="columns training">
                  <CameraViews status={status} onDisplayed={onDisplayed}/>
                  <section className="panel">
                    <Badge value={status.mode || config.mode} />
                    <h2>ข้อมูลขณะฝึก</h2>
                    <LiveValues status={status}/>
                    <dl>
                      <dt>มุมศอก (°)</dt>
                      <dd>{number(frame.elbow)}</dd>
                      <dt>อัตราภาพ (FPS)</dt>
                      <dd>{number(frame.fps)}</dd>
                      <dt>ตัวอย่างที่บันทึก</dt>
                      <dd>{status.samples || 0}</dd>
                    </dl>
                    <p className="muted">
                      ค่า “—” หมายถึงไม่มีข้อมูล ไม่ใช่ค่า 0
                    </p>
                    {status.error && <p className="error">{status.error}</p>}
                    <div className="stack">
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
                          disabled={busy || !connected || !status.ready}
                          onClick={() => run(startAttempt)}
                        >
                          เริ่มบันทึกครั้งใหม่
                        </Button>
                      )}
                      <Button
                        secondary
                        disabled={busy || !connected || !!status.attempt_id}
                        onClick={() => run(finishSession)}
                      >
                        จบรอบและดูสรุป
                      </Button>
                    </div>
                    {status.attempt_id && (
                      <p className="muted">จบหรือยกเลิกครั้งนี้ก่อนจบรอบ</p>
                    )}
                  </section>
                </div>
                <Trajectory status={status}/>
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
