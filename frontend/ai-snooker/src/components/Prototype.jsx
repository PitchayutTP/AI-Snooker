import { useEffect, useState } from 'react'
import { api, number } from '../lib/api'

export const labels = {
  elbow_mean:'มุมศอกเฉลี่ย', elbow_sd:'SD มุมศอก', torso_mean:'มุมลำตัวเฉลี่ย', torso_sd:'SD มุมลำตัว',
  stance_mean:'ระยะข้อเท้าเฉลี่ย', stance_sd:'SD ระยะข้อเท้า', head_mean:'ศีรษะเคลื่อนเฉลี่ย', head_max:'ศีรษะเคลื่อนสูงสุด',
  bridge_mean:'สะพานมือเคลื่อนเฉลี่ย', bridge_max:'สะพานมือเคลื่อนสูงสุด', cue_deviation_mean:'คิวเบี่ยงเบนเฉลี่ย',
  cue_deviation_max:'คิวเบี่ยงเบนสูงสุด', follow_through:'Follow-through (ประมาณ)', center_aim_error:'ความคลาดเคลื่อนแนวเล็ง (ประมาณ)',
  contact_fraction:'เหลี่ยมประมาณ', fraction_error:'ความคลาดเคลื่อนเหลี่ยม',
}

export function Guide({ exercise }) {
  const lesson=exercise?.lesson
  if (!lesson) return null
  const fraction=exercise.setup?.fraction ?? 1
  return <section className="panel guide"><h2>เป้าหมายและขั้นตอนฝึก</h2><p>{lesson.goal}</p><p className="notice">{lesson.camera}</p>
    <svg viewBox="0 0 440 170" className="lesson-diagram" role="img" aria-label={exercise.module_id===3 ? `ภาพแนวคิดการกระทบเหลี่ยม ${fraction}` : 'ภาพตำแหน่งกล้องด้านข้างสำหรับฝึกท่าทางและคิว'}>
      {exercise.module_id===3 ? <><rect x="10" y="10" width="420" height="150" rx="9" fill="#e8eeeb" stroke="#abb9b0"/><circle cx="310" cy="85" r="25" fill="#b65050"/><line x1="60" y1={85+50*(1-fraction)} x2="265" y2={85+50*(1-fraction)} stroke="#566a60" strokeDasharray="7 5"/><circle cx="110" cy={85+50*(1-fraction)} r="25" fill="#fff" stroke="#9eaaa3"/><text x="205" y="146" textAnchor="middle" fontSize="12">ภาพแนวคิด ไม่ใช่ตำแหน่งตั้งลูกที่สอบเทียบ</text></> : <><path d="M60 130H390" stroke="#9eaaa3" strokeWidth="5"/><circle cx="245" cy="42" r="15" fill="#e2e5ea" stroke="#798392"/><path d="M230 55L150 75L128 127 M182 68L216 97L292 112 M160 75L190 130" fill="none" stroke="#798392" strokeWidth="8" strokeLinecap="round"/><path d="M185 116L360 116" stroke="#a28c6c" strokeWidth="5"/><rect x="30" y="45" width="40" height="28" rx="3" fill="#dde2e9" stroke="#798392"/><path d="M70 50L88 40V78L70 68 M48 74V130" fill="none" stroke="#798392" strokeWidth="3"/><text x="240" y="160" textAnchor="middle" fontSize="12">กล้องด้านข้างต้องเห็นจุดร่างกายและแนวคิวครบ</text></>}
    </svg><ol>{lesson.steps.map(step=><li key={step}>{step}</li>)}</ol>
    <p className="muted">ถ้าข้อมูลไม่ครบให้จัดอุปกรณ์ใหม่ ผลที่ประเมินไม่ได้จะไม่ถูกแทนเป็น 0</p>
  </section>
}

export function Feedback({ items=[] }) {
  return <ul className="feedback">{items.map((item,i)=><li className={item.level} key={`${item.metric}-${i}`}>{item.message}</li>)}</ul>
}

