import asyncio
import json
import math
import threading
import hashlib
from pathlib import Path
from functools import wraps
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4, UUID
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func
from .database import (DB, init_db, now, Module, Exercise, Criteria, TrainingSession,
                       Attempt, Measurement, MetricDefinition, METRICS)
from .auth import router as auth_router, identity, COOKIE, ORIGINS
from .runtime import runtime
from .metrics import summarize, evaluate, stats
from .vision import ball_metrics, cue_metrics


@asynccontextmanager
async def lifespan(app):
    init_db()
    # A previous process cannot keep capturing: preserve evidence, mark interrupted work.
    with DB.begin() as db:
        for a in db.scalars(select(Attempt).where(Attempt.result_status=='IN_PROGRESS')):
            a.result_status='ABORTED'; a.result_reason='โปรแกรมปิดก่อนบันทึกเสร็จ'; a.ended_at=now()
        for s in db.scalars(select(TrainingSession).where(TrainingSession.status=='IN_PROGRESS')):
            s.status='ABORTED'; s.ended_at=now()
    yield
    runtime.stop()


app=FastAPI(title='Snooker Practice',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
                   allow_methods=['GET','POST'],allow_headers=['Content-Type'],allow_credentials=True)

app.include_router(auth_router)


@app.middleware('http')
async def authentication(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        origin = request.headers.get('origin')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if (origin and origin not in ORIGINS) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'ไม่อนุญาตคำขอจากเว็บไซต์อื่น'}, status_code=403)
        request.state.user = identity(request.cookies.get(COOKIE))
        public = {'/api/health', '/api/auth/login', '/api/auth/register', '/api/auth/logout'}
        if request.method != 'OPTIONS' and request.url.path not in public and not request.state.user:
            return JSONResponse({'detail': 'กรุณาเข้าสู่ระบบ'}, status_code=401)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


def current_user(request: Request):
    return request.state.user


def owned_session(db, sid, user):
    session = require(db, TrainingSession, sid)
    if session.profile_id != user['profile_id']:
        raise HTTPException(404, 'ไม่พบข้อมูล')
    return session


def private_snapshot(user):
    with runtime.lock:
        if runtime.owner_profile_id != user['profile_id']:
            return {'ready': False, 'frame': {}, 'session_id': None, 'attempt_id': None,
                    'samples': 0, 'collecting': False, 'busy': bool(runtime.session_id)}
        return runtime.snapshot()


operation_lock=threading.RLock()
def serialized(fn):
    @wraps(fn)
    def call(*args,**kwargs):
        with operation_lock:
            return fn(*args,**kwargs)
    return call


