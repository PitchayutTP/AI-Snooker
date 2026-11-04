export function TrialLayout({ exercise, advanced }) {
  if (exercise?.module_id === 2)
    return (
      <section className="panel">
        <h2>แบบฝึก M2: ส่งคิวตรงต่อเนื่อง</h2>
        <ol>
          <li>
            ใช้ลูกน้ำเงิน 1 ลูก แดงสองแถวข้างละ 3 ลูกชิดกัน เว้นช่องกลางให้ผ่านพร้อมระยะเผื่อ
            วางน้ำเงินตรงคู่แรกและหัวคิวหลังน้ำเงิน
          </li>
          <li>
            กล้องบนเห็นคิว มาร์กเกอร์ และลูกครบ สอบเทียบพื้นที่ เลือกกลางแดงซ้าย 1–3 ขวา 1–3
            และกรอกระยะมาร์กเกอร์หน้าถึงหัวคิวจริง
          </li>
          <li>
            เริ่มบันทึก นิ่งฐาน 1 วินาที จากนั้นแทงกลางลูกน้ำเงินด้วยแรงปานกลาง
            ส่งหัวคิวตามถึงแนวขวางศูนย์กลางแดงคู่ที่ 3 ให้น้ำเงินผ่านกลางช่องไม่ชนแดง
            คงคิวให้เห็นครบ 1.5 วินาทีหลังลูกน้ำเงินเริ่มเคลื่อน
          </li>
          <li>
            ต้องถึงแนวอย่างน้อย 2 เฟรมต่อเนื่อง และน้ำเงินผ่านพ้นคู่ที่ 3
            โดยมีระยะเผื่อไม่เข้าเขตแดง ประเมิน 1 ครั้งแล้วจบรอบ ผ่านเมื่อถึงเกณฑ์
            ข้อมูลไม่ครบให้ลองใหม่
          </li>
        </ol>
        <p>
          วัดหัวคิวโดยประมาณจากมาร์กเกอร์และระยะที่กรอก ใช้กล้องบนและคงคิวต่ำใกล้ผ้า แนวแดงคู่ที่ 3
          เป็นเกณฑ์ระยะของแบบฝึก ดูภาพย้อนหลังเพื่อเทียบความตรงกับแนวแทง
        </p>
      </section>
    );
  if (exercise?.module_id !== 3) return null;
  let settings;
  try {
    settings = JSON.parse(advanced);
  } catch {
    return null;
  }
  const [w, h] = settings.table_size || [],
    r = settings.ball_radius;
  if (!w || !h || !r || w < 10 * r || h < 8 * r)
    return <p className="notice">สอบเทียบโต๊ะก่อน เพื่อดูแผนผังจัดลูกในหน่วยจริง</p>;
  const f = exercise.setup.fraction,
    target = [w * 0.65, h * 0.5],
    cue = [w * 0.25, target[1] + 2 * r * (1 - f)];
  const format = (value) => Number(value.toFixed(2));
  return (
    <section className="panel">
      <h2>แผนผังตั้งลูกสำหรับทดลองเหลี่ยม {f}</h2>
      <p>
        ตัวอย่างตำแหน่งที่ระบบสร้างสำหรับทดลอง ไม่ใช่มาตรฐานจากหนังสือ ใช้หน่วยเดียวกับที่สอบเทียบ
        และแทงลูกน้ำเงินตามเส้นประให้ตรงในแนวนอน
      </p>
      <svg
        className="trajectory"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label="แผนผังจัดลูกทดลอง"
      >
        <rect width={w} height={h} fill="#e8eeeb" />
        <line
          x1={cue[0]}
          y1={cue[1]}
          x2={target[0] + 3 * r}
          y2={cue[1]}
          stroke="#344b6b"
          strokeWidth={w / 500}
          strokeDasharray={`${r} ${r / 2}`}
        />
        <circle cx={target[0]} cy={target[1]} r={r} fill="#b65050" />
        <circle
          cx={cue[0]}
          cy={cue[1]}
          r={r}
          fill="#2463ce"
          stroke="#344b6b"
          strokeWidth={w / 800}
        />
      </svg>
      <p>
        อ้างอิงมุมซ้ายบนที่คลิกสอบเทียบ: ลูกน้ำเงิน ({cue.map(format).join(", ")}) · ลูกเป้า (
        {target.map(format).join(", ")})
      </p>
      <p className="muted">
        ตำแหน่งนี้เป็นแนวทางจัดอุปกรณ์ เป้าหมายการประเมินคือเหลี่ยมกระทบ ไม่ใช่การลงหลุม
      </p>
    </section>
  );
}
