// Render pages with realistic state, without a browser, camera or HTTP server.
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { build } from "vite";
import React from "react";
import { renderToString } from "react-dom/server";

const folder = path.resolve("node_modules/.cache/snooker-render-check");
await mkdir(folder, { recursive: true });
const names = [
  "DashboardPage",
  "ProfilePage",
  "SetupPage",
  "CriteriaPage",
  "TrainingPage",
  "SummaryPage",
  "HistoryPage",
  "M4PreviewPage",
];
const entry = path.join(folder, "entry.jsx");
await writeFile(
  entry,
  names
    .map(
      (name) =>
        `export {default as ${name}} from ${JSON.stringify(path.resolve("src/pages", name + ".jsx").replaceAll("\\", "/"))};`,
    )
    .join("\n") +
    `\nexport {WorkspacePages} from ${JSON.stringify(path.resolve("src/components/WorkspacePages.jsx").replaceAll("\\", "/"))};`,
);
await build({
  logLevel: "error",
  build: {
    ssr: entry,
    outDir: path.join(folder, "output"),
    emptyOutDir: false,
    rollupOptions: { output: { entryFileNames: "entry.mjs" } },
  },
});
const pages = await import(pathToFileURL(path.join(folder, "output/entry.mjs")));
const exercise = {
  id: 1,
  module_id: 1,
  module: "Foundation",
  name: "ท่าทาง",
  setup: { requires: ["side"] },
  instructions: "ทดลองท่าทาง",
  lesson: { goal: "ท่าทาง", camera: "side", steps: ["หยุดนิ่ง"], metrics: ["elbow_mean"] },
  criteria: [{ id: 1, version: 1, approved: false, rules: {} }],
};
const fn = () => {};
const props = {
  user: { username: "check", display_name: "Check", dominant_hand: "RIGHT" },
  catalog: [exercise],
  exercise,
  criteria: exercise.criteria[0],
  units: { elbow_mean: "degree" },
  loaded: true,
  busy: false,
  active: false,
  progress: [],
  history: [],
  visibleHistory: [],
  historyFilter: { exercise: "", from: "", to: "", mode: "" },
  pair: ["", ""],
  comparison: null,
  page: "history",
  exerciseId: "1",
  criteriaId: "1",
  config: { mode: "LIVE", hand: "RIGHT", side_source: "0", top_source: "1" },
  advanced: "{}",
  connected: true,
  prepared: "",
  fingerprint: "check",
  frame: {},
  status: { frame: {}, mode: "LIVE", configuration: {} },
  report: {
    protocol_result: {
      purpose: "ASSESSMENT",
      status: "INCOMPLETE",
      valid_attempts: 2,
      required_valid_attempts: 4,
      invalid_attempts: 1,
      remaining: 2,
      pass_rate: 0.5,
      minimum_pass_rate: 0.75,
    },
    id: "check",
    name: "ท่าทาง",
    started_at: "2026-01-01T00:00:00Z",
    mode: "LIVE",
    attempts: [
      {
        id: "attempt",
        number: 1,
        status: "INVALID",
        reason: "ยังไม่ยืนยันเกณฑ์",
        metrics: { elbow_mean: { value: 90, unit: "degree" } },
        feedback: [],
        quality: { samples: 30, duration_s: 2, not_ready_frames: 0, processing_ms: { mean: 20 } },
        display_timing: { n: 10, median_ms: 40, p95_ms: 60, clock_uncertainty_ms: 1 },
      },
    ],
    counts: { PASS: 0, FAIL: 0 },
    pass_rate: null,
  },
  activeReport: {
    protocol_result: {
      purpose: "ASSESSMENT",
      status: "IN_PROGRESS",
      valid_attempts: 2,
      required_valid_attempts: 4,
      invalid_attempts: 1,
      remaining: 2,
      pass_rate: 0.5,
      minimum_pass_rate: 0.75,
    },
  },
  lastAttempt: { status: "INVALID", reason: "ยังไม่ยืนยันเกณฑ์", metrics: {}, feedback: [] },
};
for (const name of [
  "setPage",
  "load",
  "setCriteriaId",
  "run",
  "choose",
  "setHistoryFilter",
  "setReport",
  "setPair",
  "setComparison",
  "onLogout",
  "setConfig",
  "setAdvanced",
  "checkReady",
  "startSession",
  "setPrepared",
  "setError",
  "navigate",
  "finishAttempt",
  "startAttempt",
  "startM3",
  "finishSession",
  "onDisplayed",
])
  props[name] = fn;
