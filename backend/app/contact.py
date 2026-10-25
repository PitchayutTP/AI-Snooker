"""Experimental M3 geometric contact candidate with post-event motion evidence.

Swept relative segments reduce missed contacts between frames. This is not a
physical impact sensor; reject incomplete evidence and validate against video.
"""
import math
from .metrics import distance, line_distance


def contact_metrics(samples, config, setup):
    result = {'contact_fraction':None,'fraction_error':None,'escape_success':None}
    radius = config.get('ball_radius',0)
    if not radius or not samples:
        return result, [{'type':'INVALID','reason':'no calibrated ball radius or samples'}]
    trace=[]
    ids=None
    gap=config.get('max_frame_gap_s',.25)
    tolerance=config.get('contact_tolerance',0)
    motion=config.get('motion_threshold',0) or radius*.1
    for sample in samples:
        balls=sample.get('balls',[])
        roles=[[b for b in balls if b['class']==role] for role in ('cue_ball','target_ball')]
        if any(len(items)!=1 or items[0].get('id') is None for items in roles):
            return result,[{'type':'INVALID','reason':'missing or ambiguous ball/track'}]
        cue,target=(items[0] for items in roles)
        current_ids=(cue['id'],target['id'])
        if ids is not None and current_ids!=ids:
            return result,[{'type':'INVALID','reason':'track ID changed'}]
        if trace and not 0 < sample['t']-trace[-1][0] <= gap:
            return result,[{'type':'INVALID','reason':'frame gap or unordered timestamp'}]
        if any(len(b['xy'])!=2 or not all(math.isfinite(v) for v in b['xy']) for b in (cue,target)):
            return result,[{'type':'INVALID','reason':'invalid coordinates'}]
        ids=current_ids
        trace.append((sample['t'],cue['xy'],target['xy']))
    # Reject a setup that starts touching: an incoming trajectory is required.
    if distance(trace[0][1],trace[0][2])<=2*radius+tolerance:
        return result,[{'type':'INVALID','reason':'start with separated balls before striking'}]
    for index in range(1,len(trace)):
        t0,c0,o0=trace[index-1]; t1,c1,o1=trace[index]
        if distance(c0,c1)<motion:
            continue
        relative=[c0[i]-o0[i] for i in (0,1)]
        delta=[(c1[i]-o1[i])-relative[i] for i in (0,1)]
        squared=sum(v*v for v in delta)
        if squared<=1e-12 or sum(relative[i]*delta[i] for i in (0,1))>=0:
            continue
        u=max(0.,min(1.,-sum(relative[i]*delta[i] for i in (0,1))/squared))
        closest=math.hypot(*(relative[i]+u*delta[i] for i in (0,1)))
        if closest>2*radius+tolerance:
            continue
        # Require target departure around the candidate, not mere proximity.
        after=[row for row in trace[index:] if row[0]-t1<=.5]
        if not any(distance(o0,row[2])>=motion for row in after):
            continue
        # Use a pre-event cue segment where available, avoiding a deflected segment.
        before=trace[max(0,index-3):index]
        a=before[0][1]; b=c0
        if distance(a,b)<motion:
            a,b=c0,c1
        offset=line_distance(o0,a,b)
        if offset is None or offset>2*radius+tolerance:
            continue
        value=max(0.,min(1.,1-offset/(2*radius)))
        result.update(contact_fraction=value,fraction_error=abs(value-setup['fraction']))
        return result,[{'type':'CONTACT_CANDIDATE','t':t0+(t1-t0)*u,
                        'method':'swept-relative-segment-with-target-motion',
                        'estimated':True,'closest_distance':closest}]
    return result,[{'type':'INVALID','reason':'no contact candidate with target motion; check FPS, calibration and visibility'}]
