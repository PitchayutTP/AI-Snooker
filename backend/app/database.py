import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Integer, Float, ForeignKey, JSON, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
URL = os.getenv('DATABASE_URL', 'sqlite:///' + (DATA/'snooker.db').as_posix())
engine = create_engine(URL, connect_args={'check_same_thread': False} if URL.startswith('sqlite') else {})
if URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def enable_fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
DB = sessionmaker(engine, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase): pass


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    dominant_hand: Mapped[str] = mapped_column(String(10), default='RIGHT')


class Module(Base):
    __tablename__ = 'modules'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))


class Exercise(Base):
    __tablename__ = 'exercises'
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey('modules.id'))
    name: Mapped[str] = mapped_column(String(150))
    instructions: Mapped[str] = mapped_column(String(2000))
    setup_definition: Mapped[dict] = mapped_column(JSON)


class Criteria(Base):
    __tablename__ = 'criteria_versions'
    __table_args__ = (UniqueConstraint('exercise_id','version_no'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey('exercises.id'))
    version_no: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class TrainingSession(Base):
    __tablename__ = 'training_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    criteria_id: Mapped[int] = mapped_column(ForeignKey('criteria_versions.id'))
    started_at: Mapped[str] = mapped_column(String(40), default=now)
    ended_at: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default='IN_PROGRESS')
    configuration_snapshot: Mapped[dict] = mapped_column(JSON)


class Attempt(Base):
    __tablename__ = 'attempts'
    __table_args__ = (UniqueConstraint('session_id','attempt_number'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('training_sessions.id'))
    attempt_number: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[str] = mapped_column(String(40), default=now)
    ended_at: Mapped[str | None] = mapped_column(String(40))
    result_status: Mapped[str] = mapped_column(String(20), default='IN_PROGRESS')
    result_reason: Mapped[str] = mapped_column(String(2000), default='')
    # Explicit addition to the report: stores timestamped samples and events.
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class MetricDefinition(Base):
    __tablename__ = 'metric_definitions'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    unit: Mapped[str] = mapped_column(String(30))
    definition: Mapped[str] = mapped_column(String(500))


class Measurement(Base):
    __tablename__ = 'measurements'
    __table_args__ = (UniqueConstraint('attempt_id','metric_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey('attempts.id'))
    metric_id: Mapped[int] = mapped_column(ForeignKey('metric_definitions.id'))
    value: Mapped[float | None] = mapped_column(Float)
    validity_status: Mapped[str] = mapped_column(String(20))
    invalid_reason: Mapped[str | None] = mapped_column(String(500))


METRICS = {**{f'{k}_{s}': ('degree' if k in ['elbow','torso'] else 'pixel')
              for k in ['elbow','torso','stance'] for s in ['mean','max','sd']},
           **{f'{k}_{s}':'pixel' for k in ['head','bridge'] for s in ['mean','max']},
           'cue_deviation_mean':'pixel', 'cue_deviation_max':'pixel',
           'follow_through':'pixel', 'center_aim_error':'pixel',
           'contact_fraction':'ratio', 'fraction_error':'ratio', 'escape_success':'boolean'}


def init_db():
    Base.metadata.create_all(engine)
    with DB.begin() as db:
        if not db.get(Profile,1):
            db.add(Profile(id=1,display_name='ผู้ฝึกส่วนตัว'))
        if not db.get(Module,1):
            names=['การจัดระเบียบร่างกาย','การส่งคิวพื้นฐาน','เหลี่ยมลูกพื้นฐาน','แก้สนุกหนึ่งชิ่ง']
            for i,name in enumerate(names,1): db.add(Module(id=i,name=name))
            db.flush()
            exercises=[(1,1,'ท่าตั้งต้น',{'requires':['side']}),
                       (2,2,'การส่งคิว',{'requires':['side'],'cue_markers':True})]
            for i,f in enumerate([1.,.75,.5,.25],3):
                exercises.append((i,3,f'เหลี่ยม {f:g}',{'requires':['top'],'fraction':f}))
            for i in range(7,10):
                exercises.append((i,4,f'แก้สนุกรูปแบบ {i-6}',{'requires':['top'],'pattern':i-6}))
            for i,m,name,setup in exercises:
                db.add(Exercise(id=i,module_id=m,name=name,setup_definition=setup,
                    instructions='ตั้งท่าให้นิ่งในช่วงเก็บฐาน แล้วเริ่มเคลื่อนไหว กดจบครั้งเมื่อเสร็จ; เกณฑ์และการจัดวางต้องยืนยันก่อนทดลองหลัก'))
            db.flush()
            for i,_,_,_ in exercises:
                db.add(Criteria(exercise_id=i,version_no=1,definition={'approved':False,'rules':{},'source':'รอผลนำร่อง'}))
        for code,unit in METRICS.items():
            from sqlalchemy import select
            if not db.scalar(select(MetricDefinition).where(MetricDefinition.code==code)):
                db.add(MetricDefinition(code=code,unit=unit,definition=code))
