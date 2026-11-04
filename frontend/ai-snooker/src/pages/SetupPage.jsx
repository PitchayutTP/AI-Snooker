import { M2Status } from "../components/M2Status";
import { BallDetectionStatus } from "../components/BallDetectionStatus";
import { CameraSetup } from "../components/CameraSetup";
import { Calibration } from "../components/Calibration";
import { M1Setup } from "../components/M1Setup";
import { RecordTrialOption } from "../components/RecordTrialOption";
import { Button, Field, Table } from "../components/ui";
import { TrialLayout } from "../components/TrialLayout";
import { Guide } from "../components/Guide";
import { labels } from "../lib/labels";
import { isPrototypeCriteria } from "../lib/moduleSettings";
import { M3_CALIBRATION_LIMIT_MM } from "../lib/m3Preparation";
import { api } from "../lib/api";
import { moduleConfig } from "../lib/moduleSettings";
import { M2_CALIBRATION_LIMIT_MM } from "../lib/table";

export default function SetupPage(props) {
  const {
    exercise,
    exerciseId,
    catalog,
    choose,
    criteria,
    criteriaId,
    setCriteriaId,
    setPage,
    config,
    setConfig,
    advanced,
    setAdvanced,
    status,
    frame,
    active,
    busy,
    connected,
    prepared,
    fingerprint,
    run,
    checkReady,
    startSession,
    startM3,
    setPrepared,
    setError,
    finishSession,
    setCalibrating,
  } = props;
  const moduleId = exercise?.module_id;
  if (moduleId === 1) return <M1Setup {...props} />;
  const disabled = active || busy;
  const cameras = ["top"];
  const currentCriteria = (value) =>
    isPrototypeCriteria(value) &&
    value.template_version === (moduleId === 2 ? "m2-red-gate-single-v3" : "m3-contact-v4");
  const selected = currentCriteria(criteria) ? criteria : null;
  const plan = selected?.protocol || { required_valid_attempts: 1, minimum_pass_rate: 1 };
  const rules =
    selected?.rules ||
    (moduleId === 2
      ? {
          m2_red4_reached: { min: 1 },
          m2_gate_clear: { min: 1 },
        }
      : { fraction_error: { max: 0.1 } });
  function apply(values) {
    try {
      const current = JSON.parse(advanced);
      if (!current || Array.isArray(current) || typeof current !== "object")
        throw new Error("การตั้งค่าต้องเป็น JSON object");
      setAdvanced(JSON.stringify({ ...current, ...values }, null, 2));
      setPrepared("");
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <>
      <div className="heading">
        <h1>เตรียมฝึก M{moduleId}</h1>
        <p>
          {moduleId === 2
            ? "ฝึกส่งคิวตรงต่อเนื่องหลังสัมผัสลูกน้ำเงิน"
            : "เลือกเหลี่ยม กล้อง และสีลูก แล้วสอบเทียบโต๊ะ"}
        </p>
      </div>
      {active && (
        <section className="notice">
          <p>มีรอบฝึกเปิดอยู่ จึงล็อกการเลือกจุดและเปลี่ยนการสอบเทียบ</p>
          <Button disabled={busy || !connected} secondary onClick={() => setPage("training")}>
            กลับไปฝึกหรือจบรอบ
          </Button>
          <Button
            disabled={busy || !connected}
            secondary
            onClick={() => run(() => finishSession(true))}
          >
            ยุติรอบเพื่อสอบเทียบใหม่
          </Button>
        </section>
      )}
      <section className="panel">
        <h2>อุปกรณ์และแบบฝึก</h2>
        <RecordTrialOption {...{ config, setConfig, setPrepared, disabled }} />
        {moduleId === 3 && (
          <Field label="เหลี่ยมที่ต้องการฝึก">
            <select
              value={exerciseId}
              disabled={disabled}
              onChange={(e) => choose(catalog.find((ex) => String(ex.id) === e.target.value))}
            >
              {catalog
                .filter((ex) => ex.module_id === 3)
                .map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.name}
                  </option>
                ))}
            </select>
          </Field>
        )}
        {moduleId === 2 && (
          <Field label="ระยะศูนย์กลางมาร์กเกอร์ด้านหน้าไปถึงหัวคิว (มม.)">
            <input
              type="number"
              min="0"
              max="1000"
              step="any"
              disabled={disabled}
              value={(() => {
                try {
                  return JSON.parse(advanced).m2_tip_offset_mm ?? "";
                } catch {
                  return "";
                }
              })()}
              onChange={(e) =>
                apply({
                  m2_mode: "RED_GATE3",
                  m2_tip_offset_mm: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </Field>
        )}
        {cameras.map((camera) => (
          <Field
            key={camera}
            label={camera === "side" ? "หมายเลขกล้องด้านข้าง" : "หมายเลขกล้องด้านบน"}
          >
            <input
              disabled={disabled}
              value={config[`${camera}_source`]}
              onChange={(e) => setConfig({ ...config, [`${camera}_source`]: e.target.value })}
            />
          </Field>
        ))}
        <p className="notice">
          {moduleId === 2
            ? "ใช้กล้องบนตัวเดียว แดงสองแถวข้างละ 3 ลูกชิดกัน เว้นช่องให้น้ำเงินผ่านกลางพร้อมระยะเผื่อ วางน้ำเงินตรงแดงคู่แรก หัวคิวหลังน้ำเงิน เลือกสีมาร์กเกอร์ น้ำเงิน แดง และกลางแดงซ้าย 1–3 ขวา 1–3 สอบเทียบพื้นที่แล้วแทงเบาถึงปานกลาง น้ำเงินต้องพ้นคู่ที่ 3 และหัวคิวต้องส่งถึงแนวคู่ที่ 3"
            : "ใช้กล้องบนตัวเดียว ใช้ลูกน้ำเงินเป็นลูกแทงและลูกแดงเป็นเป้า เลือกสีจากภาพจริง แล้วสอบเทียบพื้นที่เล่น ใช้ลูกทั้งสองขนาดเดียวกัน"}
        </p>
      </section>
      <CameraSetup
        key={moduleId}
        moduleId={moduleId}
        cameras={cameras}
        config={config}
        setConfig={setConfig}
        advanced={advanced}
        onAdvanced={setAdvanced}
        status={status}
        disabled={disabled || !connected}
        onReset={() => setPrepared("")}
      />
      <Calibration
        previewImage={frame.preview_camera === "top" ? frame.image : null}
        cameraError={status.error}
        disabled={disabled || !connected}
        onApply={(values) => {
          apply(values);
          setCalibrating?.(false);
        }}
        onOpenPreview={async () => {
          setCalibrating?.(true);
          setPrepared("");
          try {
            await api("/cameras/preview", {
              camera: "top",
              detect_balls: false,
              config: moduleConfig(moduleId, config),
            });
          } catch (error) {
            setCalibrating?.(false);
            throw error;
          }
        }}
        maxCheckError={moduleId === 3 ? M3_CALIBRATION_LIMIT_MM : M2_CALIBRATION_LIMIT_MM}
      />
      <section className="panel">
        <h2>เกณฑ์ M{moduleId}</h2>
        <Field label="เกณฑ์ประเมิน">
          <select
            disabled={disabled}
            value={selected ? criteriaId : ""}
            onChange={(e) => setCriteriaId(e.target.value)}
          >
            <option value="">
              {moduleId === 3
                ? "เกณฑ์ต้นแบบ — เหลี่ยมละ 1 ครั้งที่ประเมินได้"
                : "เกณฑ์ต้นแบบ — 1 ครั้งที่ประเมินได้"}
            </option>
            {exercise?.criteria.filter(currentCriteria).map((c) => (
              <option key={c.id} value={c.id}>
                รุ่น {c.version} — ยืนยันแล้ว
              </option>
            ))}
          </select>
        </Field>
        <Table headings={["ตัวชี้วัด", "ต่ำสุด", "สูงสุด", "หน่วย"]}>
          {Object.entries(rules).map(([key, rule]) => (
            <tr key={key}>
              <td>{labels[key] || key}</td>
              <td>{rule.min ?? "—"}</td>
              <td>{rule.max ?? "—"}</td>
              <td>
                {["m2_red4_reached", "m2_gate_clear"].includes(key)
                  ? "1 = ถึงแนวเป้าหมาย"
                  : key.endsWith("_ratio") || key === "fraction_error" || key === "contact_fraction"
                    ? "สัดส่วน"
                    : "พิกเซล"}
              </td>
            </tr>
          ))}
        </Table>
        <p>
          ผ่านอย่างน้อย {Math.ceil(plan.required_valid_attempts * plan.minimum_pass_rate - 1e-9)}{" "}
          จาก {plan.required_valid_attempts} ครั้งที่ประเมินได้ ข้อมูลไม่ครบไม่นับ{" "}
          {moduleId === 3
            ? "ต้องผ่านครบเต็มใบ, 3/4, 1/2 และ 1/4 จึงครบ M3"
            : "หัวคิวประมาณต้องถึงแนวศูนย์กลางแดงคู่ที่ 3 อย่างน้อย 2 เฟรมต่อเนื่อง ภายใน 1.5 วินาทีหลังลูกน้ำเงินเริ่มเคลื่อน ต้องเห็นน้ำเงินพ้นช่องโดยแนวไม่เข้าเขตแดงด้วย เป็นค่าประมาณจากภาพ ใช้ภาพย้อนหลังดูความตรงของแนวคิว"}
        </p>
        <p className="muted">เป็นเกณฑ์ต้นแบบ ไม่ใช่มาตรฐานสากลหรือการรับรองทักษะ</p>
        <Button secondary disabled={disabled} onClick={() => setPage("criteria")}>
          ดูหรือแก้ไขเกณฑ์
        </Button>
      </section>
      <section className="panel">
        <h2>ตรวจและเริ่มฝึก</h2>
        <p>
          ระบบตั้ง LIVE การประเมิน และค่าประมวลผลให้แล้ว{" "}
          {moduleId === 2
            ? "นิ่งฐาน 1 วินาที แทงลูกน้ำเงินเปล่าและส่งคิวตามถึงแนวแดงคู่ที่ 3 คงคิวให้เห็นครบ 1.5 วินาทีหลังลูกเริ่มเคลื่อน แล้วกดจบ ไม่ต้องชนลูกแดง"
            : "พื้นที่ฝึกคงที่ 1500 × 750 มม. รัศมีลูก 26.25 มม. เลือกจุดสอบเทียบจากภาพจริง"}
        </p>
        {status.error && <p className="error">{status.error}</p>}
        {moduleId === 3 && (
          <p className="notice">
            หลังใช้ผลสอบเทียบ ระบบตรวจจับและเตรียมเกณฑ์ให้อัตโนมัติ
            เมื่อลูกน้ำเงินกับลูกแดงแยกกันและนิ่งครบ 0.5 วินาที ปุ่มเริ่มฝึกและบันทึกจะกดได้
            กดแล้วนิ่งช่วงฐาน 1 วินาทีก่อนแทง
          </p>
        )}
        <div className="actions">
          <Button
            secondary
            disabled={disabled || !connected || !exercise}
            onClick={() => run(checkReady)}
          >
            {moduleId === 3 ? "ตรวจความพร้อมอีกครั้ง" : "ตรวจความพร้อมและใช้เกณฑ์ต้นแบบ"}
          </Button>
          <Button
            disabled={
              disabled || !connected || !status.ready || prepared !== fingerprint || !criteria
            }
            onClick={() => run(moduleId === 3 ? startM3 : startSession)}
          >
            {moduleId === 3 ? "เริ่มฝึกและบันทึก" : "เริ่มรอบฝึก"}
          </Button>
        </div>
        <p>
          {!connected
            ? "กำลังเชื่อมต่อ Backend"
            : prepared !== fingerprint
              ? moduleId === 3
                ? "เลือกสีและใช้ผลสอบเทียบพื้นที่ ระบบจะตรวจความพร้อมให้อัตโนมัติ"
                : "เตรียมอุปกรณ์แล้วกดตรวจความพร้อม"
              : status.ready
                ? "พร้อมเริ่มรอบฝึก"
                : "กำลังรอผลตรวจจับครบ"}
        </p>
        {moduleId === 2 && prepared === fingerprint && connected && <M2Status status={status} />}
        {moduleId === 3 && prepared === fingerprint && connected && (
          <BallDetectionStatus status={status} />
        )}
        {prepared === fingerprint && connected && !active && (
          <div aria-live="polite">
            {frame.image && (
              <img
                src={`data:image/jpeg;base64,${frame.image}`}
                alt="ภาพตรวจความพร้อม"
                style={{ width: "100%" }}
              />
            )}
            {!status.ready && (
              <ul>
                {(status.readiness_issues || []).map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
      <details className="panel">
        <summary>วิธีทำแบบฝึกและการจัดลูก</summary>
        <Guide exercise={exercise} />
        <TrialLayout exercise={exercise} advanced={advanced} />
      </details>
    </>
  );
}
