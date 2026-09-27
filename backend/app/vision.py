"""Optional camera adapters. Heavy libraries load only in live mode."""
import math
import time
from pathlib import Path
from .metrics import angle, distance, line_distance, fraction_estimate


class DemoSource:
    def __init__(self, config): self.i=0
    def read(self):
        self.i+=1
        t=time.monotonic()
        # Deliberate missing samples exercise INVALID handling; never real observations.
        valid=self.i%23!=0
        return {'t':t,'elbow':90+4*math.sin(self.i/10) if valid else None,
                'head':[320+2*math.sin(self.i/9),180] if valid else None,
                'bridge':[450+math.sin(self.i/7),340] if valid else None,
                'torso':40.,'stance':150.,'balls':[], 'cue':None,
                'source':'DEMO','image':None,'error':None,
                'capture_ms':0.,'processing_ms':0.,'ready':True}
    def close(self): pass


class LiveSource:
    def __init__(self, config):
        import cv2
        self.cv2=cv2
        self.config=config
        self.caps={}; self.pose=None; self.yolo=None
        try:
            for name in config['required']:
                source=config[f'{name}_source']
                # Camera indices or video paths; files must be explicitly selected.
                cap=cv2.VideoCapture(int(source) if str(source).isdigit() else source)
                self.caps[name]=cap
                if not cap.isOpened(): raise ValueError(f'เปิดกล้อง/วิดีโอ {name} ไม่ได้')
            if 'side' in self.caps:
                import mediapipe as mp
                model=config['pose_model']
                if not Path(model).is_file(): raise ValueError('ไม่พบไฟล์โมเดล Pose Landmarker .task')
                self.mp=mp
                self.pose=mp.tasks.vision.PoseLandmarker.create_from_options(
                    mp.tasks.vision.PoseLandmarkerOptions(
                        base_options=mp.tasks.BaseOptions(model_asset_path=model),
                        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1))
            if 'top' in self.caps:
                from ultralytics import YOLO
                model=config['ball_model']
                if not Path(model).is_file(): raise ValueError('ไม่พบโมเดลลูกที่ฝึกไว้ (.pt)')
                if not config.get('homography'): raise ValueError('ต้องมี homography ของกล้องด้านบน')
                self.yolo=YOLO(model)
            self.ts=0
        except Exception:
            self.close()
            raise

    def read(self):
        cv2=self.cv2
        import numpy as np
        start=time.monotonic()
        sample={'t':start,'source':'LIVE','image':None,'balls':[],'cue':None,
                'elbow':None,'head':None,'bridge':None,'torso':None,'stance':None,
                'error':None,'ready':True}
        frames={}; times={}
        for name,cap in self.caps.items():
            ok,frame=cap.read(); times[name]=time.monotonic()
            if not ok:
                sample.update(ready=False,error=f'{name}: กล้องขาดการเชื่อมต่อหรือวิดีโอสิ้นสุด')
                return sample
            frames[name]=frame
        sample['capture_ms']=(time.monotonic()-start)*1000
        sample['frame_receive_times']=times
        if len(times)==2 and abs(times['side']-times['top'])*1000>self.config['sync_tolerance_ms']:
            sample.update(ready=False,error='เวลารับเฟรมต่างกันเกินเกณฑ์')
            return sample
        if 'side' in frames:
            frame=frames['side']; h,w=frame.shape[:2]
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            self.ts=max(self.ts+1,int(start*1000))
            res=self.pose.detect_for_video(self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=rgb),self.ts)
            if res.pose_landmarks:
                points=res.pose_landmarks[0]; threshold=self.config['visibility']
                def point(i):
                    p=points[i]
                    if min(p.visibility or 0,p.presence or 0)<threshold: return None
                    return [p.x*w,p.y*h]
                right=self.config['hand']=='RIGHT'
                shoulder,elbow,wrist=[point(i) for i in ([12,14,16] if right else [11,13,15])]
                sample['elbow']=angle(shoulder,elbow,wrist) if all(p is not None for p in [shoulder,elbow,wrist]) else None
                sample['head']=point(0)
                sample['bridge']=point(15 if right else 16)
                hip=point(24 if right else 23)
                if shoulder and hip:
                    sample['torso']=math.degrees(math.atan2(abs(shoulder[1]-hip[1]),abs(shoulder[0]-hip[0])))
                left,rightfoot=point(27),point(28)
                if left and rightfoot: sample['stance']=distance(left,rightfoot)
                for i in [0,11,12,13,14,15,16,23,24,27,28]:
                    p=point(i)
                    if p: cv2.circle(frame,tuple(map(int,p)),5,(60,220,90),-1)
            # Optional explicit coloured markers: real detections, no inferred cue tip.
            hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
            marker_points=[]
            for bounds in self.config.get('cue_markers',[]):
                mask=cv2.inRange(hsv,np.array(bounds['lower'],dtype=np.uint8),np.array(bounds['upper'],dtype=np.uint8))
                contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                contours=[c for c in contours if cv2.contourArea(c)>=bounds.get('min_area',10)]
                if len(contours)!=1:
                    marker_points=[]; break
                moment=cv2.moments(contours[0])
                if not moment['m00']: marker_points=[]; break
                marker_points.append([moment['m10']/moment['m00'],moment['m01']/moment['m00']])
            if len(marker_points)==2:
                sample['cue']=marker_points
                cv2.line(frame,tuple(map(int,marker_points[0])),tuple(map(int,marker_points[1])),(255,180,0),2)
        if 'top' in frames:
            frame=frames['top']
            result=self.yolo.track(frame,persist=True,verbose=False,conf=self.config['ball_confidence'])[0]
            boxes=result.boxes
            H=np.asarray(self.config['homography'],dtype=float)
            if boxes is not None:
                for box in boxes:
                    x1,y1,x2,y2=box.xyxy[0].cpu().tolist()
                    p=cv2.perspectiveTransform(np.array([[[(x1+x2)/2,(y1+y2)/2]]],dtype=np.float32),H)[0,0]
                    if not np.isfinite(p).all(): continue
                    name=str(result.names[int(box.cls.item())])
                    role=self.config.get('ball_roles',{}).get(name,name)
                    sample['balls'].append({'xy':p.tolist(),'class':role,'detected_class':name,
                        'id':int(box.id.item()) if box.id is not None else None})
                    cv2.rectangle(frame,(int(x1),int(y1)),(int(x2),int(y2)),(0,220,100),2)
        # Selected preview; raw videos are not written automatically.
        frame=frames.get('side',frames.get('top'))
        preview=cv2.resize(frame,(640,int(frame.shape[0]*640/frame.shape[1])))
        ok,jpeg=cv2.imencode('.jpg',preview,[cv2.IMWRITE_JPEG_QUALITY,65])
        if ok:
            import base64
            sample['image']=base64.b64encode(jpeg).decode('ascii')
        if 'side' in frames:
            sample['ready']=sample['elbow'] is not None and sample['head'] is not None and sample['bridge'] is not None
        if 'top' in frames:
            sample['ready']=sample['ready'] and all(
                len([b for b in sample['balls'] if b['class']==name and b['id'] is not None])==1
                for name in ['cue_ball','target_ball'])
        sample['processing_ms']=(time.monotonic()-start)*1000
        return sample

    def close(self):
        for cap in self.caps.values(): cap.release()
        if self.pose: self.pose.close()


