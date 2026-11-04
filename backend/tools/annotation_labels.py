"""Validate independent two-class box annotations for evaluation, not model training."""

import math

NAMES = ["cue_ball", "target_ball"]


def validate_label(path):
    classes = set()
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        values = line.split()
        if len(values) != 5:
            raise ValueError(f"{path.name}:{number}: expected class x y width height")
        if values[0] not in ("0", "1"):
            raise ValueError(f"{path.name}:{number}: class must be 0 or 1")
        x, y, w, h = map(float, values[1:])
        if (
            not all(math.isfinite(v) for v in (x, y, w, h))
            or w <= 0
            or h <= 0
            or min(x - w / 2, y - h / 2) < -1e-6
            or max(x + w / 2, y + h / 2) > 1 + 1e-6
        ):
            raise ValueError(f"{path.name}:{number}: invalid normalized bounding box")
        classes.add(int(values[0]))
    return classes
