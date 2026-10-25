export function TrialLayout({ exercise,advanced }) {
  if(exercise?.module_id!==3)return null;
  let settings;try{settings=JSON.parse(advanced)}catch{return null}
  const [w,h]=settings.table_size || [],r=settings.ball_radius;
  if(!w || !h || !r || w<10*r || h<8*r)return <p className="notice">สอบเทียบโต๊ะก่อน เพื่อดูแผนผังจัดลูกในหน่วยจริง</p>;
  const f=exercise.setup.fraction,target=[w*.65,h*.5],cue=[w*.25,target[1]+2*r*(1-f)];
  const format=value=>Number(value.toFixed(2));
  return <section className="panel"><h2>แผนผังตั้งลูกสำหรับทดลองเหลี่ยม {f}</h2>
    <p>ตัวอย่างตำแหน่งที่ระบบสร้างสำหรับทดลอง ไม่ใช่มาตรฐานจากหนังสือ ใช้หน่วยเดียวกับที่สอบเทียบ และแทงลูกขาวตามเส้นประให้ตรงในแนวนอน</p>
    <svg className="trajectory" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="แผนผังจัดลูกทดลอง"><rect width={w} height={h} fill="#e8eeeb"/><line x1={cue[0]} y1={cue[1]} x2={target[0]+3*r} y2={cue[1]} stroke="#344b6b" strokeWidth={w/500} strokeDasharray={`${r} ${r/2}`}/><circle cx={target[0]} cy={target[1]} r={r} fill="#b65050"/><circle cx={cue[0]} cy={cue[1]} r={r} fill="white" stroke="#344b6b" strokeWidth={w/800}/></svg>
    <p>อ้างอิงมุมซ้ายบนที่คลิกสอบเทียบ: ลูกขาว ({cue.map(format).join(', ')}) · ลูกเป้า ({target.map(format).join(', ')})</p>
    <p className="muted">ตำแหน่งนี้เป็นแนวทางจัดอุปกรณ์ เป้าหมายการประเมินคือเหลี่ยมกระทบ ไม่ใช่การลงหลุม</p>
  </section>
}
