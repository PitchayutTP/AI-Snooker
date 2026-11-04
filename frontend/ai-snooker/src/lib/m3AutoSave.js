// Save a completed decision, including invalid evidence, once per recorded attempt.
export function createM3AutoSave(save, onError = () => {}) {
  const handled = new Set();
  let pending = false;
  return {
    async update(status, { connected = true, busy = false, moduleId = 3 } = {}) {
      const id = status?.attempt_id;
      const trial = moduleId === 2 ? status.frame?.m2_trial : status.frame?.m3_trial;
      if (
        pending ||
        busy ||
        !connected ||
        ![2, 3].includes(moduleId) ||
        !id ||
        !status.session_id ||
        !(status.samples > 0) ||
        status.error ||
        status.collecting === false ||
        !["READY", "INVALID"].includes(trial?.state) ||
        handled.has(id)
      )
        return false;
      pending = true;
      handled.add(id);
      try {
        await save(id);
        return true;
      } catch (error) {
        onError(error);
        return false;
      } finally {
        pending = false;
      }
    },
  };
}
