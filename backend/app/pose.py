"""Current-frame pose measurements; never fill occluded joints from old frames."""
import math
from .metrics import angle, distance


def measure_pose(landmarks, width, height, hand, threshold, module_id):
    right = hand == 'RIGHT'
    shoulder, elbow, wrist, hip = (12, 14, 16, 24) if right else (11, 13, 15, 23)
    bridge = 15 if right else 16
    required = {0: 'ศีรษะ', shoulder: 'ไหล่ฝั่งถือคิว', elbow: 'ศอกฝั่งถือคิว',
                wrist: 'ข้อมือฝั่งถือคิว', bridge: 'ข้อมือสะพานมือ'}
    if module_id == 1:
        required = {shoulder:'ไหล่ฝั่งถือคิว', elbow:'ศอกฝั่งถือคิว', wrist:'ข้อมือฝั่งถือคิว'}
        required.update({hip:'สะโพกฝั่งแทง',26 if right else 25:'เข่าฝั่งแทง',
                         28 if right else 27:'ข้อเท้าฝั่งแทง'})
    visible = {}
    for index in required:
        if index >= len(landmarks):
            continue
        point = landmarks[index]
        values = (point.x, point.y, point.visibility, point.presence)
        if any(value is None or not math.isfinite(value) for value in values):
            continue
        if min(point.visibility, point.presence) < threshold:
            continue
        if not (0 <= point.x <= 1 and 0 <= point.y <= 1):
            continue
        visible[index] = [point.x * width, point.y * height]
    measurements = dict.fromkeys(['elbow', 'head', 'bridge'])
    if module_id == 1:
        measurements.update(knee_shooting=None)
        for key,indices in [('knee_shooting',(24,26,28) if right else (23,25,27))]:
            if all(index in visible for index in indices):
                measurements[key]=angle(*(visible[index] for index in indices))
    measurements['head'] = visible.get(0)
    measurements['bridge'] = visible.get(bridge)
    if all(index in visible for index in (shoulder, elbow, wrist)):
        measurements['elbow'] = angle(visible[shoulder], visible[elbow], visible[wrist])
    elbow_issue=None
    if module_id==1:
        minimum_segment=max(6.,min(width,height)*.0125)
        detail={'valid':False,'hand':hand,'minimum_segment_px':minimum_segment,
                'upper_arm_px':None,'forearm_px':None,'confidence':None}
        if all(index in visible for index in (shoulder,elbow,wrist)):
            detail.update(upper_arm_px=distance(visible[shoulder],visible[elbow]),
                          forearm_px=distance(visible[elbow],visible[wrist]),
                          confidence=min(min(landmarks[index].visibility,landmarks[index].presence)
                                         for index in (shoulder,elbow,wrist)))
            if min(detail['upper_arm_px'],detail['forearm_px'])<minimum_segment:
                measurements['elbow']=None
                elbow_issue='ภาพแขนฝั่งแทงสั้นหรือซ้อนกันเกินไป ขยับกล้องให้เห็นไหล่–ศอก–ข้อมือแยกกันชัดเจน'
            detail['valid']=measurements['elbow'] is not None
        measurements['elbow_detail']=detail
    issues = [f'ยังตรวจไม่พบ{label}ชัดเจน' for index, label in required.items() if index not in visible]
    if elbow_issue:issues.append(elbow_issue)
    return measurements, visible, issues
