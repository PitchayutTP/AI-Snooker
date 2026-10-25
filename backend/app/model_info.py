"""Inspect only explicitly selected local model files; no downloads."""
import hashlib
from pathlib import Path

MODEL_ROOT=Path(__file__).resolve().parents[1]/'models'


def model_path(value):
    path=Path(value)
    if not path.is_absolute(): path=MODEL_ROOT.parent/path
    path=path.resolve()
    if not path.is_relative_to(MODEL_ROOT.resolve()) or path.suffix.lower()!='.pt':
        raise ValueError('เลือกไฟล์ .pt ภายใน backend/models เท่านั้น')
    return path


def inspect_model(value):
    path=model_path(value)
    if not path.is_file(): return {'available':False,'path':value,'message':'ยังไม่มีโมเดลที่ฝึกแล้ว ดูขั้นตอนใน MODEL-TRAINING.md'}
    from ultralytics import YOLO
    model=YOLO(str(path))
    if model.task!='detect': raise ValueError('ต้องใช้โมเดล object detection')
    names=model.names
    classes=[str(x) for x in (names.values() if isinstance(names,dict) else names)]
    return {'available':True,'path':value,'classes':classes,
            'has_default_roles':{'cue_ball','target_ball'}.issubset(classes),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
