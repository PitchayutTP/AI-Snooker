"""Run real Ultralytics validation; this command does not invent accuracy values."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True);parser.add_argument('--data',required=True)
    parser.add_argument('--split',choices=['val','test'],default='test')
    parser.add_argument('--imgsz',type=int,default=640);parser.add_argument('--device',default='cpu')
    parser.add_argument('--project',default='data/validation');parser.add_argument('--name',required=True)
    args=parser.parse_args();model_file=Path(args.model).resolve();data=Path(args.data).resolve()
    out=(Path(args.project)/args.name).resolve()
    if not model_file.is_file() or not data.is_file():parser.error('Model and dataset YAML must exist')
    if out.exists():parser.error('Output run exists; choose a new name')
    import ultralytics
    from ultralytics import YOLO
    result=YOLO(str(model_file)).val(data=str(data),split=args.split,imgsz=args.imgsz,device=args.device,
                workers=0,plots=True,project=str(out.parent),name=out.name,exist_ok=False)
    metrics={key:float(value) if math.isfinite(float(value)) else None for key,value in result.results_dict.items()}
    report={'arguments':vars(args),'ultralytics_version':ultralytics.__version__,
            'model_sha256':hashlib.sha256(model_file.read_bytes()).hexdigest(),
            'dataset_yaml_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
            'metrics':metrics,'note':'Ultralytics metrics use its PR/mAP matching protocol; use evaluate_trial.py for fixed operating thresholds.'}
    out.mkdir(parents=True,exist_ok=True)
    (out/'evaluation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
