import { number } from "../lib/api";
const states = {
  OK: "พบหนึ่งลูก",
  MISSING: "ยังไม่พบลูกที่ผ่านการกรอง",
  AMBIGUOUS: "พบหลายวัตถุ",
  COLOUR_OVERLAP: "ช่วงสีซ้อนกัน",
};
export function BallDetectionStatus({ status }) {
  const frame = status.frame || {},
    balls = frame.balls || [],
    roles = frame.ball_detection?.roles;
  const module = status.configuration?.exercise_id;
  if (!(module >= 3 && module <= 6) && !frame.detection_preview) return null;
  const cueLabel = status.configuration?.cue_ball_colour === "BLUE" ? "ลูกน้ำเงิน" : "ลูกขาว";
  const labels = { cue_ball: cueLabel, target_ball: "ลูกแดง" };
  const trial = frame.m3_trial;
  return (
    <section aria-live="polite">
      <h3>การตรวจจับลูก M3</h3>
      <p>
        {frame.ball_detection?.detector || status.configuration?.ball_detector || "—"} · ต้องใช้
        {cueLabel}และลูกแดงอย่างละหนึ่งลูก
      </p>
      <dl>
        {Object.entries(labels).map(([role, label]) => {
          const list = balls.filter((b) => b.class === role),
            d = roles?.[role];
          return (
            <div key={role}>
              <dt>{label}</dt>
              <dd>
                {d ? states[d.status] || d.status : `ตรวจพบ ${list.length} ลูก`}
                {list.length === 1 && ` · ID ${list[0].id ?? "—"}`}
              </dd>
              {d && d.status !== "OK" && (
                <>
                  <dd>
                    พิกเซลสี {d.mask_pixels} · วัตถุที่ผ่าน {d.candidates} ·
                    ตัดจากพื้นที่พิกเซล/รูปร่าง/ขนาด/นอกพื้นที่สอบเทียบ: {d.rejected.area}/
                    {d.rejected.shape}/{d.rejected.size}/{d.rejected.outside ?? 0}
                  </dd>
                  {d.raw_mask_pixels > 0 && !d.mask_pixels && (
                    <dd>
                      พบสีในภาพ แต่ไม่มีสีที่เหลือผ่านพื้นที่สอบเทียบและตัวกรอง
                      ตรวจว่าลูกอยู่ในกรอบพื้นที่
                    </dd>
                  )}
                  {d.size_examples?.map((s, i) => (
                    <dd key={i}>
                      วัตถุที่ถูกตัด: เส้นผ่านศูนย์กลางจากสเกลสอบเทียบประมาณ{" "}
                      {number(s.equivalent_diameter)} มม. เทียบค่าลูกที่ตั้ง{" "}
                      {number(s.expected_diameter)} มม. · รัศมีในภาพ {number(s.image_radius_px)} px
                      — ตรวจขนาดพื้นที่จริงก่อนเปลี่ยนรัศมีลูก
                    </dd>
                  ))}
                </>
              )}
            </div>
          );
        })}
      </dl>
      {frame.ball_detection?.calibrated && (
        <p className="muted">
          กรอบสีฟ้าคือพื้นที่สอบเทียบ {frame.ball_detection.table_size?.join(" × ")} มม.
          ให้ลูกทั้งลูกอยู่ภายในกรอบ ขนาดวัตถุที่แสดงเป็นค่าจากสเกลสอบเทียบ
          ยังไม่ยืนยันว่าการสอบเทียบถูกต้อง
        </p>
      )}
      {frame.m3_preparation && !status.attempt_id && (
        <p>
          {frame.m3_preparation.state === "READY"
            ? "ลูกแยกกันและนิ่ง พร้อมเริ่ม"
            : frame.m3_preparation.state === "TOUCHING"
              ? "แยกลูกทั้งสองก่อนเริ่ม"
              : `รอลูกทั้งสองนิ่ง: ${number(frame.m3_preparation.stable_seconds)} / 0.5 วินาที`}
        </p>
      )}
      {status.attempt_id && trial && (
        <p className={trial.state === "INVALID" ? "error" : "notice"} role="status">
          {trial.reason}
          {trial.detected_events > 0 &&
            ` · พบเหตุการณ์ ${trial.detected_events} ครั้ง · เหลี่ยมประมาณ ${number(trial.contact_fraction)}`}
        </p>
      )}
      <p className="muted">
        {frame.detection_preview
          ? "โหมดทดลองสีและรูปร่าง ยังไม่กรองขนาดจริงบนโต๊ะ ไม่วัดเหลี่ยม และไม่บันทึกคะแนน ต้องสอบเทียบก่อนเริ่มฝึกจริง"
          : "การพบลูกยังไม่ยืนยันการกระทบ หลังเริ่มบันทึกให้นิ่ง 1 วินาทีก่อนแทง แล้วให้เห็นแนวลูกน้ำเงินก่อนชนและลูกแดงเคลื่อนออกหลังชน เมื่อยืนยันแล้วลูกแดงออกจากภาพได้ ระบบจะสรุปบันทึกเมื่อหลักฐานครบ ใช้ปุ่มจบการบันทึกเป็นทางเลือกสำรอง"}
      </p>
    </section>
  );
}
