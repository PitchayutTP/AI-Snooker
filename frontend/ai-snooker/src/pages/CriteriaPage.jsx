import { Button, Badge, Table } from "../components/ui";
import { CriteriaEditor } from "../components/CriteriaEditor";
import { number } from "../lib/api";
import { labels } from "../lib/labels";
export default function CriteriaPage({ exercise, criteria, units, setPage, active, load, setCriteriaId }) {
  return (<>
            <div className="heading">
              <h1>เกณฑ์ประเมิน</h1>
              <p>
                {exercise?.name} · รุ่น {criteria?.version}
              </p>
            </div>
            <section className="panel">
              <p>{criteria?.source || "ยังไม่ระบุแหล่งที่มา"}</p>
              <Badge
                value={
                  criteria?.approved ? "ยืนยันเกณฑ์แล้ว" : "ยังไม่ยืนยันเกณฑ์"
                }
              />
              <Table
                headings={["ตัวชี้วัด", "ค่าต่ำสุด", "ค่าสูงสุด", "หน่วย"]}
              >
                {Object.entries(criteria?.rules || {}).map(([key, rule]) => (
                  <tr key={key}>
                    <td>{labels[key] || key}</td>
                    <td>{number(rule.min)}</td>
                    <td>{number(rule.max)}</td>
                    <td>{units[key]}</td>
                  </tr>
                ))}
              </Table>
              {!Object.keys(criteria?.rules || {}).length && (
                <p className="muted">ยังไม่มีเกณฑ์ตัวเลขสำหรับรุ่นนี้</p>
              )}
              <Button secondary onClick={() => setPage("setup")}>
                กลับไปตั้งค่าก่อนฝึก
              </Button>
            </section>
            <CriteriaEditor key={exercise?.id} exercise={exercise} units={units} disabled={active} onSaved={async id=>{await load();setCriteriaId(String(id))}}/>
          </>);
}
