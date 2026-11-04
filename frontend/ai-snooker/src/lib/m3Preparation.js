// Only an applied, complete calibration can trigger real M3 readiness.
import { PRACTICE_AREA } from "./table.js";
export const M3_CALIBRATION_LIMIT_MM = 50;
export function m3CalibrationReady(advanced) {
  try {
    const value = JSON.parse(advanced),
      h = value.homography,
      r = value.ball_radius;
    return (
      Array.isArray(h) &&
      h.length === 3 &&
      h.every((row) => Array.isArray(row) && row.length === 3 && row.every(Number.isFinite)) &&
      Array.isArray(value.table_size) &&
      value.table_size.length === 2 &&
      value.table_size[0] === PRACTICE_AREA.width &&
      value.table_size[1] === PRACTICE_AREA.height &&
      Array.isArray(value.calibration_image_size) &&
      value.calibration_image_size.length === 2 &&
      value.calibration_image_size.every((x) => Number.isFinite(x) && x > 0) &&
      r === PRACTICE_AREA.radius &&
      Number.isFinite(value.calibration_check_error) &&
      value.calibration_check_error >= 0 &&
      value.calibration_check_error <= M3_CALIBRATION_LIMIT_MM
    );
  } catch {
    return false;
  }
}