export function CriteriaEditor({ exercise, units, disabled, onSaved }) {
  const [rows,setRows]=useState([]),[source,setSource]=useState(''),[approved,setApproved]=useState(false)
  const [error,setError]=useState(''),[saving,setSaving]=useState(false)
  const options=exercise?.lesson?.metrics || []
  function update(index,key,value) { setRows(rows.map((row,i)=>i===index ? {...row,[key]:value} : row)) }
  async function submit(event) {
    event.preventDefault(); setError(''); setSaving(true)
    try {
      const rules={}
      for (const row of rows) {
        if (!row.code || rules[row.code]) throw new Error('เลือกตัวชี้วัดไม่ซ้ำกัน')
        if (row.min==='' && row.max==='') throw new Error('ระบุค่าต่ำสุดหรือค่าสูงสุดอย่างน้อยหนึ่งค่า')
        const rule={}
        for (const key of ['min','max']) if(row[key]!=='') { const n=Number(row[key]); if(!Number.isFinite(n)) throw new Error('เกณฑ์ต้องเป็นตัวเลข'); rule[key]=n }
        if(rule.min!==undefined && rule.max!==undefined && rule.min>rule.max) throw new Error('ค่าต่ำสุดต้องไม่มากกว่าค่าสูงสุด')
        rules[row.code]=rule
      }
      if(approved && !rows.length) throw new Error('ต้องเพิ่มตัวชี้วัดก่อนยืนยันเกณฑ์')
      const result=await api(`/exercises/${exercise.id}/criteria`,{source,approved,rules})
      await onSaved(result.id)
      setRows([]);setApproved(false);setSource('')
    } catch(e) { setError(e.message) } finally {setSaving(false)}
  }
  return <section className="panel"><h2>สร้างเกณฑ์รุ่นใหม่</h2><p className="muted">กรอกค่าจากการนำร่องหรือแหล่งอ้างอิงของคุณ หน่วย pixel ใช้กับตำแหน่งกล้องเดิมเท่านั้น การยืนยันนี้เป็นการยืนยันของผู้จัดทำ ไม่ใช่มาตรฐานรับรอง</p>
    <form onSubmit={submit}><fieldset disabled={disabled || saving}><label className="field"><span>แหล่งที่มา / บันทึกการนำร่อง</span><textarea value={source} onChange={e=>setSource(e.target.value)} required minLength={5} maxLength={1000}/></label>
    {rows.map((row,i)=><div className="rule-row" key={i}><label>ตัวชี้วัด<select value={row.code} onChange={e=>update(i,'code',e.target.value)}><option value="">เลือกตัวชี้วัด</option>{options.map(code=><option value={code} key={code}>{labels[code] || code} ({units[code]})</option>)}</select></label><label>ต่ำสุด<input aria-label={`ต่ำสุดแถว ${i+1}`} type="number" step="any" value={row.min} onChange={e=>update(i,'min',e.target.value)}/></label><label>สูงสุด<input aria-label={`สูงสุดแถว ${i+1}`} type="number" step="any" value={row.max} onChange={e=>update(i,'max',e.target.value)}/></label><button type="button" className="button secondary" onClick={()=>setRows(rows.filter((_,n)=>n!==i))}>ลบ</button></div>)}
    <div className="actions"><button type="button" className="button secondary" disabled={rows.length>=options.length} onClick={()=>setRows([...rows,{code:'',min:'',max:''}])}>เพิ่มตัวชี้วัด</button></div><label className="check"><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>ยืนยันเกณฑ์รุ่นนี้สำหรับการทดลอง</label><button type="submit" className="button">{saving ? 'กำลังบันทึก…' : 'บันทึกเป็นรุ่นใหม่'}</button></fieldset>{error && <p className="error" role="alert">{error}</p>}</form>
  </section>
}

export function LiveValues({ status }) {
  const frame=status.frame || {},live=status.live_metrics || {},module=status.configuration?.exercise_id
  const readings=[['มุมศอก',frame.elbow,'°'],['มุมลำตัว',frame.torso,'°'],['ระยะข้อเท้า',frame.stance,'px'],['ศีรษะจากช่วงฐาน',live.head_displacement,'px'],['สะพานมือจากช่วงฐาน',live.bridge_displacement,'px'],['คิวจากแนวตั้งต้น',live.cue_deviation,'px']]
  return <><h3>ตัวชี้วัดขณะฝึก</h3>{module<=2 ? <dl>{readings.map(([label,value,unit])=><div className="live-reading" key={label}><dt>{label}</dt><dd>{number(value)} <small>{unit}</small></dd></div>)}</dl> : <p>ลูกที่ตรวจจับและติดตามได้: {(frame.balls || []).length}</p>}
    {status.attempt_id && !live.baseline_ready && <p className="notice">กำลังเก็บท่าตั้งต้น กรุณาหยุดนิ่งในช่วงฐาน</p>}
    <p className="muted">ค่าเคลื่อนที่ระหว่างฝึกเทียบช่วงฐานของครั้งนี้ ผลเฉลี่ยและการตัดสินแสดงเมื่อจบครั้ง</p></>
}

