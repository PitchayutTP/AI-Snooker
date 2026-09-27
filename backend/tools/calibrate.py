"""Estimate and validate homography with separate check points.

python tools/calibrate.py points.json
Input: image_points, table_points, check_image_points, check_table_points.
All points [[x,y], ...]; real units must be identical to radius/table config.
"""
import json
import sys
import cv2
import numpy as np

def calibrate(data):
    image=np.array(data['image_points'],dtype=float)
    table=np.array(data['table_points'],dtype=float)
    checks=np.array(data['check_image_points'],dtype=float)
    targets=np.array(data['check_table_points'],dtype=float)
    if len(image)<4 or image.shape!=table.shape or image.shape[1:]!=(2,):
        raise ValueError('Need at least four corresponding calibration points')
    if len(checks)<1 or checks.shape!=targets.shape or checks.shape[1:]!=(2,):
        raise ValueError('Independent check points are required')
    if not all(np.isfinite(p).all() for p in [image,table,checks,targets]):
        raise ValueError('Coordinates must be finite')
    h,_=cv2.findHomography(image,table,method=0)
    if h is None or abs(np.linalg.det(h))<1e-12: raise ValueError('Degenerate geometry')
    predicted=cv2.perspectiveTransform(checks.reshape(-1,1,2),h).reshape(-1,2)
    error=np.linalg.norm(predicted-targets,axis=1)
    return {'homography':h.tolist(),'check_mean_error':float(error.mean()),
            'check_max_error':float(error.max()),'n_check':len(checks)}

if __name__=='__main__':
    from pathlib import Path
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    print(json.dumps(calibrate(data),indent=2))
