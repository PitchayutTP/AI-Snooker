import {useState} from 'react';
import {Button,Field} from '../components/ui';

const patterns=[
  {name:'รูปแบบที่ 1 — ชิ่งด้านบน',cue:[140,220],target:[660,220],obstacle:[400,220],bounce:[400,40]},
  {name:'รูปแบบที่ 2 — ชิ่งด้านซ้าย',cue:[260,100],target:[260,300],obstacle:[260,200],bounce:[40,200]},
  {name:'รูปแบบที่ 3 — ชิ่งด้านล่าง',cue:[140,140],target:[660,140],obstacle:[400,140],bounce:[400,360]},
];

export default function M4PreviewPage({setPage}) {
  const [selected,setSelected]=useState(0);
  const pattern=patterns[selected];
  return <>
    <div className="heading"><p className="eyebrow">MODULE 04</p><h1>การแก้สนุกพื้นฐาน</h1><p>แบบฝึกแก้สนุกหนึ่งชิ่ง 3 รูปแบบ</p></div>
    <p className="notice" role="status">หน้าตัวอย่าง — ยังไม่เปิดฝึก ตรวจกล้อง หรือบันทึกผล M4</p>
    <section className="panel"><h2>เลือกรูปแบบ</h2>
      <div className="actions">{patterns.map((item,index)=><Button key={item.name} secondary={selected!==index} aria-pressed={selected===index} onClick={()=>setSelected(index)}>{item.name}</Button>)}</div>
    </section>
    <div className="columns"><section className="panel"><h2>{pattern.name}</h2>
      <svg className="trajectory" viewBox="0 0 800 400" role="img" aria-label={`แผนผังตัวอย่าง ${pattern.name}`}>
        <rect x="20" y="20" width="760" height="360" rx="18" fill="#316b57"/>
        <rect x="40" y="40" width="720" height="320" rx="6" fill="#e8eeeb" stroke="#527b69" strokeWidth="5"/>
        <path d={`M ${pattern.cue.join(' ')} L ${pattern.bounce.join(' ')} L ${pattern.target.join(' ')}`} fill="none" stroke="#315a9b" strokeWidth="4" strokeDasharray="12 8"/>
        <circle cx={pattern.bounce[0]} cy={pattern.bounce[1]} r="9" fill="#315a9b"/>
        <circle cx={pattern.cue[0]} cy={pattern.cue[1]} r="17" fill="white" stroke="#49675a" strokeWidth="2"/>
        <circle cx={pattern.target[0]} cy={pattern.target[1]} r="17" fill="#b65050"/>
        <circle cx={pattern.obstacle[0]} cy={pattern.obstacle[1]} r="17" fill="#836747"/>
      </svg>
      <p>ขาว: ลูกขาว · แดง: ลูกเป้า · น้ำตาล: ลูกกีดขวาง · เส้นประ: เส้นทางตัวอย่าง</p>
      <p className="muted">ภาพประกอบสำหรับหน้าตัวอย่าง ตำแหน่งจริงและค่าคลาดเคลื่อนของแบบฝึกยังต้องกำหนดก่อนเปิดใช้งาน</p>
    </section><section className="panel"><h2>การเตรียมฝึก</h2>
      <Field label="กล้องด้านบน"><input value="ยังไม่เปิดตั้งค่ากล้อง M4" disabled readOnly/></Field>
      <h3>เป้าหมายของแบบฝึก</h3><ol><li>จัดลูกขาว ลูกกีดขวาง และลูกเป้าตามรูปแบบ</li><li>ส่งลูกขาวไปกระทบชิ่งที่กำหนดก่อน</li><li>ให้ลูกขาวสัมผัสลูกเป้าโดยไม่ชนลูกกีดขวางก่อน</li></ol>
      <p>จำนวนครั้งและเกณฑ์ตัวเลขจะแสดงเมื่อเปิดใช้งาน ยังไม่มีผลผ่านหรือคะแนนสำหรับ M4</p>
      <div className="stack"><Button disabled>ตรวจความพร้อม — ยังไม่เปิดใช้งาน</Button><Button disabled>เริ่มฝึก M4 — ยังไม่เปิดใช้งาน</Button><Button secondary onClick={()=>setPage('dashboard')}>กลับไปเลือกแบบฝึก</Button></div>
    </section></div>
  </>;
}
