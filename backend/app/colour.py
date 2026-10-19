"""Conservative white/red colour detector for a controlled prototype table.
One visible ball per role; ambiguity loses identity rather than selecting a guess.
"""
import math

class ColourTracker:
    def __init__(self, colours, min_area=50, max_area=5000, max_jump=120, max_gap=.25):
        self.colours=colours; self.min_area=min_area; self.max_area=max_area
        self.max_jump=max_jump; self.max_gap=max_gap; self.previous={}; self.next_id=1

    def detect(self, frame, stamp, homography):
        import cv2
        import numpy as np
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        h=np.asarray(homography,dtype=float); found=[]
        for role, ranges in self.colours.items():
            mask=np.zeros(hsv.shape[:2],dtype=np.uint8)
            for bounds in ranges:
                mask=cv2.bitwise_or(mask,cv2.inRange(hsv,np.array(bounds['lower'],dtype=np.uint8),np.array(bounds['upper'],dtype=np.uint8)))
            # Only search the calibrated table plane; ignore white/red objects outside it.
            # Actual ROI is applied by caller when table dimensions are available.
            contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            candidates=[]
            for contour in contours:
                area=cv2.contourArea(contour); perimeter=cv2.arcLength(contour,True)
                if not self.min_area<=area<=self.max_area or perimeter<=0: continue
                if 4*math.pi*area/perimeter**2<.6: continue
                moment=cv2.moments(contour)
                if not moment['m00']: continue
                centre=[moment['m10']/moment['m00'],moment['m01']/moment['m00']]
                candidates.append(centre)
            if len(candidates)!=1:
                self.previous.pop(role,None); continue
            x,y=candidates[0]; old=self.previous.get(role)
            same=old and 0<=stamp-old['t']<=self.max_gap and math.hypot(x-old['xy'][0],y-old['xy'][1])<=self.max_jump
            track_id=old['id'] if same else self.next_id
            if not same: self.next_id+=1
            self.previous[role]={'t':stamp,'xy':[x,y],'id':track_id}
            mapped=cv2.perspectiveTransform(np.array([[[x,y]]],dtype=np.float32),h)[0,0]
            if not np.isfinite(mapped).all(): continue
            found.append({'class':role,'detected_class':role,'id':track_id,'xy':mapped.tolist(),'image_xy':[x,y]})
            cv2.circle(frame,(int(x),int(y)),10,(0,200,200),2)
            cv2.putText(frame,role,(int(x)+12,int(y)),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,200,200),1)
        return found