class CaptureConfig(BaseModel):
    mode: Literal['DEMO','LIVE']='DEMO'
    hand: Literal['LEFT','RIGHT']='RIGHT'
    side_source: str='0'
    top_source: str='1'
    pose_model: str='models/pose_landmarker.task'
    ball_model: str='models/snooker.pt'
    visibility: float=Field(default=.7,ge=0,le=1,allow_inf_nan=False)
    baseline_seconds: float=Field(default=1.,ge=.5,le=10,allow_inf_nan=False)
    sync_tolerance_ms: float=Field(default=100,gt=0,le=1000,allow_inf_nan=False)
    ball_confidence: float=Field(default=.5,gt=0,le=1,allow_inf_nan=False)
    ball_roles: dict[str,Literal['cue_ball','target_ball','obstacle_ball']]=Field(default_factory=dict)
    homography: list[list[float]] | None=None
    table_size: list[float]=Field(default_factory=list)
    ball_radius: float=Field(default=0,ge=0,allow_inf_nan=False)
    contact_tolerance: float=Field(default=0,ge=0,allow_inf_nan=False)
    rail_tolerance: float=Field(default=0,ge=0,allow_inf_nan=False)
    max_frame_gap_s: float=Field(default=.25,gt=0,le=5,allow_inf_nan=False)
    escape_rail: Literal['left','right','top','bottom'] | None=None
    expected_obstacles: int=Field(default=0,ge=0,le=10)
    delivery_ball_timing: bool=False
    motion_threshold: float=Field(default=0,ge=0,allow_inf_nan=False)
    side_ball_center: list[float] | None=None
    cue_markers: list[dict]=Field(default_factory=list)
    setup_notes: str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def geometry(self):
        if self.homography is not None:
            import numpy as np
            h=np.asarray(self.homography,dtype=float)
            if h.shape!=(3,3) or not np.isfinite(h).all() or abs(np.linalg.det(h))<1e-12:
                raise ValueError('homography ต้องเป็นเมทริกซ์ 3x3 ที่ผกผันได้')
        if self.table_size and (len(self.table_size)!=2 or any(not math.isfinite(x) or x<=0 for x in self.table_size)):
            raise ValueError('table_size ต้องเป็นความกว้างและความสูงมากกว่าศูนย์')
        if self.cue_markers:
            if len(self.cue_markers)!=2: raise ValueError('ต้องมี marker สองสี')
            for marker in self.cue_markers:
                for k in ['lower','upper']:
                    v=marker.get(k,[])
                    if len(v)!=3 or any(not isinstance(x,int) or x<0 or x>255 for x in v):
                        raise ValueError('HSV bounds ไม่ถูกต้อง')
                if any(a>b for a,b in zip(marker['lower'],marker['upper'])): raise ValueError('HSV lower > upper')
        if self.side_ball_center is not None and (len(self.side_ball_center)!=2 or any(not math.isfinite(x) for x in self.side_ball_center)):
            raise ValueError('side_ball_center ต้องเป็นพิกัดพิกเซลสองค่า')
        return self


class ReadyRequest(BaseModel):
    exercise_id: int
    config: CaptureConfig


class StartRequest(BaseModel):
    request_id: UUID
    criteria_id: int


class AttemptRequest(BaseModel): request_id: UUID
class FinishRequest(BaseModel): aborted: bool=False


class Rule(BaseModel):
    min: float | None=Field(default=None,allow_inf_nan=False)
    max: float | None=Field(default=None,allow_inf_nan=False)
    @model_validator(mode='after')
    def bounds(self):
        if self.min is None and self.max is None: raise ValueError('ต้องระบุ min หรือ max')
        if self.min is not None and self.max is not None and self.min>self.max: raise ValueError('min > max')
        return self


class CriteriaRequest(BaseModel):
    source: str=Field(min_length=5,max_length=1000)
    approved: bool=False
    rules: dict[str,Rule]


def require(db, model, key):
    item=db.get(model,key)
    if not item: raise HTTPException(404,'ไม่พบข้อมูล')
    return item


@app.get('/api/health')
def health(): return {'status':'ok','version':'0.1.0','scope':'local accounts, one training device'}


@app.get('/api/catalog')
def catalog():
    with DB() as db:
        return [{'id':e.id,'module_id':e.module_id,'module':db.get(Module,e.module_id).name,
                 'name':e.name,'instructions':e.instructions,'setup':e.setup_definition,
                 'criteria':[{'id':c.id,'version':c.version_no,**c.definition} for c in
                    db.scalars(select(Criteria).where(Criteria.exercise_id==e.id).order_by(Criteria.version_no.desc()))]}
                for e in db.scalars(select(Exercise).order_by(Exercise.id))]


@app.get('/api/metrics')
def metric_catalog(): return METRICS


@app.post('/api/exercises/{eid}/criteria')
@serialized
def new_criteria(eid:int, body:CriteriaRequest):
    if any(k not in METRICS for k in body.rules): raise HTTPException(422,'รหัสตัวชี้วัดไม่ถูกต้อง')
    if body.approved and not body.rules: raise HTTPException(422,'ต้องกำหนดกฎก่อนยืนยัน')
    with runtime.lock, DB.begin() as db:
        require(db,Exercise,eid)
        version=(db.scalar(select(func.max(Criteria.version_no)).where(Criteria.exercise_id==eid)) or 0)+1
        c=Criteria(exercise_id=eid,version_no=version,definition=body.model_dump(exclude_none=True))
        db.add(c); db.flush()
        return {'id':c.id,'version':version}