let count = 0;
for (const [name, Page] of Object.entries(pages).filter(([name]) => name !== "WorkspacePages")) {
  for (const variant of name === "HistoryPage"
    ? [{ page: "history" }, { page: "compare" }]
    : name === "TrainingPage"
      ? [
          { active: false },
          {
            active: true,
            status: {
              frame: {
                t: 1,
                images: { side: "AA==", top: "AA==" },
                image_sizes: { side: [1280, 720], top: [1280, 720] },
              },
              configuration: { table_size: [3500, 1750] },
              mode: "LIVE",
            },
          },
        ]
      : name === "SetupPage"
        ? [
            {},
            {
              exercise: { ...exercise, module_id: 3, setup: { fraction: 0.5 } },
              advanced: JSON.stringify({ table_size: [3500, 1750], ball_radius: 26 }),
            },
          ]
        : [{}]) {
    const html = renderToString(React.createElement(Page, { ...props, ...variant }));
    if (!html.length) throw new Error(`${name} rendered empty`);
    count++;
  }
}
const completedPlan = {
  purpose: "ASSESSMENT",
  status: "READY_TO_FINISH",
  valid_attempts: 1,
  required_valid_attempts: 1,
  invalid_attempts: 2,
  remaining: 0,
  pass_rate: 1,
  minimum_pass_rate: 1,
};
const m1Criteria = {
  approved: true,
  rules: {
    elbow_min: { min: 80 },
    elbow_max: { max: 100 },
    knee_shooting_min: { min: 160 },
    knee_shooting_max: { max: 180 },
  },
  minimum_active_seconds: 7,
};
const training = renderToString(
  React.createElement(pages.TrainingPage, {
    ...props,
    active: true,
    criteria: m1Criteria,
    activeReport: { protocol_result: completedPlan },
    units: {
      elbow_min: "degree",
      elbow_max: "degree",
      knee_shooting_min: "degree",
      knee_shooting_max: "degree",
    },
  }),
);
for (const text of [
  "ผ่านอย่างน้อย 1 จาก 1",
  "ครบจำนวนแล้ว",
  "มุมศอกต่ำสุด",
  "ต่ำสุด 80",
  "สูงสุด 100",
  "ต่ำสุด 160",
  "สูงสุด 180",
]) {
  if (!training.replaceAll("<!-- -->", "").includes(text))
    throw new Error(`M1 completion guidance missing: ${text}`);
}
const criteriaPage = renderToString(
  React.createElement(pages.CriteriaPage, { ...props, criteria: m1Criteria }),
);
if (!criteriaPage.includes("เติมเกณฑ์ตั้งต้น M1 พร้อมแผนจบรอบ"))
  throw new Error("M1 template action missing");
