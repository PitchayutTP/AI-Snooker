import { useState } from "react";
import { api } from "../lib/api";
import { labels } from "../lib/labels";
export function CriteriaEditor({ exercise, units, disabled, onSaved }) {
  const [rows, setRows] = useState([]),
    [source, setSource] = useState(""),
    [approved, setApproved] = useState(false);
  const [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const options = exercise?.lesson?.metrics || [];
  function update(index, key, value) {
    setRows(
      rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)),
    );
  }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const rules = {};
      for (const row of rows) {
        if (!row.code || rules[row.code])
          throw new Error("เลือกตัวชี้วัดไม่ซ้ำกัน");
        if (row.min === "" && row.max === "")
          throw new Error("ระบุค่าต่ำสุดหรือค่าสูงสุดอย่างน้อยหนึ่งค่า");
        const rule = {};
        for (const key of ["min", "max"])
          if (row[key] !== "") {
            const n = Number(row[key]);
            if (!Number.isFinite(n)) throw new Error("เกณฑ์ต้องเป็นตัวเลข");
            rule[key] = n;
          }
        if (
          rule.min !== undefined &&
          rule.max !== undefined &&
          rule.min > rule.max
        )
          throw new Error("ค่าต่ำสุดต้องไม่มากกว่าค่าสูงสุด");
        rules[row.code] = rule;
      }
      if (approved && !rows.length)
        throw new Error("ต้องเพิ่มตัวชี้วัดก่อนยืนยันเกณฑ์");
      const result = await api(`/exercises/${exercise.id}/criteria`, {
        source,
        approved,
        rules,
      });
      await onSaved(result.id);
      setRows([]);
      setApproved(false);
      setSource("");
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
        กรอกค่าจากการนำร่องหรือแหล่งอ้างอิงของคุณ หน่วย pixel
        ใช้กับตำแหน่งกล้องเดิมเท่านั้น การยืนยันนี้เป็นการยืนยันของผู้จัดทำ
        ไม่ใช่มาตรฐานรับรอง
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={disabled || saving}>
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
                <select
                  value={row.code}
                  onChange={(e) => update(i, "code", e.target.value)}
                >
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

