import { useEffect } from "react";

export function useRuntimeConnection({ setStatus, setConnected }) {
  useEffect(() => {
    let disposed = false,
      socket,
      timer,
      watchdog;
    function connect() {
      const current = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`,
      );
      socket = current;
      current.onopen = () => {
        if (disposed || socket !== current) return;
        setConnected(true);
        armWatchdog();
      };
      function armWatchdog() {
        clearTimeout(watchdog);
        watchdog = setTimeout(() => {
          if (disposed || socket !== current) return;
          setConnected(false);
          setStatus((old) => ({ ...old, ready: false, frame: {}, live_metrics: {} }));
          current.close();
        }, 4000);
      }
      current.onmessage = (e) => {
        if (!disposed && socket === current) {
          setStatus(JSON.parse(e.data));
          armWatchdog();
        }
      };
      current.onclose = () => {
        if (!disposed && socket === current) {
          clearTimeout(watchdog);
          setConnected(false);
          setStatus((old) => ({ ...old, ready: false, frame: {}, live_metrics: {} }));
          timer = setTimeout(connect, 2000);
        }
      };
    }
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      clearTimeout(watchdog);
      socket?.close();
    };
  }, [setStatus, setConnected]);
}