count += 2;
for (const [moduleId, extra, required, absent] of [
  [
    1,
    {},
    ["หมายเลขกล้องด้านข้าง", "มือที่ถนัด"],
    ["หมายเลขกล้องด้านบน", "เลือกจุดสอบเทียบพื้นที่ฝึกจากกล้องบน", "ไฟล์โมเดลลูก (ภายใน"],
  ],
  [
    2,
    {},
    [
      "มาร์กเกอร์ใกล้ปลายคิวหนึ่งจุด",
      "หมายเลขกล้องด้านบน",
      "เลือกจุดสอบเทียบพื้นที่ฝึกจากกล้องบน",
      "หัวคิวส่งถึงแนวคู่ที่ 3",
    ],
    ["หมายเลขกล้องด้านข้าง"],
  ],
  [
    2,
    { m2_mode: "RED_GATE3", delivery_ball_timing: false },
    ["หมายเลขกล้องด้านบน", "1,500 × 750", "26.25", "ระยะศูนย์กลางมาร์กเกอร์ด้านหน้าไปถึงหัวคิว"],
    ["หมายเลขกล้องด้านข้าง", "ระยะเริ่มเคลื่อนลูก (มม.;"],
  ],
  [
    3,
    {},
    ["หมายเลขกล้องด้านบน", "1,500 × 750", "52.5", "26.25"],
    [
      "หมายเลขกล้องด้านข้าง",
      "มือที่ถนัด",
      "M2 ใช้สองกล้อง",
      "จำนวนเฟรม Moving Average",
      "ช่วงฐาน (วินาที)",
    ],
  ],
]) {
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: moduleId },
      advanced: JSON.stringify(extra),
    }),
  ).replaceAll("<!-- -->", "");
  for (const text of required)
    if (!html.includes(text)) throw new Error(`M${moduleId} setup missing ${text}`);
  for (const text of absent)
    if (html.includes(text)) throw new Error(`M${moduleId} setup has unnecessary ${text}`);
  if (html.includes("<details open"))
    throw new Error("Advanced settings should be collapsed by default");
  if (!html.includes(`ตั้งค่ากล้อง M${moduleId}`)) throw new Error("Module camera heading missing");
  count++;
}
for (const [phase, elapsed, text] of [
  ["RECORDING", 3, "เหลือประมาณ 5 วินาที"],
  ["FINISHING", 8, "ครบเวลาแล้ว"],
]) {
  const html = renderToString(
    React.createElement(pages.TrainingPage, {
      ...props,
      active: true,
      m1Auto: { phase },
      status: {
        ...props.status,
        attempt_id: "timed",
        attempt_elapsed_s: elapsed,
        configuration: { m1_auto_seconds: 8 },
      },
    }),
  ).replaceAll("<!-- -->", "");
  if (
    !html.includes(text) ||
    html.includes("เริ่มและจบแต่ละครั้งด้วยตนเอง") ||
    html.includes("จบการบันทึกครั้งนี้")
  )
    throw new Error(`Timed M1 guidance incorrect: ${phase}`);
  count++;
}
const scopedCatalog = [1, 2, 3].map((module_id) => ({
  ...exercise,
  id: module_id,
  module_id,
  name: `unique-module-${module_id}`,
}));
for (const ex of scopedCatalog) {
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      catalog: scopedCatalog,
      exercise: ex,
      exerciseId: String(ex.id),
    }),
  );
  for (const other of scopedCatalog.filter((item) => item.id !== ex.id))
    if (html.includes(other.name)) throw new Error("Other module leaked into exercise selector");
  count++;
}
const simpleM1 = renderToString(
  React.createElement(pages.SetupPage, {
    ...props,
    status: {
      ...props.status,
      frame: { preview_only: true, preview_camera: "side", image: "AA==", image_size: [1280, 720] },
    },
  }),
).replaceAll("<!-- -->", "");
for (const text of [
  "มือที่ถนัด",
  "หมายเลขกล้องด้านข้าง",
  "ตั้งค่ากล้อง M1",
  "เกณฑ์ M1",
  "เริ่มตรวจท่าอัตโนมัติ 8 วินาที",
  "Median 15 เฟรม + EMA 0.8 วินาที",
])
  if (!simpleM1.includes(text)) throw new Error(`M1 essential control missing: ${text}`);
for (const text of [
  "การตั้งค่าเพิ่มเติม (JSON)",
  "โหมดข้อมูล",
  "เก็บภาพดิบเป็นหลักฐาน",
  "โหลดไฟล์ตั้งค่า",
  "จำนวนเฟรม Moving Average",
  "ส่งออกค่าโมดูลนี้",
  "ดาวน์โหลดภาพสอบเทียบ",
  "ช่วงฐาน (วินาที)",
])
  if (simpleM1.includes(text)) throw new Error(`M1 unnecessary control visible: ${text}`);
count++;
const preparation = renderToString(
  React.createElement(pages.SetupPage, { ...props, m1Auto: { phase: "COUNTDOWN", remaining: 3 } }),
).replaceAll("<!-- -->", "");
if (simpleM1.includes('type="checkbox"') && simpleM1.includes("ฉันยืนยันว่าจะจัดคาง"))
  throw new Error("M1 still requires chin confirmation");
