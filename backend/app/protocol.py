"""Round-level decisions, independent of database and camera implementations."""
from .criteria_templates import M1_TEMPLATE_VERSION


def assessment_problem(definition,configuration):
    if configuration.get('mode')!='LIVE':return 'รอบประเมินต้องใช้ข้อมูล LIVE เท่านั้น'
    if not definition.get('approved') or not definition.get('rules') or not definition.get('protocol'):
        return 'รอบประเมินต้องมีเกณฑ์ยืนยัน จำนวนครั้ง และเงื่อนไขผ่านพร้อมที่มา'
    if 'top' in configuration.get('required',[]):
        if configuration.get('ball_detector')!='YOLO' and definition.get('validation_scope')!='PROTOTYPE':return 'รอบประเมินตามรายงานต้องใช้ YOLO; หากใช้ HSV ให้เลือกเกณฑ์ที่ระบุขอบเขต PROTOTYPE'
        if not configuration.get('calibration_image_size'):return 'สอบเทียบจากภาพและบันทึกขนาดภาพก่อนรอบประเมิน'
    rules=definition['rules']
    version=definition.get('template_version') or ''
    if version.startswith('m1-'):
        if version!=M1_TEMPLATE_VERSION:
            return 'เกณฑ์ M1 รุ่นนี้เลิกใช้แล้ว กรุณาเริ่มด้วยเกณฑ์ปัจจุบันจากหน้าเตรียมฝึก'
        if (configuration.get('m1_auto_seconds')!=8 or configuration.get('baseline_seconds')!=1 or
                configuration.get('smoothing_window')!=15 or configuration.get('smoothing_method')!='MEDIAN_EMA' or
                configuration.get('smoothing_tau_seconds')!=.8 or configuration.get('smoothing_max_gap_s')!=.75 or
                not configuration.get('smoothing_for_evaluation')):
            return 'เกณฑ์ M1 ใช้ Median 15 เฟรม + EMA 0.8 วินาที ช่วงรีเซ็ต 0.75 วินาที บันทึก 8 วินาที ฐาน 1 วินาที'
    if any(key in rules for key in ('follow_through','center_aim_error','follow_through_ratio','center_aim_ratio')) and not configuration.get('delivery_ball_timing'):
        return 'เกณฑ์นี้ต้องเปิดสองกล้องเพื่อประมาณ Follow-through/แนวเล็งก่อน'
    if any(key in rules for key in ('center_aim_error','center_aim_ratio')) and configuration.get('side_ball_center') is None:
        return 'เลือกศูนย์กลางลูกขาวในภาพด้านข้างก่อนใช้เกณฑ์แนวเล็ง'
    return None


def protocol_result(counts, definition, configuration, session_status):
    valid = counts.get('PASS',0) + counts.get('FAIL',0)
    rate = counts.get('PASS',0)/valid if valid else None
    plan = definition.get('protocol')
    result = {'purpose':configuration.get('purpose','PILOT'),'valid_attempts':valid,
              'validation_scope':definition.get('validation_scope','REPORT'),
              'invalid_attempts':counts.get('INVALID',0),'pass_rate':rate,
              'required_valid_attempts':plan.get('required_valid_attempts') if plan else None,
              'minimum_pass_rate':plan.get('minimum_pass_rate') if plan else None,
              'remaining':None,'status':'PILOT'}
    if result['purpose']!='ASSESSMENT': return result
    if not plan or not definition.get('approved') or configuration.get('mode')!='LIVE':
        result['status']='INVALID'
        return result
    result['remaining']=max(0,plan['required_valid_attempts']-valid)
    if session_status=='ABORTED': result['status']='ABORTED'
    elif result['remaining']:
        result['status']='IN_PROGRESS' if session_status=='IN_PROGRESS' else 'INCOMPLETE'
    elif session_status=='IN_PROGRESS': result['status']='READY_TO_FINISH'
    else: result['status']='PASS' if rate>=plan['minimum_pass_rate'] else 'FAIL'
    return result