def ball_metrics(samples, config, setup):
    """Experimental discrete contact/rail candidates. Must be validated with labels.
    Reject gaps, missing IDs, ambiguity and ID switches instead of joining traces.
    """
    result={'contact_fraction':None,'fraction_error':None,'escape_success':None}
    events=[]; previous=None; previous_t=None; track_ids=None; rail=None; hit=False
    radius=config.get('ball_radius',0)
    table=config.get('table_size',[])
    if not radius or len(table)!=2: return result,events
    for sample_index,sample in enumerate(samples):
        cue=[b for b in sample.get('balls',[]) if b['class']=='cue_ball']
        target=[b for b in sample.get('balls',[]) if b['class']=='target_ball']
        if len(cue)!=1 or len(target)!=1 or cue[0]['id'] is None or target[0]['id'] is None:
            return result,[{'type':'INVALID','reason':'missing or ambiguous ball/track'}]
        ids=(cue[0]['id'],target[0]['id'])
        if track_ids is not None and ids!=track_ids:
            return result,[{'type':'INVALID','reason':'track ID changed'}]
        track_ids=ids
        if 'pattern' in setup and len([b for b in sample.get('balls',[]) if b['class']=='obstacle_ball' and b['id'] is not None])!=config.get('expected_obstacles',0):
            return result,[{'type':'INVALID','reason':'missing obstacle detections'}]
        c=cue[0]['xy']; t=target[0]['xy']
        if previous_t is not None and sample['t']-previous_t>config['max_frame_gap_s']:
            return result,[{'type':'INVALID','reason':'frame gap'}]
        if any(distance(c,b['xy'])<=2*radius+config['contact_tolerance'] for b in sample.get('balls',[]) if b['class']=='obstacle_ball'):
            events.append({'type':'OBSTACLE','t':sample['t']})
            hit=True
        edges={'left':c[0],'right':table[0]-c[0],'top':c[1],'bottom':table[1]-c[1]}
        if previous and rail is None:
            for edge,d in edges.items():
                if d<=radius+config['rail_tolerance']:
                    # Candidate needs subsequent direction reversal to count as a rail.
                    events.append({'type':'RAIL_CANDIDATE','edge':edge,'t':sample['t']})
                    rail=edge
        if previous and distance(c,t)<=2*radius+config['contact_tolerance']:
            value=fraction_estimate(previous,c,t,radius)
            result['contact_fraction']=value
            if value is not None and 'fraction' in setup:
                result['fraction_error']=abs(value-setup['fraction'])
            events.append({'type':'CONTACT_CANDIDATE','t':sample['t']})
            # Escape classification intentionally unavailable until directional reversal
            # is validated; exposed below only with sufficient geometric evidence.
            required=config.get('escape_rail')
            if required and rail:
                candidates=[i for i,s in enumerate(samples[:sample_index+1]) if any(b['class']=='cue_ball' and
                    ({'left':b['xy'][0],'right':table[0]-b['xy'][0],'top':b['xy'][1],'bottom':table[1]-b['xy'][1]}[rail]
                     <=radius+config['rail_tolerance']) for b in s.get('balls',[]))]
                idx=candidates[0] if candidates else 0
                axis=0 if rail in ['left','right'] else 1
                if 0<idx<sample_index:
                    def cp(j): return next(b['xy'][axis] for b in samples[j]['balls'] if b['class']=='cue_ball')
                    reversed_direction=(cp(idx)-cp(idx-1))*(cp(idx+1)-cp(idx))<0
                    if reversed_direction:
                        result['escape_success']=float(rail==required and not hit)
            return result,events
        previous=c; previous_t=sample['t']
    return result,events


