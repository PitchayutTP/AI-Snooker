import { useState, useEffect } from "react";
export function Trajectory({ status }) {
  const [trace, setTrace] = useState({ attempt: null, tracks: {} });
  const frame = status.frame,
    attempt = status.attempt_id;
  useEffect(() => {
    if (!attempt || !frame?.balls?.length) return;
    setTrace((old) => {
      const tracks = old.attempt === attempt ? { ...old.tracks } : {};
      for (const ball of frame.balls) {
        const key = ball.class + ":" + ball.id;
        const points = tracks[key] || [];
        if (points.at(-1)?.t !== frame.t)
          tracks[key] = [...points, { t: frame.t, xy: ball.xy }].slice(-300);
      }
      return { attempt, tracks };
    });
  }, [frame, attempt]);
  const [width, height] = status.configuration?.table_size || [];
  if (!width || !height) return null;
  const tracks = trace.attempt === attempt ? trace.tracks : {};
  return (
    <section className="panel">
      <h2>เส้นทางลูกระหว่างบันทึก</h2>
      <p className="muted">
        แสดงจุดที่ตรวจจับได้สูงสุด 300 จุดต่อเส้นจาก WebSocket ไม่ใช่ภาพทุกเฟรม
        หลักฐานใน JSON ใช้ข้อมูลที่ Backend บันทึก
      </p>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="trajectory"
        role="img"
        aria-label="เส้นทางลูกในพิกัดโต๊ะ"
      >
        <rect width={width} height={height} fill="#e8eeeb" />
        {Object.entries(tracks).map(([key, points]) => (
          <polyline
            key={key}
            points={points.map((p) => p.xy.join(",")).join(" ")}
            fill="none"
            stroke={key.startsWith("cue_ball") ? "#344b6b" : "#b65050"}
            strokeWidth={width / 250}
          />
        ))}
      </svg>
      <p className="muted">สีน้ำเงิน: ลูกขาว · สีแดง: ลูกเป้า</p>
    </section>
  );
}
