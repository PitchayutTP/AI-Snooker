import { M3_BALL_COLOURS } from "./cameraColour.js";
const camera = [
  "mode",
  "purpose",
  "camera_backend",
  "camera_mjpeg",
  "capture_width",
  "capture_height",
  "capture_fps",
];
const quality = [
  "record_frames",
  "min_valid_frames",
  "min_valid_ratio",
  "max_frame_gap_s",
  "setup_notes",
];
const side = [
  "hand",
  "side_source",
  "baseline_seconds",
  "pose_model",
  "visibility",
  "smoothing_window",
  "smoothing_for_evaluation",
  "smoothing_method",
  "smoothing_tau_seconds",
  "smoothing_max_gap_s",
];
const top = [
  "top_source",
  "ball_detector",
  "ball_colours",
  "ball_min_area",
  "ball_max_area",
  "ball_max_jump",
  "homography",
  "table_size",
  "ball_radius",
  "calibration_image_size",
  "calibration_check_error",
  "contact_tolerance",
  "motion_threshold",
];
const delivery = ["cue_markers", "m2_mode", "m2_red_points", "m2_tip_offset_mm"];
const configKeys = new Set([
  ...camera,
  "record_frames",
  "hand",
  "side_source",
  "top_source",
  "baseline_seconds",
  "visibility",
  "smoothing_window",
  "smoothing_for_evaluation",
  "smoothing_method",
  "smoothing_tau_seconds",
  "smoothing_max_gap_s",
]);
function allowed(moduleId) {
  if (moduleId === 1) return new Set([...camera, ...quality, ...side]);
  if (moduleId === 2)
    return new Set([
      ...camera,
      ...quality,
      ...top,
      ...delivery,
      "baseline_seconds",
      "cue_ball_colour",
    ]);
  if (moduleId === 3)
    return new Set([...camera, ...quality, ...top, "baseline_seconds", "cue_ball_colour"]);
  throw new Error("ไม่พบโมดูลสำหรับการตั้งค่า");
}
function project(value, keys) {
  if (!value || Array.isArray(value) || typeof value !== "object")
    throw new Error("การตั้งค่าต้องเป็น JSON object");
  return Object.fromEntries(Object.entries(value).filter(([key]) => keys.has(key)));
}
export function defaultModuleSettings(moduleId, hand = "RIGHT") {
  return {
    config: {
      mode: "LIVE",
      purpose: "PILOT",
      ...(moduleId === 1
        ? { hand, side_source: "0", baseline_seconds: 1 }
        : moduleId === 2
          ? { baseline_seconds: 1 }
          : {}),
      ...(moduleId !== 1 ? { top_source: "1" } : {}),
    },
    advanced:
      moduleId === 3
        ? JSON.stringify({ cue_ball_colour: "BLUE", ball_colours: M3_BALL_COLOURS })
        : moduleId === 2
          ? JSON.stringify({
              m2_mode: "RED_GATE3",
              cue_ball_colour: "BLUE",
              ball_colours: M3_BALL_COLOURS,
            })
          : "{}",
  };
}
export function moduleConfig(moduleId, value) {
  const keys = allowed(moduleId);
  return project(value, new Set([...configKeys].filter((key) => keys.has(key))));
}
export function moduleAdvanced(moduleId, value) {
  // Keep invalid JSON visible in the editor; validation happens before capture.
  let parsed;
  try {
    parsed = JSON.parse(value);
  } catch {
    return value;
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") return value;
  return JSON.stringify(project(parsed, allowed(moduleId)), null, 2);
}
export function moduleCaptureConfig(moduleId, config, advanced) {
  const result = project(
    { ...project(JSON.parse(advanced), allowed(moduleId)), ...config },
    allowed(moduleId),
  );
  return result;
}

export function essentialTrialSettings(moduleId, config, advanced) {
  const original = project(JSON.parse(advanced), allowed(moduleId));
  const physical = new Set([
    "ball_colours",
    "cue_ball_colour",
    "cue_markers",
    "m2_mode",
    "m2_red_points",
    "m2_tip_offset_mm",
    "homography",
    "table_size",
    "ball_radius",
    "calibration_image_size",
    "calibration_check_error",
    "ball_detector",
    "setup_notes",
  ]);
  const settings = project(original, physical);
  settings.ball_detector ??= "HSV";
  if (moduleId === 2) {
    settings.m2_mode = "RED_GATE3";
    settings.min_valid_ratio = 0.8;
    // Initial noise tolerance, not a measured accuracy or a training pass rule.
    settings.motion_threshold =
      original.motion_threshold > 0
        ? original.motion_threshold
        : (settings.ball_radius || 26.25) * 0.2;
  }
  if (moduleId === 3) {
    settings.ball_min_area = 12;
    settings.motion_threshold = (settings.ball_radius || 26.25) * 0.2;
  }
  return {
    config: moduleConfig(moduleId, {
      ...config,
      mode: "LIVE",
      purpose: "ASSESSMENT",
      baseline_seconds: 1,
    }),
    advanced: moduleAdvanced(moduleId, JSON.stringify(settings)),
  };
}
export function isPrototypeCriteria(value) {
  return !!(
    value?.approved &&
    value.validation_scope === "PROTOTYPE" &&
    Object.keys(value.rules || {}).length &&
    value.protocol?.required_valid_attempts > 0 &&
    value.protocol?.minimum_pass_rate > 0
  );
}
