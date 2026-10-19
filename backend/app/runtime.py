import threading
import time
import statistics
from .metrics import distance, line_distance
from .vision import DemoSource, LiveSource


class Runtime:
    def __init__(self):
        self.lock=threading.RLock(); self.stop_event=threading.Event()
        self.thread=None; self.latest=None; self.samples=[]; self.collecting=False
        self.owner_profile_id=None
        self.config={}; self.error=None; self.session_id=None; self.attempt_id=None

    def start(self, config):
        self.stop()
        source=DemoSource(config) if config['mode']=='DEMO' else LiveSource(config)
        self.stop_event.clear(); self.config=config; self.error=None; self.latest=None
        def worker():
            try:
                last=time.monotonic()
                while not self.stop_event.is_set():
                    sample=source.read()
                    stamp=time.monotonic()
                    sample['fps']=1/max(.001,stamp-last); last=stamp
                    sample['received_at']=time.time()
                    with self.lock:
                        self.latest=sample
                        if self.collecting:
                            if len(self.samples)>=6000:
                                self.error='จำนวนเฟรมเกินขีดจำกัด กรุณาจบครั้งหรือยกเลิก'
                                self.collecting=False
                            else: self.samples.append({k:v for k,v in sample.items() if k!='image'})
                    if sample.get('error'):
                        self.error=sample.get('error'); break
                    self.stop_event.wait(.05)
            except Exception as exc:
                self.error=str(exc)
            finally:
                source.close()
        self.thread=threading.Thread(target=worker,daemon=True); self.thread.start()

    def snapshot(self):
        with self.lock:
            frame=dict(self.latest or {})
            fresh=bool(frame) and time.time()-frame.get('received_at',0)<2 and not self.error
            issues=list(frame.get('readiness_issues',[]))
            if not fresh:
                issues=[self.error or ('ภาพจากกล้องไม่อัปเดต กรุณาตรวจความพร้อมอีกครั้ง' if frame else 'กำลังรอภาพจากกล้อง')]
                frame={k:None for k in ['elbow','head','bridge','torso','stance','image']}
            live={}
            if fresh and self.samples:
                baseline=[s for s in self.samples if s['t']-self.samples[0]['t']<=self.config.get('baseline_seconds',1)]
                elapsed=frame['t']-self.samples[0]['t']
                live['baseline_ready']=elapsed>self.config.get('baseline_seconds',1) and len(baseline)>=5
                if live['baseline_ready']:
                    for key in ['head','bridge']:
                        points=[s[key] for s in baseline if s.get(key) is not None]
                        if len(points)>=5 and frame.get(key) is not None:
                            origin=[statistics.mean(p[i] for p in points) for i in (0,1)]
                            live[key+'_displacement']=distance(frame[key],origin)
                    cues=[s['cue'] for s in baseline if s.get('cue')]
                    if len(cues)>=5 and frame.get('cue'):
                        a,b=[tuple(statistics.mean(c[k][i] for c in cues) for i in (0,1)) for k in (0,1)]
                        live['cue_deviation']=line_distance(frame['cue'][0],a,b)
            return {'live_metrics':live,'frame':frame,'ready':fresh and bool(self.latest.get('ready')),
                    'readiness_issues':issues,
                    'error':self.error,'mode':self.config.get('mode'),'configuration':dict(self.config),
                    'session_id':self.session_id,'attempt_id':self.attempt_id,
                    'samples':len(self.samples),'collecting':self.collecting}

    def begin(self, attempt_id):
        with self.lock:
            self.samples=[]; self.attempt_id=attempt_id; self.collecting=True

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive(): raise ValueError('กล้องยังไม่หยุด กรุณาปิดและเปิด Backend ใหม่')
        self.thread=None; self.collecting=False
        with self.lock:
            self.latest=None


runtime=Runtime()
