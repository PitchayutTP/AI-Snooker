import assert from "node:assert/strict";
import {
  imagePoint,
  rgbToHsv,
  ranges,
  validateBallColour,
  DEFAULT_BALL_COLOURS,
  M3_BALL_COLOURS,
  blueBallRanges,
} from "../src/lib/cameraColour.js";
assert.deepEqual(rgbToHsv(255, 0, 0), [0, 255, 255]);
assert.deepEqual(rgbToHsv(255, 255, 255), [0, 0, 255]);
assert.deepEqual(
  imagePoint({ left: 0, top: 0, width: 1000, height: 650 }, 1000, 2000, 500, 325),
  [500, 1000],
);
assert.throws(() => imagePoint({ left: 0, top: 0, width: 1000, height: 650 }, 1000, 2000, 50, 325));
assert.deepEqual(
  imagePoint({ left: 10, top: 20, width: 640, height: 360 }, 1280, 720, 330, 200),
  [640, 360],
);
for (const hue of [0, 179]) {
  const red = ranges([hue, 230, 180]);
  assert.equal(red.length, 2);
  assert.ok(red.some((r) => r.lower[0] === 0));
  assert.ok(red.some((r) => r.upper[0] === 179));
  validateBallColour("target_ball", [hue, 230, 180]);
}
assert.throws(() => validateBallColour("target_ball", [0, 0, 255]));
assert.throws(() => validateBallColour("target_ball", [60, 200, 180]));
assert.throws(() => validateBallColour("cue_ball", [60, 200, 180]));
assert.throws(() => validateBallColour("cue_ball", [0, 0, 50]));
validateBallColour("cue_ball", [0, 30, 180]);
validateBallColour("cue_ball", [28, 130, 175]);
assert.throws(() => validateBallColour("cue_ball", [60, 130, 180]));
assert.throws(() => validateBallColour("cue_ball", [28, 220, 180]));
const contains = (choices, p) =>
  choices.some((r) => p.every((v, i) => v >= r.lower[i] && v <= r.upper[i]));
for (const colour of [
  [110, 220, 180],
  [120, 170, 100],
]) {
  validateBallColour("cue_ball", colour, "BLUE");
  assert.ok(contains(M3_BALL_COLOURS.cue_ball, colour));
  assert.ok(contains(blueBallRanges(colour), colour));
}
for (const colour of [
  [60, 180, 170],
  [0, 230, 200],
  [28, 100, 200],
  [110, 0, 255],
]) {
  assert.throws(() => blueBallRanges(colour));
  assert.ok(!contains(M3_BALL_COLOURS.cue_ball, colour));
}
for (const choices of [DEFAULT_BALL_COLOURS.cue_ball, ranges([28, 100, 210], true, true)]) {
  for (const colour of [
    [0, 0, 240],
    [28, 110, 175],
    [25, 140, 120],
  ])
    assert.ok(contains(choices, colour));
  for (const colour of [
    [60, 130, 180],
    [28, 220, 180],
    [0, 240, 200],
  ])
    assert.ok(!contains(choices, colour));
}
console.log(
  "Camera colour checks passed: contained-image coordinates, red hue wrap, wrong-colour/glare rejection",
);
