import assert from "node:assert/strict";
import {
  defaultModuleSettings,
  moduleConfig,
  moduleAdvanced,
  moduleCaptureConfig,
  essentialTrialSettings,
  isPrototypeCriteria,
} from "../src/lib/moduleSettings.js";
const modules = Object.fromEntries([1, 2, 3].map((id) => [id, defaultModuleSettings(id, "LEFT")]));
assert.equal(JSON.parse(modules[3].advanced).cue_ball_colour, "BLUE");
const blueCapture = moduleCaptureConfig(3, modules[3].config, modules[3].advanced);
assert.equal(blueCapture.cue_ball_colour, "BLUE");
assert.equal(blueCapture.ball_colours.cue_ball[0].lower[0], 95);
assert.equal(
  JSON.parse(essentialTrialSettings(3, modules[3].config, modules[3].advanced).advanced)
    .cue_ball_colour,
  "BLUE",
);
const m2Blue = moduleCaptureConfig(2, modules[2].config, modules[2].advanced);
assert.equal(m2Blue.cue_ball_colour, "BLUE");
assert.deepEqual(m2Blue.ball_colours.cue_ball, blueCapture.ball_colours.cue_ball);
assert.equal(
  JSON.parse(essentialTrialSettings(2, modules[2].config, modules[2].advanced).advanced)
    .cue_ball_colour,
  "BLUE",
);
modules[1].config.side_source = "8";
assert.equal(modules[2].config.side_source, undefined);
assert.equal(modules[3].config.side_source, undefined);
assert.equal(modules[1].config.top_source, undefined);
const mixed = {
  pose_model: "pose.task",
  cue_markers: [1, 2],
  hand: "LEFT",
  side_source: "7",
  top_source: "9",
  ball_detector: "HSV",
  homography: [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ],
  table_size: [3569, 1778],
  ball_radius: 26.25,
  m1_auto_seconds: 15,
  smoothing_window: 3,
  delivery_ball_timing: true,
  record_frames: true,
  side_ball_center: [2, 3],
};
const m1 = moduleCaptureConfig(1, modules[1].config, JSON.stringify(mixed));
for (const key of [
  "cue_markers",
  "top_source",
  "homography",
  "ball_detector",
  "table_size",
  "ball_radius",
  "delivery_ball_timing",
  "side_ball_center",
  "m1_auto_seconds",
])
  assert.equal(key in m1, false, key);
assert.equal(m1.pose_model, "pose.task");
assert.equal(m1.hand, "LEFT");
const m3 = moduleCaptureConfig(3, modules[3].config, JSON.stringify(mixed));
for (const key of [
  "hand",
  "side_source",
  "pose_model",
  "cue_markers",
  "delivery_ball_timing",
  "smoothing_window",
  "side_ball_center",
  "m1_auto_seconds",
])
  assert.equal(key in m3, false, key);
assert.deepEqual(m3.table_size, [3569, 1778]);
const m2 = moduleCaptureConfig(
  2,
  modules[2].config,
  JSON.stringify({ ...mixed, m2_mode: "RED_GATE3" }),
);
assert.ok(m2.cue_markers);
assert.ok(m2.homography);
assert.equal(m2.top_source, "1");
for (const removed of [
  "side_source",
  "hand",
  "pose_model",
  "delivery_ball_timing",
  "side_ball_center",
])
  assert.equal(removed in m2, false, removed);
assert.equal("m1_auto_seconds" in m2, false);
assert.equal(moduleConfig(3, mixed).side_source, undefined);
assert.equal(JSON.parse(moduleAdvanced(1, JSON.stringify(mixed))).cue_markers, undefined);
for (const invalid of ["{", "[]", "null", "3"]) {
  assert.equal(moduleAdvanced(1, invalid), invalid);
  assert.throws(() => moduleCaptureConfig(1, {}, invalid));
}
const essential = essentialTrialSettings(
  2,
  { ...modules[2].config, mode: "DEMO", baseline_seconds: 8 },
  JSON.stringify({ ...mixed, min_valid_ratio: 0.01, record_frames: true, ball_radius: 26.25 }),
);
assert.equal(essential.config.mode, "LIVE");
assert.equal(essential.config.purpose, "ASSESSMENT");
assert.equal(essential.config.baseline_seconds, 1);
const clean = JSON.parse(essential.advanced);
assert.equal(clean.motion_threshold, 5.25);
assert.equal("delivery_ball_timing" in clean, false);
assert.equal(clean.m2_mode, "RED_GATE3");
assert.ok(clean.cue_markers);
assert.ok(clean.homography);
assert.equal("record_frames" in clean, false);
assert.equal(clean.min_valid_ratio, 0.8);
const customNoise = essentialTrialSettings(
  2,
  modules[2].config,
  JSON.stringify({ ...mixed, motion_threshold: 4 }),
);
assert.equal(JSON.parse(customNoise.advanced).motion_threshold, 4);
const topOnly = essentialTrialSettings(3, modules[3].config, JSON.stringify(mixed));
assert.equal("cue_markers" in JSON.parse(topOnly.advanced), false);
assert.ok(
  isPrototypeCriteria({
    approved: true,
    validation_scope: "PROTOTYPE",
    rules: { fraction_error: { max: 0.1 } },
    protocol: { required_valid_attempts: 5, minimum_pass_rate: 0.8 },
  }),
);
assert.equal(isPrototypeCriteria({ approved: true, validation_scope: "REPORT" }), false);
const m3Defaults = essentialTrialSettings(
  3,
  modules[3].config,
  JSON.stringify({ ...mixed, ball_radius: 26.25, calibration_check_error: 2 }),
);
assert.equal(m3Defaults.config.baseline_seconds, 1);
const m3Advanced = JSON.parse(m3Defaults.advanced);
assert.equal(m3Advanced.ball_min_area, 12);
assert.equal(m3Advanced.motion_threshold, 5.25);
assert.equal(m3Advanced.calibration_check_error, 2);
console.log("Module settings isolation and essential defaults checks passed");
