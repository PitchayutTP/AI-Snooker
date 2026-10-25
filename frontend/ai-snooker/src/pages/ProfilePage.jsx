import { Button } from "../components/ui";
import { api } from "../lib/api";
export default function ProfilePage({ user, busy, active, run, onLogout }) {
  return (<>
            <div className="heading">
              <h1>โปรไฟล์ผู้ฝึก</h1>
            </div>
            <section className="panel narrow">
              <h2>{user.display_name}</h2>
              <p>ชื่อผู้ใช้: {user.username}</p>
              <p>
                มือข้างที่ถนัด: {user.dominant_hand === "LEFT" ? "ซ้าย" : "ขวา"}
              </p>
              <p className="muted">บัญชีนี้ใช้แยกประวัติและผลการฝึกของคุณ</p>
              <Button
                secondary
                disabled={busy || active}
                onClick={() =>
                  run(async () => {
                    await api("/auth/logout", {});
                    onLogout();
                  })
                }
              >
                ออกจากระบบ
              </Button>
              {active && <p>กรุณาจบรอบฝึกก่อนออกจากระบบ</p>}
            </section>
          </>);
}