@app.post('/api/readiness')
@serialized
def readiness(body:ReadyRequest, user=Depends(current_user)):
    # Do not hold the worker lock while joining the previous worker.
    if runtime.session_id: raise HTTPException(409,'ต้องจบรอบฝึกก่อนเปลี่ยนกล้อง')
    with DB() as db:
        exercise=require(db,Exercise,body.exercise_id)
        config=body.config.model_dump()
        config.update(required=exercise.setup_definition['requires'],exercise_id=exercise.id)
        if exercise.module_id==2 and config['delivery_ball_timing']:
            if not config['cue_markers'] or config['motion_threshold']<=0:
                raise HTTPException(422,'การประมาณ Follow-through ต้องมี marker และเกณฑ์เริ่มเคลื่อนลูกจากการนำร่อง')
            config['required']=['side','top']
        config['software_version']='prototype-v0.1'
        if config['mode']=='LIVE':
            hashes={}
            for camera,key in [('side','pose_model'),('top','ball_model')]:
                if camera in config['required'] and Path(config[key]).is_file():
                    with open(config[key],'rb') as model_file:
                        hashes[key]=hashlib.file_digest(model_file,'sha256').hexdigest()
            config['model_sha256']=hashes
        if config['mode']=='LIVE' and 'top' in config['required']:
            if not config['homography'] or not config['table_size'] or not config['ball_radius']:
                raise HTTPException(422,'กรุณาระบุ homography ขนาดโต๊ะ และรัศมีลูกในหน่วยเดียวกัน')
            if exercise.module_id==4 and (not config['escape_rail'] or not config['setup_notes'] or not config['expected_obstacles']):
                raise HTTPException(422,'ต้องระบุชิ่งและบันทึกแผนผังจัดลูกของรูปแบบนี้')
        try:
            runtime.stop()
            with runtime.lock:
                runtime.owner_profile_id=user['profile_id']
            runtime.start(config)
        except Exception as exc: raise HTTPException(400,str(exc)) from exc
    return {'status':'STARTING','note':'รอสถานะพร้อมจากภาพจริงก่อนเริ่มรอบ'}


@app.post('/api/sessions')
@serialized
def start_session(body:StartRequest, user=Depends(current_user)):
    sid=str(body.request_id)
    with runtime.lock,DB.begin() as db:
        old=db.get(TrainingSession,sid)
        if old:
            owned_session(db, sid, user)
            if old.criteria_id!=body.criteria_id: raise HTTPException(409,'request_id ถูกใช้กับคำขออื่นแล้ว')
            return {'id':old.id,'status':old.status}
        if runtime.session_id: raise HTTPException(409,'มีรอบฝึกที่ยังไม่จบ')
        if runtime.owner_profile_id != user['profile_id']: raise HTTPException(409,'กรุณาตรวจความพร้อมด้วยบัญชีนี้ก่อน')
        if not runtime.snapshot()['ready']: raise HTTPException(409,'กล้องหรือข้อมูลยังไม่พร้อม')
        c=require(db,Criteria,body.criteria_id)
        if c.exercise_id!=runtime.config['exercise_id']: raise HTTPException(409,'เกณฑ์ไม่ตรงกับแบบฝึกที่ตรวจความพร้อม')
        s=TrainingSession(id=sid,profile_id=user['profile_id'],criteria_id=c.id,configuration_snapshot=dict(runtime.config))
        db.add(s)
    runtime.session_id=sid
    return {'id':sid,'status':'IN_PROGRESS'}


