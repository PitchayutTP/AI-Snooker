import { number } from "../lib/api";

export function QualityReport({ attempt }) {
  const q = attempt.quality,
    timing = attempt.display_timing;
  if (!q && !timing) return null;
  return (
    <div className="quality-report">
      <h4>คุณภาพข้อมูล</h4>
      {q && (
        <p>
          ตัวอย่าง {q.samples ?? "—"} เฟรม · ช่วงบันทึก {number(q.duration_s)} วินาที ·
          เฟรมข้อมูลไม่พร้อม {q.not_ready_frames ?? "—"} · เวลาอ่านและประมวลผลเฉลี่ย{" "}
          {number(q.processing_ms?.mean)} ms
        </p>
      )}
      {q?.pose_inference_ms?.n > 0 && (
        <p>เวลาประมวลผล MediaPipe เฉลี่ย {number(q.pose_inference_ms.mean)} ms ต่อเฟรม</p>
      )}
      {q?.effective_capture_fps != null && (
        <p>
          อัตราเก็บข้อมูลครบกระบวนการ {number(q.effective_capture_fps)} FPS · บันทึกภาพดิบ{" "}
          {q.recorded_frames ?? 0} เฟรม
        </p>
      )}
      {q?.active_valid_counts && (
        <p>
          เฟรม active ที่มีข้อมูล:{" "}
          {Object.entries(q.active_valid_counts)
            .map(([key, n]) => `${key} ${n}/${q.active_samples}`)
            .join(" · ")}
        </p>
      )}
      {q?.m1_frame_assessment && (
        <p>
          M1 หลังฐาน: วัดแขนและขาร่วมกันได้ {q.m1_frame_assessment.valid_frames}/
          {q.m1_frame_assessment.active_frames} เฟรม (
          {number(q.m1_frame_assessment.valid_ratio * 100)}%) · ทำถูกพร้อมกัน{" "}
          {q.m1_frame_assessment.correct_frames}/{q.m1_frame_assessment.valid_frames} เฟรม (
          {q.m1_frame_assessment.correct_ratio == null
            ? "—"
            : number(q.m1_frame_assessment.correct_ratio * 100)}
          %)
        </p>
      )}
      {q?.m2_assessment && (
        <p>
          M2: {q.m2_assessment.reason} ·{" "}
          {q.m2_assessment.method?.startsWith("m2-red")
            ? `ระยะมาร์กเกอร์ถึงหัวคิว ${number(q.m2_assessment.tip_offset_mm)} มม. · เฟรมต่อเนื่องที่ถึงแนว ${q.m2_assessment.target_consecutive_frames ?? q.m2_assessment.red4_consecutive_frames ?? "—"}`
            : `ระยะมาร์กเกอร์ ${number(q.m2_assessment.marker_span_px)} px`}{" "}
          · ช่วงวัดหลังฐาน {number(q.m2_assessment.valid_active_seconds)} วินาที
        </p>
      )}
      {q?.m2_assessment?.gate_reason && (
        <p>
          ช่องทางน้ำเงิน: {q.m2_assessment.gate_reason} ·
          ค่าประมาณทางเรขาคณิตจากภาพและตำแหน่งแดงที่สอบเทียบ
        </p>
      )}
      {q?.m3_events?.map((event, i) => (
        <p key={i}>
          M3: {event.reason_th || event.reason || event.type}
          {event.incoming_offset != null &&
            ` · ระยะเยื้องแนวก่อนกระทบ ${number(event.incoming_offset)} หน่วยโต๊ะ`}
        </p>
      ))}
      {q?.m3_events
        ?.filter((event) => event.brief_occlusions?.length > 0)
        .map((event, i) => (
          <p key={`gap-${i}`}>
            มีจุดตรวจจับหายช่วงสั้น{" "}
            {event.brief_occlusions.reduce((sum, g) => sum + g.missing_frames, 0)} เฟรม
            ผลเป็นค่าประมาณจากตำแหน่งจริงก่อน–หลังช่วงหาย ไม่ใช่การเห็นจังหวะสัมผัสโดยตรง
          </p>
        ))}
      {timing && (
        <p>
          เวลาจากเริ่มรับภาพถึง image load ในเบราว์เซอร์ (ประมาณ): median {number(timing.median_ms)}{" "}
          ms · P95 {number(timing.p95_ms)} ms · จำนวน {timing.n} · ความไม่แน่นอนจากการเทียบเวลา ±
          {number(timing.clock_uncertainty_ms)} ms
        </p>
      )}
      <p className="muted">
        เวลานี้รวมการอ่าน/ประมวลผล/ส่งภาพและโหลดภาพ ไม่ใช่เวลาจาก sensor
        หรือการยืนยันว่าจอวาดภาพเสร็จ และข้อมูลฝั่งเบราว์เซอร์เป็นการรายงานจากไคลเอนต์
      </p>
    </div>
  );
}
