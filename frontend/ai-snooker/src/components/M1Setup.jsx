import { Button, Field, Table } from "./ui";
import { CameraSetup } from "./CameraSetup";
import { labels } from "../lib/labels";
import { isTimedM1Criteria } from "../lib/m1AutoTrial";
import { ElbowDetail } from "./ElbowDetail";
import { RecordTrialOption } from "./RecordTrialOption";

export function M1Setup({
  exercise,
  criteria,
  criteriaId,
  setCriteriaId,
  config,
  setConfig,
  status,
  frame,
  active,
  busy,
  connected,
  m1Auto,
  prepareM1,
  cancelM1,
  run,
  setPrepared,
  setAdvanced,
  setPage,
}) {
  const counting = m1Auto?.phase === "COUNTDOWN";
  const waiting = m1Auto?.phase === "WAITING" || counting;
  const disabled = active || busy || waiting || m1Auto?.phase === "STARTING";
  const selected = isTimedM1Criteria(criteria) ? criteria : null;
  const rules = selected?.frame_rules || {
    forearm_tilt: { max: 15 },
    knee_shooting: { min: 160, max: 180 },
  };
  return (
    <>
      <div className="heading">
        <h1>เตรียมฝึก M1</h1>
        <p>เลือกมือ กล้อง และเกณฑ์ จากนั้นเริ่มตรวจท่าได้เลย</p>
      </div>
      <section className="panel">
        <h2>มือที่ถนัดและหมายเลขกล้อง</h2>
        <RecordTrialOption {...{ config, setConfig, setPrepared, disabled }} />
        <Field label="มือที่ถนัด">
          <select
            disabled={disabled}
            value={config.hand}
            onChange={(e) => setConfig({ ...config, hand: e.target.value })}
          >
            <option value="RIGHT">ขวา</option>
            <option value="LEFT">ซ้าย</option>
          </select>
        </Field>
        <Field label="หมายเลขกล้องด้านข้าง">
          <input
            disabled={disabled}
            value={config.side_source}
            onChange={(e) => setConfig({ ...config, side_source: e.target.value })}
          />
        </Field>
      </section>
      <CameraSetup
        moduleId={1}
        cameras={["side"]}
        config={config}
        setConfig={setConfig}
        advanced="{}"
        onAdvanced={setAdvanced}
        status={status}
        disabled={disabled || !connected}
        onReset={() => setPrepared("")}
      />
      <section className="panel">
        <h2>เกณฑ์ M1</h2>
        <Field label="เกณฑ์สำหรับตรวจท่า 8 วินาที">
          <select
            disabled={disabled}
            value={selected ? criteriaId : ""}
            onChange={(e) => setCriteriaId(e.target.value)}
          >
            <option value="">เกณฑ์ต้นแบบ — ท่อนแขนใกล้แนวดิ่ง และขาฝั่งแทง</option>
            {exercise?.criteria.filter(isTimedM1Criteria).map((c) => (
              <option key={c.id} value={c.id}>
                รุ่น {c.version} — ยืนยันแล้ว
              </option>
            ))}
          </select>
        </Field>
        <Table headings={["ตัวชี้วัด", "ต่ำสุด", "สูงสุด", "หน่วย"]}>
          {Object.entries(rules).map(([key, rule]) => (
            <tr key={key}>
              <td>
                {{ forearm_tilt: "ท่อนแขนเอียงจากแนวดิ่ง", knee_shooting: "มุมเข่าฝั่งแทง" }[key] ||
                  labels[key] ||
                  key}
              </td>
              <td>{rule.min ?? "—"}</td>
              <td>{rule.max ?? "—"}</td>
              <td>องศา</td>
            </tr>
          ))}
        </Table>
        <p>
          ข้อมือต้องต่ำกว่าศอก ต้องวัดแขนและเข่าร่วมกันได้อย่างน้อย 80% ของเฟรมหลังฐาน
          และทำถูกพร้อมกันอย่างน้อย 80% ของเฟรมที่วัดได้ ข้อมูลไม่พอเป็น INVALID ทำผิดเกณฑ์เป็น FAIL
          ประเมินหนึ่งครั้งจบรอบ มุมเป็นมุมฉายในภาพและเกณฑ์นำร่อง ไม่ใช่มาตรฐานสากล
        </p>
        <Button secondary disabled={disabled} onClick={() => setPage("criteria")}>
          ดูหรือแก้ไขเกณฑ์
        </Button>
      </section>
      <section className="panel">
        <h2>เริ่มฝึก</h2>
        <p className="muted">
          จุดที่ใช้: ไหล่–ศอก–ข้อมือฝั่งถือคิว และสะโพก–เข่า–ข้อเท้าฝั่งแทง
          ตั้งกล้องด้านข้างฝั่งแทงให้ตรงระดับ การก้มอย่างน้อย 30° จากแนวดิ่งใช้เป็นเงื่อนไขก่อนเริ่ม
          ไม่ใช้ตัดสินระหว่างบันทึก ไม่ตรวจคางหรือขาฝั่งสะพานมือ ระบบไม่ใช้จุดเก่าทดแทนจุดที่หาย
        </p>
        <p>
          เมื่อก้มเตรียมท่าและจุดครบต่อเนื่อง 1 วินาที จะเตรียมตัว 5 วินาที แล้วบันทึก 8
          วินาทีและสรุปผลอัตโนมัติ ช่วงเตรียมตัวไม่รวมในเวลาบันทึก
        </p>
        <details>
          <summary>รายละเอียดการวัดและตัวกรอง</summary>
          <p>
            ใช้ MediaPipe Full ตรวจคนเดียว ความมั่นใจการตรวจ/ติดตาม 0.6 และจุดร่างกาย 0.6
            ส่วนแขนและขาต้องยาวอย่างน้อย max(20 px, 3% ของด้านสั้นภาพ)
            ไม่ใช้ช่วงที่เล็กหรือซ้อนกันวัดมุม ค่าเหล่านี้เป็นการตั้งต้นที่ต้องตรวจจากภาพจริง
          </p>
          <p>
            Median 15 เฟรม + EMA 0.8 วินาที ทั้งแสดงผลและตัดสิน หน่วงโดยประมาณ 1–1.5 วินาทีที่ 10–30
            FPS จุดที่หายไม่ถูกเติมทดแทน เก็บค่าดิบไว้ตรวจสอบ
          </p>
          <p>
            พักจุดบนภาพภายใน 1.5 พิกเซล และพักตัวเลขภายใน 0.25° เฉพาะหน้าจอ
            ผลตัดสินใช้ค่ากรองเต็มความละเอียด รีเซ็ตตัวกรองเมื่อเฟรมห่างเกิน 0.75 วินาที
          </p>
        </details>
        {status.error && <p className="error">{status.error}</p>}
        <Button disabled={disabled || !connected || !exercise} onClick={() => run(prepareM1)}>
          เริ่มตรวจท่าอัตโนมัติ 8 วินาที
        </Button>
        {waiting && (
          <>
            {counting ? (
              <div className="notice" role="timer" aria-live="polite">
                <strong style={{ fontSize: "2rem" }}>
                  เตรียมตัว {m1Auto.remaining ?? 5} วินาที
                </strong>
                <p>ยังไม่บันทึก จัดท่าให้นิ่งและอยู่ในภาพ หากจุดหายหรือยืนขึ้นจะกลับไปรอใหม่</p>
              </div>
            ) : (
              <p role="status">กำลังรอจุดร่างกายครบและก้มเตรียมท่า</p>
            )}
            <Button secondary onClick={cancelM1}>
              ยกเลิกการรอ
            </Button>
            {frame.image && (
              <img
                src={`data:image/jpeg;base64,${frame.image}`}
                alt="ภาพตรวจความพร้อม M1"
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
          </>
        )}
        {!connected && <p className="notice">กำลังเชื่อมต่อข้อมูลสดกับ Backend</p>}
      </section>
      {waiting && <ElbowDetail frame={frame} />}
    </>
  );
}
