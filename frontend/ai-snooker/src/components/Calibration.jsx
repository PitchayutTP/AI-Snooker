import { useState } from "react";
import { api, number } from "../lib/api";
export function Calibration({ disabled, onApply, previewImage }) {
  const [image, setImage] = useState(""),
    [dimensions, setDimensions] = useState([1, 1]),
    [points, setPoints] = useState([]),
    [size, setSize] = useState({ width: "", height: "", radius: "" });
  const [result, setResult] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const steps = [
    "มุมซ้ายบน",
    "มุมขวาบน",
    "มุมขวาล่าง",
    "มุมซ้ายล่าง",
    "จุดกึ่งกลางโต๊ะที่ทำเครื่องหมายไว้ (จุดตรวจสอบอิสระ)",
  ];
  async function calculate() {
    setError("");
    setBusy(true);
    setResult(null);
    try {
      const width = Number(size.width),
        height = Number(size.height),
        radius = Number(size.radius);
      if (
        width <= 0 ||
        height <= 0 ||
        radius <= 0 ||
        radius * 2 >= Math.min(width, height)
      )
        throw new Error(
          "ระบุขนาดพื้นที่เล่นและรัศมีลูกที่เหมาะสมด้วยหน่วยเดียวกัน",
        );
      if (points.length !== 5) throw new Error("เลือกจุดบนภาพให้ครบ 5 จุด");
      const output = await api("/calibration", {
        image_points: points.slice(0, 4),
        table_width: width,
        table_height: height,
        check_image_point: points[4],
        check_table_point: [width / 2, height / 2],
      });
      setResult({
        ...output,
        table_size: [width, height],
        ball_radius: radius,
        calibration_image_size: dimensions,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function reset() {
    setPoints([]);
    setResult(null);
    setError("");
  }
  return (
    <details className="panel">
      <summary>ช่วยสอบเทียบกล้องด้านบนจากภาพถ่าย</summary>
      <p>
        ใช้ภาพเต็มจากกล้องด้านบนที่ความละเอียดเดียวกับตอนฝึก
        ทำเครื่องหมายจุดกึ่งกลางพื้นที่เล่นจริงก่อนถ่ายภาพ
        จุดนี้ใช้ตรวจสอบและไม่ได้ใช้คำนวณ homography
      </p>
      <p className="muted">
        ภาพอยู่ในเบราว์เซอร์ ไม่อัปโหลดไป Backend ระบบส่งเฉพาะพิกัดที่คลิก
        ต้องยึดกล้องและความละเอียดให้คงเดิม
      </p>
      <fieldset disabled={disabled || busy}>
        <button type="button" className="button secondary" disabled={!previewImage} onClick={()=>{reset();setImage(`data:image/jpeg;base64,${previewImage}`)}}>ใช้ภาพดิบด้านบนที่เปิดอยู่</button>
        <div className="filters">
          {[
            ["width", "ความกว้างพื้นที่เล่น"],
            ["height", "ความสูงพื้นที่เล่น"],
            ["radius", "รัศมีลูก"],
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                type="number"
                min="0"
                step="any"
                value={size[key]}
                onChange={(e) => {
                  setSize({ ...size, [key]: e.target.value });
                  setResult(null);
                }}
              />
            </label>
          ))}
        </div>
        <label className="field">
          <span>ภาพเต็มจากกล้องด้านบน (JPG / PNG ไม่เกิน 10 MB)</span>
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              reset();
              setImage("");
              if (file.size > 10000000) {
                setError("ภาพใหญ่เกิน 10 MB");
                return;
              }
              const reader = new FileReader();
              reader.onload = () => setImage(String(reader.result));
              reader.readAsDataURL(file);
            }}
          />
        </label>
        {image && (
          <>
            <p>
              {points.length < 5
                ? `คลิกจุดที่ ${points.length + 1}: ${steps[points.length]}`
                : "เลือกครบแล้ว กดคำนวณเพื่อตรวจสอบ"}
            </p>
            <div
              className="calibration-image"
              onClick={(e) => {
                if (disabled || points.length >= 5) return;
                const img = e.currentTarget.querySelector("img"),
                  rect = img.getBoundingClientRect();
                const x =
                    ((e.clientX - rect.left) * img.naturalWidth) / rect.width,
                  y =
                    ((e.clientY - rect.top) * img.naturalHeight) / rect.height;
                if (
                  x < 0 ||
                  y < 0 ||
                  x > img.naturalWidth ||
                  y > img.naturalHeight
                )
                  return;
                setPoints([...points, [x, y]]);
              }}
            >
              <img
                src={image}
                alt="ภาพกล้องสำหรับเลือกมุมโต๊ะ"
                onLoad={(e) => {
                  setDimensions([
                    e.target.naturalWidth,
                    e.target.naturalHeight,
                  ]);
                  setPoints([]);
                }}
              />
              {points.map((p, i) => (
                <span
                  key={i}
                  style={{
                    left: `${(p[0] / dimensions[0]) * 100}%`,
                    top: `${(p[1] / dimensions[1]) * 100}%`,
                  }}
                >
                  {i + 1}
                </span>
              ))}
            </div>
          </>
        )}
        <div className="actions">
          <button type="button" className="button secondary" onClick={reset}>
            เลือกจุดใหม่
          </button>
          <button
            type="button"
            className="button"
            disabled={points.length !== 5}
            onClick={calculate}
          >
            คำนวณ
          </button>
        </div>
      </fieldset>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <>
          <p className="notice">
            ความคลาดเคลื่อนที่จุดตรวจสอบ: {number(result.check_max_error)}{" "}
            หน่วยเดียวกับขนาดโต๊ะ
            ตรวจว่าเหมาะกับความแม่นยำที่ต้องใช้ก่อนนำค่าไปใช้
            จุดตรวจสอบเดียวไม่ยืนยันทั้งพื้นที่โต๊ะ
          </p>
          <button
            type="button"
            className="button"
            disabled={disabled || busy}
            onClick={() =>
              onApply({
                homography: result.homography,
                table_size: result.table_size,
                  ball_radius: result.ball_radius,
                  calibration_image_size: result.calibration_image_size,
              })
            }
          >
            นำค่าไปใช้ในการตั้งค่าเพิ่มเติม
          </button>
        </>
      )}
    </details>
  );
}

