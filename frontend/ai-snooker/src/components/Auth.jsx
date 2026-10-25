import { useState } from "react";
import { api } from "../lib/api";
import { Button, Field } from "./ui";
export default function Auth({ onLogin }) {
  const [register, setRegister] = useState(false),
    [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (register && values.password !== values.confirmation)
        throw new Error("รหัสผ่านทั้งสองช่องไม่ตรงกัน");
      const body = { username: values.username, password: values.password };
      if (register)
        Object.assign(body, {
          display_name: values.display_name,
          dominant_hand: values.dominant_hand,
        });
      onLogin(await api(`/auth/${register ? "register" : "login"}`, body));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth">
      <div className="brand">
        AI<span>SNOOKER</span>
      </div>
      <h1>{register ? "สมัครสมาชิก" : "เข้าสู่ระบบ"}</h1>
      <p className="muted">ระบบช่วยฝึกสนุกเกอร์ด้วยตนเอง</p>
      <form onSubmit={submit} key={String(register)}>
        {register && (
          <Field label="ชื่อที่แสดง">
            <input
              name="display_name"
              required
              maxLength={100}
              autoComplete="name"
            />
          </Field>
        )}
        <Field label="ชื่อผู้ใช้">
          <input
            name="username"
            required
            minLength={3}
            maxLength={50}
            pattern="[A-Za-z0-9_.\-]+"
            autoComplete="username"
            placeholder="ชื่อผู้ใช้ภาษาอังกฤษ"
          />
        </Field>
        <Field label="รหัสผ่าน">
          <input
            name="password"
            type={show ? "text" : "password"}
            required
            minLength={register ? 12 : 1}
            maxLength={128}
            autoComplete={register ? "new-password" : "current-password"}
            placeholder={register ? "อย่างน้อย 12 ตัวอักษร" : "รหัสผ่าน"}
          />
        </Field>
        {register && (
          <>
            <Field label="ยืนยันรหัสผ่าน">
              <input
                name="confirmation"
                type={show ? "text" : "password"}
                required
                autoComplete="new-password"
              />
            </Field>
            <Field label="มือข้างที่ถนัด">
              <select name="dominant_hand">
                <option value="RIGHT">ขวา</option>
                <option value="LEFT">ซ้าย</option>
              </select>
            </Field>
          </>
        )}
        <label className="check">
          <input
            type="checkbox"
            checked={show}
            onChange={(e) => setShow(e.target.checked)}
          />
          แสดงรหัสผ่าน
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <Button disabled={busy}>
          {busy ? "กำลังดำเนินการ…" : register ? "สมัครสมาชิก" : "เข้าสู่ระบบ"}
        </Button>
      </form>
      <button
        className="text-button"
        disabled={busy}
        onClick={() => {
          setRegister(!register);
          setError("");
        }}
      >
        {register ? "มีบัญชีแล้ว? เข้าสู่ระบบ" : "ยังไม่มีบัญชี? สมัครสมาชิก"}
      </button>
    </main>
  );
}

