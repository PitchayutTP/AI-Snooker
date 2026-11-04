import { ProtocolStatus } from "../components/ProtocolStatus";
import { CameraViews } from "../components/CameraViews";
import { Button, Badge, Table } from "../components/ui";
import { Feedback } from "../components/Feedback";
import { LiveValues } from "../components/LiveValues";
import { Trajectory } from "../components/Trajectory";
import { number } from "../lib/api";
import { labels } from "../lib/labels";
import { ElbowDetail } from "../components/ElbowDetail";
export default function TrainingPage({
  m1Auto,
  cancelM1,
  criteria,
  exercise,
  activeReport,
  onDisplayed,
  status,
  active,
  frame,
  config,
  busy,
  connected,
  run,
  finishAttempt,
  startAttempt,
  finishSession,
  lastAttempt,
  units,
}) {
  const recordingSeconds = status.configuration?.m1_auto_seconds || 0;
  const automatic = exercise?.module_id === 1 && recordingSeconds > 0;
  const m3Minimum =
    (status.configuration?.baseline_seconds ?? 1) + (criteria?.minimum_active_seconds ?? 1);
  const m3TooShort = exercise?.module_id === 3 && (status.attempt_elapsed_s || 0) < m3Minimum;
  const m2Blocked =
    exercise?.module_id === 2 && !["READY", "INVALID"].includes(status.frame?.m2_trial?.state);
  const autoBusy = m1Auto?.phase === "STARTING" || m1Auto?.phase === "FINISHING";
  return (
    <>
      <div className="heading">
        <h1>ฝึกและบันทึกผล</h1>
        <p className="muted">
          {automatic
            ? `บันทึกและสรุปผลอัตโนมัติ ${recordingSeconds} วินาที`
            : exercise?.module_id === 3
              ? "เริ่มบันทึกก่อนแทง ระบบสรุปและบันทึกเมื่อหลักฐานการกระทบหรือการพลาดครบ"
              : "บันทึกหนึ่งครั้ง ระบบสรุปผลและจบรอบอัตโนมัติเมื่อประเมินได้ ข้อมูลไม่ครบให้ลองใหม่"}
        </p>
        {status.attempt_id && status.recording_error && (
          <p className="error" role="status">
            {status.recording_error}
          </p>
        )}
      </div>
      {!active ? (
        <p className="notice">ไม่มีรอบฝึกที่กำลังทำงาน กรุณาเลือกแบบฝึกเพื่อเริ่มต้น</p>
      ) : (
        <>
          <ProtocolStatus result={activeReport?.protocol_result} />
          {exercise?.module_id === 3 && (
            <section
              className={
                (status.attempt_id && status.samples > 0) || lastAttempt ? "notice" : "error"
              }
              role="status"
            >
              {!status.attempt_id
                ? lastAttempt
                  ? "บันทึกผลครั้งล่าสุดแล้ว — ดูผลด้านล่าง จัดลูกให้นิ่งแล้วกดเริ่มบันทึกครั้งใหม่"
                  : "ยังไม่ได้เริ่มบันทึก — จัดลูกให้นิ่ง แล้วกดเริ่มบันทึกครั้งใหม่ก่อนแทง"
                : !status.samples
                  ? "เริ่มคำสั่งบันทึกแล้ว กำลังรอเฟรมแรกจากกล้อง — อย่าเพิ่งแทง"
                  : status.attempt_elapsed_s < 1
                    ? "กำลังบันทึกช่วงฐาน — นิ่งลูกทั้งสอง 1 วินาที ยังไม่ต้องแทง"
                    : frame.m3_trial?.state === "INVALID"
                      ? "ข้อมูลตรวจจับขาดช่วงหรือไม่ชัดเจน — ยังไม่นับผล ตรวจสาเหตุด้านล่างแล้วจบหรือยกเลิกครั้งนี้"
                      : "กำลังบันทึกแล้ว — แทงได้ ระบบจะสรุปและบันทึกผลอัตโนมัติเมื่อหลักฐานครบ"}
              {status.attempt_id && !status.ready && !status.error && (
                <p>{status.readiness_issues?.join(" · ") || "ตรวจภาพกล้องและการติดตามลูก"}</p>
              )}
            </section>
          )}
          {exercise?.module_id === 1 && (
            <section className="notice">
              <p>
                {automatic
                  ? `คงท่าให้นิ่ง เหลือประมาณ ${Math.max(0, Math.ceil(recordingSeconds - (status.attempt_elapsed_s || 0)))} วินาที ระบบจะหยุดและสรุปให้เอง`
                  : `ตั้งท่าให้เห็นจุดร่างกายครบ นิ่งช่วงฐาน ${status.configuration?.baseline_seconds ?? config.baseline_seconds ?? 1} วินาที จากนั้นคงท่าอย่างน้อย ${criteria?.minimum_active_seconds ?? 5} วินาที ก่อนกดจบครั้ง`}
              </p>
              {automatic && !status.ready && (
                <p className="error">
                  จุดร่างกายบางส่วนหาย กรุณากลับเข้ามุมกล้อง ข้อมูลไม่ครบจะเป็นประเมินไม่ได้
                </p>
              )}
              {automatic && m1Auto?.phase === "FINISHING" && (
                <p role="status">ครบเวลาแล้ว กำลังบันทึกและสรุปผล…</p>
              )}
              <p>
                เกณฑ์ที่เลือก:{" "}
                {Object.entries(criteria?.rules || {})
                  .map(
                    ([key, rule]) =>
                      `${labels[key] || key}: ${rule.min != null ? "ต่ำสุด " + rule.min + " " : ""}${rule.max != null ? "สูงสุด " + rule.max : ""} ${units[key] || ""}`,
                  )
                  .join(" · ") || "ยังไม่กำหนดเกณฑ์"}
              </p>
              {criteria?.template_version === "m1-forearm-stance-8s-v11" && (
                <p>
                  ท่อนแขนเอียงไม่เกิน 15° ข้อมือต่ำกว่าศอก เข่าฝั่งแทง 160–180°
                  ต้องถูกพร้อมกันอย่างน้อย 80% ของเฟรมที่วัดได้
                </p>
              )}
              <p>ผ่านหมายถึงอยู่ในเกณฑ์รุ่นนี้ ไม่ใช่การรับรองท่าสนุกเกอร์ถูกต้องทั้งหมด</p>
            </section>
          )}
          <div className="columns training">
            <CameraViews status={status} onDisplayed={onDisplayed} />
            <section className="panel">
              <Badge value={status.mode || config.mode} />
              <h2>ข้อมูลขณะฝึก</h2>
              <LiveValues status={status} />
              <dl>
                <dt>อัตราภาพ (FPS)</dt>
                <dd>{number(frame.fps)}</dd>
                <dt>ตัวอย่างที่บันทึก</dt>
                <dd>{status.samples || 0}</dd>
              </dl>
              <p className="muted">ค่า “—” หมายถึงไม่มีข้อมูล ไม่ใช่ค่า 0</p>
              {status.error && <p className="error">{status.error}</p>}
              {exercise?.module_id === 3 && status.attempt_id && (
                <p>
                  บันทึกแล้ว {number(status.attempt_elapsed_s)} วินาที · ขั้นต่ำรวม {m3Minimum}{" "}
                  วินาที และต้องมีหลักฐานการกระทบหรือการพลาดที่ชัดเจน
                </p>
              )}
              {!automatic && (
                <div className="stack">
                  {status.attempt_id ? (
                    <>
                      <Button
                        disabled={busy || !connected || m3TooShort || m2Blocked}
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
                      disabled={
                        busy ||
                        !connected ||
                        !status.ready ||
                        activeReport?.protocol_result?.remaining === 0
                      }
                      onClick={() => run(startAttempt)}
                    >
                      เริ่มบันทึกครั้งใหม่
                    </Button>
                  )}
                  <Button
                    secondary
                    disabled={busy || !connected || !!status.attempt_id}
                    onClick={() => run(() => finishSession(false))}
                  >
                    จบรอบและดูสรุป
                  </Button>
                  <Button
                    secondary
                    disabled={busy || !connected}
                    onClick={() => run(() => finishSession(true))}
                  >
                    ยุติรอบก่อนจบแผน
                  </Button>
                </div>
              )}
              {automatic && (
                <Button
                  secondary
                  disabled={busy || !connected || autoBusy}
                  onClick={() => run(cancelM1)}
                >
                  ยกเลิกการตรวจท่าครั้งนี้
                </Button>
              )}
              {status.attempt_id && !automatic && (
                <p className="muted">จบหรือยกเลิกครั้งนี้ก่อนจบรอบ</p>
              )}
            </section>
          </div>
          <Trajectory status={status} />
          {exercise?.module_id === 1 && <ElbowDetail frame={frame} />}
          {lastAttempt && (
            <section className="panel">
              <h2>
                ผลครั้งล่าสุด <Badge value={lastAttempt.status} />
              </h2>
              <p>{lastAttempt.reason}</p>
              <Feedback items={lastAttempt.feedback} />
              <Table headings={["ตัวชี้วัด", "ค่า", "หน่วย"]}>
                {Object.entries(lastAttempt.metrics || {}).map(([key, value]) => (
                  <tr key={key}>
                    <td>{labels[key] || key}</td>
                    <td>{number(value)}</td>
                    <td>{units[key]}</td>
                  </tr>
                ))}
              </Table>
            </section>
          )}
        </>
      )}
    </>
  );
}
