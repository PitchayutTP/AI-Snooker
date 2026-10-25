"""Convert a downloaded session export into prediction frames and a numeric worksheet."""
import argparse
import csv
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--attempt-id',required=True)
    parser.add_argument('--unit',required=True,help='Calibrated table coordinate unit, e.g. mm')
    parser.add_argument('--coordinates',choices=['table','image'],default='table')
    parser.add_argument('--out',required=True)
    args=parser.parse_args();data=json.loads(Path(args.session).read_text(encoding='utf-8-sig'))
    if args.coordinates=='image' and args.unit!='pixel':parser.error('Image coordinates must use --unit pixel')
    evidence=next((row for row in data.get('evidence',[]) if row['attempt_id']==args.attempt_id),None)
    attempt=next((row for row in data['attempts'] if row['id']==args.attempt_id),None)
    if not evidence or not attempt:parser.error('Attempt not found in export')
    out=Path(args.out)
    if out.exists():parser.error('Output directory exists; choose a new one')
    output={'unit':args.unit,'coordinates':args.coordinates,'session_id':data['id'],'attempt_id':args.attempt_id,'source':evidence.get('source'),'frames':[]}
    for index,sample in enumerate(evidence.get('samples',[])):
        objects=[]
        for ball in sample.get('balls',[]):
            item={'class':ball['class'],'track_id':ball.get('id'),'xy':ball['xy']}
            if 'box_xyxy' in ball:item['bbox']=ball['box_xyxy']
            if args.coordinates=='image':
                if 'image_xy' in ball:item['xy']=ball['image_xy']
                elif 'bbox' in item:
                    a,b,c,d=item['bbox'];item['xy']=[(a+c)/2,(b+d)/2]
                else:parser.error('No image position in this export; record new data with current code')
            if 'confidence' in ball:item['confidence']=ball['confidence']
            objects.append(item)
        image=sample.get('recorded_images',{}).get('top')
        image_path=str((Path(args.session).resolve().parent/image).resolve()) if image else None
        output['frames'].append({'frame_id':index,'t':sample['t'],'objects':objects,
                                'image':image_path,'image_size':sample.get('image_sizes',{}).get('top')})
    out.mkdir(parents=True)
    (out/'predictions.json').write_text(json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    with (out/'measurements.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['trial_id','metric','unit','reference','prediction']);writer.writeheader()
        for metric,item in attempt['metrics'].items():
            if metric=='escape_success':continue
            writer.writerow({'trial_id':args.attempt_id,'metric':metric,'unit':item['unit'],'reference':'','prediction':item['value'] if item['value'] is not None else ''})
    print('Exported predictions; fill independent references before evaluation:',out)


if __name__=='__main__':main()
