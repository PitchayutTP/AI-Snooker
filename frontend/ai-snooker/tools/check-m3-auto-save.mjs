import assert from "node:assert/strict";
import { createM3AutoSave } from "../src/lib/m3AutoSave.js";
const calls = [],
  errors = [];
const controller = createM3AutoSave(
  async (id) => calls.push(id),
  (error) => errors.push(error.message),
);
const ready = {
  session_id: "s",
  attempt_id: "a",
  samples: 40,
  frame: { m3_trial: { state: "READY" } },
};
for (const status of [
  { ...ready, attempt_id: null },
  { ...ready, samples: 0 },
  { ...ready, samples: undefined },
  { ...ready, collecting: false },
  { ...ready, error: "กล้องไม่ส่งภาพ" },
  { ...ready, frame: { m3_trial: { state: "CONTACT" } } },
])
  assert.equal(await controller.update(status), false);
assert.equal(await controller.update(ready, { connected: false }), false);
assert.equal(await controller.update(ready, { busy: true }), false);
assert.equal(await controller.update(ready, { moduleId: 2 }), false);
assert.equal(await controller.update(ready), true);
assert.equal(await controller.update(ready), false);
assert.deepEqual(calls, ["a"]);
assert.equal(await controller.update({ ...ready, attempt_id: "b" }), true);
assert.equal(
  await controller.update({
    ...ready,
    attempt_id: "recovering",
    frame: { m3_trial: { state: "RECOVERING" } },
  }),
  false,
);
assert.equal(
  await controller.update({
    ...ready,
    attempt_id: "invalid",
    frame: { m3_trial: { state: "INVALID" } },
  }),
  true,
);
assert.equal(
  await controller.update({
    ...ready,
    attempt_id: "invalid",
    frame: { m3_trial: { state: "INVALID" } },
  }),
  false,
);
const failure = createM3AutoSave(
  async () => {
    throw new Error("DB unavailable");
  },
  (error) => errors.push(error.message),
);
assert.equal(await failure.update(ready), false);
assert.equal(await failure.update(ready), false);
assert.deepEqual(errors, ["DB unavailable"]);
let release;
const pending = createM3AutoSave(
  () =>
    new Promise((resolve) => {
      release = resolve;
    }),
);
const running = pending.update(ready);
assert.equal(await pending.update(ready), false);
release();
assert.equal(await running, true);
console.log(
  "M3 auto-save checks passed: recording required, complete evidence, once per attempt, retry remains manual",
);
const m2Calls = [];
const m2 = createM3AutoSave(async (id) => m2Calls.push(id));
for (const state of ["READY", "INVALID"]) {
  const status = { ...ready, attempt_id: `m2-${state}`, frame: { m2_trial: { state } } };
  assert.equal(await m2.update(status, { moduleId: 2 }), true);
  assert.equal(await m2.update(status, { moduleId: 2 }), false);
}
assert.equal(
  await m2.update(
    { ...ready, attempt_id: "m2-wait", frame: { m2_trial: { state: "BASELINE" } } },
    { moduleId: 2 },
  ),
  false,
);
assert.deepEqual(m2Calls, ["m2-READY", "m2-INVALID"]);
console.log(
  "M2 auto-save checks passed: complete or invalid evidence saved once; baseline not saved",
);
