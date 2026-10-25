import { useEffect, useState } from "react";
import { api } from "./lib/api";
import { Button } from "./components/ui";
import Auth from "./components/Auth";
import Workspace from "./Workspace";
export default function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("/auth/me")
      .then((value) => {
        if (live) setUser(value);
      })
      .catch((e) => {
        if (live && e.status !== 401) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    const expired = () => setUser(null);
    window.addEventListener("auth-expired", expired);
    return () => {
      live = false;
      window.removeEventListener("auth-expired", expired);
    };
  }, []);
  if (loading)
    return (
      <main className="auth">
        <p role="status">กำลังโหลดระบบ…</p>
      </main>
    );
  if (error)
    return (
      <main className="auth">
        <p className="error">เชื่อมต่อ Backend ไม่ได้: {error}</p>
        <Button onClick={() => location.reload()}>ลองอีกครั้ง</Button>
      </main>
    );
  return user ? (
    <Workspace user={user} onLogout={() => setUser(null)} />
  ) : (
    <Auth onLogin={setUser} />
  );
}
