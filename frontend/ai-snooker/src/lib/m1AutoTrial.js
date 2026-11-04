// One-shot controller. Readiness is not a posture correctness assessment.
export const M1_RECORD_SECONDS = 8;
export const M1_MINIMUM_ACTIVE_SECONDS = 7;
export const M1_SMOOTHING_WINDOW = 15;
export const M1_SMOOTHING_TAU_SECONDS = 0.8;
export function isTimedM1Criteria(value) {
  return !!(
    value?.approved &&
    value.template_version === "m1-forearm-stance-8s-v11" &&
    Object.keys(value.rules || {}).length === 1 &&
    value.rules.m1_correct_frame_ratio?.min === 0.8 &&
    Object.keys(value.frame_rules || {}).length === 2 &&
    value.frame_rules.forearm_tilt?.max === 15 &&
    value.frame_rules.knee_shooting?.min === 160 &&
    value.frame_rules.knee_shooting?.max === 180 &&
    value.minimum_valid_frame_ratio === 0.8 &&
    value.preparation_lean_min === 30 &&
    value.protocol?.required_valid_attempts === 1 &&
    value.protocol?.minimum_pass_rate === 1 &&
    value.minimum_active_seconds === M1_MINIMUM_ACTIVE_SECONDS
  );
}

export function createM1AutoTrial({ start, finish, onChange }) {
  let phase = "IDLE",
    readySince = null,
    lastTime = null,
    earliestImage = 0,
    prepareSince = null,
    remaining = null;
  function change(next, error = "") {
    phase = next;
    onChange({ phase, error, remaining });
  }
  return {
    arm(epoch = Date.now()) {
      earliestImage = epoch;
      readySince = null;
      lastTime = null;
      prepareSince = null;
      remaining = null;
      change("WAITING");
    },
    cancel(recording = false) {
      if (phase === "WAITING" || phase === "COUNTDOWN" || (recording && phase === "RECORDING"))
        change("IDLE");
    },
    async update(status, connected) {
      if (phase === "WAITING" || phase === "COUNTDOWN") {
        const t = status.frame?.t;
        if (
          !connected ||
          !status.ready ||
          status.frame?.source !== "LIVE" ||
          !(status.frame?.capture_epoch_ms >= earliestImage) ||
          !Number.isFinite(t)
        ) {
          readySince = null;
          lastTime = null;
          prepareSince = null;
          remaining = null;
          if (phase === "COUNTDOWN") change("WAITING");
          return;
        }
        if (lastTime !== null && (t < lastTime || t - lastTime > 1)) {
          readySince = null;
          prepareSince = null;
          remaining = null;
          if (phase === "COUNTDOWN") change("WAITING");
        }
        lastTime = t;
        readySince ??= t;
        if (phase === "WAITING") {
          if (t - readySince < 1) return;
          prepareSince = t;
          remaining = 5;
          change("COUNTDOWN");
          return;
        }
        const seconds = Math.max(0, Math.ceil(5 - (t - prepareSince)));
        if (seconds !== remaining) {
          remaining = seconds;
          change("COUNTDOWN");
        }
        if (t - prepareSince < 5) return;
        change("STARTING");
        try {
          await start();
          change("RECORDING");
        } catch (e) {
          change("ERROR", e.message);
        }
      } else if (
        phase === "RECORDING" &&
        connected &&
        status.attempt_id &&
        (status.recording_limit_reached || status.error)
      ) {
        change("FINISHING");
        try {
          await finish();
          change("DONE");
        } catch (e) {
          change("ERROR", e.message);
        }
      }
    },
  };
}
