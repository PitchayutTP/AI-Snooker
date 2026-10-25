"""Trailing moving averages for body/cue values. Never fill missing observations.

Ball trajectories are deliberately excluded to preserve collision timing.
"""
from collections import deque
from copy import deepcopy
import statistics

KEYS=('elbow','torso','stance','head','bridge','cue')


def average(values):
    if isinstance(values[0],(list,tuple)):
        return [average([v[i] for v in values]) for i in range(len(values[0]))]
    return statistics.mean(values)


class MovingAverage:
    def __init__(self,window=1,max_gap=.25):
        self.window=window; self.max_gap=max_gap; self.last=None
        self.values={key:deque(maxlen=window) for key in KEYS}
        self.intervals=deque(maxlen=max(1,window))

    def reset(self):
        for queue in self.values.values(): queue.clear()
        self.intervals.clear(); self.last=None

    def apply(self,sample):
        stamp=sample.get('t')
        if stamp is None: return sample
        if self.last is not None:
            dt=stamp-self.last
            if dt<=0 or dt>self.max_gap: self.reset()
            else: self.intervals.append(dt)
        self.last=stamp
        raw={key:deepcopy(sample.get(key)) for key in KEYS}
        filtered={}
        for key,value in raw.items():
            queue=self.values[key]
            if value is None:
                queue.clear();filtered[key]=None
            else:
                queue.append(value);filtered[key]=average(list(queue))
        sample.update(filtered)
        sample['raw_measurements']=raw
        sample['display_measurements']=deepcopy(filtered)
        sample['smoothing_window']=self.window
        sample['estimated_smoothing_delay_ms']=(self.window-1)/2*statistics.mean(self.intervals)*1000 if self.intervals else 0
        return sample
