import { number } from "../lib/api";

export function ElbowDetail({ frame = {} }) {
  const detail = frame.elbow_detail;
  if (!detail && !frame.elbow_preview?.image) return null;
  return (
    <section className="panel">
      <h2>รายละเอียดท่อนแขนฝั่งแทง</h2>
      {frame.elbow_preview?.image && (
        <img
          src={`data:image/jpeg;base64,${frame.elbow_preview.image}`}
          alt="ภาพขยายไหล่ ศอก และข้อมือฝั่งแทง"
          style={{ width: "100%", maxWidth: 640 }}
        />
      )}
      <p className="muted">
        เส้นเชื่อมไหล่–ศอก–ข้อมือ ภาพขยายจากเฟรมต้นฉบับช่วยตรวจจุด ไม่ใช่การเพิ่มความแม่นยำของโมเดล
      </p>
      {detail && (
        <>
          <p>
            {detail.valid
              ? "จุดศอก–ข้อมือแยกกันพอวัดแนวท่อนแขน"
              : "ยังวัดท่อนแขนไม่ได้ จัดให้เห็นศอกและข้อมือฝั่งแทงแยกกัน"}
          </p>
          <details>
            <summary>คุณภาพจุดศอกและค่ามุม</summary>
            <dl>
              <dt>ความมั่นใจต่ำสุดของจุดแขน (0–1)</dt>
              <dd>{number(detail.confidence)}</dd>
              <dt>ระยะไหล่ถึงศอก / ศอกถึงข้อมือ (px)</dt>
              <dd>
                {number(detail.upper_arm_px)} / {number(detail.forearm_px)}
              </dd>
              <dt>ระยะส่วนแขนขั้นต่ำในภาพ (px)</dt>
              <dd>{number(detail.minimum_segment_px)}</dd>
            </dl>
          </details>
        </>
      )}
    </section>
  );
}
