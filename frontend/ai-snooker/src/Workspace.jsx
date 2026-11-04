import { WorkspacePages } from "./components/WorkspacePages";
import { useRuntimeConnection } from "./hooks/useRuntimeConnection";
import { useWorkspaceData } from "./hooks/useWorkspaceData";
import { useDisplayTiming } from "./hooks/useDisplayTiming";
import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api";
import { createPageHistory } from "./lib/pageHistory";
import {
  createM1AutoTrial,
  isTimedM1Criteria,
  M1_RECORD_SECONDS,
  M1_SMOOTHING_WINDOW,
  M1_SMOOTHING_TAU_SECONDS,
} from "./lib/m1AutoTrial";
import {
  defaultModuleSettings,
  moduleConfig,
  moduleAdvanced,
  moduleCaptureConfig,
  essentialTrialSettings,
  isPrototypeCriteria,
} from "./lib/moduleSettings";
import { m3CalibrationReady } from "./lib/m3Preparation";
import { createM3AutoSave } from "./lib/m3AutoSave";
import { M2_CALIBRATION_LIMIT_MM } from "./lib/table";
export default function Workspace({ user, onLogout }) {
  const [page, setPageState] = useState("dashboard"),
    [catalog, setCatalog] = useState([]),
    [units, setUnits] = useState({});
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false);
  const [exerciseId, setExerciseId] = useState(""),
    [criteriaId, setCriteriaId] = useState("");
  const moduleId = catalog.find((e) => String(e.id) === exerciseId)?.module_id || 1;
  const [settingsByModule, setSettingsByModule] = useState(() =>
    Object.fromEntries([1, 2, 3].map((id) => [id, defaultModuleSettings(id, user.dominant_hand)])),
  );
  const { config, advanced } = settingsByModule[moduleId];
  function setConfig(value) {
    setSettingsByModule((previous) => ({
      ...previous,
      [moduleId]: {
        ...previous[moduleId],
        config: moduleConfig(moduleId, {
          ...defaultModuleSettings(moduleId, user.dominant_hand).config,
          ...(typeof value === "function" ? value(previous[moduleId].config) : value),
        }),
      },
    }));
  }
  function setAdvanced(value) {
    setSettingsByModule((previous) => ({
      ...previous,
      [moduleId]: {
        ...previous[moduleId],
        advanced: moduleAdvanced(
          moduleId,
          typeof value === "function" ? value(previous[moduleId].advanced) : value,
        ),
      },
    }));
  }
  const [prepared, setPrepared] = useState("");
  const [calibrating, setCalibrating] = useState(false);
  const [status, setStatus] = useState({ frame: {} }),
    [connected, setConnected] = useState(false);
  const [history, setHistory] = useState([]),
    [report, setReport] = useState(null),
    [lastAttempt, setLastAttempt] = useState(null);
  const [pair, setPair] = useState(["", ""]),
    [comparison, setComparison] = useState(null);
  const [progress, setProgress] = useState([]);
  const [activeReport, setActiveReport] = useState(null);
  const [m1Auto, setM1Auto] = useState({ phase: "IDLE", error: "" });
  const autoController = useRef(null),
    autoCriteria = useRef(null),
    autoContext = useRef(null);
  autoContext.current = {
    status,
    connected,
    start: async () => {
      const sid = await startSession({ criteriaId: autoCriteria.current, purpose: "ASSESSMENT" });
      await startAttempt(sid);
    },
    finish: async () => {
      const result = await finishAttempt(false);
      await finishSession(result.status === "INVALID" || result.status === "ABORTED");
    },
  };
  useEffect(() => {
    let mounted = true;
    const controller = createM1AutoTrial({
      start: () => autoContext.current.start(),
      finish: () => autoContext.current.finish(),
      onChange: (value) => {
        if (mounted) {
          setM1Auto(value);
          if (value.error) setError(value.error);
        }
      },
    });
    autoController.current = controller;
    const timer = setInterval(() => {
      const current = autoContext.current;
      void controller.update(current.status, current.connected);
    }, 100);
    return () => {
      mounted = false;
      clearInterval(timer);
      controller.cancel();
      autoController.current = null;
    };
  }, []);
  const [historyFilter, setHistoryFilter] = useState({ exercise: "", from: "", to: "", mode: "" });
  const navigation = useRef(null);
  const deletedSessions = useRef(new Set());
  const navigationContext = useRef(null);
  navigationContext.current = { exerciseId, criteriaId, report, sessionId: status.session_id };
  useEffect(() => {
    const controller = createPageHistory(window, {
      capture: () => navigationContext.current,
      resolve: (target, context) => {
        if ((target === "setup" || target === "criteria") && !context.exerciseId)
          return "dashboard";
        if (target === "training" && !navigationContext.current.sessionId) return "dashboard";
        if (
          target === "summary" &&
          (!context.report || deletedSessions.current.has(context.report.id))
        )
          return "history";
        return target;
      },
      onChange: (target, context) => {
        if (target !== "setup" || context.exerciseId !== navigationContext.current.exerciseId)
          autoController.current?.cancel();
        setPageState(target);
        // Browsing history must not switch the exercise/criteria of a live round.
        if (!navigationContext.current.sessionId) {
          setExerciseId(context.exerciseId || "");
          setCriteriaId(context.criteriaId || "");
        }
        setReport(
          context.report && !deletedSessions.current.has(context.report.id) ? context.report : null,
        );
      },
    });
    navigation.current = controller;
    controller.start();
    return () => {
      controller.stop();
      navigation.current = null;
    };
  }, []);
  function setPage(target, context) {
    if (target !== "setup" && ["WAITING", "COUNTDOWN"].includes(m1Auto.phase))
      autoController.current?.cancel();
    navigation.current?.navigate(target, context);
  }
  const visibleHistory = history.filter(
    (s) =>
      (!historyFilter.exercise || String(s.exercise_id) === historyFilter.exercise) &&
      (!historyFilter.mode || s.mode === historyFilter.mode) &&
      (!historyFilter.from ||
        new Date(s.started_at) >= new Date(historyFilter.from + "T00:00:00")) &&
      (!historyFilter.to || new Date(s.started_at) <= new Date(historyFilter.to + "T23:59:59.999")),
  );
  const sessionRequest = useRef(null),
    attemptRequest = useRef(null);
  const exercise = catalog.find((e) => String(e.id) === exerciseId);
  const criteria = exercise?.criteria.find((c) => String(c.id) === criteriaId);
  const fingerprint = JSON.stringify([exerciseId, config, advanced]);
  const active = Boolean(status.session_id);
  const displayTiming = useDisplayTiming(status.attempt_id);
  const m3SaveContext = useRef(null);
  m3SaveContext.current = {
    status,
    connected,
    busy,
    moduleId,
    save: async (id) => {
      setBusy(true);
      setError("");
      try {
        await finishAttempt(false, id);
      } finally {
        setBusy(false);
      }
    },
    error: (e) =>
      setError(`บันทึกผลอัตโนมัติไม่สำเร็จ: ${e.message} กดจบการบันทึกครั้งนี้เพื่อลองใหม่`),
  };
  useEffect(() => {
    const controller = createM3AutoSave(
      (id) => m3SaveContext.current.save(id),
      (e) => m3SaveContext.current.error(e),
    );
    const timer = setInterval(() => {
      const current = m3SaveContext.current;
      void controller.update(current.status, current);
    }, 250);
    return () => clearInterval(timer);
  }, []);
  const m3Check = useRef(null),
    m3Checked = useRef("");
  m3Check.current = () => run(checkReady);
  let m3CheckKey = "";
  if ((moduleId === 2 || moduleId === 3) && m3CalibrationReady(advanced)) {
    const settings = JSON.parse(advanced);
    const ready =
      moduleId === 3 ||
      (settings.calibration_check_error <= M2_CALIBRATION_LIMIT_MM &&
        settings.cue_markers?.length > 0 &&
        settings.m2_red_points?.length === 6 &&
        settings.m2_red_points.every(
          (point) => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite),
        ) &&
        Number.isFinite(settings.m2_tip_offset_mm));
    if (ready) {
      const normalized = essentialTrialSettings(moduleId, config, advanced);
      m3CheckKey = JSON.stringify([exerciseId, normalized.config, normalized.advanced]);
    }
  }
  useEffect(() => {
    if (page !== "setup" || ![2, 3].includes(moduleId)) {
      m3Checked.current = "";
      return;
    }
    if (
      !connected ||
      active ||
      busy ||
      calibrating ||
      !m3CheckKey ||
      m3Checked.current === m3CheckKey
    )
      return;
    const timer = setTimeout(() => {
      m3Checked.current = m3CheckKey;
      void m3Check.current();
    }, 600);
    return () => clearTimeout(timer);
  }, [page, moduleId, connected, active, busy, calibrating, m3CheckKey]);
  useEffect(() => {
    let disposed = false;
    if (!status.session_id) return;
    api(`/sessions/${status.session_id}`)
      .then((value) => {
        if (!disposed) setActiveReport(value);
      })
      .catch((e) => {
        if (!disposed) setError(e.message);
      });
    return () => {
      disposed = true;
    };
  }, [status.session_id, status.attempt_id, lastAttempt]);
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
    const [list, metrics] = await Promise.all([api("/catalog"), api("/metrics")]);
    setCatalog(list);
    setUnits(metrics);
    setLoaded(true);
  }
  useWorkspaceData({ page, setCatalog, setUnits, setLoaded, setError, setHistory, setProgress });
  useRuntimeConnection({ setStatus, setConnected });
  function choose(item) {
    setCalibrating(false);
    setExerciseId(String(item.id));
    setCriteriaId(String(item.criteria[0]?.id || ""));
    setPrepared("");
    setPage("setup", {
      exerciseId: String(item.id),
      criteriaId: String(item.criteria[0]?.id || ""),
    });
    setLastAttempt(null);
  }
  function navigate(target) {
    setPage(target);
  }
  async function checkReady() {
    setCalibrating(false);
    setPrepared("");
    const extra = JSON.parse(advanced);
    if (!extra || Array.isArray(extra) || typeof extra !== "object")
      throw new Error("การตั้งค่าเพิ่มเติมต้องเป็น JSON object");
    let captureConfig = config;
    let captureAdvanced = advanced;
    if (moduleId === 2 || moduleId === 3) {
      const template = await api(`/exercises/${exerciseId}/criteria-template`);
      const existing =
        isPrototypeCriteria(criteria) && criteria.template_version === template.template_version
          ? criteria
          : exercise.criteria.find(
              (c) =>
                c.approved &&
                c.validation_scope === "PROTOTYPE" &&
                c.template_version === template.template_version &&
                JSON.stringify(c.rules) === JSON.stringify(template.rules) &&
                JSON.stringify(c.protocol) === JSON.stringify(template.protocol) &&
                c.minimum_active_seconds === template.minimum_active_seconds,
            );
      const chosen =
        existing ||
        (await api(`/exercises/${exerciseId}/criteria`, { ...template, approved: true }));
      setCriteriaId(String(chosen.id));
      if (!existing) await load();
      const defaults = essentialTrialSettings(moduleId, config, advanced);
      captureConfig = defaults.config;
      captureAdvanced = defaults.advanced;
      setConfig(captureConfig);
      setAdvanced(captureAdvanced);
    }
    await api("/readiness", {
      exercise_id: Number(exerciseId),
      config: moduleCaptureConfig(moduleId, captureConfig, captureAdvanced),
    });
    setStatus((previous) => ({
      ...previous,
      ready: false,
      frame: {},
      readiness_issues: ["กำลังรอผลตรวจจับจากการตั้งค่าล่าสุด"],
    }));
    setPrepared(JSON.stringify([exerciseId, captureConfig, captureAdvanced]));
  }
  async function prepareM1() {
    autoController.current?.cancel();
    setPrepared("");
    const template = await api(`/exercises/${exerciseId}/criteria-template`);
    const existing = isTimedM1Criteria(criteria)
      ? criteria
      : exercise.criteria.find(
          (c) =>
            isTimedM1Criteria(c) &&
            c.template_version === template.template_version &&
            JSON.stringify(c.rules) === JSON.stringify(template.rules),
        );
    const created =
      existing || (await api(`/exercises/${exerciseId}/criteria`, { ...template, approved: true }));
    autoCriteria.current = created.id;
    if (!existing) await load();
    setCriteriaId(String(created.id));
    // Pilot detection threshold, separate from posture pass/fail criteria.
    const liveConfig = {
      ...config,
      mode: "LIVE",
      purpose: "ASSESSMENT",
      baseline_seconds: 1,
      visibility: 0.6,
      pose_model: "models/pose_landmarker_full.task",
      smoothing_window: M1_SMOOTHING_WINDOW,
      smoothing_method: "MEDIAN_EMA",
      smoothing_tau_seconds: M1_SMOOTHING_TAU_SECONDS,
      smoothing_max_gap_s: 0.75,
      smoothing_for_evaluation: true,
    };
    setConfig(liveConfig);
    setAdvanced("{}");
    const epoch = Date.now();
    await api("/readiness", {
      exercise_id: Number(exerciseId),
      config: { ...moduleCaptureConfig(1, liveConfig, "{}"), m1_auto_seconds: M1_RECORD_SECONDS },
    });
    autoController.current?.arm(epoch);
  }
  async function startSession(options = {}) {
    sessionRequest.current ||= crypto.randomUUID();
    const result = await api("/sessions", {
      request_id: sessionRequest.current,
      criteria_id: Number(options.criteriaId ?? criteriaId),
      purpose: options.purpose ?? config.purpose ?? "PILOT",
    });
    sessionRequest.current = null;
    // Navigation runs synchronously, before React commits setStatus below.
    // Publish the confirmed session now so the training route guard sees it.
    navigationContext.current = { ...navigationContext.current, sessionId: result.id };
    setStatus((s) => ({ ...s, session_id: result.id }));
    setLastAttempt(null);
    if (!options.deferNavigation) setPage("training");
    return result.id;
  }
  async function startAttempt(sid = status.session_id) {
    attemptRequest.current ||= crypto.randomUUID();
    const result = await api(`/sessions/${sid}/attempts`, {
      request_id: attemptRequest.current,
    });
    attemptRequest.current = null;
    setStatus((s) => ({ ...s, attempt_id: result.id }));
    setLastAttempt(null);
    return result.id;
  }
  async function startM3() {
    const sid = await startSession({ purpose: "ASSESSMENT", deferNavigation: true });
    try {
      await startAttempt(sid);
    } catch (e) {
      setPage("training");
      throw new Error(
        `สร้างรอบแล้ว แต่ยังไม่ได้เริ่มบันทึก: ${e.message} จัดลูกให้นิ่งแล้วกดเริ่มบันทึกครั้งใหม่`,
        { cause: e },
      );
    }
    setPage("training");
  }
  async function finishAttempt(aborted, aid = status.attempt_id) {
    const result = await api(`/attempts/${aid}/finish`, {
      aborted,
      display_timing: displayTiming.summary(),
    });
    setLastAttempt(result);
    setStatus((s) => ({ ...s, attempt_id: null }));
    if (
      [2, 3].includes(moduleId) &&
      criteria?.protocol?.required_valid_attempts === 1 &&
      ["PASS", "FAIL"].includes(result.status)
    )
      await finishSession();
    return result;
  }
  async function finishSession(aborted = false) {
    const result = await api(`/sessions/${status.session_id}/finish`, {
      aborted,
    });
    setReport(result);
    setStatus((s) => ({ ...s, session_id: null, attempt_id: null }));
    setPage("summary", { report: result });
    try {
      setProgress(await api("/progress"));
    } catch (e) {
      setError(e.message);
    }
    setPrepared("");
  }
  function resetTrainingState() {
    autoController.current?.cancel();
    setHistory([]);
    setReport(null);
    setActiveReport(null);
    setLastAttempt(null);
    setProgress([]);
    setPair(["", ""]);
    setComparison(null);
    setPrepared("");
    setM1Auto({ phase: "IDLE", error: "" });
    setStatus({
      frame: {},
      ready: false,
      session_id: null,
      attempt_id: null,
      samples: 0,
      collecting: false,
    });
    sessionRequest.current = null;
    attemptRequest.current = null;
    navigation.current?.reset("profile", { report: null, sessionId: null });
  }
  async function deleteSession(sid) {
    const result = await api(`/sessions/${sid}/delete`, { confirmation: "DELETE_SESSION" });
    deletedSessions.current.add(sid);
    setHistory((previous) => previous.filter((session) => session.id !== sid));
    setReport((previous) => (previous?.id === sid ? null : previous));
    setComparison(null);
    setPair((previous) => previous.map((id) => (id === sid ? "" : id)));
    try {
      setProgress(await api("/progress"));
    } catch (error) {
      setError(error.message);
    }
    return result;
  }
  const frame = status.frame || {};
  const view = {
    deleteSession,
    setCalibrating: (value) => {
      if (value) m3Checked.current = "";
      setCalibrating(value);
    },
    activeReport: activeReport?.id === status.session_id ? activeReport : null,
    history,
    onDisplayed: displayTiming.record,
    status,
    exercise,
    criteria,
    units,
    setPage,
    active,
    load,
    setCriteriaId,
    loaded,
    busy,
    run,
    progress,
    catalog,
    choose,
    page,
    historyFilter,
    setHistoryFilter,
    visibleHistory,
    setReport,
    pair,
    setPair,
    setComparison,
    comparison,
    user,
    onLogout,
    exerciseId,
    criteriaId,
    config,
    setConfig,
    setAdvanced,
    advanced,
    connected,
    checkReady,
    prepared,
    fingerprint,
    startSession,
    startM3,
    frame,
    setPrepared,
    setError,
    report,
    navigate,
    finishAttempt,
    startAttempt,
    finishSession,
    lastAttempt,
  };
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
          {active && <button onClick={() => setPage("training")}>กลับไปฝึก ●</button>}
        </nav>
      </header>
      <main className="workspace">
        {page !== "dashboard" && (
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={() => navigation.current?.back()}
          >
            ← ย้อนกลับ
          </button>
        )}
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
        <WorkspacePages
          page={page}
          view={view}
          m1Auto={m1Auto}
          prepareM1={prepareM1}
          cancelM1={() => autoController.current?.cancel()}
          cancelM1Training={() => {
            autoController.current?.cancel(true);
            return finishSession(true);
          }}
          resetTrainingState={resetTrainingState}
        />
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
