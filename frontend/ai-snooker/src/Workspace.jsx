import { useDisplayTiming } from "./hooks/useDisplayTiming";
import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api";
import DashboardPage from "./pages/DashboardPage";
import ProfilePage from "./pages/ProfilePage";
import SetupPage from "./pages/SetupPage";
import CriteriaPage from "./pages/CriteriaPage";
import TrainingPage from "./pages/TrainingPage";
import SummaryPage from "./pages/SummaryPage";
import HistoryPage from "./pages/HistoryPage";
export default function Workspace({ user, onLogout }) {
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
  const [progress,setProgress]=useState([]);
  const [historyFilter,setHistoryFilter]=useState({exercise:'',from:'',to:'',mode:''});
  const visibleHistory=history.filter(s=> (!historyFilter.exercise || String(s.exercise_id)===historyFilter.exercise) && (!historyFilter.mode || s.mode===historyFilter.mode) && (!historyFilter.from || new Date(s.started_at)>=new Date(historyFilter.from+'T00:00:00')) && (!historyFilter.to || new Date(s.started_at)<=new Date(historyFilter.to+'T23:59:59.999')));
  const sessionRequest = useRef(null),
    attemptRequest = useRef(null);
  const exercise = catalog.find((e) => String(e.id) === exerciseId);
  const criteria = exercise?.criteria.find((c) => String(c.id) === criteriaId);
  const fingerprint = JSON.stringify([exerciseId, config, advanced]);
  const active = Boolean(status.session_id);
  const displayTiming = useDisplayTiming(status.attempt_id);
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
  useEffect(()=>{let mounted=true;api('/progress').then(value=>{if(mounted)setProgress(value)}).catch(()=>{});return ()=>{mounted=false}},[]);
  useEffect(() => {
    let disposed = false,
      socket,
      timer, watchdog;
    function connect() {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`,
      );
      socket.onopen = () => {
        if (!disposed) setConnected(true);
      };
      socket.onmessage = (e) => {
        if (!disposed) {
          setStatus(JSON.parse(e.data));
          clearTimeout(watchdog);
          watchdog=setTimeout(()=>{setConnected(false);setStatus(old=>({...old,ready:false,frame:{},live_metrics:{}}));socket.close()},4000);
        }
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
      clearTimeout(watchdog);
      socket?.close();
    };
  }, []);
  function choose(item) {
    setExerciseId(String(item.id));
    setCriteriaId(String(item.criteria[0]?.id || ""));
    setPrepared("");
    setPage("setup");
    setLastAttempt(null);
  }
  async function navigate(target) {
    if (target === "history" || target === "compare")
      await run(async () => {
        setHistory(await api("/sessions"));
        setPage(target);
      });
    else {
      if(target==='dashboard') await run(async()=>setProgress(await api('/progress')));
      setPage(target);
    }
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
      display_timing: displayTiming.summary(),
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
  const view = { history, onDisplayed: displayTiming.record, status, exercise, criteria, units, setPage, active, load, setCriteriaId, loaded, busy, run, progress, catalog, choose, page, historyFilter, setHistoryFilter, visibleHistory, setReport, pair, setPair, setComparison, comparison, user, onLogout, exerciseId, criteriaId, config, setConfig, setAdvanced, advanced, connected, checkReady, prepared, fingerprint, startSession, frame, setPrepared, setError, report, navigate, finishAttempt, startAttempt, finishSession, lastAttempt };
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
        {page === "dashboard" && <DashboardPage {...view} />}
        {page === "profile" && <ProfilePage {...view} />}
        {page === "setup" && <SetupPage {...view} />}
        {page === "criteria" && <CriteriaPage {...view} />}
        {page === "training" && <TrainingPage {...view} />}
        {page === "summary" && report && <SummaryPage {...view} />}
        {(page === "history" || page === "compare") && <HistoryPage {...view} />}
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

