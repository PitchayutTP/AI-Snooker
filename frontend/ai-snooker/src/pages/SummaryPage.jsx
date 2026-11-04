import { ProtocolStatus } from "../components/ProtocolStatus";
import { QualityReport } from "../components/QualityReport";
import { Button, Badge, Table } from "../components/ui";
import { Feedback } from "../components/Feedback";
import { number, date } from "../lib/api";
import { moduleCompletion } from "../lib/moduleCompletion";
export default function SummaryPage({
  report,
  navigate,
  progress = [],
  catalog = [],
  choose,
  active = false,
  busy = false,
}) {
  const exercise = catalog.find((ex) => ex.id === report.exercise_id);
  const moduleId = exercise?.module_id;
  const completion = moduleId ? moduleCompletion(moduleId, progress, catalog) : null;
  return (
    <>
      <div className="heading">
        <h1>สรุปผลการฝึก</h1>
        <p>
          {report.name} · {date(report.started_at)}
        </p>
        <Badge value={report.mode} />
      </div>
      {exercise && report.status !== "IN_PROGRESS" && (
        <div className="actions">
          <Button disabled={active || busy} onClick={() => choose(exercise)}>
            เริ่มฝึกแบบเดิมอีกครั้ง
          </Button>
        </div>
      )}
      <ProtocolStatus result={report.protocol_result} />
      {report.criteria?.source && (
        <details className="panel">
          <summary>เกณฑ์ที่ใช้ในรอบนี้</summary>
          <p>{report.criteria.source}</p>
        </details>
      )}
      {completion && (
        <section className="notice">
          <h2>
            M{moduleId}:{" "}
            {completion.status === "PASS"
              ? "ผ่านครบตามเกณฑ์"
              : completion.status === "DIFFERENT_SETTINGS"
                ? "ค่าตั้งแต่ละแบบต่างกัน ยังรวมเป็นผลผ่านโมดูลไม่ได้"
                : "ยังผ่านไม่ครบโมดูล"}
          </h2>
          <p>
            แบบฝึกที่ผ่านรอบล่าสุด {completion.passed}/{completion.total}{" "}
            ผลนี้แสดงการผ่านเกณฑ์ที่เลือก ไม่ใช่การรับรองทักษะ
          </p>
          {moduleId === 3 && (
            <div className="actions">
              {catalog
                .filter(
                  (ex) =>
                    ex.module_id === 3 &&
                    progress.find((row) => row.exercise_id === ex.id)?.latest_assessment_status !==
                      "PASS",
                )
                .map((ex) => (
                  <Button key={ex.id} secondary onClick={() => choose(ex)}>
                    ฝึก {ex.name}
                  </Button>
                ))}
            </div>
          )}
        </section>
      )}
      <div className="stats">
        {[
          ["จำนวนครั้ง", report.attempts.length],
          ["ผ่านเกณฑ์", report.counts.PASS],
          ["อัตราผ่าน", report.pass_rate == null ? "—" : `${number(report.pass_rate * 100)}%`],
        ].map(([label, value]) => (
          <section className="panel" key={label}>
            <p className="muted">{label}</p>
            <strong>{value}</strong>
          </section>
        ))}
      </div>
      <section className="panel">
        <p className="muted">อัตราผ่านคำนวณเฉพาะครั้งที่มีผล PASS หรือ FAIL</p>
        <Table headings={["ครั้งที่", "ผลการประเมิน", "รายละเอียด"]}>
          {report.attempts.map((a) => (
            <tr key={a.id}>
              <td>{a.number}</td>
              <td>
                <Badge value={a.status} />
              </td>
              <td>
                {a.reason || "—"}
                {a.quality?.recording_error && <p className="error">{a.quality.recording_error}</p>}
                {(Object.keys(a.videos || {}).length > 0 || a.quality?.recorded_frames > 0) && (
                  <details>
                    <summary>คลิปจากกล้อง</summary>
                    <a
                      className="button secondary"
                      href={`/api/attempts/${a.id}/clip.webm`}
                      target="_blank"
                      rel="noopener"
                    >
                      เปิดคลิปครั้งที่ {a.number}
                    </a>
                  </details>
                )}
                <details>
                  <summary>ค่าที่วัดได้</summary>
                  <Feedback items={a.feedback} />
                  <QualityReport attempt={a} />
                  {Object.entries(a.metrics).map(([key, m]) => (
                    <p key={key}>
                      {key}: {number(m.value)} {m.unit} {m.reason && `(${m.reason})`}
                    </p>
                  ))}
                </details>
              </td>
            </tr>
          ))}
        </Table>
        {!report.attempts.length && <p>ยังไม่มีครั้งฝึกในรอบนี้</p>}
        <div className="actions">
          <a className="button secondary" href={`/api/sessions/${report.id}/export`} download>
            ดาวน์โหลดผล JSON
          </a>
          <a className="button secondary" href={`/api/sessions/${report.id}/evidence.zip`} download>
            ดาวน์โหลด ZIP หลักฐานและวิดีโอ
          </a>
          <Button onClick={() => navigate("history")}>ดูประวัติการฝึก</Button>
        </div>
      </section>
    </>
  );
}
