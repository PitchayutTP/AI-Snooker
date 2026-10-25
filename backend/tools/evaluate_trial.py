"""Evaluate independent references, with explicit operating thresholds and missing data."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def finite_point(value,size):
    return isinstance(value,list) and len(value)==size and all(type(x) in (int,float) and math.isfinite(x) for x in value)


def frames(document,allow_empty=False):
    if document.get('example_only'):raise ValueError('Example data cannot be used as experiment evidence')
    result={}
    for frame in document['frames']:
        key=str(frame['frame_id'])
        if key in result:raise ValueError('Duplicate frame_id')
        if not isinstance(frame.get('objects'),list):raise ValueError('Each labelled frame needs an objects list (empty for confirmed negatives)')
        for item in frame['objects']:
            if not isinstance(item.get('class'),str) or not item['class']:raise ValueError('Object class missing')
            if 'confidence' in item and (type(item['confidence']) not in (int,float) or not math.isfinite(item['confidence']) or not 0<=item['confidence']<=1):raise ValueError('Invalid confidence')
            if 'bbox' in item and (not finite_point(item['bbox'],4) or item['bbox'][2]<=item['bbox'][0] or item['bbox'][3]<=item['bbox'][1]):raise ValueError('Invalid xyxy box')
            if 'xy' in item and not finite_point(item['xy'],2):raise ValueError('Invalid table coordinate')
        result[key]=frame['objects']
    if not result and not allow_empty:raise ValueError('No labelled reference frames')
    return result


def iou(a,b):
    left=max(a[0],b[0]);top=max(a[1],b[1]);right=min(a[2],b[2]);bottom=min(a[3],b[3])
    intersection=max(0,right-left)*max(0,bottom-top)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union else 0


def detection_report(reference,prediction,min_iou,confidence):
    if not 0<min_iou<=1 or not 0<=confidence<=1:raise ValueError('Invalid IoU/confidence threshold')
    gt=frames(reference);pred=frames(prediction,True);tp=fp=fn=0;per_class={}
    def count(label,kind):
        per_class.setdefault(label,{'tp':0,'fp':0,'fn':0})[kind]+=1
    for key,truth in gt.items():
        candidates=[x for x in pred.get(key,[]) if x.get('confidence',1)>=confidence]
        if any('bbox' not in x for x in truth+candidates):raise ValueError('Detection evaluation needs bbox on every object')
        used=set()
        for item in sorted(candidates,key=lambda x:x.get('confidence',1),reverse=True):
            possible=[(iou(item['bbox'],target['bbox']),j) for j,target in enumerate(truth) if j not in used and target['class']==item['class']]
            overlap,index=max(possible,default=(0,-1))
            if overlap>=min_iou:
                used.add(index);tp+=1;count(item['class'],'tp')
            else:fp+=1;count(item['class'],'fp')
        for j,item in enumerate(truth):
            if j not in used:fn+=1;count(item['class'],'fn')
    def rates(counts):
        a,b,c=counts['tp'],counts['fp'],counts['fn']
        return {**counts,'precision':a/(a+b) if a+b else None,'recall':a/(a+c) if a+c else None}
    return {'labelled_frames':len(gt),'missing_prediction_frames':sum(key not in pred for key in gt),
            'unlabelled_prediction_frames':sum(key not in gt for key in pred),
            'matching':'confidence descending, same class, one-to-one IoU',
            'min_iou':min_iou,'confidence':confidence,'zero_denominator':'null',
            **rates({'tp':tp,'fp':fp,'fn':fn}),'per_class':{key:rates(value) for key,value in per_class.items()}}


def tracking_report(reference,prediction,max_distance):
    if not math.isfinite(max_distance) or max_distance<=0:raise ValueError('max_distance must be positive in the calibrated table unit')
    if not reference.get('unit') or reference.get('unit')!=prediction.get('unit'):raise ValueError('Tracking coordinate units must be explicit and equal')
    gt=frames(reference);pred=frames(prediction,True);errors=[];x_errors=[];y_errors=[];missing=total=switches=opportunities=0
    previous={}
    for key,truth in gt.items():
        candidates=pred.get(key,[])
        if any('xy' not in item for item in truth+candidates):raise ValueError('Tracking needs xy on every object')
        pairs=sorted((math.dist(a['xy'],b['xy']),i,j) for i,a in enumerate(truth) for j,b in enumerate(candidates) if a['class']==b['class'])
        used_gt=set();used_pred=set();matches={}
        for distance,i,j in pairs:
            if distance<=max_distance and i not in used_gt and j not in used_pred:
                used_gt.add(i);used_pred.add(j);matches[i]=j
                errors.append(distance);x_errors.append(abs(truth[i]['xy'][0]-candidates[j]['xy'][0]));y_errors.append(abs(truth[i]['xy'][1]-candidates[j]['xy'][1]))
        present={}
        for i,item in enumerate(truth):
            total+=1
            if item.get('track_id') is None:raise ValueError('Reference objects require persistent track_id')
            identity=(item['class'],str(item['track_id']))
            if identity in present:raise ValueError('Duplicate reference identity in frame')
            present[identity]=True
            if i not in matches:missing+=1;continue
            matched=candidates[matches[i]]
            if matched.get('track_id') is None:missing+=1;continue
            current=str(matched['track_id'])
            if identity in previous:
                opportunities+=1;switches+=previous[identity]!=current
            present[identity]=current
        previous={key:value for key,value in present.items() if isinstance(value,str)}
    return {'reference_observations':total,'matched_positions':len(errors),'missing_or_untracked':missing,
            'missing_rate':missing/total if total else None,'unit':reference['unit'],
            'mean_position_error':statistics.mean(errors) if errors else None,
            'x_mae':statistics.mean(x_errors) if x_errors else None,'y_mae':statistics.mean(y_errors) if y_errors else None,
            'id_switches':switches,'consecutive_match_opportunities':opportunities,
            'id_switch_policy':'consecutive labelled frames; reset after missing observation',
            'max_distance':max_distance,'matching':'same class, nearest distance, one-to-one; reference frame order must be chronological'}


def measurement_report(rows):
    groups={}
    for row in rows:
        metric=row.get('metric','').strip();unit=row.get('unit','').strip()
        if not metric or not unit:raise ValueError('Each numeric row needs metric and unit')
        group=groups.setdefault((metric,unit),{'metric':metric,'unit':unit,'n_total':0,'errors':[],'bias':[]})
        group['n_total']+=1
        try:a,b=float(row['reference']),float(row['prediction'])
        except (ValueError,TypeError,KeyError):continue
        if not math.isfinite(a) or not math.isfinite(b):continue
        group['errors'].append(abs(a-b));group['bias'].append(b-a)
    result=[]
    for group in groups.values():
        errors=group.pop('errors');bias=group.pop('bias');n=len(errors)
        result.append({**group,'n_valid_pairs':n,'n_missing_pairs':group['n_total']-n,
                       'mae':statistics.mean(errors) if n else None,
                       'rmse':math.sqrt(statistics.mean(e*e for e in errors)) if n else None,
                       'bias_prediction_minus_reference':statistics.mean(bias) if n else None})
    if not result:raise ValueError('No measurement rows')
    return {'metrics':result,'matching':'Rows must be independently aligned before evaluation; units are never mixed'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='kind',required=True)
    for kind in ['detection','tracking']:
        tool=sub.add_parser(kind);tool.add_argument('--reference',required=True);tool.add_argument('--prediction',required=True)
        if kind=='detection':tool.add_argument('--iou',required=True,type=float);tool.add_argument('--confidence',required=True,type=float)
        else:tool.add_argument('--max-distance',required=True,type=float)
        tool.add_argument('--out',required=True)
    tool=sub.add_parser('measurements');tool.add_argument('--csv',required=True);tool.add_argument('--out',required=True)
    args=parser.parse_args()
    try:
        if args.kind=='measurements':
            with open(args.csv,encoding='utf-8-sig',newline='') as stream:result=measurement_report(list(csv.DictReader(stream)))
        else:
            reference=json.loads(Path(args.reference).read_text(encoding='utf-8-sig'))
            prediction=json.loads(Path(args.prediction).read_text(encoding='utf-8-sig'))
            result=detection_report(reference,prediction,args.iou,args.confidence) if args.kind=='detection' else tracking_report(reference,prediction,args.max_distance)
        with open(args.out,'x',encoding='utf-8') as output:json.dump(result,output,indent=2,ensure_ascii=False,allow_nan=False)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
