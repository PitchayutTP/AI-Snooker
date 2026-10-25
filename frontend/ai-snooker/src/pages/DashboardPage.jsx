import { Button } from "../components/ui";
import { Progress } from "../components/Progress";
export default function DashboardPage({ loaded, busy, run, load, progress, catalog, choose, active }) {
  return (<>
            <div className="heading">
              <p className="eyebrow">YOUR PRACTICE SPACE</p>
              <h1>เลือกแบบฝึกของคุณ</h1>
              <p className="muted">
                ฝึกทีละทักษะ บันทึกผล และติดตามการฝึกของตนเอง
              </p>
            </div>
            {!loaded && (
              <Button secondary disabled={busy} onClick={() => run(load)}>
                โหลดแบบฝึกอีกครั้ง
              </Button>
            )}
            <Progress data={progress} catalog={catalog} onChoose={choose} disabled={busy || active}/>
            <div className="modules">
              {[...new Set(catalog.map((e) => e.module_id))].map(
                (id, index) => {
                  const list = catalog.filter((e) => e.module_id === id);
                  return (
                    <article className="module" key={id}>
                      <div className="module-art">
                        <span>0{index + 1}</span>
                        <div className="ball" />
                      </div>
                      <div className="module-body">
                        <p className="eyebrow">
                          MODULE 0{index + 1} · {list.length} แบบฝึก
                        </p>
                        <h2>{list[0].module}</h2>
                        <p className="muted">
                          {list.map((e) => e.name).join(" · ")}
                        </p>
                        <Button
                          disabled={busy || active}
                          onClick={() => choose(list[0])}
                        >
                          เลือกแบบฝึก →
                        </Button>
                      </div>
                    </article>
                  );
                },
              )}
            </div>
          </>);
}
