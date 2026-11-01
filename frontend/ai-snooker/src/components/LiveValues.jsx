import { number,angleNumber } from "../lib/api";
export function LiveValues({ status }) {
  const frame = status.frame || {},
    live = status.live_metrics || {},
    module = status.configuration?.exercise_id;
  const shown=frame.angle_display || frame;
  const readings = module===1 ? [
    ['มุมศอก',shown.elbow,'°'],['เข่าฝั่งแทง',shown.knee_shooting,'°'],
  ] : [
    ["มุมศอก", frame.elbow, "°"],
    ["ศีรษะจากช่วงฐาน", live.head_displacement, "px"],
    ["สะพานมือจากช่วงฐาน", live.bridge_displacement, "px"],
    ["คิวจากแนวตั้งต้น", live.cue_deviation, "px"],
  ];
  return (
    <>
      <h3>ตัวชี้วัดขณะฝึก</h3>
      {frame.smoothing_window>1 && <p className="muted">{frame.smoothing_method==='MEDIAN_EMA' ? `Median ${frame.smoothing_window} เฟรม + EMA ${frame.smoothing_time_constant_s ?? .35} วินาที` : `Moving Average ${frame.smoothing_window} เฟรม`} · ความล่าช้าจากการกรองโดยประมาณ {number(frame.estimated_smoothing_delay_ms)} ms</p>}
      {module===1 && status.configuration?.smoothing_for_evaluation && <p className="muted">ผลประเมินใช้มุมที่กรองแล้ว ค่าดิบยังเก็บในหลักฐาน</p>}
      {module===1 && frame.angle_display && <p className="muted">ตัวเลขบนหน้าจอพักเมื่อเปลี่ยนไม่เกิน 0.25° แสดงทศนิยมหนึ่งตำแหน่ง ผลตัดสินใช้ค่ากรองเต็มความละเอียด</p>}
      {module <= 2 ? (
        <dl>
          {readings.map(([label, value, unit]) => (
            <div className="live-reading" key={label}>
              <dt>{label}</dt>
              <dd>
                {module===1 ? angleNumber(value) : number(value)} <small>{unit}</small>
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>ลูกที่ตรวจจับและติดตามได้: {(frame.balls || []).length}</p>
      )}
      {module===1 && frame.angle_display && <details><summary>ค่ามุมละเอียดสำหรับตรวจสอบ</summary><dl>
        {[['elbow','ศอก'],['knee_shooting','เข่าฝั่งแทง']].map(([key,label])=><div key={key}><dt>{label}: ดิบ / กรองสำหรับตัดสิน (°)</dt><dd>{number(frame.raw_measurements?.[key])} / {number(frame[key])}</dd></div>)}
      </dl></details>}
      {status.attempt_id && !live.baseline_ready && (
        <p className="notice">กำลังเก็บท่าตั้งต้น กรุณาหยุดนิ่งในช่วงฐาน</p>
      )}
      <p className="muted">
        ค่าเคลื่อนที่ระหว่างฝึกเทียบช่วงฐานของครั้งนี้
        ผลเฉลี่ยและการตัดสินแสดงเมื่อจบครั้ง
      </p>
    </>
  );
}

