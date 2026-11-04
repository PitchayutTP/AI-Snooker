import { number } from "../lib/api";
export function M2Status({ status }) {
  if (status.configuration?.exercise_id !== 2) return null;
  const frame = status.frame || {},
    markers = frame.marker_detection,
    trial = frame.m2_trial;
  const prep = frame.m2_preparation;
  return (
    <section aria-live="polite">
      <h3>สถานะการวัดระยะส่งคิว M2</h3>
      <p>
        มาร์กเกอร์ปลายคิว: {markers?.status === "OK" ? "พบหนึ่งจุด" : "ยังไม่พบ"} · จุดอ้างอิงแดง{" "}
        {frame.m2_reference_points?.length ?? 0}/6 จุด · ลูกน้ำเงิน{" "}
        {frame.balls?.filter((b) => b.class === "cue_ball").length ?? 0} ลูก
      </p>
      <p>
        หัวคิวประมาณเทียบแนวแดงคู่ที่ 3: {number(frame.m2_tip_margin_mm)} มม. (ลบ = ยังไม่ถึง, 0
        หรือบวก = ถึงแนว)
      </p>
      {!status.attempt_id && prep && (
        <p>
          {prep.state === "READY"
            ? "พร้อมเริ่มบันทึก"
            : `รอคิวและลูกน้ำเงินนิ่ง ${number(prep.stable_seconds)} / 0.5 วินาที`}
        </p>
      )}
      {status.attempt_id && (
        <p className={trial?.state === "INVALID" ? "error" : "notice"}>
          {trial?.state === "INVALID" ? "ประเมินไม่ได้ ให้ลองใหม่ · " : ""}
          {trial?.reason || "นิ่งฐาน 1 วินาทีก่อนแทง"}
        </p>
      )}
      <p className="muted">
        ต้องถึงแนวแดงคู่ที่ 3 หลังลูกน้ำเงินเริ่มเคลื่อนอย่างน้อยสองเฟรมต่อเนื่อง
        และน้ำเงินผ่านพ้นคู่ที่ 3 โดยแนวไม่เข้าเขตแดง เก็บหลังเริ่มเคลื่อน 1.5 วินาที
        คงคิวต่ำใกล้ผ้าและให้น้ำเงินผ่านกลางช่องไม่ชนแดง เป็นการประมาณหัวคิวจากมาร์กเกอร์ในภาพ
      </p>
      <p className="muted">
        จัดคิวขนานกับแถวแดง 1 ไป 3 ระบบประมาณระยะจากมาร์กเกอร์ถึงหัวคิวตามแนวแถวแดง ใช้แดงทั้ง 6
        จุดเป็นอ้างอิงคงที่ ตรวจทางผ่านน้ำเงินจากภาพจริง เป็นค่าประมาณในภาพ
        ยืนยันการสัมผัสจริงไม่ได้ หากใกล้ขอบหรือภาพขาดให้ลองใหม่
      </p>
    </section>
  );
}
