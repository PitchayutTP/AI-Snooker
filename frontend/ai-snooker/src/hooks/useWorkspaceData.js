import { useEffect } from "react";
import { api } from "../lib/api";

export function useWorkspaceData({
  page,
  setCatalog,
  setUnits,
  setLoaded,
  setError,
  setHistory,
  setProgress,
}) {
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
  }, [setCatalog, setUnits, setLoaded, setError]);
  useEffect(() => {
    let mounted = true;
    if (page === "history" || page === "compare")
      api("/sessions?compact=true")
        .then((value) => {
          if (mounted) setHistory(value);
        })
        .catch((e) => {
          if (mounted) setError(e.message);
        });
    if (page === "dashboard")
      api("/progress")
        .then((value) => {
          if (mounted) setProgress(value);
        })
        .catch((e) => {
          if (mounted) setError(e.message);
        });
    return () => {
      mounted = false;
    };
  }, [page, setHistory, setProgress, setError]);
}
