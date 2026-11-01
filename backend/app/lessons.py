"""Prototype lessons: original diagrams/text, not copied book pages."""
LESSONS = {
  1: {'goal':'ทดลองตรวจเฉพาะช่วงมุมศอกและขาฝั่งแทงตามเกณฑ์ที่ผู้จัดทำเลือก',
      'camera':'กล้องด้านข้างเห็นไหล่ ศอก ข้อมือฝั่งแทง และสะโพก เข่า ข้อเท้าฝั่งแทง',
      'steps':['เลือกมือแทงและปรับกล้องให้เห็นแขนฝั่งแทงกับขาฝั่งแทง ไม่บังคับตรวจศีรษะหรือมือสะพาน','กดเริ่ม ระบบรอจุดครบต่อเนื่อง 1 วินาที เตรียมตัว 5 วินาทีแล้วบันทึกประมาณ 8 วินาที','คงศอก 80–100° เข่าฝั่งแทง 160–180°','ใช้มุมที่กรอง Median 15 เฟรม + EMA 0.8 วินาทีตรวจต่ำสุด–สูงสุดหลังฐาน 1 วินาที ช่วงวัดอย่างน้อย 7 วินาที ต้องอยู่ในช่วงทุกข้อ เก็บค่าดิบไว้ตรวจสอบ ไม่เติมจุดที่หาย ไม่ใช้ SD ไม่ประเมินการก้มหรือคางกับคิว ข้อมูลไม่ครบเป็นประเมินไม่ได้ ไม่ใช่มาตรฐานสากล'],
      'metrics':['elbow_mean','elbow_min','elbow_max',
                 'knee_shooting_mean','knee_shooting_min','knee_shooting_max']},
  2: {'goal':'สังเกตการส่งคิวเทียบแนวตั้งต้นและความนิ่งของศีรษะกับสะพานมือ',
      'camera':'กล้องด้านข้างเห็นแนวคิวและ marker สองสีที่ติดกับคิว ตำแหน่งแรกเป็น marker ด้านปลายคิว',
      'steps':['ใช้ลูกขาวหนึ่งลูก ไม่ต้องมีลูกแดงหรือแทงลงหลุม ตั้งกล้องข้างและบนพร้อมเลือกมาร์กเกอร์สองสี','เริ่มบันทึกแล้วนิ่งช่วงฐานอย่างน้อย 1 วินาที จากนั้นแทงตรงบริเวณกึ่งกลางลูกขาวโดยไม่ตั้งใจใช้ไซด์','ส่งคิวตามและคงท่าชั่วครู่ก่อนจบการบันทึก จัดลูกกลับตำแหน่งเดิมทุกครั้ง','ทำจนประเมินได้ 5 ครั้ง ผ่านอย่างน้อย 4 ครั้งแล้วจบรอบ ใช้เกณฑ์ต้นแบบที่ยังต้องตรวจนำร่อง'],
      'metrics':['cue_deviation_mean','cue_deviation_max','head_mean','head_max','bridge_mean','bridge_max','follow_through','center_aim_error','cue_deviation_ratio','head_motion_ratio','bridge_motion_ratio','center_aim_ratio','follow_through_ratio']},
  3: {'goal':'ฝึกให้ลูกขาวกระทบลูกเป้าตามเหลี่ยมที่เลือก ไม่ใช้การลงหลุมเป็นเกณฑ์',
      'camera':'กล้องด้านบนเห็นพื้นที่ฝึกบนโต๊ะที่สอบเทียบแล้ว สำหรับ HSV ใช้ลูกขาวหนึ่งลูกและลูกแดงหนึ่งลูก',
      'steps':['สอบเทียบพิกัดบนโต๊ะและรัศมีลูกให้ใช้หน่วยเดียวกัน','จัดลูกขาวกับลูกเป้า และเลือกเต็มใบ 3/4 1/2 หรือ 1/4','เริ่มบันทึกก่อนแทง เคลื่อนลูกขาวเข้าหาลูกเป้า แล้วจบหลังการกระทบ','ตรวจเหตุการณ์และค่าประมาณเหลี่ยม ค่าที่ขาดหายให้ทำซ้ำโดยไม่แทนเป็นคะแนน'],
      'metrics':['contact_fraction','fraction_error']},
}

LABELS = {
 **{f'{key}_{part}':label+suffix for key,label in
    [('elbow','มุมศอก'),('torso','มุมลำตัวกับแนวนอน'),('knee_shooting','มุมเข่าฝั่งแทง'),('knee_support','มุมเข่าฝั่งสะพานมือ')]
    for part,suffix in [('min','ต่ำสุด'),('max','สูงสุด'),('mean','เฉลี่ย'),('sd',' (SD)')]},
 'cue_deviation_ratio':'คิวเบี่ยงเบนสูงสุด/ระยะมาร์กเกอร์',
 'head_motion_ratio':'ศีรษะเคลื่อนสูงสุด/ระยะมาร์กเกอร์',
 'bridge_motion_ratio':'สะพานมือเคลื่อนสูงสุด/ระยะมาร์กเกอร์',
 'center_aim_ratio':'แนวเล็งคลาดเคลื่อน/ระยะมาร์กเกอร์ (ประมาณ)',
 'follow_through_ratio':'Follow-through/ระยะมาร์กเกอร์ (ประมาณ)',
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
