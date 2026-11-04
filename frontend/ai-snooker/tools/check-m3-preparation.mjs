import assert from "node:assert/strict";
import { m3CalibrationReady, M3_CALIBRATION_LIMIT_MM } from "../src/lib/m3Preparation.js";
const calibrated = {
  homography: [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ],
  table_size: [1500, 750],
  ball_radius: 26.25,
  calibration_image_size: [1280, 720],
  calibration_check_error: 2,
};
assert.equal(m3CalibrationReady(JSON.stringify(calibrated)), true);
assert.equal(M3_CALIBRATION_LIMIT_MM, 50);
for (const error of [7, 25, 50])
  assert.equal(
    m3CalibrationReady(JSON.stringify({ ...calibrated, calibration_check_error: error })),
    true,
  );
assert.equal(
  m3CalibrationReady(JSON.stringify({ ...calibrated, calibration_check_error: 50.01 })),
  false,
);
for (const patch of [
  { homography: null },
  { table_size: [] },
  { table_size: [750, 1500] },
  { table_size: [3569, 1778] },
  { ball_radius: 25 },
  { calibration_check_error: 55 },
  { calibration_check_error: null },
  { ball_radius: 0 },
  { calibration_image_size: [] },
])
  assert.equal(m3CalibrationReady(JSON.stringify({ ...calibrated, ...patch })), false);
for (const invalid of ["{}", "{", "null"]) assert.equal(m3CalibrationReady(invalid), false);
console.log("M3 applied calibration readiness checks passed");
