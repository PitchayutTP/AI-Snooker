import { number, angleNumber } from "../lib/api";
import { M2Status } from "./M2Status";
import { BallDetectionStatus } from "./BallDetectionStatus";
export function LiveValues({ status }) {
  const frame = status.frame || {},
    live = status.live_metrics || {},
    module = status.configuration?.exercise_id;
  const shown = frame.angle_display || frame;
  const readings =
    module === 1
      ? [
          ["ท่อนแขนเอียงจากแนวดิ่ง (0° = ตั้งตรง)", shown.forearm_tilt, "°"],
          ["เข่าฝั่งแทง", shown.knee_shooting, "°"],
        ]
      : [];
  return (
    <>
      <h3>ตัวชี้วัดขณะฝึก</h3>
      {module === 2 && <M2Status status={status} />}
      {module === 1 && frame.pose_model_name && (
        <p className="muted">
          โมเดล: {frame.pose_model_name} · ประมวลผลท่าทาง {number(frame.pose_inference_ms)} ms
          ต่อเฟรม
        </p>
      )}
      {frame.smoothing_window > 1 && (
        <p className="muted">
          {frame.smoothing_method === "MEDIAN_EMA"
            ? `Median ${frame.smoothing_window} เฟรม + EMA ${frame.smoothing_time_constant_s ?? 0.35} วินาที`
            : `Moving Average ${frame.smoothing_window} เฟรม`}{" "}
          · ความล่าช้าจากการกรองโดยประมาณ {number(frame.estimated_smoothing_delay_ms)} ms
        </p>
      )}
      {module === 1 && status.configuration?.smoothing_for_evaluation && (
        <p className="muted">ผลประเมินใช้มุมที่กรองแล้ว ค่าดิบยังเก็บในหลักฐาน</p>
      )}
      {module === 1 && frame.angle_display && (
        <p className="muted">
          ตัวเลขบนหน้าจอพักเมื่อเปลี่ยนไม่เกิน 0.25° แสดงทศนิยมหนึ่งตำแหน่ง
          ผลตัดสินใช้ค่ากรองเต็มความละเอียด
        </p>
      )}
      {module === 1 ? (
        <dl>
          {readings.map(([label, value, unit]) => (
            <div className="live-reading" key={label}>
              <dt>{label}</dt>
              <dd>
                {module === 1 ? angleNumber(value) : number(value)} <small>{unit}</small>
              </dd>
            </div>
          ))}
        </dl>
      ) : module >= 3 ? (
        <BallDetectionStatus status={status} />
      ) : null}
      {module === 1 && (
        <p>
          ข้อมือต่ำกว่าศอก:{" "}
          {frame.forearm_down === true
            ? "ใช่"
            : frame.forearm_down === false
              ? "ไม่ใช่"
              : "ยังวัดไม่ได้"}{" "}
          · การก้มก่อนเริ่ม: {angleNumber(frame.torso_lean)}° จากแนวดิ่ง (ใช้เตรียมท่าเท่านั้น)
        </p>
      )}
      {module === 1 && frame.angle_display && (
        <details>
          <summary>ค่ามุมละเอียดสำหรับตรวจสอบ</summary>
          <dl>
            {[
              ["forearm_tilt", "ท่อนแขนเอียงจากแนวดิ่ง"],
              ["knee_shooting", "เข่าฝั่งแทง"],
            ].map(([key, label]) => (
              <div key={key}>
                <dt>{label}: ดิบ / กรองสำหรับตัดสิน (°)</dt>
                <dd>
                  {number(frame.raw_measurements?.[key])} / {number(frame[key])}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {status.attempt_id && !live.baseline_ready && (
        <p className="notice">
          {module >= 3
            ? "กำลังเก็บตำแหน่งลูกนิ่งในช่วงฐาน กรุณารอก่อนแทง"
            : "กำลังเก็บท่าตั้งต้น กรุณาหยุดนิ่งในช่วงฐาน"}
        </p>
      )}
      <p className="muted">
        ค่าเคลื่อนที่ระหว่างฝึกเทียบช่วงฐานของครั้งนี้ ผลเฉลี่ยและการตัดสินแสดงเมื่อจบครั้ง
      </p>
    </>
  );
}