for (const text of ["ท่อนแขนเอียงจากแนวดิ่ง", "มุมเข่าฝั่งแทง", "80%", "30°"])
  if (!simpleM1.includes(text)) throw new Error(`M1 forearm/leg rule missing: ${text}`);
if (simpleM1.includes("มุมเข่าฝั่งสะพานมือต่ำสุด"))
  throw new Error("M1 still evaluates support leg");
if (simpleM1.includes("มุมลำตัวกับแนวนอนต่ำสุด")) throw new Error("M1 still evaluates torso");
if (
  !preparation.includes("เตรียมตัว 3 วินาที") ||
  !preparation.includes("ยังไม่บันทึก") ||
  !preparation.includes("ยกเลิกการรอ")
)
  throw new Error("M1 preparation countdown missing");
count++;
for (const id of [2, 3]) {
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: id },
      advanced: "{}",
    }),
  );
  for (const text of [
    "การตั้งค่าเพิ่มเติม (JSON)",
    "โหมดข้อมูล",
    "เก็บภาพดิบเป็นหลักฐาน",
    "จำนวนเฟรม Moving Average",
    "โหลดไฟล์ตั้งค่า",
    "ส่งออกค่าโมดูลนี้",
    "ช่วงฐาน (วินาที)",
    "พื้นที่ลูกต่ำสุด (px²)",
    "ระยะเริ่มเคลื่อนลูก (มม.;",
    'type="file"',
  ])
    if (html.includes(text)) throw new Error(`M${id} unnecessary setting: ${text}`);
  for (const text of [
    `เกณฑ์ M${id}`,
    id === 3 ? "ตรวจความพร้อมอีกครั้ง" : "ตรวจความพร้อมและใช้เกณฑ์ต้นแบบ",
    id === 3 ? "เริ่มฝึกและบันทึก" : "เริ่มรอบฝึก",
  ])
    if (!html.replaceAll("<!-- -->", "").includes(text))
      throw new Error(`M${id} essential action missing: ${text}`);
  count++;
}
for (const active of [false, true]) {
  const html = renderToString(React.createElement(pages.ProfilePage, { ...props, active }));
  if (!html.includes("ล้างข้อมูลการฝึกทั้งหมด"))
    throw new Error("Reset component missing from profile");
  if (active && !html.includes("จบหรือยุติรอบฝึกก่อนรีเซ็ต"))
    throw new Error("Reset active-session guard missing");
  count++;
}

