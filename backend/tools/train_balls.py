"""Train your own annotated snooker detector; never generates labels or accuracy.

python tools/train_balls.py --data path/to/data.yaml --model yolov8n.pt --epochs 50
The caller selects epochs from their experiment, not from a report claim.
Ultralytics may download initial model weights when explicitly requested.
"""
import argparse
from pathlib import Path

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--epochs',required=True,type=int)
    parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--device',default='cpu')
    args=parser.parse_args()
    if not Path(args.data).is_file(): parser.error('Dataset YAML does not exist')
    if args.epochs<1: parser.error('epochs must be positive')
    from ultralytics import YOLO
    model=YOLO(args.model)
    model.train(data=args.data,epochs=args.epochs,imgsz=args.imgsz,device=args.device,
                project='data/training',name='snooker',exist_ok=False)
