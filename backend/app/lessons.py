"""Prototype lessons: original diagrams/text, not copied book pages."""
LESSONS = {
  1: {'goal':'สังเกตความสม่ำเสมอของท่าตั้งต้น ไม่ใช้ค่ามุมเดียวตัดสินท่าที่เหมาะกับทุกคน',
      'camera':'กล้องด้านข้างต้องเห็นศีรษะ ไหล่ ศอก ข้อมือ สะโพก และข้อเท้าทั้งสองข้าง',
      'steps':['เลือกมือถนัดและปรับกล้องให้เห็นจุดร่างกายครบ','ตั้งท่าตามที่ฝึกและหยุดนิ่งอย่างน้อย 1 วินาทีแรกหลังเริ่มบันทึก','คงท่าเดิมอีก 3–5 วินาที แล้วจบการบันทึก','ทบทวนความแปรปรวนของมุมและการเคลื่อนของศีรษะ เปรียบเทียบภายใต้ตำแหน่งกล้องเดิม'],
      'metrics':['elbow_mean','elbow_sd','torso_mean','torso_sd','stance_mean','stance_sd','head_mean','head_max']},
  2: {'goal':'สังเกตการส่งคิวเทียบแนวตั้งต้นและความนิ่งของศีรษะกับสะพานมือ',
      'camera':'กล้องด้านข้างเห็นแนวคิวและ marker สองสีที่ติดกับคิว ตำแหน่งแรกเป็น marker ด้านปลายคิว',
      'steps':['ตั้ง HSV ของ marker สองสีตามอุปกรณ์และแสงจริง','ตั้งแนวคิวให้นิ่งในช่วงฐานอย่างน้อย 1 วินาที','ส่งคิวตามแบบฝึกแล้วจบการบันทึกเมื่อเคลื่อนไหวเสร็จ','ถ้าจะประมาณ Follow-through ให้เปิดการตรวจเวลาลูกเริ่มเคลื่อนและตั้งค่ากล้องด้านบนด้วย'],
      'metrics':['cue_deviation_mean','cue_deviation_max','head_mean','head_max','bridge_mean','bridge_max','follow_through','center_aim_error']},
  3: {'goal':'ฝึกให้ลูกขาวกระทบลูกเป้าตามเหลี่ยมที่เลือก ไม่ใช้การลงหลุมเป็นเกณฑ์',
      'camera':'กล้องด้านบนเห็นพื้นที่ฝึกบนโต๊ะที่สอบเทียบแล้ว สำหรับ HSV ใช้ลูกขาวหนึ่งลูกและลูกแดงหนึ่งลูก',
      'steps':['สอบเทียบพิกัดบนโต๊ะและรัศมีลูกให้ใช้หน่วยเดียวกัน','จัดลูกขาวกับลูกเป้า และเลือกเต็มใบ 3/4 1/2 หรือ 1/4','เริ่มบันทึกก่อนแทง เคลื่อนลูกขาวเข้าหาลูกเป้า แล้วจบหลังการกระทบ','ตรวจเหตุการณ์และค่าประมาณเหลี่ยม ค่าที่ขาดหายให้ทำซ้ำโดยไม่แทนเป็นคะแนน'],
      'metrics':['contact_fraction','fraction_error']},
}

LABELS = {
 'elbow_mean':'มุมศอกเฉลี่ย', 'elbow_sd':'ความแปรปรวนของมุมศอก (SD)',
 'torso_mean':'มุมลำตัวเฉลี่ย', 'torso_sd':'ความแปรปรวนของมุมลำตัว (SD)',
 'stance_mean':'ระยะข้อเท้าเฉลี่ย', 'stance_sd':'ความแปรปรวนของระยะข้อเท้า (SD)',
 'head_mean':'การเคลื่อนศีรษะเฉลี่ย', 'head_max':'การเคลื่อนศีรษะสูงสุด',
 'bridge_mean':'การเคลื่อนสะพานมือเฉลี่ย','bridge_max':'การเคลื่อนสะพานมือสูงสุด',
 'cue_deviation_mean':'ความเบี่ยงเบนคิวเฉลี่ย','cue_deviation_max':'ความเบี่ยงเบนคิวสูงสุด',
 'follow_through':'ระยะส่งคิวหลังลูกเริ่มเคลื่อน (ค่าประมาณ)',
 'center_aim_error':'ระยะห่างแนวคิวจากศูนย์กลางลูก (ค่าประมาณแนวเล็ง)',
 'contact_fraction':'เหลี่ยมที่ประมาณได้','fraction_error':'ความคลาดเคลื่อนจากเหลี่ยมที่กำหนด',
}

def feedback(metrics, rules=None):
    """Explain observations against user-selected rules without inventing advice."""
    result=[]
    for code, rule in (rules or {}).items():
        value=metrics.get(code)
        if value is None:
            result.append({'metric':code,'level':'missing','message':f'{LABELS.get(code,code)}: ข้อมูลไม่พอ ตรวจภาพ กล้องและช่วงบันทึกแล้วทดลองใหม่'})
        elif ('min' in rule and value<rule['min']) or ('max' in rule and value>rule['max']):
            result.append({'metric':code,'level':'review','message':f'{LABELS.get(code,code)}อยู่นอกเกณฑ์รุ่นนี้ ทบทวนการเคลื่อนไหวและตำแหน่งกล้องก่อนฝึกซ้ำ'})
        else:
            result.append({'metric':code,'level':'within','message':f'{LABELS.get(code,code)}อยู่ในเกณฑ์รุ่นนี้'})
    if not rules:
        result.append({'metric':None,'level':'info','message':'ยังไม่มีเกณฑ์ยืนยัน ใช้ทบทวนค่าที่วัดได้เท่านั้น'})
    if metrics.get('follow_through') is not None or metrics.get('center_aim_error') is not None:
        result.append({'metric':None,'level':'info','message':'ค่าการส่งคิวใช้ marker และเวลาลูกเริ่มเคลื่อนเป็นตัวแทน ไม่ใช่การตรวจจุดสัมผัสจริงบนลูกขาว'})
    return result
