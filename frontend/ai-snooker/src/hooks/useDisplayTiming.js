import { useEffect, useRef } from 'react';
import { api } from '../lib/api';

export function useDisplayTiming(attemptId) {
  const clock=useRef(null), samples=useRef([]),currentAttempt=useRef(null);
  useEffect(()=>{
    let disposed=false;
    async function sync() {
      let best=null;
      for(let i=0;i<3;i++) {
        const start=Date.now();
        try {const reply=await api('/clock');const end=Date.now(),rtt=end-start;
          if(!best || rtt<best.rtt)best={rtt,offset:reply.epoch_ms-(start+end)/2};
        }catch{return}
      }
      if(!disposed)clock.current=best;
    }
    sync(); const timer=setInterval(sync,60000);
    return ()=>{disposed=true;clearInterval(timer)};
  },[]);
  // Event handlers use the current attempt to avoid carrying measurements across rounds.
  function reset(id) {samples.current=[];currentAttempt.current=id}
  function record(frame) {
    if(!attemptId || !clock.current || !frame.capture_epoch_ms)return;
    if(currentAttempt.current!==attemptId)reset(attemptId);
    const value=Date.now()+clock.current.offset-frame.capture_epoch_ms;
    if(value>=0 && Number.isFinite(value) && samples.current.length<6000)samples.current.push(value);
  }
  function summary() {
    if(currentAttempt.current!==attemptId || !clock.current || !samples.current.length)return undefined;
    const values=[...samples.current].sort((a,b)=>a-b),n=values.length;
    return {n,median_ms:n%2 ? values[(n-1)/2] : (values[n/2-1]+values[n/2])/2,
      p95_ms:values[Math.ceil(n*.95)-1],max_ms:values[n-1],clock_uncertainty_ms:clock.current.rtt/2};
  }
  return {record,summary,reset};
}
