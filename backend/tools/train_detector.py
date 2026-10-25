"""Train a YOLOv8 detector from real annotated data, with reproducible run metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True);parser.add_argument('--model',required=True)
    parser.add_argument('--epochs',required=True,type=int);parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--batch',type=int,default=8);parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--device',default='cpu');parser.add_argument('--project',default='data/training')
    parser.add_argument('--name',required=True);parser.add_argument('--export-model')
    args=parser.parse_args();data=Path(args.data).resolve();run=(Path(args.project)/args.name).resolve()
    if not data.is_file():parser.error('Dataset YAML does not exist')
    if args.epochs<1 or args.imgsz<32 or args.batch<1:parser.error('Invalid epochs/imgsz/batch')
    if run.exists():parser.error('Training run already exists; choose another --name')
    destination=Path(args.export_model).resolve() if args.export_model else None
    if destination and destination.exists():parser.error('Export target exists; choose a new filename')
    import yaml
    import ultralytics
    from ultralytics import YOLO
    dataset=yaml.safe_load(data.read_text(encoding='utf-8-sig'))
    if not isinstance(dataset,dict):parser.error('Dataset YAML must be a mapping')
    names=dataset.get('names',[])
    classes=list(names.values()) if isinstance(names,dict) else names
    if classes!=['cue_ball','target_ball']:parser.error('Class order must be 0: cue_ball, 1: target_ball')
    if not dataset.get('val') or not dataset.get('test'):parser.error('Dataset needs independent val and test splits')
    model=YOLO(args.model)
    if model.task!='detect':parser.error('An object detection model is required')
    model.train(data=str(data),epochs=args.epochs,imgsz=args.imgsz,batch=args.batch,device=args.device,
                seed=args.seed,deterministic=True,workers=0,project=str(run.parent),name=run.name,exist_ok=False)
    best=run/'weights/best.pt'
    if not best.is_file():raise RuntimeError('Training finished without best.pt; inspect the actual run logs')
    record={'arguments':vars(args),'ultralytics_version':ultralytics.__version__,
            'dataset_yaml_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
            'best_model_sha256':hashlib.sha256(best.read_bytes()).hexdigest(),
            'classes':classes,'run_directory':str(run),'test_split_evaluated':False}
    manifest=data.parent/'manifest.json'
    if manifest.is_file():record['dataset_manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
    (run/'training-info.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    if destination:
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as output, best.open('rb') as source:shutil.copyfileobj(source,output)
        destination.with_suffix('.training.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Training complete:',best)
    print('Evaluate held-out test data before selecting this model for the main experiment.')


if __name__=='__main__':main()
