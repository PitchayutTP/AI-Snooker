"""Pure, independently testable measurements. None of these defines an ideal posture."""
import math
import statistics


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle(a, b, c):
    u = [a[i] - b[i] for i in (0, 1)]
    v = [c[i] - b[i] for i in (0, 1)]
    den = math.hypot(*u) * math.hypot(*v)
    if den < 1e-9:
        return None
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x,y in zip(u,v))/den))))


def line_distance(p, a, b):
    den = distance(a, b)
    return None if den < 1e-9 else abs((b[0]-a[0])*(a[1]-p[1])-(a[0]-p[0])*(b[1]-a[1]))/den


def stats(values):
    values = [v for v in values if v is not None and math.isfinite(v)]
    return {'n': len(values), 'mean': statistics.mean(values) if values else None,
            'max': max(values) if values else None,
            'sd': statistics.stdev(values) if len(values) >= 2 else None}


def fraction_estimate(previous_cue, cue, target, radius):
    """Projected overlap fraction, not a measurement of actual surface contact.

    Assumes equal radii, straight incoming motion, stationary target, planar
    calibrated centres. Call only for a detected contact candidate.
    """
    if radius <= 0 or distance(previous_cue, cue) < 1e-9:
        return None
    d = line_distance(target, previous_cue, cue)
    return max(0., min(1., 1 - d/(2*radius)))


def evaluate(measurements, definition):
    if not definition.get('approved'):
        return 'INVALID', 'ยังไม่มีเกณฑ์ที่ผู้จัดทำยืนยัน ใช้ดูค่าการวัดเท่านั้น'
    rules = definition.get('rules', {})
    if not rules:
        return 'INVALID', 'ไม่มีกฎตัดสินผล'
    missing = [key for key in rules if measurements.get(key) is None]
    if missing:
        return 'INVALID', 'ข้อมูลไม่ครบ: ' + ', '.join(missing)
    failed = []
    for key, rule in rules.items():
        value = measurements[key]
        if not math.isfinite(value):
            return 'INVALID', f'ค่าที่ไม่เป็นจำนวนจำกัด: {key}'
        if ('min' in rule and value < rule['min']) or ('max' in rule and value > rule['max']):
            failed.append(key)
    return ('FAIL', 'นอกเกณฑ์: '+', '.join(failed)) if failed else ('PASS', 'ผ่านเกณฑ์รุ่นที่เลือก')


def summarize(samples, baseline_seconds=1., min_valid=5, min_ratio=.7):
    """First baseline_seconds are a setup phase; subsequent frames are measurement.
    Missing frames are counted and not bridged into an invented trajectory.
    """
    values = {}
    if not samples:
        return values
    start = samples[0]['t']
    baseline = [s for s in samples if s['t']-start <= baseline_seconds]
    active = [s for s in samples if s['t']-start > baseline_seconds]
    for key, unit in [('elbow','degree'), ('torso','degree'), ('stance','pixel')]:
        x = [s.get(key) for s in active]
        good = [v for v in x if v is not None]
        valid = len(good) >= min_valid and len(good)/max(1,len(x)) >= min_ratio
        summary = stats(good)
        for part in ['mean','max','sd']:
            values[f'{key}_{part}'] = summary[part] if valid else None
    for key in ['head', 'bridge']:
        base = [s[key] for s in baseline if s.get(key) is not None]
        if len(base) < min_valid or len(base)/max(1,len(baseline)) < min_ratio:
            values[f'{key}_mean'] = values[f'{key}_max'] = None
            continue
        origin = tuple(statistics.mean(p[i] for p in base) for i in (0,1))
        moves = [distance(s[key],origin) for s in active if s.get(key) is not None]
        valid = len(moves)>=min_valid and len(moves)/max(1,len(active))>=min_ratio
        for part in ['mean','max']:
            values[f'{key}_{part}'] = stats(moves)[part] if valid else None
    return values