def cue_metrics(samples, baseline_seconds, config=None):
    result={'cue_deviation_mean':None,'cue_deviation_max':None,
            'follow_through':None,'center_aim_error':None}
    if not samples: return result
    import statistics
    base=[s['cue'] for s in samples if s.get('cue') and s['t']-samples[0]['t']<=baseline_seconds]
    active=[s for s in samples if s['t']-samples[0]['t']>baseline_seconds]
    valid=[s['cue'] for s in active if s.get('cue')]
    if len(base)<5 or len(valid)<5 or len(valid)/max(1,len(active))<.7: return result
    a,b=[tuple(statistics.mean(c[k][i] for c in base) for i in (0,1)) for k in (0,1)]
    deviations=[line_distance(c[0],a,b) for c in valid]
    deviations=[d for d in deviations if d is not None]
    if deviations:
        result['cue_deviation_mean']=statistics.mean(deviations)
        result['cue_deviation_max']=max(deviations)
    config=config or {}
    # Optional experimental timing from top-view cue-ball departure, not observed impact.
    if config.get('delivery_ball_timing') and config.get('motion_threshold',0)>0:
        baseballs=[]; trace=[]; ids=set()
        for s in samples:
            balls=[ball for ball in s.get('balls',[]) if ball['class']=='cue_ball' and ball['id'] is not None]
            if len(balls)!=1: return result
            ball=balls[0]; ids.add(ball['id'])
            if s['t']-samples[0]['t']<=baseline_seconds: baseballs.append(ball['xy'])
            else: trace.append((s,ball['xy']))
        if len(ids)!=1 or len(baseballs)<5: return result
        origin=[statistics.mean(p[i] for p in baseballs) for i in (0,1)]
        motion=None
        for i in range(1,len(trace)):
            before,p=trace[i-1]; current,q=trace[i]
            if current['t']-before['t']>config.get('max_frame_gap_s',.25): return result
            if distance(p,origin)>config['motion_threshold'] and distance(q,origin)>config['motion_threshold']:
                motion=i-1; break
        if motion is not None:
            contact=trace[motion][0]
            later=[s for s,_ in trace[motion:]]
            if contact.get('cue') and all(s.get('cue') for s in later):
                tip,back=contact['cue']; length=distance(tip,back)
                if length>1e-9:
                    direction=[(tip[i]-back[i])/length for i in (0,1)]
                    projected=[sum((s['cue'][0][i]-tip[i])*direction[i] for i in (0,1)) for s in later]
                    result['follow_through']=max(0.,max(projected))
            # Cue-line aim proxy immediately before movement; NOT physical contact point.
            pre=trace[max(0,motion-1)][0]
            center=config.get('side_ball_center')
            if center is not None and pre.get('cue'):
                result['center_aim_error']=line_distance(center,*pre['cue'])
    return result
