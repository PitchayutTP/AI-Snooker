"""Round-level decisions, independent of database and camera implementations."""


def assessment_problem(definition,configuration):
    if configuration.get('mode')!='LIVE':return 'รอบประเมินต้องใช้ข้อมูล LIVE เท่านั้น'
    if not definition.get('approved') or not definition.get('rules') or not definition.get('protocol'):
        return 'รอบประเมินต้องมีเกณฑ์ยืนยัน จำนวนครั้ง และเงื่อนไขผ่านพร้อมที่มา'
    if 'top' in configuration.get('required',[]):
        if configuration.get('ball_detector')!='YOLO':return 'รอบประเมินที่ใช้กล้องด้านบนต้องเลือก YOLO ตามรายงาน; HSV ใช้เก็บข้อมูลนำร่องได้'
        if not configuration.get('calibration_image_size'):return 'สอบเทียบจากภาพและบันทึกขนาดภาพก่อนรอบประเมิน'
    rules=definition['rules']
    if any(key in rules for key in ('follow_through','center_aim_error')) and not configuration.get('delivery_ball_timing'):
        return 'เกณฑ์นี้ต้องเปิดสองกล้องเพื่อประมาณ Follow-through/แนวเล็งก่อน'
    if 'center_aim_error' in rules and configuration.get('side_ball_center') is None:
        return 'เลือกศูนย์กลางลูกขาวในภาพด้านข้างก่อนใช้เกณฑ์แนวเล็ง'
    return None


def protocol_result(counts, definition, configuration, session_status):
    valid = counts.get('PASS',0) + counts.get('FAIL',0)
    rate = counts.get('PASS',0)/valid if valid else None
    plan = definition.get('protocol')
    result = {'purpose':configuration.get('purpose','PILOT'),'valid_attempts':valid,
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