count++;
const elbowFrame = {
  t: 1,
  elbow: 90,
  knee_shooting: 170,
  elbow_preview: { image: "AA==" },
  raw_measurements: { elbow: 91 },
  elbow_detail: {
    valid: true,
    confidence: 0.9,
    upper_arm_px: 80,
    forearm_px: 75,
    minimum_segment_px: 9,
  },
};
for (const name of ["SetupPage", "TrainingPage"]) {
  const html = renderToString(
    React.createElement(pages[name], {
      ...props,
      active: name === "TrainingPage",
      criteria: { approved: true, template_version: "m1-forearm-stance-8s-v11", rules: {} },
      m1Auto: { phase: "WAITING" },
      frame: elbowFrame,
      status: {
        ...props.status,
        frame: elbowFrame,
        configuration: { exercise_id: 1, m1_auto_seconds: 8 },
      },
    }),
  ).replaceAll("<!-- -->", "");
  for (const text of [
    "รายละเอียดท่อนแขนฝั่งแทง",
    "ภาพขยายไหล่ ศอก และข้อมือฝั่งแทง",
    "คุณภาพจุดศอกและค่ามุม",
  ])
    if (!html.includes(text)) throw new Error(`${name}: elbow detail missing ${text}`);
  if (html.includes("เข่าอีกข้าง (°)")) throw new Error("Support leg value still displayed");
  count++;
}
for (const [elapsed, blocked] of [
  [1.9, true],
  [2, false],
]) {
  const html = renderToString(
    React.createElement(pages.TrainingPage, {
      ...props,
      active: true,
      exercise: { ...exercise, module_id: 3 },
      criteria: { minimum_active_seconds: 1 },
      status: {
        attempt_id: "m3",
        attempt_elapsed_s: elapsed,
        frame: { balls: [] },
        configuration: { exercise_id: 3, baseline_seconds: 1 },
      },
    }),
  );
  const finish = html.match(/<button[^>]*>จบการบันทึกครั้งนี้<\/button>/)?.[0];
  if (!finish || finish.includes("disabled") !== blocked)
    throw new Error("M3 minimum recording duration guard failed");
  if (!html.includes("การตรวจจับลูก M3")) throw new Error("M3 ball status missing");
  count++;
}
for (const state of ["MISSING", "AMBIGUOUS", "COLOUR_OVERLAP"]) {
  const detail = {
    status: state,
    mask_pixels: 123,
    candidates: state === "AMBIGUOUS" ? 2 : 0,
    rejected: { area: 1, shape: 2, size: 3 },
  };
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: 3, setup: { fraction: 0.5 } },
      prepared: "check",
      status: {
        configuration: { exercise_id: 3 },
        frame: {
          balls: [],
          ball_detection: { detector: "HSV", roles: { cue_ball: detail, target_ball: detail } },
          m3_preparation: { state: "WAITING", stable_seconds: 0 },
        },
      },
    }),
  );
  if (!html.includes("การตรวจจับลูก M3") || !html.includes("พิกเซลสี"))
    throw new Error("M3 detection diagnostics missing");
  count++;
}
for (const state of ["BASELINE", "WAITING_SHOT", "FOLLOW_THROUGH", "READY", "INVALID"]) {
  const status = {
    attempt_id: "m2",
    configuration: { exercise_id: 2 },
    frame: { balls: [], m2_trial: { state, reason: `M2 ${state}` } },
  };
  const html = renderToString(
    React.createElement(pages.TrainingPage, {
      ...props,
      active: true,
      exercise: { ...exercise, module_id: 2 },
      status,
    }),
  );
  const finish = html.match(/<button[^>]*>จบการบันทึกครั้งนี้<\/button>/)?.[0];
  if (!finish || finish.includes("disabled") !== !["READY", "INVALID"].includes(state))
    throw new Error(`M2 finish gate failed: ${state}`);
  if (!html.includes(`M2 ${state}`)) throw new Error(`M2 phase missing: ${state}`);
  count++;
}
{
  const frame = {
    preview_only: true,
    preview_camera: "top",
    detection_preview: true,
    image: "preview",
    balls: [
      { class: "cue_ball", id: 1 },
      { class: "target_ball", id: 2 },
    ],
    ball_detection: {
      detector: "HSV",
      roles: { cue_ball: { status: "OK" }, target_ball: { status: "OK" } },
    },
  };
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: 3 },
      frame,
      status: { configuration: {}, frame },
    }),
  );
  if (
    !html.includes("ทดลองตรวจจับสีลูก — ไม่ต้องสอบเทียบ") ||
    !html.includes("พบหนึ่งลูก") ||
    !html.includes("ยังไม่กรองขนาดจริงบนโต๊ะ")
  )
    throw new Error("Uncalibrated M3 inspection missing");
  if (html.includes("หยุดภาพเพื่อเลือกจุด"))
    throw new Error("Colour selection must use raw image, not detection overlay");
  count++;
}
for (const ready of [false, true]) {
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: 3 },
      prepared: "check",
      fingerprint: "check",
      status: { configuration: { exercise_id: 3 }, ready, frame: {} },
    }),
  );
  const button = html.match(/<button[^>]*>เริ่มฝึกและบันทึก<\/button>/)?.[0];
  if (!button || button.includes("disabled") === ready)
    throw new Error("M3 ready-to-record gate failed");
  if (!html.includes("ระบบตรวจจับและเตรียมเกณฑ์ให้อัตโนมัติ"))
    throw new Error("M3 auto preparation guidance missing");
  count++;
}
{
  const detail = {
    status: "MISSING",
    mask_pixels: 400,
    raw_mask_pixels: 400,
    roi_mask_pixels: 400,
    candidates: 0,
    rejected: { area: 0, shape: 0, size: 1, outside: 0 },
    size_examples: [{ equivalent_diameter: 25, expected_diameter: 52.5, image_radius_px: 15 }],
  };
  const frame = {
    ball_detection: {
      calibrated: true,
      table_size: [800, 400],
      detector: "HSV",
      roles: { cue_ball: detail, target_ball: detail },
    },
  };
  const html = renderToString(
    React.createElement(pages.SetupPage, {
      ...props,
      exercise: { ...exercise, module_id: 3 },
      prepared: "check",
      frame,
      status: { configuration: { exercise_id: 3 }, frame },
    }),
  );
  if (
    !html.includes("เส้นผ่านศูนย์กลางจากสเกลสอบเทียบประมาณ") ||
    !html.includes("กรอบสีฟ้าคือพื้นที่สอบเทียบ")
  )
    throw new Error("Calibrated detection rejection explanation missing");
  count++;
}
{
  const status = {
    configuration: { exercise_id: 2, m2_mode: "RED_GATE3" },
    attempt_id: "red4",
    frame: {
      m2_red_visible: [true, true, true, true, true],
      m2_tip_margin_mm: 10,
      m2_trial: { state: "READY", reason: "เก็บครบแดงลูกที่ 3" },
    },
  };
  const html = renderToString(
    React.createElement(pages.TrainingPage, {
      ...props,
      active: true,
      exercise: { ...exercise, module_id: 2 },
      status,
    }),
  );
  if (!html.includes("หัวคิวประมาณเทียบแนวแดงคู่ที่ 3") || html.includes("ศีรษะจากช่วงฐาน"))
    throw new Error("RED3 training still uses old posture measurements");
  count++;
}
for (const [attempt, samples, elapsed, expected] of [
  [null, 0, 0, "ยังไม่ได้เริ่มบันทึก"],
  ["a", 0, 0, "กำลังรอเฟรมแรกจากกล้อง"],
  ["a", 10, 0.5, "กำลังบันทึกช่วงฐาน"],
  ["a", 30, 1.5, "กำลังบันทึกแล้ว"],
]) {
  const status = {
    session_id: "s",
    attempt_id: attempt,
    samples,
    attempt_elapsed_s: elapsed,
    configuration: { exercise_id: 3 },
    frame: {},
  };
  const html = renderToString(
    React.createElement(pages.TrainingPage, {
      ...props,
      active: true,
      lastAttempt: null,
      exercise: { ...exercise, module_id: 3 },
      status,
    }),
  );
  if (!html.includes(expected)) throw new Error("M3 recording state not visible: " + expected);
  count++;
}
console.log(`Page render checks passed: ${count} states`);

