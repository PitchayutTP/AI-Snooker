import { ProtocolStatus } from "../components/ProtocolStatus";
import { QualityReport } from "../components/QualityReport";
import { Button, Badge, Table } from "../components/ui";
import { Feedback } from "../components/Feedback";
import { number, date } from "../lib/api";
export default function SummaryPage({ report, navigate }) {
  return (<>
            <div className="heading">
              <h1>สรุปผลการฝึก</h1>
              <p>
                {report.name} · {date(report.started_at)}
              </p>
              <Badge value={report.mode} />
            </div>
            <ProtocolStatus result={report.protocol_result}/>
            <div className="stats">
              {[
                ["จำนวนครั้ง", report.attempts.length],
                ["ผ่านเกณฑ์", report.counts.PASS],
                [
                  "อัตราผ่าน",
                  report.pass_rate == null
                    ? "—"
                    : `${number(report.pass_rate * 100)}%`,
                ],
              ].map(([label, value]) => (
                <section className="panel" key={label}>
                  <p className="muted">{label}</p>
                  <strong>{value}</strong>
                </section>
              ))}
            </div>
            <section className="panel">
              <p className="muted">
                อัตราผ่านคำนวณเฉพาะครั้งที่มีผล PASS หรือ FAIL
              </p>
              <Table headings={["ครั้งที่", "ผลการประเมิน", "รายละเอียด"]}>
                {report.attempts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.number}</td>
                    <td>
                      <Badge value={a.status} />
                    </td>
                    <td>
                      {a.reason || "—"}
                      <details>
                        <summary>ค่าที่วัดได้</summary>
                        <Feedback items={a.feedback}/>
                        <QualityReport attempt={a}/>
                        {Object.entries(a.metrics).map(([key, m]) => (
                          <p key={key}>
                            {key}: {number(m.value)} {m.unit}{" "}
                            {m.reason && `(${m.reason})`}
                          </p>
                        ))}
                      </details>
                    </td>
                  </tr>
                ))}
              </Table>
              {!report.attempts.length && <p>ยังไม่มีครั้งฝึกในรอบนี้</p>}
              <div className="actions">
                <a
                  className="button secondary"
                  href={`/api/sessions/${report.id}/export`}
                  download
                >
                  ดาวน์โหลดผล JSON
                </a>
                <a className="button secondary" href={`/api/sessions/${report.id}/evidence.zip`} download>ดาวน์โหลด ZIP หลักฐานและภาพดิบ</a>
                <Button onClick={() => navigate("history")}>
                  ดูประวัติการฝึก
                </Button>
              </div>
            </section>
          </>);
}
