"""Stable, display-only crop from the original side-camera frame."""
import math
from .cameras import encode_image


class ElbowPreview:
    def __init__(self):
        self.box=None
        self.size=None

    def render(self,frame,points,hand):
        import cv2
        indices=(12,14,16) if hand=='RIGHT' else (11,13,15)
        if not all(index in points for index in indices):
            self.box=None
            return None
        height,width=frame.shape[:2]
        if self.size!=(width,height):self.box=None
        self.size=(width,height)
        xs=[points[index][0] for index in indices]
        ys=[points[index][1] for index in indices]
        if self.box is None or not (self.box[0]+12<=min(xs) and max(xs)<=self.box[2]-12 and
                                    self.box[1]+12<=min(ys) and max(ys)<=self.box[3]-12):
            span=max(max(xs)-min(xs),max(ys)-min(ys))
            size=max(160,math.ceil(span+2*max(36,span*.25)))
            crop_width=min(width,size);crop_height=min(height,size)
            left=max(0,min(width-crop_width,round((min(xs)+max(xs)-crop_width)/2)))
            top=max(0,min(height-crop_height,round((min(ys)+max(ys)-crop_height)/2)))
            self.box=(left,top,left+crop_width,top+crop_height)
        left,top,right,bottom=self.box
        crop=frame[top:bottom,left:right]
        target_width=min(640,crop.shape[1]*2)
        crop=cv2.resize(crop,(target_width,round(crop.shape[0]*target_width/crop.shape[1])),interpolation=cv2.INTER_LINEAR)
        return {'image':encode_image(cv2,crop,85),'source_box':list(self.box),
                'source_size':[width,height]}
