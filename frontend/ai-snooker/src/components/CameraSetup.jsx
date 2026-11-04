import { useState } from "react";
import { api } from "../lib/api";
import { Button, Field } from "./ui";
import { moduleCaptureConfig } from "../lib/moduleSettings";
import { BallDetectionStatus } from "./BallDetectionStatus";

import {
  hsvAt,
  ranges,
  validateBallColour,
  M3_BALL_COLOURS,
  blueBallRanges,
} from "../lib/cameraColour";

export function CameraSetup({
  moduleId,
  cameras = ["side", "top"],
  config,
  setConfig,
  advanced,
  onAdvanced,
  status,
  disabled,
  onReset,
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [role, setRole] = useState(() =>
    moduleId === 2 && status.frame?.preview_camera !== "top" ? "marker_tip" : "cue_ball",
  );
  const [frozen, setFrozen] = useState(null);
  const frame = status.frame || {};
  const preview = frame.preview_only && cameras.includes(frame.preview_camera) ? frame : null;
  const current = frozen || preview;
  const usesTop = cameras.includes("top");
  const selectable = moduleId !== 1 && !current?.detection_preview;
  const roles =
    current?.preview_camera === "side"
      ? []
      : [
          ...(moduleId === 2
            ? [["marker_tip", "สีมาร์กเกอร์ใกล้ปลายคิว (เลือกสีต่างจากลูกน้ำเงิน)"]]
            : []),
          ["cue_ball", "สีลูกน้ำเงิน"],
          ...([2, 3].includes(moduleId) ? [["target_ball", "สีลูกแดง"]] : []),
          ...(moduleId === 2
            ? [1, 2, 3, 4, 5, 6].map((n) => [
                `red_${n}`,
                `ศูนย์กลางแดง${n <= 3 ? "ซ้าย" : "ขวา"}ลูกที่ ${((n - 1) % 3) + 1} (นับออกจากผู้แทง)`,
              ])
            : []),
        ];
  function extra() {
    const value = JSON.parse(advanced);
    if (!value || Array.isArray(value) || typeof value !== "object")
      throw new Error("การตั้งค่าต้องเป็น JSON object");
    return value;
  }
  function apply(patch) {
    onAdvanced(JSON.stringify({ ...extra(), ...patch }, null, 2));
    onReset();
  }
  async function action(task) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function previewCamera(camera, detectBalls = false) {
    setFrozen(null);
    setRole(camera === "side" ? "marker_tip" : "cue_ball");
    onReset();
    await api("/cameras/preview", {
      camera,
      detect_balls: detectBalls,
      config: moduleCaptureConfig(moduleId, config, advanced),
    });
  }
  function pick(event) {
    if (disabled || busy || !current || !selectable) return;
    try {
      const picked = hsvAt(event.currentTarget, event),
        settings = extra(),
        side = current.preview_camera === "side";
      if (role.startsWith("red_")) {
        if (side) throw new Error("เลือกแถวลูกแดงจากภาพบน");
        const index = Number(role.split("_")[1]) - 1;
        const points = [...(settings.m2_red_points || Array(6).fill(null))];
        points[index] = picked.xy;
        apply({ m2_red_points: points });
        if (index < 5) setRole(`red_${index + 2}`);
      } else if (role.startsWith("marker")) {
        if (!side && moduleId !== 2) throw new Error("เลือกสีมาร์กเกอร์จากภาพด้านข้าง");
        const choices = ranges(picked.hsv);
        if (choices.length !== 1)
          throw new Error("สีนี้คร่อมช่วงแดง เลือกมาร์กเกอร์สีอื่น เช่น สีเหลือง");
        apply({ cue_markers: [{ ...choices[0], min_area: 10 }] });
      } else {
        if (side) throw new Error("เลือกสีลูกจากภาพด้านบน");
        validateBallColour(role, picked.hsv, "BLUE");
        const colours = settings.ball_colours || M3_BALL_COLOURS;
        apply({
          ball_detector: "HSV",
          cue_ball_colour: "BLUE",
          ball_colours: {
            ...colours,
            [role]:
              role === "cue_ball" ? blueBallRanges(picked.hsv) : ranges(picked.hsv, false, true),
          },
        });
      }
      setMessage(
        `เลือกแล้ว (ค่ากลางพื้นที่ 5×5 พิกเซล): พิกัด ${picked.xy.join(", ")} / HSV ${picked.hsv.join(", ")} ตรวจผลจริงอีกครั้งหลังนำไปใช้`,
      );
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <section className="panel camera-setup">
      <h2>ตั้งค่ากล้อง M{moduleId}</h2>
      <p className="muted">
        {moduleId === 1
          ? "เปิดภาพด้านข้างและจัดให้เห็นจุดร่างกายครบ แล้วกดเริ่มตรวจท่าได้เลย"
          : "เปิดภาพ หยุดภาพแล้วเลือกสีจากกลางวัตถุที่ไม่มีแสงสะท้อน"}
      </p>
      <fieldset disabled={disabled || busy}>
        <details>
          <summary>แก้ปัญหากล้อง / ความละเอียด / DSHOW</summary>
          <div className="filters">
            {[
              ["capture_width", "ความกว้างภาพ", 1280],
              ["capture_height", "ความสูงภาพ", 720],
              ["capture_fps", "FPS ที่ร้องขอ", 30],
            ].map(([key, label, value]) => (
              <Field key={key} label={label}>
                <input
                  type="number"
                  value={config[key] ?? value}
                  onChange={(e) => {
                    setConfig({ ...config, [key]: Number(e.target.value) });
                    onReset();
                  }}
                />
              </Field>
            ))}
            <Field label="วิธีเปิดกล้อง">
              <select
                value={config.camera_backend || "AUTO"}
                onChange={(e) => {
                  setConfig({ ...config, camera_backend: e.target.value });
                  onReset();
                }}
              >
                <option>AUTO</option>
                <option>DSHOW</option>
                <option>MSMF</option>
              </select>
            </Field>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={!!config.camera_mjpeg}
              onChange={(e) => {
                setConfig({ ...config, camera_mjpeg: e.target.checked });
                onReset();
              }}
            />
            ร้องขอ MJPEG สำหรับเว็บแคมที่รองรับ
          </label>
        </details>
        <div className="actions">
          {cameras.map((camera) => (
            <Button key={camera} type="button" onClick={() => action(() => previewCamera(camera))}>
              {camera === "side" ? "ดูภาพดิบด้านข้าง" : "ดูภาพดิบด้านบน"}
            </Button>
          ))}
          <Button
            type="button"
            secondary
            onClick={() =>
              action(async () => {
                await api("/cameras/stop", {});
                setFrozen(null);
                onReset();
              })
            }
          >
            ปิดกล้อง
          </Button>
        </div>
        {moduleId === 3 && (
          <>
            <Button
              type="button"
              secondary
              onClick={() => action(() => previewCamera("top", true))}
            >
              ทดลองตรวจจับสีลูก — ไม่ต้องสอบเทียบ
            </Button>
            <p className="muted">
              เลือกสีจากภาพดิบก่อน แล้วกดทดลองตรวจจับ ตรวจเฉพาะสีและรูปร่างในภาพ ยังไม่วัดระยะ
              เหลี่ยม หรือบันทึกผลฝึก หากต้องการเลือกสีใหม่ให้กดดูภาพดิบด้านบน
            </p>
          </>
        )}
        {current?.image && (
          <>
            <p>
              ภาพ{current.preview_camera === "side" ? "ด้านข้าง" : "ด้านบน"} · ขนาดจริง{" "}
              {current.image_size?.join(" × ")} px
            </p>
            {selectable && (
              <div className="actions">
                <Button
                  type="button"
                  secondary
                  onClick={() => setFrozen({ ...preview })}
                  disabled={!preview}
                >
                  หยุดภาพเพื่อเลือกจุด
                </Button>
                <Button type="button" secondary onClick={() => setFrozen(null)}>
                  กลับภาพสด
                </Button>
                <a
                  className="button secondary"
                  download={`camera-${current.preview_camera}.jpg`}
                  href={`data:image/jpeg;base64,${current.image}`}
                >
                  ดาวน์โหลดภาพสอบเทียบ
                </a>
              </div>
            )}
            {selectable && roles.length > 0 && (
              <Field label="สิ่งที่จะเลือกจากภาพ">
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  {roles.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <img
              className="setup-preview"
              src={`data:image/jpeg;base64,${current.image}`}
              alt={
                current.detection_preview
                  ? "ภาพทดลองตรวจจับสีลูก ไม่ใช้ประเมินเหลี่ยม"
                  : selectable
                    ? "คลิกเลือกสีหรือจุดบนภาพกล้องดิบ"
                    : "ภาพกล้องด้านข้าง"
              }
              onClick={selectable ? pick : undefined}
            />
          </>
        )}
        {moduleId === 2 && usesTop && (
          <p className="muted">
            เลือกมาร์กเกอร์ใกล้ปลายคิวหนึ่งจุด ลูกน้ำเงิน และกลางแดงซ้าย 1–3 ขวา 1–3
            จากภาพบนเดียวกัน อย่าย้ายแถวแดงหรือกล้องหลังตั้งค่า
            หัวคิวประมาณจากมาร์กเกอร์และระยะที่วัดจริง คิวต้องอยู่ต่ำและกล้องใกล้มุมบน
          </p>
        )}
        {moduleId === 2 && (
          <Button
            type="button"
            secondary
            onClick={() => action(async () => apply({ m2_red_points: [] }))}
          >
            ล้างจุดอ้างอิงแดงทั้ง 6 ลูก เพื่อเลือกใหม่
          </Button>
        )}
        {moduleId === 3 && preview?.detection_preview && <BallDetectionStatus status={status} />}
      </fieldset>
      {busy && <p role="status">กำลังเปิดกล้อง/ดำเนินการ…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p className="notice">{message}</p>}
    </section>
  );
}
