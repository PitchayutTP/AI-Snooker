import { useState } from "react";
import { api } from "../lib/api";
import { labels } from "../lib/labels";
export function CriteriaEditor({ exercise, units, disabled, onSaved }) {
  const [rows, setRows] = useState([]),
    [source, setSource] = useState(""),
    [approved, setApproved] = useState(false);
  const [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const [useProtocol, setUseProtocol] = useState(false);
  const [protocol, setProtocol] = useState({
    required_valid_attempts: "",
    minimum_pass_percent: "",
    rationale: "",
  });
  const [minimumSeconds, setMinimumSeconds] = useState("");
  const [scope, setScope] = useState("REPORT"),
    [templateVersion, setTemplateVersion] = useState(null);
  const [frameDefinition, setFrameDefinition] = useState({});
  const options = exercise?.lesson?.metrics || [];
  async function loadTemplate() {
    setSaving(true);
    setError("");
    try {
      const template = await api(`/exercises/${exercise.id}/criteria-template`);
      setRows(
        Object.entries(template.rules).map(([code, rule]) => ({
          code,
          min: rule.min ?? "",
          max: rule.max ?? "",
        })),
      );
      setFrameDefinition(
        template.frame_rules
          ? {
              frame_rules: template.frame_rules,
              minimum_valid_frame_ratio: template.minimum_valid_frame_ratio,
              preparation_lean_min: template.preparation_lean_min,
            }
          : {},
      );
      setSource(template.source);
      setScope(template.validation_scope || "REPORT");
      setTemplateVersion(template.template_version || null);
      setApproved(false);
      setMinimumSeconds(String(template.minimum_active_seconds));
      setUseProtocol(true);
      setProtocol({
        required_valid_attempts: String(template.protocol.required_valid_attempts),
        minimum_pass_percent: String(template.protocol.minimum_pass_rate * 100),
        rationale: template.protocol.rationale,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  function update(index, key, value) {
    setRows(rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const rules = {};
      for (const row of rows) {
        if (!row.code || rules[row.code]) throw new Error("เลือกตัวชี้วัดไม่ซ้ำกัน");
        if (row.min === "" && row.max === "")
          throw new Error("ระบุค่าต่ำสุดหรือค่าสูงสุดอย่างน้อยหนึ่งค่า");
        const rule = {};
        for (const key of ["min", "max"])
          if (row[key] !== "") {
            const n = Number(row[key]);
            if (!Number.isFinite(n)) throw new Error("เกณฑ์ต้องเป็นตัวเลข");
            rule[key] = n;
          }
        if (rule.min !== undefined && rule.max !== undefined && rule.min > rule.max)
          throw new Error("ค่าต่ำสุดต้องไม่มากกว่าค่าสูงสุด");
        rules[row.code] = rule;
      }
      if (approved && !rows.length) throw new Error("ต้องเพิ่มตัวชี้วัดก่อนยืนยันเกณฑ์");
      let plan;
      if (useProtocol) {
        const n = Number(protocol.required_valid_attempts),
          rate = Number(protocol.minimum_pass_percent);
        if (
          !Number.isInteger(n) ||
          n < 1 ||
          n > 1000 ||
          !Number.isFinite(rate) ||
          rate <= 0 ||
          rate > 100 ||
          protocol.rationale.trim().length < 5
        )
          throw new Error(
            "ระบุ N (1–1000) อัตราผ่าน (มากกว่า 0 ถึง 100%) และที่มาของแผนอย่างน้อย 5 ตัวอักษร",
          );
        plan = {
          required_valid_attempts: n,
          minimum_pass_rate: rate / 100,
          rationale: protocol.rationale,
        };
      }
      const result = await api(`/exercises/${exercise.id}/criteria`, {
        ...frameDefinition,
        source,
        approved,
        rules,
        protocol: plan,
        validation_scope: scope,
        template_version: templateVersion,
        minimum_active_seconds: minimumSeconds === "" ? null : Number(minimumSeconds),
      });
      await onSaved(result.id);
      setRows([]);
      setApproved(false);
      setSource("");
      setMinimumSeconds("");
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="panel">
      <h2>สร้างเกณฑ์รุ่นใหม่</h2>
      <p className="muted">
        กรอกค่าจากการนำร่องหรือแหล่งอ้างอิงของคุณ หน่วย pixel ใช้กับตำแหน่งกล้องเดิมเท่านั้น
        การยืนยันนี้เป็นการยืนยันของผู้จัดทำ ไม่ใช่มาตรฐานรับรอง
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={disabled || saving}>
          {exercise?.module_id === 1 && (
            <div className="notice">
              <p>
                M1: ท่อนแขนเอียงจากแนวดิ่งไม่เกิน 15° ข้อมือต่ำกว่าศอก เข่าฝั่งแทง 160–180°
                ก้มอย่างน้อย 30° ก่อนเริ่มเท่านั้น บันทึก 8 วินาที ฐาน 1 วินาที
                ต้องวัดพร้อมกันได้อย่างน้อย 80% ของเฟรมหลังฐาน และถูกพร้อมกันอย่างน้อย 80%
                ของเฟรมที่วัดได้ N=1
              </p>
              <p>
                ใช้ค่ากรองเต็มความละเอียด ไม่ใช้ต่ำสุด–สูงสุดตัดสิน เป็นมุมฉายในภาพและเกณฑ์นำร่อง
                ไม่ใช่มาตรฐานสากล ปุ่มเติมเกณฑ์จะบันทึกเงื่อนไขรายเฟรมและการก้มไว้กับรุ่นเกณฑ์ด้วย
              </p>
              <button type="button" className="button secondary" onClick={loadTemplate}>
                เติมเกณฑ์ตั้งต้น M1 พร้อมแผนจบรอบ
              </button>
            </div>
          )}
          {(exercise?.module_id === 2 || exercise?.module_id === 3) && (
            <div className="notice">
              <p>
                {exercise?.module_id === 3
                  ? "มีเกณฑ์ต้นแบบ เหลี่ยมละ 1 ครั้งที่ประเมินได้"
                  : "มีเกณฑ์ต้นแบบ ประเมิน 1 ครั้งแล้วจบรอบ"}{" "}
                ค่าตัวเลขต้องตรวจความเหมาะสมจากการนำร่อง ไม่ใช่ค่าสากล
              </p>
              <button type="button" className="button secondary" onClick={loadTemplate}>
                เติมเกณฑ์ตั้งต้น M{exercise.module_id} พร้อมแผนจบรอบ
              </button>
            </div>
          )}
          <label className="field">
            เวลาวัดขั้นต่ำหลังช่วงฐาน (วินาที; เว้นว่างหากไม่กำหนด)
            <input
              type="number"
              min="0"
              max="600"
              step="any"
              value={minimumSeconds}
              onChange={(e) => setMinimumSeconds(e.target.value)}
            />
          </label>
          <label className="field">
            <span>แหล่งที่มา / บันทึกการนำร่อง</span>
            <textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              required
              minLength={5}
              maxLength={1000}
            />
          </label>
          {rows.map((row, i) => (
            <div className="rule-row" key={i}>
              <label>
                ตัวชี้วัด
                <select value={row.code} onChange={(e) => update(i, "code", e.target.value)}>
                  <option value="">เลือกตัวชี้วัด</option>
                  {options.map((code) => (
                    <option value={code} key={code}>
                      {labels[code] || code} ({units[code]})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                ต่ำสุด
                <input
                  aria-label={`ต่ำสุดแถว ${i + 1}`}
                  type="number"
                  step="any"
                  value={row.min}
                  onChange={(e) => update(i, "min", e.target.value)}
                />
              </label>
              <label>
                สูงสุด
                <input
                  aria-label={`สูงสุดแถว ${i + 1}`}
                  type="number"
                  step="any"
                  value={row.max}
                  onChange={(e) => update(i, "max", e.target.value)}
                />
              </label>
              <button
                type="button"
                className="button secondary"
                onClick={() => setRows(rows.filter((_, n) => n !== i))}
              >
                ลบ
              </button>
            </div>
          ))}
          <div className="actions">
            <button
              type="button"
              className="button secondary"
              disabled={rows.length >= options.length}
              onClick={() => setRows([...rows, { code: "", min: "", max: "" }])}
            >
              เพิ่มตัวชี้วัด
            </button>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={useProtocol}
              onChange={(e) => setUseProtocol(e.target.checked)}
            />
            กำหนดแผนประเมินรายรอบตามข้อมูลนำร่อง
          </label>
          {useProtocol && (
            <div className="panel">
              <label>
                จำนวนครั้งที่มีผล PASS/FAIL (N)
                <input
                  type="number"
                  min="1"
                  max="1000"
                  required
                  value={protocol.required_valid_attempts}
                  onChange={(e) =>
                    setProtocol({ ...protocol, required_valid_attempts: e.target.value })
                  }
                />
              </label>
              <label>
                อัตราผ่านขั้นต่ำ (%)
                <input
                  type="number"
                  min="0.01"
                  max="100"
                  step="any"
                  required
                  value={protocol.minimum_pass_percent}
                  onChange={(e) =>
                    setProtocol({ ...protocol, minimum_pass_percent: e.target.value })
                  }
                />
              </label>
              <label>
                เหตุผล/ที่มาของจำนวนครั้งและอัตราผ่าน
                <textarea
                  required
                  minLength={5}
                  maxLength={1000}
                  value={protocol.rationale}
                  onChange={(e) => setProtocol({ ...protocol, rationale: e.target.value })}
                />
              </label>
              <p className="muted">
                ระบบไม่กำหนดค่าเริ่มต้นแทนผู้จัดทำ ครั้งที่ INVALID/ABORTED ไม่นับเข้า N
              </p>
            </div>
          )}
          <label className="check">
            <input
              type="checkbox"
              checked={approved}
              onChange={(e) => setApproved(e.target.checked)}
            />
            ยืนยันเกณฑ์รุ่นนี้สำหรับการทดลอง
          </label>
          <button type="submit" className="button">
            {saving ? "กำลังบันทึก…" : "บันทึกเป็นรุ่นใหม่"}
          </button>
        </fieldset>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}
