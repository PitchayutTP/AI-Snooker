import { Button, Field, Badge, Table } from "../components/ui";
import { api, number, date } from "../lib/api";
import { labels } from "../lib/labels";
import { useState } from "react";
export default function HistoryPage({
  history,
  page,
  historyFilter,
  setHistoryFilter,
  catalog,
  visibleHistory,
  busy,
  setReport,
  setPage,
  pair,
  setPair,
  setComparison,
  run,
  comparison,
  units,
  deleteSession,
}) {
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [deleteMessage, setDeleteMessage] = useState("");
  const [cleanupOnly, setCleanupOnly] = useState(false);
  async function confirmDelete() {
    setDeleting(true);
    setDeleteError("");
    setDeleteMessage("");
    try {
      const result = await deleteSession(pendingDelete.id);
      if (result.cleanup_complete) {
        setPendingDelete(null);
        setDeleteMessage("ลบประวัติ ผลวัด และไฟล์หลักฐานของรอบนี้แล้ว");
      } else {
        setCleanupOnly(true);
        setDeleteError(
          "ลบประวัติแล้ว แต่ไฟล์บางส่วนยังลบไม่ได้ ปิดคลิปที่เปิดอยู่แล้วลองลบไฟล์ที่เหลืออีกครั้ง",
        );
      }
    } catch (error) {
      setDeleteError(error.message);
    } finally {
      setDeleting(false);
    }
  }
  return (
    <>
      <div className="heading">
        <h1>{page === "history" ? "ประวัติการฝึก" : "เปรียบเทียบผลการฝึก"}</h1>
        <p className="muted">แสดงผลจากบัญชีของคุณเท่านั้น</p>
      </div>
      {page === "history" && pendingDelete && (
        <section className="panel">
          <h2>{cleanupOnly ? "ลบไฟล์หลักฐานที่เหลือ" : "ยืนยันลบประวัติรอบนี้"}</h2>
          <p>
            {pendingDelete.name} · {date(pendingDelete.started_at)}
          </p>
          <p>ลบผลวัด ภาพ และวิดีโอของรอบนี้ การลบย้อนกลับไม่ได้</p>
          <div className="actions">
            <Button disabled={busy || deleting} onClick={confirmDelete}>
              {deleting
                ? "กำลังลบ…"
                : cleanupOnly
                  ? "ลองลบไฟล์ที่เหลืออีกครั้ง"
                  : "ยืนยันลบรายการนี้"}
            </Button>
            <Button
              secondary
              disabled={deleting}
              onClick={() => {
                setPendingDelete(null);
                setDeleteError("");
              }}
            >
              {cleanupOnly ? "ปิด" : "ยกเลิก"}
            </Button>
          </div>
        </section>
      )}
      {page === "history" && deleteError && (
        <p className="error" role="alert">
          {deleteError}
        </p>
      )}
      {page === "history" && deleteMessage && (
        <p className="notice" role="status">
          {deleteMessage}
        </p>
      )}
      {page === "history" ? (
        <section className="panel">
          <div className="filters">
            <label>
              แบบฝึก
              <select
                value={historyFilter.exercise}
                onChange={(e) =>
                  setHistoryFilter({
                    ...historyFilter,
                    exercise: e.target.value,
                  })
                }
              >
                <option value="">ทั้งหมด</option>
                {catalog.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              ตั้งแต่
              <input
                type="date"
                value={historyFilter.from}
                onChange={(e) => setHistoryFilter({ ...historyFilter, from: e.target.value })}
              />
            </label>
            <label>
              ถึง
              <input
                type="date"
                min={historyFilter.from}
                value={historyFilter.to}
                onChange={(e) => setHistoryFilter({ ...historyFilter, to: e.target.value })}
              />
            </label>
            <label>
              โหมด
              <select
                value={historyFilter.mode}
                onChange={(e) => setHistoryFilter({ ...historyFilter, mode: e.target.value })}
              >
                <option value="">ทั้งหมด</option>
                <option>DEMO</option>
                <option>LIVE</option>
              </select>
            </label>
          </div>
          <Table headings={["วันและเวลา", "แบบฝึก", "โหมด", "สถานะ", "รายละเอียด"]}>
            {visibleHistory.map((s) => (
              <tr key={s.id}>
                <td>{date(s.started_at)}</td>
                <td>{s.name}</td>
                <td>
                  <Badge value={s.mode} />
                </td>
                <td>
                  <Badge value={s.status} />
                </td>
                <td>
                  <Button
                    secondary
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        const report = await api(`/sessions/${encodeURIComponent(s.id)}`);
                        setReport(report);
                        setPage("summary", { report });
                      })
                    }
                  >
                    ดูผล
                  </Button>
                  <Button
                    secondary
                    disabled={busy || deleting || s.status === "IN_PROGRESS"}
                    onClick={() => {
                      setPendingDelete(s);
                      setCleanupOnly(false);
                      setDeleteError("");
                      setDeleteMessage("");
                    }}
                  >
                    ลบ
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
          {!visibleHistory.length && (
            <p className="empty">ยังไม่มีประวัติ เริ่มฝึกเพื่อบันทึกผลครั้งแรก</p>
          )}
        </section>
      ) : (
        <section className="panel">
          <p className="notice">เลือกรอบที่จบแล้วและใช้แบบฝึก รุ่นเกณฑ์ และการตั้งค่าเดียวกัน</p>
          <div className="columns">
            {[0, 1].map((i) => (
              <Field label={`รอบ ${i === 0 ? "A" : "B"}`} key={i}>
                <select
                  value={pair[i]}
                  onChange={(e) => {
                    setPair((p) => p.map((v, n) => (n === i ? e.target.value : v)));
                    setComparison(null);
                  }}
                >
                  <option value="">เลือกรอบฝึก</option>
                  {history
                    .filter((s) => s.status === "COMPLETED")
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} · {date(s.started_at)} · {s.id.slice(0, 8)}
                      </option>
                    ))}
                </select>
              </Field>
            ))}
          </div>
          <Button
            disabled={busy || !pair[0] || !pair[1] || pair[0] === pair[1]}
            onClick={() =>
              run(async () => {
                setComparison(null);
                setComparison(
                  await api(
                    `/compare?left=${encodeURIComponent(pair[0])}&right=${encodeURIComponent(pair[1])}`,
                  ),
                );
              })
            }
          >
            เปรียบเทียบผล
          </Button>
          {comparison && (
            <>
              <p>
                {comparison.note} · {comparison.mode}
              </p>
              <Table
                headings={[
                  "ตัวชี้วัด",
                  "ค่าเฉลี่ย A",
                  "จำนวน A",
                  "ค่าเฉลี่ย B",
                  "จำนวน B",
                  "ผลต่าง B − A",
                  "หน่วย",
                ]}
              >
                {Object.entries(comparison.metrics).map(([key, value]) => (
                  <tr key={key}>
                    <td>{labels[key] || key}</td>
                    <td>{number(value.left.mean)}</td>
                    <td>{value.left.n}</td>
                    <td>{number(value.right.mean)}</td>
                    <td>{value.right.n}</td>
                    <td>{number(value.difference)}</td>
                    <td>{units[key]}</td>
                  </tr>
                ))}
              </Table>
            </>
          )}
        </section>
      )}
    </>
  );
}
