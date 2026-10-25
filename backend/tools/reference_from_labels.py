"""Build image-coordinate references from independently annotated YOLO labels.

Uses frame IDs/image sizes, never predicted boxes. Missing labels are unlabelled,
not negative examples. For this controlled setup, one object per role is expected.
"""
import argparse
import json
from pathlib import Path
try:
    from .prepare_dataset import validate_label,NAMES
except ImportError:
    from prepare_dataset import validate_label,NAMES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions',required=True);parser.add_argument('--labels',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args();pred=json.loads(Path(args.predictions).read_text(encoding='utf-8-sig'))
    output={'unit':'pixel','coordinates':'image','reference_method':'independent YOLO boxes; centre of annotated box',
            'track_id_policy':'one cue_ball and one target_ball in controlled setup','frames':[],'unlabelled_frames':0}
    for frame in pred['frames']:
        index=frame['frame_id'];label=Path(args.labels)/f'{int(index):06d}.txt'
        if not label.is_file():output['unlabelled_frames']+=1;continue
        size=frame.get('image_size')
        if not size or len(size)!=2:parser.error('Original image dimensions missing; use a new recorded export')
        validate_label(label)
        width,height=size;objects=[];seen=set()
        for line in label.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():continue
            name,x,y,w,h=line.split();name=NAMES[int(name)]
            if name in seen:parser.error('More than one object per role; supply explicit independent track IDs instead')
            seen.add(name);x,y,w,h=map(float,(x,y,w,h))
            objects.append({'class':name,'track_id':name,'xy':[x*width,y*height],
                            'bbox':[(x-w/2)*width,(y-h/2)*height,(x+w/2)*width,(y+h/2)*height]})
        output['frames'].append({'frame_id':index,'objects':objects})
    if not output['frames']:parser.error('No independent labels found')
    with open(args.out,'x',encoding='utf-8') as stream:json.dump(output,stream,indent=2,allow_nan=False)
    print('Reference frames:',len(output['frames']),'unlabelled:',output['unlabelled_frames'])


if __name__=='__main__':main()
