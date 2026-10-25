import threading
import time
import statistics
from .metrics import distance, line_distance
from .vision import DemoSource, LiveSource
from .cameras import PreviewSource
from .smoothing import MovingAverage
from .recordings import FrameRecorder


class Runtime:
    def __init__(self):
        self.lock=threading.RLock(); self.stop_event=threading.Event()
        self.thread=None; self.latest=None; self.samples=[]; self.collecting=False
        self.owner_profile_id=None
        self.config={}; self.error=None; self.session_id=None; self.attempt_id=None
        self.smoother=None
        self.recorder=None

    def start(self, config):
        self.stop()
        source=PreviewSource(config) if config.get('preview_only') else DemoSource(config) if config['mode']=='DEMO' else LiveSource(config)
        self.stop_event.clear(); self.config=config; self.error=None; self.latest=None
        smoother=MovingAverage(config.get('smoothing_window',1),config.get('max_frame_gap_s',.25))
        self.smoother=smoother
        def worker():
            try:
                last=time.monotonic()
                while not self.stop_event.is_set():
                    sample=source.read()
                    stamp=time.monotonic()
                    sample['fps']=1/max(.001,stamp-last); last=stamp
                    sample['received_at']=time.time()
                    with self.lock:
                        if not config.get('preview_only'): smoother.apply(sample)
                        raw=sample.pop('_raw_frames',{})
                        if self.collecting and self.recorder and len(self.samples)<6000:
                            recording_start=time.monotonic()
                            sample['recorded_images']=self.recorder.write(raw,len(self.samples))
                            sample['recording_ms']=(time.monotonic()-recording_start)*1000
                        self.latest=sample
                        if self.collecting:
                            if len(self.samples)>=6000:
                                self.error='จำนวนเฟรมเกินขีดจำกัด กรุณาจบครั้งหรือยกเลิก'
                                self.collecting=False
                            else:
                                record={k:v for k,v in sample.items() if k not in ('image','images')}
                                if not config.get('smoothing_for_evaluation',False):
                                    record.update(sample.get('raw_measurements',{}))
                                self.samples.append(record)
                    if sample.get('error'):
                        self.error=sample.get('error'); break
                    self.stop_event.wait(.1 if config.get('preview_only') else .05 if config['mode']=='DEMO' else .001)
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
                baseline=[s.get('display_measurements',s) for s in self.samples if s['t']-self.samples[0]['t']<=self.config.get('baseline_seconds',1)]
                elapsed=frame['t']-self.samples[0]['t']
                minimum=self.config.get('min_valid_frames',5)
                live['baseline_ready']=elapsed>self.config.get('baseline_seconds',1) and len(baseline)>=minimum
                if live['baseline_ready']:
                    for key in ['head','bridge']:
                        points=[s[key] for s in baseline if s.get(key) is not None]
                        if len(points)>=minimum and frame.get(key) is not None:
                            origin=[statistics.mean(p[i] for p in points) for i in (0,1)]
                            live[key+'_displacement']=distance(frame[key],origin)
                    cues=[s['cue'] for s in baseline if s.get('cue')]
                    if len(cues)>=minimum and frame.get('cue'):
                        a,b=[tuple(statistics.mean(c[k][i] for c in cues) for i in (0,1)) for k in (0,1)]
                        live['cue_deviation']=line_distance(frame['cue'][0],a,b)
            return {'live_metrics':live,'frame':frame,'ready':fresh and bool(self.latest.get('ready')),
                    'readiness_issues':issues,
                    'error':self.error,'mode':self.config.get('mode'),'configuration':dict(self.config),
                    'session_id':self.session_id,'attempt_id':self.attempt_id,
                    'samples':len(self.samples),'collecting':self.collecting}

    def begin(self, attempt_id):
        with self.lock:
            if self.smoother: self.smoother.reset()
            self.samples=[]; self.attempt_id=attempt_id; self.collecting=True
            self.recorder=None
            if self.config.get('record_frames') and self.config.get('mode')=='LIVE':
                try:self.recorder=FrameRecorder(self.owner_profile_id,self.session_id,attempt_id)
                except Exception as exc:
                    self.error=f'Cannot start reference recording: {exc}';self.collecting=False

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive(): raise ValueError('กล้องยังไม่หยุด กรุณาปิดและเปิด Backend ใหม่')
        self.thread=None; self.collecting=False
        self.recorder=None
        with self.lock:
            self.latest=None


runtime=Runtime()
