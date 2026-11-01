import { useDisplayTiming } from "./hooks/useDisplayTiming";
import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api";
import { createPageHistory } from './lib/pageHistory';
import { createM1AutoTrial,isTimedM1Criteria,M1_RECORD_SECONDS,M1_SMOOTHING_WINDOW,M1_SMOOTHING_TAU_SECONDS } from './lib/m1AutoTrial';
import { defaultModuleSettings,moduleConfig,moduleAdvanced,moduleCaptureConfig,essentialTrialSettings,isPrototypeCriteria } from './lib/moduleSettings';
import DashboardPage from "./pages/DashboardPage";
import ProfilePage from "./pages/ProfilePage";
import SetupPage from "./pages/SetupPage";
import CriteriaPage from "./pages/CriteriaPage";
import TrainingPage from "./pages/TrainingPage";
import SummaryPage from "./pages/SummaryPage";
import HistoryPage from "./pages/HistoryPage";
import M4PreviewPage from './pages/M4PreviewPage';
export default function Workspace({ user, onLogout }) {
  const [page, setPageState] = useState("dashboard"),
    [catalog, setCatalog] = useState([]),
    [units, setUnits] = useState({});
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false);
  const [exerciseId, setExerciseId] = useState(""),
    [criteriaId, setCriteriaId] = useState("");
  const moduleId=catalog.find(e=>String(e.id)===exerciseId)?.module_id || 1;
  const [settingsByModule,setSettingsByModule]=useState(()=>Object.fromEntries([1,2,3].map(id=>[id,defaultModuleSettings(id,user.dominant_hand)])));
  const {config,advanced}=settingsByModule[moduleId];
  function setConfig(value) {
    setSettingsByModule(previous=>({...previous,[moduleId]:{...previous[moduleId],config:moduleConfig(moduleId,{...defaultModuleSettings(moduleId,user.dominant_hand).config,...(typeof value==='function' ? value(previous[moduleId].config) : value)})}}));
  }
  function setAdvanced(value) {
    setSettingsByModule(previous=>({...previous,[moduleId]:{...previous[moduleId],advanced:moduleAdvanced(moduleId,typeof value==='function' ? value(previous[moduleId].advanced) : value)}}));
  }
  const [prepared, setPrepared] = useState("");
  const [status, setStatus] = useState({ frame: {} }),
    [connected, setConnected] = useState(false);
  const [history, setHistory] = useState([]),
    [report, setReport] = useState(null),
    [lastAttempt, setLastAttempt] = useState(null);
  const [pair, setPair] = useState(["", ""]),
    [comparison, setComparison] = useState(null);
  const [progress,setProgress]=useState([]);
  const [activeReport,setActiveReport]=useState(null);
  const [m1Auto,setM1Auto]=useState({phase:'IDLE',error:''});
  const autoController=useRef(null),autoCriteria=useRef(null),autoContext=useRef(null);
  autoContext.current={status,connected,
    start:async()=>{const sid=await startSession({criteriaId:autoCriteria.current,purpose:'ASSESSMENT'});await startAttempt(sid)},
    finish:async()=>{const result=await finishAttempt(false);await finishSession(result.status==='INVALID' || result.status==='ABORTED')},
  };
  useEffect(()=>{
    let mounted=true;
    const controller=createM1AutoTrial({
      start:()=>autoContext.current.start(),finish:()=>autoContext.current.finish(),
      onChange:value=>{if(mounted){setM1Auto(value);if(value.error)setError(value.error)}},
    });
    autoController.current=controller;
    const timer=setInterval(()=>{const current=autoContext.current;void controller.update(current.status,current.connected)},100);
    return ()=>{mounted=false;clearInterval(timer);controller.cancel();autoController.current=null};
  },[]);
  const [historyFilter,setHistoryFilter]=useState({exercise:'',from:'',to:'',mode:''});
  const navigation = useRef(null);
  const navigationContext = useRef(null);
  navigationContext.current = {exerciseId,criteriaId,report,sessionId:status.session_id};
  useEffect(() => {
    const controller=createPageHistory(window,{
      capture:()=>navigationContext.current,
      resolve:(target,context)=>{
        if((target==='setup' || target==='criteria') && !context.exerciseId)return 'dashboard';
        if(target==='training' && !navigationContext.current.sessionId)return 'dashboard';
        if(target==='summary' && !context.report)return 'history';
        return target;
      },
      onChange:(target,context)=>{
        if(target!=='setup' || context.exerciseId!==navigationContext.current.exerciseId)autoController.current?.cancel();
        setPageState(target);
        // Browsing history must not switch the exercise/criteria of a live round.
        if(!navigationContext.current.sessionId) {
          setExerciseId(context.exerciseId || '');
          setCriteriaId(context.criteriaId || '');
        }
        setReport(context.report || null);
      },
    });
    navigation.current=controller;
    controller.start();
    return ()=>{controller.stop();navigation.current=null};
  },[]);
  function setPage(target,context) {
    if(target!=='setup' && ['WAITING','COUNTDOWN'].includes(m1Auto.phase))autoController.current?.cancel();
    navigation.current?.navigate(target,context);
  }
  const visibleHistory=history.filter(s=> (!historyFilter.exercise || String(s.exercise_id)===historyFilter.exercise) && (!historyFilter.mode || s.mode===historyFilter.mode) && (!historyFilter.from || new Date(s.started_at)>=new Date(historyFilter.from+'T00:00:00')) && (!historyFilter.to || new Date(s.started_at)<=new Date(historyFilter.to+'T23:59:59.999')));
  const sessionRequest = useRef(null),
    attemptRequest = useRef(null);
  const exercise = catalog.find((e) => String(e.id) === exerciseId);
  const criteria = exercise?.criteria.find((c) => String(c.id) === criteriaId);
  const fingerprint = JSON.stringify([exerciseId, config, advanced]);
  const active = Boolean(status.session_id);
  const displayTiming = useDisplayTiming(status.attempt_id);
  useEffect(()=>{
    let disposed=false;
    if(!status.session_id)return;
    api(`/sessions/${status.session_id}`).then(value=>{if(!disposed)setActiveReport(value)}).catch(e=>{if(!disposed)setError(e.message)});
    return ()=>{disposed=true};
  },[status.session_id,status.attempt_id,lastAttempt]);
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
  useEffect(()=>{
    let mounted=true;
    if(page==='history' || page==='compare')api('/sessions').then(value=>{if(mounted)setHistory(value)}).catch(e=>{if(mounted)setError(e.message)});
    if(page==='dashboard')api('/progress').then(value=>{if(mounted)setProgress(value)}).catch(e=>{if(mounted)setError(e.message)});
    return ()=>{mounted=false};
  },[page]);
  useEffect(() => {
    let disposed = false,
      socket,
      timer, watchdog;
    function connect() {
      const current = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`,
      );
      socket = current;
      current.onopen = () => {
        if (disposed || socket !== current) return;
        setConnected(true);
        armWatchdog();
      };
      function armWatchdog() {
        clearTimeout(watchdog);
        watchdog = setTimeout(() => {
          if (disposed || socket !== current) return;
          setConnected(false);
          setStatus(old => ({ ...old, ready: false, frame: {}, live_metrics: {} }));
          current.close();
        }, 4000);
      }
      current.onmessage = (e) => {
        if (!disposed && socket === current) {
          setStatus(JSON.parse(e.data));
          armWatchdog();
        }
      };
      current.onclose = () => {
        if (!disposed && socket === current) {
          clearTimeout(watchdog);
          setConnected(false);
          setStatus(old => ({ ...old, ready: false, frame: {}, live_metrics: {} }));
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
    setPage("setup",{exerciseId:String(item.id),criteriaId:String(item.criteria[0]?.id || '')});
    setLastAttempt(null);
  }
  function navigate(target) { setPage(target); }
  async function checkReady() {
    setPrepared("");
    const extra = JSON.parse(advanced);
    if (!extra || Array.isArray(extra) || typeof extra !== "object")
      throw new Error("การตั้งค่าเพิ่มเติมต้องเป็น JSON object");
    let captureConfig=config;
    let captureAdvanced=advanced;
    if(moduleId===2 || moduleId===3) {
      const template=await api(`/exercises/${exerciseId}/criteria-template`);
      const existing=isPrototypeCriteria(criteria) ? criteria : exercise.criteria.find(c=>c.approved && c.validation_scope==='PROTOTYPE' && c.template_version===template.template_version && JSON.stringify(c.rules)===JSON.stringify(template.rules) && JSON.stringify(c.protocol)===JSON.stringify(template.protocol) && c.minimum_active_seconds===template.minimum_active_seconds);
      const chosen=existing || await api(`/exercises/${exerciseId}/criteria`,{...template,approved:true});
      setCriteriaId(String(chosen.id));
      if(!existing)await load();
      const defaults=essentialTrialSettings(moduleId,config,advanced);
      captureConfig=defaults.config;
      captureAdvanced=defaults.advanced;
      setConfig(captureConfig);
      setAdvanced(captureAdvanced);
    }
    await api("/readiness", {
      exercise_id: Number(exerciseId),
      config: moduleCaptureConfig(moduleId,captureConfig,captureAdvanced),
    });
    setPrepared(JSON.stringify([exerciseId,captureConfig,captureAdvanced]));
  }
  async function prepareM1() {
    autoController.current?.cancel();
    setPrepared('');
    const template=await api(`/exercises/${exerciseId}/criteria-template`);
    const existing=isTimedM1Criteria(criteria) ? criteria : exercise.criteria.find(c=>isTimedM1Criteria(c) && c.template_version===template.template_version && JSON.stringify(c.rules)===JSON.stringify(template.rules));
    const created=existing || await api(`/exercises/${exerciseId}/criteria`,{...template,approved:true});
    autoCriteria.current=created.id;
    if(!existing)await load();
    setCriteriaId(String(created.id));
    // Pilot detection threshold, separate from posture pass/fail criteria.
    const liveConfig={...config,mode:'LIVE',purpose:'ASSESSMENT',baseline_seconds:1,visibility:.5,
      smoothing_window:M1_SMOOTHING_WINDOW,smoothing_method:'MEDIAN_EMA',smoothing_tau_seconds:M1_SMOOTHING_TAU_SECONDS,smoothing_max_gap_s:.75,smoothing_for_evaluation:true};
    setConfig(liveConfig);
    setAdvanced('{}');
    const epoch=Date.now();
    await api('/readiness',{exercise_id:Number(exerciseId),config:{...moduleCaptureConfig(1,liveConfig,'{}'),m1_auto_seconds:M1_RECORD_SECONDS}});
    autoController.current?.arm(epoch);
  }
  async function startSession(options={}) {
    sessionRequest.current ||= crypto.randomUUID();
    const result = await api("/sessions", {
      request_id: sessionRequest.current,
      criteria_id: Number(options.criteriaId ?? criteriaId),
      purpose: options.purpose ?? config.purpose ?? "PILOT",
    });
    sessionRequest.current = null;
    // Navigation runs synchronously, before React commits setStatus below.
    // Publish the confirmed session now so the training route guard sees it.
    navigationContext.current={...navigationContext.current,sessionId:result.id};
    setStatus((s) => ({ ...s, session_id: result.id }));
    setLastAttempt(null);
    setPage("training");
    return result.id;
  }
  async function startAttempt(sid=status.session_id) {
    attemptRequest.current ||= crypto.randomUUID();
    const result = await api(`/sessions/${sid}/attempts`, {
      request_id: attemptRequest.current,
    });
    attemptRequest.current = null;
    setStatus((s) => ({ ...s, attempt_id: result.id }));
    setLastAttempt(null);
    return result.id;
  }
  async function finishAttempt(aborted) {
    const result = await api(`/attempts/${status.attempt_id}/finish`, {
      aborted,
      display_timing: displayTiming.summary(),
    });
    setLastAttempt(result);
    setStatus((s) => ({ ...s, attempt_id: null }));
    return result;
  }
  async function finishSession(aborted=false) {
    const result = await api(`/sessions/${status.session_id}/finish`, {
      aborted,
    });
    setReport(result);
    setStatus((s) => ({ ...s, session_id: null, attempt_id: null }));
    setPage("summary",{report:result});
    try {setProgress(await api('/progress'));} catch(e) {setError(e.message);}
    setPrepared("");
  }
  function resetTrainingState() {
    autoController.current?.cancel();
    setHistory([]);setReport(null);setActiveReport(null);setLastAttempt(null);setProgress([]);
    setPair(['','']);setComparison(null);setPrepared('');setM1Auto({phase:'IDLE',error:''});
    setStatus({frame:{},ready:false,session_id:null,attempt_id:null,samples:0,collecting:false});
    sessionRequest.current=null;attemptRequest.current=null;
    navigation.current?.reset('profile',{report:null,sessionId:null});
  }
  const frame = status.frame || {};
  const view = { activeReport: activeReport?.id===status.session_id ? activeReport : null, history, onDisplayed: displayTiming.record, status, exercise, criteria, units, setPage, active, load, setCriteriaId, loaded, busy, run, progress, catalog, choose, page, historyFilter, setHistoryFilter, visibleHistory, setReport, pair, setPair, setComparison, comparison, user, onLogout, exerciseId, criteriaId, config, setConfig, setAdvanced, advanced, connected, checkReady, prepared, fingerprint, startSession, frame, setPrepared, setError, report, navigate, finishAttempt, startAttempt, finishSession, lastAttempt };
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
        {page!=='dashboard' && <button type="button" className="button secondary" disabled={busy} onClick={()=>navigation.current?.back()}>← ย้อนกลับ</button>}
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
        {page === 'm4-preview' && <M4PreviewPage setPage={setPage}/>}
        {page === "profile" && <ProfilePage {...view} onTrainingReset={resetTrainingState} />}
        {page === "setup" && <SetupPage {...view} m1Auto={m1Auto} prepareM1={prepareM1} cancelM1={()=>autoController.current?.cancel()} />}
        {page === "criteria" && <CriteriaPage {...view} />}
        {page === "training" && <TrainingPage {...view} m1Auto={m1Auto} cancelM1={()=>{autoController.current?.cancel(true);return finishSession(true)}} />}
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

