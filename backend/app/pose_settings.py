"""M1 inference defaults. Engineering choices requiring real-camera validation."""

M1_POSE_MODEL = "models/pose_landmarker_full.task"
M1_VISIBILITY = 0.6
M1_POSE_CONFIDENCE = 0.6


def pose_options(mp, model, module_id):
    confidence = M1_POSE_CONFIDENCE if module_id == 1 else 0.5
    return mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_buffer=model.read_bytes()),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=confidence,
        min_pose_presence_confidence=confidence,
        min_tracking_confidence=confidence,
        output_segmentation_masks=False,
    )


def m1_capture_defaults(config, explicitly_set):
    result = dict(config)
    if "pose_model" not in explicitly_set:
        result["pose_model"] = M1_POSE_MODEL
    if "visibility" not in explicitly_set:
        result["visibility"] = M1_VISIBILITY
    return result
