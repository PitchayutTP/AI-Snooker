"""Validate YOLO annotations and split by capture group, not by individual frame."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import shutil

NAMES=['cue_ball','target_ball']


def validate_label(path):
    classes=set()
    for number,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip(): continue
        values=line.split()
        if len(values)!=5: raise ValueError(f'{path.name}:{number}: expected class x y width height')
        if values[0] not in ('0','1'): raise ValueError(f'{path.name}:{number}: class must be 0 or 1')
        x,y,w,h=map(float,values[1:])
        if not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0 or min(x-w/2,y-h/2)<-1e-6 or max(x+w/2,y+h/2)>1+1e-6:
            raise ValueError(f'{path.name}:{number}: invalid normalized bounding box')
        classes.add(int(values[0]))
    return classes


def prepare(manifest,out,seed=42,val_fraction=.2,test_fraction=.2):
    import cv2
    import numpy as np
    manifest=Path(manifest).resolve();out=Path(out).resolve()
    if out.exists(): raise ValueError('Output directory already exists; choose a new directory')
    if val_fraction<=0 or test_fraction<=0 or val_fraction+test_fraction>=1: raise ValueError('Invalid split fractions')
    with manifest.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
    if not rows: raise ValueError('Manifest is empty')
    groups={};seen={};items=[]
    for row in rows:
        group=row.get('group','').strip()
        if not group or not row.get('image') or not row.get('label'): raise ValueError('Every row needs image,label,group')
        image=(manifest.parent/row['image']).resolve();label=(manifest.parent/row['label']).resolve()
        if not image.is_file() or not label.is_file(): raise ValueError(f'Image/annotation missing: {row["image"]}. Annotate first; missing labels are not negatives.')
        if image.suffix.lower() not in ('.jpg','.jpeg','.png','.bmp','.webp'): raise ValueError('Unsupported image extension')
        decoded=cv2.imdecode(np.fromfile(str(image),dtype=np.uint8),cv2.IMREAD_COLOR)
        if decoded is None:raise ValueError(f'Cannot decode image: {image.name}')
        digest=hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in seen: raise ValueError(f'Duplicate image contents in groups {seen[digest]} and {group}; remove duplicates before splitting')
        seen[digest]=group
        split=row.get('split','').strip().lower()
        if split and split not in ('train','val','test'): raise ValueError('split must be train/val/test or blank')
        groups.setdefault(group,set()).add(split)
        items.append({'image':image,'label':label,'group':group,'split':split,'sha256':digest,'classes':validate_label(label)})
    if any(len(values)!=1 for values in groups.values()): raise ValueError('All images from a group must use the same split')
    explicit=any(item['split'] for item in items)
    if explicit and not all(item['split'] for item in items): raise ValueError('Specify split for every row or leave every split blank')
    if not explicit:
        names=sorted(groups)
        if len(names)<3: raise ValueError('Need at least 3 independent capture groups for train/val/test')
        random.Random(seed).shuffle(names)
        nv=max(1,int(len(names)*val_fraction));nt=max(1,int(len(names)*test_fraction))
        if nv+nt>=len(names): raise ValueError('Not enough groups for requested fractions')
        assignment={name:'val' if i<nv else 'test' if i<nv+nt else 'train' for i,name in enumerate(names)}
        for item in items:item['split']=assignment[item['group']]
    if {item['split'] for item in items}!={'train','val','test'}: raise ValueError('All three splits must be nonempty')
    train_classes=set().union(*(item['classes'] for item in items if item['split']=='train'))
    if train_classes!={0,1}: raise ValueError('Training annotations must include both cue_ball and target_ball')
    # Validate every input before creating output. Existing directories are never overwritten.
    out.mkdir(parents=True,exist_ok=False)
    record=[]
    for item in items:
        split=item['split'];stem=item['sha256'][:24]
        image_dir=out/'images'/split;label_dir=out/'labels'/split
        image_dir.mkdir(parents=True,exist_ok=True);label_dir.mkdir(parents=True,exist_ok=True)
        destination=image_dir/(stem+item['image'].suffix.lower())
        shutil.copy2(item['image'],destination);shutil.copy2(item['label'],label_dir/(stem+'.txt'))
        record.append({'image':destination.relative_to(out).as_posix(),'group':item['group'],'split':split,
                       'sha256':item['sha256'],'label_sha256':hashlib.sha256(item['label'].read_bytes()).hexdigest()})
    config={'path':out.as_posix(),'train':'images/train','val':'images/val','test':'images/test','names':NAMES}
    (out/'data.yaml').write_text(json.dumps(config,indent=2),encoding='utf-8')
    summary={'seed':seed,'split_unit':'capture group','classes':NAMES,'images':record,
             'counts':{split:sum(item['split']==split for item in items) for split in ('train','val','test')}}
    (out/'manifest.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--val-fraction',type=float,default=.2);parser.add_argument('--test-fraction',type=float,default=.2)
    args=parser.parse_args()
    try: result=prepare(args.manifest,args.out,args.seed,args.val_fraction,args.test_fraction)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(result['counts'],indent=2))
