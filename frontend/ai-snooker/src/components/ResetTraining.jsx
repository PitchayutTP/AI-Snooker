import {useState} from 'react';
import {api} from '../lib/api';
import {Button} from './ui';

export function ResetTraining({disabled,onReset}) {
  const [summary,setSummary]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  async function review() {
    setBusy(true);setError('');setMessage('');
    try{setSummary(await api('/training/reset-summary'));}catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function reset() {
    setBusy(true);setError('');setMessage('');
    try {
      const result=await api('/training/reset',{confirmation:'RESET_TRAINING'});
      setSummary(null);
      await onReset();
      setMessage(result.cleanup_complete ? `รีเซ็ตแล้ว: ลบ ${result.sessions_removed} รอบ / ${result.attempts_removed} ครั้ง และภาพ ${result.images_removed} ภาพ` : 'ประวัติในฐานข้อมูลถูกล้างแล้ว แต่ภาพหลักฐานบางไฟล์ยังลบไม่ได้ ปิดโปรแกรมที่เปิดภาพแล้วกดรีเซ็ตอีกครั้ง');
    } catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <section className="panel narrow"><h2>รีเซ็ตข้อมูลการฝึก</h2>
    <p>ลบรอบฝึก ผลวัด ความก้าวหน้า และภาพหลักฐานของบัญชีนี้ทั้งหมด การลบย้อนกลับไม่ได้ บัญชี เกณฑ์ และค่าตั้งกล้องยังอยู่</p>
    {disabled && <p className="notice">จบหรือยุติรอบฝึกก่อนรีเซ็ต</p>}
    {!summary ? <Button secondary disabled={disabled || busy} onClick={review}>ล้างข้อมูลการฝึกทั้งหมด</Button> : <div className="notice"><p>จะลบ {summary.sessions} รอบ / {summary.attempts} ครั้ง / ภาพหลักฐาน {summary.images} ภาพ ของบัญชีนี้ ยืนยันการลบหรือไม่?</p>
      <div className="actions"><Button disabled={disabled || busy} onClick={reset}>ยืนยันลบข้อมูลการฝึกทั้งหมด</Button><Button secondary disabled={busy} onClick={()=>setSummary(null)}>ยกเลิก</Button></div>
    </div>}
    {busy && <p role="status">กำลังดำเนินการ…</p>}{error && <p className="error" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}
  </section>;
}