export function Progress({ data, catalog, onChoose, disabled }) {
  return <section className="panel"><h2>ความก้าวหน้าการฝึก</h2><p className="muted">จำนวนการฝึกเป็นประวัติการใช้งาน ยังไม่ยืนยันว่าทักษะดีขึ้น</p><div className="table-scroll"><table><thead><tr><th>แบบฝึก</th><th>รอบที่จบ</th><th>ครั้งทั้งหมด</th><th>LIVE ผ่าน</th><th>ฝึกต่อ</th></tr></thead><tbody>{catalog.map(ex=>{const item=data.find(x=>x.exercise_id===ex.id);return <tr key={ex.id}><td>{ex.name}</td><td>{item?.sessions || 0}</td><td>{item?.attempts || 0}</td><td>{item?.live_pass || 0}</td><td><button className="button secondary" disabled={disabled} onClick={()=>onChoose(ex)}>เลือก</button></td></tr>})}</tbody></table></div></section>
}

export function SettingsImport({ onImport, disabled }) {
  const [error,setError]=useState('')
  return <><label className="field"><span>โหลดไฟล์ตั้งค่า JSON (เฉพาะค่าการวัดเพิ่มเติม)</span><input disabled={disabled} type="file" accept=".json,application/json" onChange={async e=>{setError('');const file=e.target.files?.[0];if(!file)return;try{if(file.size>64000)throw new Error('ไฟล์ต้องไม่เกิน 64 KB');const data=JSON.parse(await file.text());if(!data || Array.isArray(data) || typeof data!=='object')throw new Error('ต้องเป็น JSON object');onImport(JSON.stringify(data,null,2))}catch(err){setError(err.message)}e.target.value=''}}/></label>{error && <p className="error">{error}</p>}</>
}

