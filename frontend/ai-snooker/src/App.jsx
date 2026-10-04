import { useEffect, useRef, useState } from "react";
import { api, number, date, names } from "./lib/api";

function Button({ children, secondary = false, ...props }) {
  return (
    <button className={secondary ? "button secondary" : "button"} {...props}>
      {children}
    </button>
  );
}
function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function Badge({ value }) {
  return <span className={`badge ${value}`}>{names[value] || value}</span>;
}
function Table({ headings, children }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {headings.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function Auth({ onLogin }) {
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

function Workspace({ user, onLogout }) {
  const [page, setPage] = useState("dashboard"),
    [catalog, setCatalog] = useState([]),
    [units, setUnits] = useState({});
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false);
  const [exerciseId, setExerciseId] = useState(""),
    [criteriaId, setCriteriaId] = useState("");
  const [config, setConfig] = useState({
    mode: "DEMO",
    hand: user.dominant_hand,
    side_source: "0",
    top_source: "1",
    baseline_seconds: 1,
  });
  const [advanced, setAdvanced] = useState("{}"),
    [prepared, setPrepared] = useState("");
  const [status, setStatus] = useState({ frame: {} }),
    [connected, setConnected] = useState(false);
  const [history, setHistory] = useState([]),
    [report, setReport] = useState(null),
    [lastAttempt, setLastAttempt] = useState(null);
  const [pair, setPair] = useState(["", ""]),
    [comparison, setComparison] = useState(null);
  const sessionRequest = useRef(null),
    attemptRequest = useRef(null);
  const exercise = catalog.find((e) => String(e.id) === exerciseId);
  const criteria = exercise?.criteria.find((c) => String(c.id) === criteriaId);
  const fingerprint = JSON.stringify([exerciseId, config, advanced]);
  const active = Boolean(status.session_id);
  async function run(task) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function load() {
    const [list, metrics] = await Promise.all([
      api("/catalog"),
      api("/metrics"),
    ]);
    setCatalog(list);
    setUnits(metrics);
    setLoaded(true);
  }
  useEffect(() => {
    let live = true;
    Promise.all([api("/catalog"), api("/metrics")])
      .then(([list, metrics]) => {
        if (live) {
          setCatalog(list);
          setUnits(metrics);
          setLoaded(true);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    let disposed = false,
      socket,
      timer;
    function connect() {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`,
      );
      socket.onopen = () => {
        if (!disposed) setConnected(true);
      };
      socket.onmessage = (e) => {
        if (!disposed) setStatus(JSON.parse(e.data));
      };
      socket.onclose = () => {
        if (!disposed) {
          setConnected(false);
          timer = setTimeout(connect, 2000);
        }
      };
    }
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, []);
  function choose(item) {
    setExerciseId(String(item.id));
    setCriteriaId(String(item.criteria[0]?.id || ""));
    setPrepared("");
    setPage("setup");
  }
  async function navigate(target) {
    if (target === "history" || target === "compare")
      await run(async () => {
        setHistory(await api("/sessions"));
        setPage(target);
      });
    else setPage(target);
  }
  async function checkReady() {
    setPrepared("");
    const extra = JSON.parse(advanced);
    if (!extra || Array.isArray(extra) || typeof extra !== "object")
      throw new Error("การตั้งค่าเพิ่มเติมต้องเป็น JSON object");
    await api("/readiness", {
      exercise_id: Number(exerciseId),
      config: { ...extra, ...config },
    });
    setPrepared(fingerprint);
  }
  async function startSession() {
    sessionRequest.current ||= crypto.randomUUID();
    const result = await api("/sessions", {
      request_id: sessionRequest.current,
      criteria_id: Number(criteriaId),
    });
    sessionRequest.current = null;
    setStatus((s) => ({ ...s, session_id: result.id }));
    setLastAttempt(null);
    setPage("training");
  }
  async function startAttempt() {
    attemptRequest.current ||= crypto.randomUUID();
    const result = await api(`/sessions/${status.session_id}/attempts`, {
      request_id: attemptRequest.current,
    });
    attemptRequest.current = null;
    setStatus((s) => ({ ...s, attempt_id: result.id }));
    setLastAttempt(null);
  }
  async function finishAttempt(aborted) {
    const result = await api(`/attempts/${status.attempt_id}/finish`, {
      aborted,
    });
    setLastAttempt(result);
    setStatus((s) => ({ ...s, attempt_id: null }));
  }
  async function finishSession() {
    const result = await api(`/sessions/${status.session_id}/finish`, {
      aborted: false,
    });
    setReport(result);
    setStatus((s) => ({ ...s, session_id: null, attempt_id: null }));
    setPage("summary");
    setPrepared("");
  }
  const frame = status.frame || {};
  return (
    <>
      <header>
        <button className="wordmark" onClick={() => setPage("dashboard")}>
          AI SNOOKER<span>Practice better.</span>
        </button>
        <nav aria-label="เมนูหลัก">
          {[
            ["dashboard", "แบบฝึก"],
            ["history", "ประวัติการฝึก"],
            ["compare", "เปรียบเทียบ"],
            ["profile", user.display_name],
          ].map(([key, label]) => (
            <button
              key={key}
              disabled={busy}
              className={page === key ? "selected" : ""}
              onClick={() => navigate(key)}
            >
              {label}
            </button>
          ))}
          {active && (
            <button onClick={() => setPage("training")}>กลับไปฝึก ●</button>
          )}
        </nav>
      </header>
      <main className="workspace">
        <div className="connection">
          <i className={connected ? "online" : ""} />
          {connected ? "เชื่อมต่อระบบแล้ว" : "กำลังเชื่อมต่อระบบ…"}
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
            <button className="text-button" onClick={() => setError("")}>
              ปิด
            </button>
          </div>
        )}
        {page === "dashboard" && (
          <>
            <div className="heading">
              <p className="eyebrow">YOUR PRACTICE SPACE</p>
              <h1>เลือกแบบฝึกของคุณ</h1>
              <p className="muted">
                ฝึกทีละทักษะ บันทึกผล และติดตามการฝึกของตนเอง
              </p>
            </div>
            {!loaded && (
              <Button secondary disabled={busy} onClick={() => run(load)}>
                โหลดแบบฝึกอีกครั้ง
              </Button>
            )}
            <div className="modules">
              {[...new Set(catalog.map((e) => e.module_id))].map(
                (id, index) => {
                  const list = catalog.filter((e) => e.module_id === id);
                  return (
                    <article className="module" key={id}>
                      <div className="module-art">
                        <span>0{index + 1}</span>
                        <div className="ball" />
                      </div>
                      <div className="module-body">
                        <p className="eyebrow">
                          MODULE 0{index + 1} · {list.length} แบบฝึก
                        </p>
                        <h2>{list[0].module}</h2>
                        <p className="muted">
                          {list.map((e) => e.name).join(" · ")}
                        </p>
                        <Button
                          disabled={busy || active}
                          onClick={() => choose(list[0])}
                        >
                          เลือกแบบฝึก →
                        </Button>
                      </div>
                    </article>
                  );
                },
              )}
            </div>
          </>
        )}
        {page === "profile" && (
          <>
            <div className="heading">
              <h1>โปรไฟล์ผู้ฝึก</h1>
            </div>
            <section className="panel narrow">
              <h2>{user.display_name}</h2>
              <p>ชื่อผู้ใช้: {user.username}</p>
              <p>
                มือข้างที่ถนัด: {user.dominant_hand === "LEFT" ? "ซ้าย" : "ขวา"}
              </p>
              <p className="muted">บัญชีนี้ใช้แยกประวัติและผลการฝึกของคุณ</p>
              <Button
                secondary
                disabled={busy || active}
                onClick={() =>
                  run(async () => {
                    await api("/auth/logout", {});
                    onLogout();
                  })
                }
              >
                ออกจากระบบ
              </Button>
              {active && <p>กรุณาจบรอบฝึกก่อนออกจากระบบ</p>}
            </section>
          </>
        )}
        {page === "setup" && (
          <>
            <div className="heading">
              <h1>ตั้งค่าก่อนฝึก</h1>
              <p className="muted">เลือกแบบฝึกและตรวจสอบกล้องก่อนเริ่มบันทึก</p>
            </div>
            <div className="columns">
              <section className="panel">
                <Field label="แบบฝึก">
                  <select
                    value={exerciseId}
                    disabled={active}
                    onChange={(e) =>
                      choose(
                        catalog.find((x) => String(x.id) === e.target.value),
                      )
                    }
                  >
                    {catalog.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.module} — {e.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <p>{exercise?.instructions}</p>
                <Field label="เกณฑ์ประเมิน">
                  <select
                    value={criteriaId}
                    disabled={active}
                    onChange={(e) => setCriteriaId(e.target.value)}
                  >
                    {exercise?.criteria.map((c) => (
                      <option key={c.id} value={c.id}>
                        รุ่น {c.version} —{" "}
                        {c.approved ? "ยืนยันเกณฑ์แล้ว" : "ยังไม่ยืนยันเกณฑ์"}
                      </option>
                    ))}
                  </select>
                </Field>
                <Button secondary onClick={() => setPage("criteria")}>
                  ดูเกณฑ์ประเมิน
                </Button>
                <Field label="โหมดการฝึก">
                  <select
                    disabled={active}
                    value={config.mode}
                    onChange={(e) =>
                      setConfig({ ...config, mode: e.target.value })
                    }
                  >
                    <option value="DEMO">DEMO — ทดสอบการทำงาน</option>
                    <option value="LIVE">LIVE — กล้องจริง</option>
                  </select>
                </Field>
                <Field label="มือที่ถนัด">
                  <select
                    disabled={active}
                    value={config.hand}
                    onChange={(e) =>
                      setConfig({ ...config, hand: e.target.value })
                    }
                  >
                    <option value="RIGHT">ขวา</option>
                    <option value="LEFT">ซ้าย</option>
                  </select>
                </Field>
              </section>
              <section className="panel">
                <h2>กล้องและการตรวจจับ</h2>
                {[
                  ["side_source", "กล้องด้านข้าง"],
                  ["top_source", "กล้องด้านบน"],
                ].map(([key, label]) => (
                  <Field label={label} key={key}>
                    <input
                      disabled={active}
                      value={config[key]}
                      onChange={(e) =>
                        setConfig({ ...config, [key]: e.target.value })
                      }
                    />
                  </Field>
                ))}
                <details>
                  <summary>การตั้งค่าการวัดเพิ่มเติม (JSON)</summary>
                  <p className="muted">
                    LIVE ต้องมีโมเดลและการสอบเทียบตามไฟล์ใน configs
                  </p>
                  <textarea
                    aria-label="การตั้งค่าเพิ่มเติม"
                    value={advanced}
                    disabled={active}
                    onChange={(e) => setAdvanced(e.target.value)}
                    rows={8}
                    spellCheck={false}
                  />
                </details>
                <p className="notice">
                  {config.mode === "DEMO"
                    ? "DEMO ใช้ข้อมูลจำลอง ผลจะเป็น “ประเมินไม่ได้” และไม่ใช้ยืนยันทักษะ"
                    : "ใช้กล้องที่เชื่อมต่อกับเครื่อง Backend และจัดตำแหน่งลูกตามคำแนะนำของแบบฝึก"}
                </p>
                {status.error && <p className="error">{status.error}</p>}
                <div className="actions">
                  <Button
                    secondary
                    disabled={busy || active || !connected || !exercise}
                    onClick={() => run(checkReady)}
                  >
                    ตรวจความพร้อม
                  </Button>
                  <Button
                    disabled={
                      busy ||
                      active ||
                      !connected ||
                      !status.ready ||
                      prepared !== fingerprint ||
                      !criteria
                    }
                    onClick={() => run(startSession)}
                  >
                    เริ่มรอบฝึก
                  </Button>
                </div>
                <p className="muted">
                  {prepared === fingerprint && connected && status.ready
                    ? "พร้อมเริ่มรอบฝึก"
                    : "ต้องตรวจความพร้อมหลังเปลี่ยนการตั้งค่า"}
                </p>
              </section>
            </div>
          </>
        )}
        {page === "criteria" && (
          <>
            <div className="heading">
              <h1>เกณฑ์ประเมิน</h1>
              <p>
                {exercise?.name} · รุ่น {criteria?.version}
              </p>
            </div>
            <section className="panel">
              <p>{criteria?.source || "ยังไม่ระบุแหล่งที่มา"}</p>
              <Badge
                value={
                  criteria?.approved ? "ยืนยันเกณฑ์แล้ว" : "ยังไม่ยืนยันเกณฑ์"
                }
              />
              <Table
                headings={["ตัวชี้วัด", "ค่าต่ำสุด", "ค่าสูงสุด", "หน่วย"]}
              >
                {Object.entries(criteria?.rules || {}).map(([key, rule]) => (
                  <tr key={key}>
                    <td>{key}</td>
                    <td>{number(rule.min)}</td>
                    <td>{number(rule.max)}</td>
                    <td>{units[key]}</td>
                  </tr>
                ))}
              </Table>
              {!Object.keys(criteria?.rules || {}).length && (
                <p className="muted">ยังไม่มีเกณฑ์ตัวเลขสำหรับรุ่นนี้</p>
              )}
              <Button secondary onClick={() => setPage("setup")}>
                กลับไปตั้งค่าก่อนฝึก
              </Button>
            </section>
          </>
        )}
        {page === "training" && (
          <>
            <div className="heading">
              <h1>ฝึกและบันทึกผล</h1>
              <p className="muted">เริ่มและจบแต่ละครั้งด้วยตนเอง</p>
            </div>
            {!active ? (
              <p className="notice">
                ไม่มีรอบฝึกที่กำลังทำงาน กรุณาเลือกแบบฝึกเพื่อเริ่มต้น
              </p>
            ) : (
              <>
                <div className="columns training">
                  <div className="video">
                    {frame.image ? (
                      <img
                        src={`data:image/jpeg;base64,${frame.image}`}
                        alt="ภาพจากกล้องสำหรับการฝึก"
                      />
                    ) : (
                      <div>
                        <span className="camera-symbol">◎</span>
                        <p>
                          {status.mode === "DEMO"
                            ? "โหมดสาธิต — ไม่มีภาพกล้องจริง"
                            : "กำลังรอภาพจากกล้อง"}
                        </p>
                      </div>
                    )}
                  </div>
                  <section className="panel">
                    <Badge value={status.mode || config.mode} />
                    <h2>ข้อมูลขณะฝึก</h2>
                    <dl>
                      <dt>มุมศอก (°)</dt>
                      <dd>{number(frame.elbow)}</dd>
                      <dt>อัตราภาพ (FPS)</dt>
                      <dd>{number(frame.fps)}</dd>
                      <dt>ตัวอย่างที่บันทึก</dt>
                      <dd>{status.samples || 0}</dd>
                    </dl>
                    <p className="muted">
                      ค่า “—” หมายถึงไม่มีข้อมูล ไม่ใช่ค่า 0
                    </p>
                    {status.error && <p className="error">{status.error}</p>}
                    <div className="stack">
                      {status.attempt_id ? (
                        <>
                          <Button
                            disabled={busy || !connected}
                            onClick={() => run(() => finishAttempt(false))}
                          >
                            จบการบันทึกครั้งนี้
                          </Button>
                          <Button
                            secondary
                            disabled={busy || !connected}
                            onClick={() => run(() => finishAttempt(true))}
                          >
                            ยกเลิกครั้งนี้
                          </Button>
                        </>
                      ) : (
                        <Button
                          disabled={busy || !connected || !status.ready}
                          onClick={() => run(startAttempt)}
                        >
                          เริ่มบันทึกครั้งใหม่
                        </Button>
                      )}
                      <Button
                        secondary
                        disabled={busy || !connected || !!status.attempt_id}
                        onClick={() => run(finishSession)}
                      >
                        จบรอบและดูสรุป
                      </Button>
                    </div>
                    {status.attempt_id && (
                      <p className="muted">จบหรือยกเลิกครั้งนี้ก่อนจบรอบ</p>
                    )}
                  </section>
                </div>
                {lastAttempt && (
                  <section className="panel">
                    <h2>
                      ผลครั้งล่าสุด <Badge value={lastAttempt.status} />
                    </h2>
                    <p>{lastAttempt.reason}</p>
                    <Table headings={["ตัวชี้วัด", "ค่า", "หน่วย"]}>
                      {Object.entries(lastAttempt.metrics || {}).map(
                        ([key, value]) => (
                          <tr key={key}>
                            <td>{key}</td>
                            <td>{number(value)}</td>
                            <td>{units[key]}</td>
                          </tr>
                        ),
                      )}
                    </Table>
                  </section>
                )}
              </>
            )}
          </>
        )}
        {page === "summary" && report && (
          <>
            <div className="heading">
              <h1>สรุปผลการฝึก</h1>
              <p>
                {report.name} · {date(report.started_at)}
              </p>
              <Badge value={report.mode} />
            </div>
            <div className="stats">
              {[
                ["จำนวนครั้ง", report.attempts.length],
                ["ผ่านเกณฑ์", report.counts.PASS],
                [
                  "อัตราผ่าน",
                  report.pass_rate == null
                    ? "—"
                    : `${number(report.pass_rate * 100)}%`,
                ],
              ].map(([label, value]) => (
                <section className="panel" key={label}>
                  <p className="muted">{label}</p>
                  <strong>{value}</strong>
                </section>
              ))}
            </div>
            <section className="panel">
              <p className="muted">
                อัตราผ่านคำนวณเฉพาะครั้งที่มีผล PASS หรือ FAIL
              </p>
              <Table headings={["ครั้งที่", "ผลการประเมิน", "รายละเอียด"]}>
                {report.attempts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.number}</td>
                    <td>
                      <Badge value={a.status} />
                    </td>
                    <td>
                      {a.reason || "—"}
                      <details>
                        <summary>ค่าที่วัดได้</summary>
                        {Object.entries(a.metrics).map(([key, m]) => (
                          <p key={key}>
                            {key}: {number(m.value)} {m.unit}{" "}
                            {m.reason && `(${m.reason})`}
                          </p>
                        ))}
                      </details>
                    </td>
                  </tr>
                ))}
              </Table>
              {!report.attempts.length && <p>ยังไม่มีครั้งฝึกในรอบนี้</p>}
              <div className="actions">
                <a
                  className="button secondary"
                  href={`/api/sessions/${report.id}/export`}
                  download
                >
                  ดาวน์โหลดผล JSON
                </a>
                <Button onClick={() => navigate("history")}>
                  ดูประวัติการฝึก
                </Button>
              </div>
            </section>
          </>
        )}
        {(page === "history" || page === "compare") && (
          <>
            <div className="heading">
              <h1>
                {page === "history" ? "ประวัติการฝึก" : "เปรียบเทียบผลการฝึก"}
              </h1>
              <p className="muted">แสดงผลจากบัญชีของคุณเท่านั้น</p>
            </div>
            {page === "history" ? (
              <section className="panel">
                <Table
                  headings={[
                    "วันและเวลา",
                    "แบบฝึก",
                    "โหมด",
                    "สถานะ",
                    "รายละเอียด",
                  ]}
                >
                  {history.map((s) => (
                    <tr key={s.id}>
                      <td>{date(s.started_at)}</td>
                      <td>{s.name}</td>
                      <td>
                        <Badge value={s.mode} />
                      </td>
                      <td>
                        <Badge value={s.status} />
                      </td>
                      <td>
                        <Button
                          secondary
                          disabled={busy}
                          onClick={() => {
                            setReport(s);
                            setPage("summary");
                          }}
                        >
                          ดูผล
                        </Button>
                      </td>
                    </tr>
                  ))}
                </Table>
                {!history.length && (
                  <p className="empty">
                    ยังไม่มีประวัติ เริ่มฝึกเพื่อบันทึกผลครั้งแรก
                  </p>
                )}
              </section>
            ) : (
              <section className="panel">
                <p className="notice">
                  เลือกรอบที่จบแล้วและใช้แบบฝึก รุ่นเกณฑ์ และการตั้งค่าเดียวกัน
                </p>
                <div className="columns">
                  {[0, 1].map((i) => (
                    <Field label={`รอบ ${i === 0 ? "A" : "B"}`} key={i}>
                      <select
                        value={pair[i]}
                        onChange={(e) => {
                          setPair((p) =>
                            p.map((v, n) => (n === i ? e.target.value : v)),
                          );
                          setComparison(null);
                        }}
                      >
                        <option value="">เลือกรอบฝึก</option>
                        {history
                          .filter((s) => s.status === "COMPLETED")
                          .map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name} · {date(s.started_at)} ·{" "}
                              {s.id.slice(0, 8)}
                            </option>
                          ))}
                      </select>
                    </Field>
                  ))}
                </div>
                <Button
                  disabled={busy || !pair[0] || !pair[1] || pair[0] === pair[1]}
                  onClick={() =>
                    run(async () => {
                      setComparison(null);
                      setComparison(
                        await api(
                          `/compare?left=${encodeURIComponent(pair[0])}&right=${encodeURIComponent(pair[1])}`,
                        ),
                      );
                    })
                  }
                >
                  เปรียบเทียบผล
                </Button>
                {comparison && (
                  <>
                    <p>
                      {comparison.note} · {comparison.mode}
                    </p>
                    <Table
                      headings={[
                        "ตัวชี้วัด",
                        "ค่าเฉลี่ย A",
                        "ค่าเฉลี่ย B",
                        "ผลต่าง B − A",
                        "หน่วย",
                      ]}
                    >
                      {Object.entries(comparison.metrics).map(
                        ([key, value]) => (
                          <tr key={key}>
                            <td>{key}</td>
                            <td>{number(value.left.mean)}</td>
                            <td>{number(value.right.mean)}</td>
                            <td>{number(value.difference)}</td>
                            <td>{units[key]}</td>
                          </tr>
                        ),
                      )}
                    </Table>
                  </>
                )}
              </section>
            )}
          </>
        )}
        {busy && (
          <p className="busy" role="status">
            กำลังดำเนินการ…
          </p>
        )}
      </main>
      <footer>AI SNOOKER · ระบบต้นแบบสำหรับฝึกด้วยตนเอง</footer>
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("/auth/me")
      .then((value) => {
        if (live) setUser(value);
      })
      .catch((e) => {
        if (live && e.status !== 401) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    const expired = () => setUser(null);
    window.addEventListener("auth-expired", expired);
    return () => {
      live = false;
      window.removeEventListener("auth-expired", expired);
    };
  }, []);
  if (loading)
    return (
      <main className="auth">
        <p role="status">กำลังโหลดระบบ…</p>
      </main>
    );
  if (error)
    return (
      <main className="auth">
        <p className="error">เชื่อมต่อ Backend ไม่ได้: {error}</p>
        <Button onClick={() => location.reload()}>ลองอีกครั้ง</Button>
      </main>
    );
  return user ? (
    <Workspace user={user} onLogout={() => setUser(null)} />
  ) : (
    <Auth onLogin={setUser} />
  );
}
