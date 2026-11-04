import { moduleCompletion } from "../lib/moduleCompletion";
export function Progress({ data, catalog, onChoose, disabled }) {
  return (
    <section className="panel">
      <h2>ความก้าวหน้าการฝึก</h2>
      <p className="muted">จำนวนการฝึกเป็นประวัติการใช้งาน ยังไม่ยืนยันว่าทักษะดีขึ้น</p>
      <div className="columns">
        {[1, 2, 3].map((id) => {
          const completion = moduleCompletion(id, data, catalog);
          return (
            <div key={id} className="notice">
              <strong>
                M{id}:{" "}
                {completion.status === "PASS"
                  ? "ผ่านครบตามเกณฑ์"
                  : completion.status === "DIFFERENT_SETTINGS"
                    ? "ค่าตั้งต่างกัน ต้องเก็บให้เทียบกันได้"
                    : "ยังไม่ครบ"}
              </strong>
              <p>
                แบบฝึกที่ผ่านล่าสุด {completion.passed}/{completion.total}
              </p>
              {id === 3 && (
                <p>
                  ต้องผ่านเต็มใบ, 3/4, 1/2 และ 1/4 ครบทั้งสี่ โดยใช้เกณฑ์และค่าตั้งที่เทียบกันได้
                </p>
              )}
            </div>
          );
        })}
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>แบบฝึก</th>
              <th>รอบที่จบ</th>
              <th>ครั้งทั้งหมด</th>
              <th>LIVE ผ่าน</th>
              <th>รอบประเมินผ่าน/ทั้งหมด</th>
              <th>ผลรอบประเมินล่าสุด</th>
              <th>ฝึกต่อ</th>
            </tr>
          </thead>
          <tbody>
            {catalog.map((ex) => {
              const item = data.find((x) => x.exercise_id === ex.id);
              return (
                <tr key={ex.id}>
                  <td>{ex.name}</td>
                  <td>{item?.sessions || 0}</td>
                  <td>{item?.attempts || 0}</td>
                  <td>{item?.live_pass || 0}</td>
                  <td>
                    {item?.assessments_passed || 0}/{item?.assessments_completed || 0}
                  </td>
                  <td>
                    {item?.latest_assessment_status === "PASS"
                      ? "ผ่าน"
                      : item?.latest_assessment_status === "FAIL"
                        ? "ไม่ผ่าน"
                        : "ยังไม่มีผล"}
                    {item?.latest_assessment_scope === "PROTOTYPE" && " (เกณฑ์ต้นแบบ)"}
                  </td>
                  <td>
                    <button
                      className="button secondary"
                      disabled={disabled}
                      onClick={() => onChoose(ex)}
                    >
                      เลือก
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