export function Calibration({ disabled, onApply }) {
  const [image,setImage]=useState(''),[dimensions,setDimensions]=useState([1,1]),[points,setPoints]=useState([]),[size,setSize]=useState({width:'',height:'',radius:''})
  const [result,setResult]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const steps=['มุมซ้ายบน','มุมขวาบน','มุมขวาล่าง','มุมซ้ายล่าง','จุดกึ่งกลางโต๊ะที่ทำเครื่องหมายไว้ (จุดตรวจสอบอิสระ)']
  async function calculate() {
    setError('');setBusy(true);setResult(null)
    try {
      const width=Number(size.width),height=Number(size.height),radius=Number(size.radius)
      if(width<=0 || height<=0 || radius<=0 || radius*2>=Math.min(width,height))throw new Error('ระบุขนาดพื้นที่เล่นและรัศมีลูกที่เหมาะสมด้วยหน่วยเดียวกัน')
      if(points.length!==5)throw new Error('เลือกจุดบนภาพให้ครบ 5 จุด')
      const output=await api('/calibration',{image_points:points.slice(0,4),table_width:width,table_height:height,check_image_point:points[4],check_table_point:[width/2,height/2]})
      setResult({...output,table_size:[width,height],ball_radius:radius})
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  function reset(){setPoints([]);setResult(null);setError('')}
  return <details className="panel"><summary>ช่วยสอบเทียบกล้องด้านบนจากภาพถ่าย</summary><p>ใช้ภาพเต็มจากกล้องด้านบนที่ความละเอียดเดียวกับตอนฝึก ทำเครื่องหมายจุดกึ่งกลางพื้นที่เล่นจริงก่อนถ่ายภาพ จุดนี้ใช้ตรวจสอบและไม่ได้ใช้คำนวณ homography</p><p className="muted">ภาพอยู่ในเบราว์เซอร์ ไม่อัปโหลดไป Backend ระบบส่งเฉพาะพิกัดที่คลิก ต้องยึดกล้องและความละเอียดให้คงเดิม</p>
    <fieldset disabled={disabled || busy}><div className="filters">{[['width','ความกว้างพื้นที่เล่น'],['height','ความสูงพื้นที่เล่น'],['radius','รัศมีลูก']].map(([key,label])=><label key={key}>{label}<input type="number" min="0" step="any" value={size[key]} onChange={e=>{setSize({...size,[key]:e.target.value});setResult(null)}}/></label>)}</div>
    <label className="field"><span>ภาพเต็มจากกล้องด้านบน (JPG / PNG ไม่เกิน 10 MB)</span><input type="file" accept="image/jpeg,image/png" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;reset();setImage('');if(file.size>10000000){setError('ภาพใหญ่เกิน 10 MB');return}const reader=new FileReader();reader.onload=()=>setImage(String(reader.result));reader.readAsDataURL(file)}}/></label>
    {image && <><p>{points.length<5 ? `คลิกจุดที่ ${points.length+1}: ${steps[points.length]}` : 'เลือกครบแล้ว กดคำนวณเพื่อตรวจสอบ'}</p><div className="calibration-image" onClick={e=>{if(disabled || points.length>=5)return;const img=e.currentTarget.querySelector('img'),rect=img.getBoundingClientRect();const x=(e.clientX-rect.left)*img.naturalWidth/rect.width,y=(e.clientY-rect.top)*img.naturalHeight/rect.height;if(x<0 || y<0 || x>img.naturalWidth || y>img.naturalHeight)return;setPoints([...points,[x,y]])}}><img src={image} alt="ภาพกล้องสำหรับเลือกมุมโต๊ะ" onLoad={e=>{setDimensions([e.target.naturalWidth,e.target.naturalHeight]);setPoints([])}}/>{points.map((p,i)=><span key={i} style={{left:`${p[0]/dimensions[0]*100}%`,top:`${p[1]/dimensions[1]*100}%`}}>{i+1}</span>)}</div></>}
    <div className="actions"><button type="button" className="button secondary" onClick={reset}>เลือกจุดใหม่</button><button type="button" className="button" disabled={points.length!==5} onClick={calculate}>คำนวณ</button></div></fieldset>
    {error && <p className="error" role="alert">{error}</p>}{result && <><p className="notice">ความคลาดเคลื่อนที่จุดตรวจสอบ: {number(result.check_max_error)} หน่วยเดียวกับขนาดโต๊ะ ตรวจว่าเหมาะกับความแม่นยำที่ต้องใช้ก่อนนำค่าไปใช้ จุดตรวจสอบเดียวไม่ยืนยันทั้งพื้นที่โต๊ะ</p><button type="button" className="button" disabled={disabled || busy} onClick={()=>onApply({homography:result.homography,table_size:result.table_size,ball_radius:result.ball_radius})}>นำค่าไปใช้ในการตั้งค่าเพิ่มเติม</button></>}
  </details>
}


export function Trajectory({ status }) {
  const [trace,setTrace]=useState({attempt:null,tracks:{}})
  const frame=status.frame, attempt=status.attempt_id
  useEffect(()=>{
    if(!attempt || !frame?.balls?.length)return
    setTrace(old=>{
      const tracks=old.attempt===attempt ? {...old.tracks} : {}
      for(const ball of frame.balls){const key=ball.class+':'+ball.id; const points=tracks[key] || []; if(points.at(-1)?.t!==frame.t)tracks[key]=[...points,{t:frame.t,xy:ball.xy}].slice(-300)}
      return {attempt,tracks}
    })
  },[frame,attempt])
  const [width,height]=status.configuration?.table_size || []
  if(!width || !height)return null
  const tracks=trace.attempt===attempt ? trace.tracks : {}
  return <section className="panel"><h2>เส้นทางลูกระหว่างบันทึก</h2><p className="muted">แสดงจุดที่ตรวจจับได้สูงสุด 300 จุดต่อเส้นจาก WebSocket ไม่ใช่ภาพทุกเฟรม หลักฐานใน JSON ใช้ข้อมูลที่ Backend บันทึก</p><svg viewBox={`0 0 ${width} ${height}`} className="trajectory" role="img" aria-label="เส้นทางลูกในพิกัดโต๊ะ"><rect width={width} height={height} fill="#e8eeeb"/>{Object.entries(tracks).map(([key,points])=><polyline key={key} points={points.map(p=>p.xy.join(',')).join(' ')} fill="none" stroke={key.startsWith('cue_ball') ? '#344b6b' : '#b65050'} strokeWidth={width/250}/>)}</svg><p className="muted">สีน้ำเงิน: ลูกขาว · สีแดง: ลูกเป้า</p></section>
}
