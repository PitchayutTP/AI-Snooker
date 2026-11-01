"""Project-defined pilot thresholds, not universal snooker technique standards."""
M1_TEMPLATE_VERSION='m1-elbow-shooting-leg-8s-v10'


def m1_timed_template():
    result={'validation_scope':'PROTOTYPE','approved':False}
    result['source']='M1-ELBOW-LEGS-8S-PILOT-v10: ศอก 80–100° เข่าฝั่งแทง 160–180° ตามที่ผู้จัดทำเลือก ไม่ประเมินการก้มหรือคางกับคิว เป็นมุมฉายในภาพ ไม่ใช่ค่าสากล บันทึกประมาณ 8 วินาที เก็บฐาน 1 วินาที วัดอย่างน้อย 7 วินาที ใช้ Median 15 เฟรม + EMA 0.8 วินาทีกับมุมทั้งการแสดงและตัดสินต่ำสุด–สูงสุด รีเซ็ตตัวกรองเมื่อเฟรมห่างเกิน 0.75 วินาที เก็บค่าดิบไว้ตรวจสอบ ไม่เติมค่าที่หาย การกรองลดความสั่นแต่เพิ่มความล่าช้าและไม่รับรองความแม่นยำ ไม่บังคับขาฝั่งสะพานมือ จุดไหล่–ศอก–ข้อมือต้องแยกกันพอวัดมุมได้ เกณฑ์ความยาวส่วนแขนขั้นต่ำ max(6 px, 1.25% ของด้านสั้นภาพ) เป็นเกณฑ์คุณภาพนำร่อง ต้องตรวจนำร่อง'
    result['rules']={'elbow_min':{'min':80.},'elbow_max':{'max':100.},
        'knee_shooting_min':{'min':160.},'knee_shooting_max':{'max':180.}}
    result['minimum_active_seconds']=7.
    result['template_version']=M1_TEMPLATE_VERSION
    result['protocol']={'required_valid_attempts':1,'minimum_pass_rate':1.,
        'rationale':'หนึ่งครั้ง 8 วินาที ผ่านเมื่อมุมศอกและเข่าฝั่งแทงที่กรอง Median 15 เฟรม + EMA 0.8 วินาทีอยู่ในช่วงทุกข้อหลังฐาน ไม่ใช้ SD ข้อมูลไม่ครบไม่นับ ไม่ใช่มาตรฐานสากล'}
    return result


def training_template(module_id,fraction=None):
    if module_id==1:return m1_timed_template()
    plan={'required_valid_attempts':5,'minimum_pass_rate':.8,
          'rationale':'แผนต้นแบบที่ผู้จัดทำเลือก: ประเมินได้ 5 ครั้ง ผ่านอย่างน้อย 4 ครั้ง INVALID/ABORTED ไม่นับ ไม่ใช่มาตรฐานสากล'}
    if module_id==2:
        return {'validation_scope':'PROTOTYPE','template_version':'m2-full-v1','approved':False,
            'source':'M2-FULL-PROTOTYPE-v1: แทงตรงกึ่งกลางลูกขาว ไม่ตั้งใจใช้ไซด์ ใช้สองกล้อง; ตัวเลขเป็นเกณฑ์ตั้งต้นเชิงวิศวกรรม ต้องตรวจนำร่อง ไม่ใช่ค่าจากมาตรฐาน/หนังสือ; ระยะหารด้วยระยะมาร์กเกอร์สองจุดเฉลี่ยในช่วงฐาน จัดตำแหน่งมาร์กเกอร์และกล้องให้คงเดิม ค่าระยะเป็นสัดส่วนในภาพ ไม่ใช่มิลลิเมตรจริง',
            'rules':{'cue_deviation_ratio':{'max':.03},'head_motion_ratio':{'max':.03},
                     'bridge_motion_ratio':{'max':.03},'center_aim_ratio':{'max':.03},
                     'follow_through_ratio':{'min':.1}},
            'minimum_active_seconds':1.,'protocol':plan}
    if module_id==3:
        return {'validation_scope':'PROTOTYPE','template_version':'m3-contact-v1','approved':False,
            'source':f'M3-CONTACT-PROTOTYPE-v1: เหลี่ยมเป้าหมาย {fraction}; ยอมให้คลาดเคลื่อนสัมบูรณ์ไม่เกิน 0.10 ของสัดส่วนเต็มลูก (10 จุดเปอร์เซ็นต์ ไม่ใช่ 10% ของเป้าหมาย) ไม่พิจารณาลงหลุม ต้องพบหลักฐานกระทบจากการเคลื่อนลูกเป้า ตัวเลขเป็นเกณฑ์นำร่องของโครงงาน ไม่ใช่มาตรฐานสากล ต้องตรวจเทียบข้อมูลอ้างอิงก่อนใช้ผลวิจัย',
            'rules':{'fraction_error':{'max':.1}},'minimum_active_seconds':1.,'protocol':plan}
    raise ValueError('ยังไม่เปิดใช้เกณฑ์ของโมดูลนี้')
