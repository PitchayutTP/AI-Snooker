import { useState } from "react";
export function SettingsImport({ onImport, disabled }) {
  const [error, setError] = useState("");
  return (
    <>
      <label className="field">
        <span>โหลดไฟล์ตั้งค่า JSON (เฉพาะค่าการวัดเพิ่มเติม)</span>
        <input
          disabled={disabled}
          type="file"
          accept=".json,application/json"
          onChange={async (e) => {
            setError("");
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              if (file.size > 64000) throw new Error("ไฟล์ต้องไม่เกิน 64 KB");
              const data = JSON.parse(await file.text());
              if (!data || Array.isArray(data) || typeof data !== "object")
                throw new Error("ต้องเป็น JSON object");
              onImport(JSON.stringify(data, null, 2));
            } catch (err) {
              setError(err.message);
            }
            e.target.value = "";
          }}
        />
      </label>
      {error && <p className="error">{error}</p>}
    </>
  );
}