const m4 = renderToString(React.createElement(pages.M4PreviewPage, { setPage: fn }));
for (const text of [
  "รูปแบบที่ 1",
  "รูปแบบที่ 2",
  "รูปแบบที่ 3",
  "ยังไม่เปิดฝึก",
  "ยังไม่เปิดใช้งาน",
])
  if (!m4.includes(text)) throw new Error(`M4 preview missing ${text}`);
if (!m4.includes('disabled=""')) throw new Error("M4 actions must remain disabled");
const dashboard = renderToString(React.createElement(pages.DashboardPage, props));
if (!dashboard.includes("ดูหน้าตัวอย่าง M4")) throw new Error("M4 dashboard entry missing");

for (const page of [
  "dashboard",
  "profile",
  "setup",
  "criteria",
  "training",
  "m4-preview",
  "summary",
  "history",
  "compare",
]) {
  const html = renderToString(
    React.createElement(pages.WorkspacePages, {
      page,
      view: { ...props, page },
      m1Auto: { phase: "IDLE" },
      prepareM1: fn,
      cancelM1: fn,
      cancelM1Training: fn,
      resetTrainingState: fn,
    }),
  );
  if (!html.length) throw new Error(`Workspace screen selection failed: ${page}`);
}
console.log("Workspace screen selection checks passed: all nine destinations, including M4");