@app.post('/api/sessions/{sid}/attempts')
@serialized
def begin_attempt(sid:str,body:AttemptRequest, user=Depends(current_user)):
    aid=str(body.request_id)
    with runtime.lock, DB.begin() as db:
        owned_session(db, sid, user)
        old=db.get(Attempt,aid)
        if old:
            owned_session(db, old.session_id, user)
            if old.session_id!=sid: raise HTTPException(409,'request_id ถูกใช้ในรอบอื่น')
            return {'id':old.id,'status':old.result_status}
        s=require(db,TrainingSession,sid)
        if s.status!='IN_PROGRESS' or runtime.session_id!=sid: raise HTTPException(409,'รอบนี้ไม่ได้กำลังทำงาน')
        if runtime.attempt_id: raise HTTPException(409,'ต้องจบครั้งก่อนหน้า')
        if not runtime.snapshot()['ready']: raise HTTPException(409,'ข้อมูลกล้องไม่พร้อม')
        number=(db.scalar(select(func.max(Attempt.attempt_number)).where(Attempt.session_id==sid)) or 0)+1
        db.add(Attempt(id=aid,session_id=sid,attempt_number=number))
    runtime.begin(aid)
    return {'id':aid,'status':'IN_PROGRESS'}


@app.post('/api/attempts/{aid}/finish')
@serialized
def finish_attempt(aid:str,body:FinishRequest, user=Depends(current_user)):
    with runtime.lock:
        with DB.begin() as db:
            a=require(db,Attempt,aid)
            owned_session(db, a.session_id, user)
            if a.result_status!='IN_PROGRESS': return {'id':aid,'status':a.result_status,'reason':a.result_reason}
            if runtime.attempt_id!=aid: raise HTTPException(409,'ไม่ใช่ครั้งที่กำลังบันทึก')
            # Freeze samples; a failed database commit can retry the exact same evidence.
            runtime.collecting=False
            samples=list(runtime.samples)
            s=require(db,TrainingSession,a.session_id); c=require(db,Criteria,s.criteria_id)
            exercise=require(db,Exercise,c.exercise_id)
            config=s.configuration_snapshot
            measured=summarize(samples,config['baseline_seconds'])
            measured.update(cue_metrics(samples,config['baseline_seconds'],config))
            balls,events=ball_metrics(samples,config,exercise.setup_definition)
            measured.update(balls)
            if body.aborted: status,reason='ABORTED','ผู้ฝึกยุติก่อนจบ'
            elif runtime.error: status,reason='INVALID',runtime.error
            elif config['mode']=='DEMO': status,reason='INVALID','ข้อมูลสาธิต ไม่ใช่ผลฝึกจริง'
            else: status,reason=evaluate(measured,c.definition)
            a.result_status=status; a.result_reason=reason; a.ended_at=now()
            a.evidence={'samples':samples,'events':events,'source':config['mode'],
                        'algorithm':'prototype-v0.1','segmentation':'manual-start-stop'}
            for metric in db.scalars(select(MetricDefinition)):
                value=measured.get(metric.code)
                if value is not None and not math.isfinite(value): value=None
                db.add(Measurement(attempt_id=aid,metric_id=metric.id,value=value,
                    validity_status='VALID' if value is not None else 'INVALID',
                    invalid_reason=None if value is not None else 'ข้อมูลไม่พอหรือยังไม่มีวิธีวัดที่รองรับ'))
        runtime.attempt_id=None; runtime.samples=[]
    return {'id':aid,'status':status,'reason':reason,'metrics':measured}


@app.post('/api/sessions/{sid}/finish')
@serialized
def finish_session(sid:str,body:FinishRequest, user=Depends(current_user)):
    with DB() as db:
        owned_session(db, sid, user)
    with runtime.lock:
        if runtime.session_id==sid and runtime.attempt_id:
            finish_attempt(runtime.attempt_id,FinishRequest(aborted=True),user)
        with DB.begin() as db:
            s=require(db,TrainingSession,sid)
            if s.status=='IN_PROGRESS':
                s.status='ABORTED' if body.aborted else 'COMPLETED'; s.ended_at=now()
        if runtime.session_id==sid: runtime.session_id=None
    return session_detail(sid,user)


