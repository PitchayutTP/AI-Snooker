"""Camera opening and unprocessed setup preview, shared with live capture."""
import base64
import time


def open_camera(cv2, source, config):
    source = int(source) if str(source).isdigit() else source
    backends = {'AUTO': cv2.CAP_ANY, 'DSHOW': cv2.CAP_DSHOW, 'MSMF': cv2.CAP_MSMF}
    cap = cv2.VideoCapture(source, backends[config.get('camera_backend', 'AUTO')])
    if not cap.isOpened():
        cap.release()
        raise ValueError(f'เปิดกล้อง {source} ไม่ได้ ตรวจหมายเลข สิทธิ์ และปิดแอปที่ใช้กล้องเดียวกัน')
    if isinstance(source, int):
        if config.get('camera_mjpeg', False):
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        for key, prop in [('capture_width', cv2.CAP_PROP_FRAME_WIDTH),
                          ('capture_height', cv2.CAP_PROP_FRAME_HEIGHT), ('capture_fps', cv2.CAP_PROP_FPS)]:
            cap.set(prop, config.get(key, {'capture_width':1280,'capture_height':720,'capture_fps':30}[key]))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def encode_image(cv2, frame, quality=75):
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(encoded).decode('ascii') if ok else None


class PreviewSource:
    """Full resolution, no model, calibration or training evaluation required."""
    def __init__(self, config):
        import cv2
        self.cv2 = cv2
        self.camera = config['preview_camera']
        self.cap = open_camera(cv2, config[self.camera+'_source'], config)

    def read(self):
        started = time.monotonic()
        epoch = time.time()*1000
        ok, image = self.cap.read()
        if not ok:
            return {'ready':False,'error':'กล้องไม่ส่งภาพ','image':None}
        return {'t':started,'capture_epoch_ms':epoch,'source':'LIVE','ready':False,
                'preview_camera':self.camera,'preview_only':True,'balls':[],
                'image':encode_image(self.cv2,image),
                'image_size':[image.shape[1],image.shape[0]],
                'readiness_issues':['โหมดดูภาพสำหรับตั้งค่า กดตรวจความพร้อมอีกครั้งหลังตั้งค่าเสร็จ'],
                'error':None,'processing_ms':(time.monotonic()-started)*1000}

    def close(self):
        self.cap.release()
