export function Progress({ data, catalog, onChoose, disabled }) {
  return (
    <section className="panel">
      <h2>ความก้าวหน้าการฝึก</h2>
      <p className="muted">
        จำนวนการฝึกเป็นประวัติการใช้งาน ยังไม่ยืนยันว่าทักษะดีขึ้น
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>แบบฝึก</th>
              <th>รอบที่จบ</th>
              <th>ครั้งทั้งหมด</th>
              <th>LIVE ผ่าน</th>
              <th>รอบประเมินผ่าน/ทั้งหมด</th>
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
                  <td>{item?.assessments_passed || 0}/{item?.assessments_completed || 0}</td>
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

