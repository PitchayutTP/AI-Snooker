"""Explicitly open a camera to save candidate images; annotations are manual."""
import argparse
import csv
from datetime import datetime,timezone
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera',type=int,required=True);parser.add_argument('--group',required=True)
    parser.add_argument('--out',required=True);parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=720)
    args=parser.parse_args()
    import cv2
    out=Path(args.out).resolve()
    if out.exists():parser.error('Choose a new output directory')
    cap=cv2.VideoCapture(args.camera)
    if not cap.isOpened():cap.release();parser.error('Cannot open camera; close the web app camera first')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,args.width);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,args.height)
    try:
        (out/'images').mkdir(parents=True);(out/'labels').mkdir()
        with (out/'capture.csv').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['image','label','group','split']);writer.writeheader()
            print('S: save image, Q: quit. Label files must be created by annotation before preparing dataset.')
            while True:
                ok,frame=cap.read()
                if not ok:break
                cv2.imshow('Dataset capture - S save / Q quit',frame)
                key=cv2.waitKey(1)&255
                if key in (ord('q'),27):break
                if key==ord('s'):
                    name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                    ok,encoded=cv2.imencode('.jpg',frame)
                    if not ok:continue
                    encoded.tofile(str(out/'images'/(name+'.jpg')))
                    writer.writerow({'image':f'images/{name}.jpg','label':f'labels/{name}.txt','group':args.group,'split':''})
                    stream.flush();print('Saved',name)
    finally:
        cap.release();cv2.destroyAllWindows()


if __name__=='__main__':main()
