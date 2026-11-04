import { useState } from "react";
import { api, number } from "../lib/api";
import { PRACTICE_AREA } from "../lib/table";
export function Calibration({
  disabled,
  onApply,
  previewImage,
  cameraError,
  maxCheckError,
  onOpenPreview,
}) {
  const [image, setImage] = useState(""),
    [dimensions, setDimensions] = useState([1, 1]),
    [points, setPoints] = useState([]);
  const size = PRACTICE_AREA;
  const [result, setResult] = useState(null),
    [applied, setApplied] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const steps = [
    "มุมซ้ายบน",
    "มุมขวาบน",
    "มุมขวาล่าง",
    "มุมซ้ายล่าง",
    "จุดกึ่งกลางพื้นที่ฝึกที่ทำเครื่องหมายไว้ (จุดตรวจสอบอิสระ)",
  ];
  async function calculate() {
    setError("");
    setBusy(true);
    setResult(null);
    setApplied(false);
    try {
      const width = Number(size.width),
        height = Number(size.height),
        radius = Number(size.radius);
      if (
        width <= 0 ||
        height <= 0 ||
        radius <= 0 ||
        ![width, height, radius].every(Number.isFinite) ||
        radius * 2 >= Math.min(width, height)
      )
        throw new Error("ระบุขนาดพื้นที่เล่นและรัศมีลูกที่เหมาะสมด้วยหน่วยเดียวกัน");
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
  async function openPreview() {
    setError("");
    setBusy(true);
    try {
      await onOpenPreview();
      reset();
      setImage("");
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="panel">
      <summary>เลือกจุดสอบเทียบพื้นที่ฝึกจากกล้องบน</summary>
      <p>
        เปิดภาพกล้อง → บันทึกภาพนิ่งสำหรับสอบเทียบ → เลือกมุมพื้นที่ 4 จุดและจุดกึ่งกลางที่วัดไว้ →
        คำนวณ → ใช้ผลสอบเทียบนี้
      </p>
      <p>พื้นที่ฝึกกำหนดคงที่ 1,500 × 750 มม. ลูกเส้นผ่านศูนย์กลาง 52.5 มม. รัศมี 26.25 มม.</p>
      <p className="notice">
        แนวนอนของภาพ {size.width} มม. × แนวตั้ง {size.height} มม. รัศมีลูก {size.radius} มม.
        เลือกมุมของพื้นที่ฝึกทั้งสี่ และทำเครื่องหมายกึ่งกลางที่ระยะ 750 × 375 มม.
      </p>
      <p>
        ใช้ภาพเต็มจากกล้องด้านบนที่ความละเอียดเดียวกับตอนฝึก
        ทำเครื่องหมายจุดกึ่งกลางพื้นที่เล่นจริงก่อนถ่ายภาพ จุดนี้ใช้ตรวจสอบและไม่ได้ใช้คำนวณ
        homography
      </p>
      <p className="muted">
        ภาพอยู่ในเบราว์เซอร์ ไม่อัปโหลดไป Backend ระบบส่งเฉพาะพิกัดที่คลิก
        ต้องยึดกล้องและความละเอียดให้คงเดิม
      </p>
      <fieldset disabled={disabled || busy}>
        {onOpenPreview && (
          <button type="button" className="button secondary" onClick={openPreview}>
            เปิดภาพกล้องบนเพื่อสอบเทียบ
          </button>
        )}
        {previewImage && !image && (
          <img
            src={`data:image/jpeg;base64,${previewImage}`}
            alt="ภาพสดกล้องบนสำหรับสอบเทียบ"
            style={{ display: "block", width: "100%", margin: "12px 0" }}
          />
        )}
        {cameraError && (
          <p className="error" role="status">
            {cameraError}
          </p>
        )}
        {!previewImage && <p>กดเปิดภาพกล้องบนก่อน แล้วรอภาพปรากฏเพื่อหยุดภาพเลือกจุด</p>}
        <button
          type="button"
          className="button secondary"
          disabled={!previewImage}
          onClick={() => {
            reset();
            setImage(`data:image/jpeg;base64,${previewImage}`);
          }}
        >
          บันทึกภาพนิ่งสำหรับสอบเทียบ
        </button>
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
                const x = ((e.clientX - rect.left) * img.naturalWidth) / rect.width,
                  y = ((e.clientY - rect.top) * img.naturalHeight) / rect.height;
                if (x < 0 || y < 0 || x > img.naturalWidth || y > img.naturalHeight) return;
                setPoints([...points, [x, y]]);
              }}
            >
              <img
                src={image}
                alt="ภาพกล้องสำหรับเลือกมุมโต๊ะ"
                onLoad={(e) => {
                  setDimensions([e.target.naturalWidth, e.target.naturalHeight]);
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
          {result.check_max_error > (maxCheckError ?? result.ball_radius * 0.25) && (
            <p className="error">
              ยังใช้ผลนี้ไม่ได้ จุดกึ่งกลางคลาดเคลื่อนเกินเกณฑ์ ตรวจขนาดพื้นที่และเลือกจุดใหม่
            </p>
          )}
          {applied && (
            <p className="notice" role="status">
              ใช้ผลสอบเทียบแล้ว ให้จัดลูกทั้งสองในพื้นที่และตรวจความพร้อมก่อนเริ่ม
            </p>
          )}
          <p className="notice">
            ความคลาดเคลื่อนที่จุดตรวจสอบ: {number(result.check_max_error)} หน่วยเดียวกับขนาดโต๊ะ
            เกณฑ์นำร่องไม่เกิน {number(maxCheckError ?? result.ball_radius * 0.25)} มม.
            หากเกินต้องเลือกจุดใหม่ จุดตรวจสอบเดียวไม่ยืนยันทั้งพื้นที่โต๊ะ
          </p>
          {maxCheckError != null && result.check_max_error > result.ball_radius * 0.25 && (
            <p className="notice">
              ใช้เกณฑ์ผ่อนปรนสำหรับทดลอง ความคลาดเคลื่อนเกินเกณฑ์เดิม
              ผลเหลี่ยมยังต้องตรวจเทียบข้อมูลอ้างอิง และพื้นที่ที่เลือกต้องตรงกับขนาด 1500 × 750 มม.
            </p>
          )}
          <button
            type="button"
            className="button"
            disabled={
              disabled ||
              busy ||
              result.check_max_error > (maxCheckError ?? result.ball_radius * 0.25)
            }
            onClick={() => {
              onApply({
                homography: result.homography,
                table_size: result.table_size,
                ball_radius: result.ball_radius,
                calibration_image_size: result.calibration_image_size,
                calibration_check_error: result.check_max_error,
              });
              setApplied(true);
            }}
          >
            ใช้ผลสอบเทียบนี้
          </button>
        </>
      )}
    </details>
  );
}