def detail(db,s):
    c=db.get(Criteria,s.criteria_id); e=db.get(Exercise,c.exercise_id)
    attempts=[]; counts={key:0 for key in ['PASS','FAIL','INVALID','ABORTED','IN_PROGRESS']}
    for a in db.scalars(select(Attempt).where(Attempt.session_id==s.id).order_by(Attempt.attempt_number)):
        counts[a.result_status]+=1
        measurements={}
        for m in db.scalars(select(Measurement).where(Measurement.attempt_id==a.id)):
            d=db.get(MetricDefinition,m.metric_id)
            measurements[d.code]={'value':m.value,'unit':d.unit,'status':m.validity_status,'reason':m.invalid_reason}
        attempts.append({'id':a.id,'number':a.attempt_number,'status':a.result_status,
                         'reason':a.result_reason,'metrics':measurements})
    total=counts['PASS']+counts['FAIL']
    summary={code:stats([a['metrics'].get(code,{}).get('value') for a in attempts
                         if a['status']!='ABORTED']) for code in METRICS}
    return {'id':s.id,'name':e.name,'exercise_id':e.id,'criteria_id':s.criteria_id,
            'criteria':c.definition,'config':s.configuration_snapshot,'started_at':s.started_at,
            'ended_at':s.ended_at,'status':s.status,'counts':counts,'pass_rate':counts['PASS']/total if total else None,
            'attempts':attempts,'summary':summary,'mode':s.configuration_snapshot['mode']}


@app.get('/api/sessions')
def sessions(user=Depends(current_user)):
    with DB() as db:
        return [detail(db,s) for s in db.scalars(select(TrainingSession).where(TrainingSession.profile_id==user['profile_id']).order_by(TrainingSession.started_at.desc()).limit(100))]


@app.get('/api/sessions/{sid}')
def session_detail(sid:str, user=Depends(current_user)):
    with DB() as db: return detail(db,owned_session(db,sid,user))


@app.get('/api/sessions/{sid}/export')
def export(sid:str, user=Depends(current_user)):
    with DB() as db:
        result=detail(db,owned_session(db,sid,user))
        result['evidence']=[{'attempt_id':a.id,**a.evidence} for a in
                            db.scalars(select(Attempt).where(Attempt.session_id==sid))]
    return Response(json.dumps(result,ensure_ascii=False,allow_nan=False),media_type='application/json',
                    headers={'Content-Disposition':'attachment; filename="session.json"'})


@app.get('/api/compare')
def compare(left:str,right:str, user=Depends(current_user)):
    a=session_detail(left,user); b=session_detail(right,user)
    if a['status']=='IN_PROGRESS' or b['status']=='IN_PROGRESS': raise HTTPException(409,'จบรอบก่อนเปรียบเทียบ')
    if a['criteria_id']!=b['criteria_id'] or a['config']!=b['config']:
        raise HTTPException(409,'แบบฝึก รุ่นเกณฑ์ หรือการตั้งค่าต่างกัน จึงไม่เปรียบเทียบโดยตรง')
    return {'left':a['id'],'right':b['id'],'mode':a['mode'],
            'note':'ความต่างของค่าวัดไม่ยืนยันว่าทักษะดีขึ้น',
            'metrics':{k:{'left':a['summary'][k],'right':b['summary'][k],
                 'difference':b['summary'][k]['mean']-a['summary'][k]['mean']
                 if a['summary'][k]['mean'] is not None and b['summary'][k]['mean'] is not None else None}
                 for k in METRICS}}


@app.get('/api/status')
def status(user=Depends(current_user)): return private_snapshot(user)


@app.websocket('/ws')
async def websocket(ws:WebSocket):
    origin=ws.headers.get('origin')
    token=ws.cookies.get(COOKIE)
    if origin not in ORIGINS or not identity(token):
        await ws.close(code=1008); return
    await ws.accept()
    try:
        while True:
            user=identity(token)
            if not user:
                await ws.close(code=1008); return
            await ws.send_json(private_snapshot(user))
            await asyncio.sleep(.1)
    except WebSocketDisconnect: pass
