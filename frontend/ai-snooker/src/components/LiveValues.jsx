import { number } from "../lib/api";
export function LiveValues({ status }) {
  const frame = status.frame || {},
    live = status.live_metrics || {},
    module = status.configuration?.exercise_id;
  const readings = [
    ["มุมศอก", frame.elbow, "°"],
    ["มุมลำตัว", frame.torso, "°"],
    ["ระยะข้อเท้า", frame.stance, "px"],
    ["ศีรษะจากช่วงฐาน", live.head_displacement, "px"],
    ["สะพานมือจากช่วงฐาน", live.bridge_displacement, "px"],
    ["คิวจากแนวตั้งต้น", live.cue_deviation, "px"],
  ];
  return (
    <>
      <h3>ตัวชี้วัดขณะฝึก</h3>
      {module <= 2 ? (
        <dl>
          {readings.map(([label, value, unit]) => (
            <div className="live-reading" key={label}>
              <dt>{label}</dt>
              <dd>
                {number(value)} <small>{unit}</small>
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>ลูกที่ตรวจจับและติดตามได้: {(frame.balls || []).length}</p>
      )}
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

