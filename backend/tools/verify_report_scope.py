"""Offline checks for the report-aligned M1-M3 additions. No database or camera."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from app.protocol import protocol_result,assessment_problem
from app.smoothing import MovingAverage
from app.metrics import data_quality
from tools.evaluate_trial import detection_report,tracking_report,measurement_report
from tools.prepare_dataset import prepare


class ReportScopeChecks(unittest.TestCase):
    def definition(self):
        return {'approved':True,'rules':{'elbow_mean':{'min':80,'max':100}},
                'protocol':{'required_valid_attempts':4,'minimum_pass_rate':.75,'rationale':'unit test only'}}

    def test_protocol_excludes_invalid_and_waits_for_finish(self):
        counts={'PASS':3,'FAIL':1,'INVALID':2,'ABORTED':1}
        config={'mode':'LIVE','purpose':'ASSESSMENT'}
        ready=protocol_result(counts,self.definition(),config,'IN_PROGRESS')
        self.assertEqual(ready['status'],'READY_TO_FINISH');self.assertEqual(ready['remaining'],0)
        final=protocol_result(counts,self.definition(),config,'COMPLETED')
        self.assertEqual(final['status'],'PASS');self.assertEqual(final['pass_rate'],.75)
        self.assertEqual(final['valid_attempts'],4)

    def test_protocol_incomplete_fail_and_abort(self):
        config={'mode':'LIVE','purpose':'ASSESSMENT'}
        self.assertEqual(protocol_result({'PASS':1,'INVALID':20},self.definition(),config,'COMPLETED')['status'],'INCOMPLETE')
        self.assertEqual(protocol_result({'PASS':2,'FAIL':2},self.definition(),config,'COMPLETED')['status'],'FAIL')
        self.assertEqual(protocol_result({'PASS':4},self.definition(),config,'ABORTED')['status'],'ABORTED')

    def test_pilot_and_demo_never_claim_round_pass(self):
        self.assertEqual(protocol_result({'PASS':4},self.definition(),{'mode':'LIVE'},'COMPLETED')['status'],'PILOT')
        self.assertEqual(protocol_result({'PASS':4},self.definition(),{'mode':'DEMO','purpose':'ASSESSMENT'},'COMPLETED')['status'],'INVALID')

    def test_assessment_preconditions(self):
        definition=self.definition()
        self.assertIsNone(assessment_problem(definition,{'mode':'LIVE','required':['side']}))
        self.assertIsNotNone(assessment_problem(definition,{'mode':'DEMO'}))
        self.assertIsNotNone(assessment_problem({**definition,'approved':False},{'mode':'LIVE'}))
        self.assertIsNotNone(assessment_problem(definition,{'mode':'LIVE','required':['top'],'ball_detector':'HSV'}))
        self.assertIsNotNone(assessment_problem(definition,{'mode':'LIVE','required':['top'],'ball_detector':'YOLO'}))
        self.assertIsNone(assessment_problem(definition,{'mode':'LIVE','required':['top'],'ball_detector':'YOLO','calibration_image_size':[1280,720]}))

    def test_moving_average_missing_and_gap(self):
        filter=MovingAverage(3,.25)
        a=filter.apply({'t':0,'head':[0,0],'elbow':80,'balls':[{'xy':[0,0]}]})
        b=filter.apply({'t':.1,'head':[6,0],'elbow':100,'balls':[{'xy':[20,0]}]})
        self.assertEqual(b['head'],[3,0]);self.assertEqual(b['elbow'],90)
        self.assertEqual(b['raw_measurements']['elbow'],100)
        self.assertEqual(b['balls'],[{'xy':[20,0]}]);self.assertGreater(b['estimated_smoothing_delay_ms'],0)
        self.assertIsNone(filter.apply({'t':.2,'head':None})['head'])
        self.assertEqual(filter.apply({'t':.3,'head':[9,0]})['head'],[9,0])
        self.assertEqual(filter.apply({'t':1,'head':[30,0]})['head'],[30,0])
        self.assertEqual(a['head'],[0,0])

    def test_detection_one_to_one_and_missing_predictions(self):
        ref={'frames':[{'frame_id':0,'objects':[{'class':'cue_ball','bbox':[0,0,10,10]}]}]}
        pred={'frames':[{'frame_id':0,'objects':[{'class':'cue_ball','bbox':[0,0,10,10],'confidence':.9},
                                              {'class':'cue_ball','bbox':[0,0,10,10],'confidence':.8}]}]}
        result=detection_report(ref,pred,.5,.5)
        self.assertEqual((result['tp'],result['fp'],result['fn']),(1,1,0));self.assertEqual(result['precision'],.5)
        result=detection_report(ref,{'frames':[]},.5,.5)
        self.assertEqual(result['fn'],1);self.assertIsNone(result['precision']);self.assertEqual(result['recall'],0)

    def test_tracking_id_switch_and_missing(self):
        ref={'unit':'pixel','frames':[{'frame_id':i,'objects':[{'class':'cue_ball','track_id':'white','xy':[i,0]}]} for i in range(4)]}
        pred=deepcopy(ref)
        pred['frames'][0]['objects'][0]['track_id']='first'
        pred['frames'][1]['objects'][0]['track_id']='second'
        pred['frames'][2]['objects']=[]
        pred['frames'][3]['objects'][0]['track_id']='third'
        result=tracking_report(ref,pred,2)
        self.assertEqual(result['id_switches'],1);self.assertEqual(result['missing_rate'],.25)
        self.assertEqual(result['mean_position_error'],0)
        with self.assertRaises(ValueError):tracking_report(ref,{**pred,'unit':'mm'},2)

    def test_measurements_keep_units_separate(self):
        rows=[{'metric':'head','unit':'pixel','reference':'10','prediction':'12'},
              {'metric':'head','unit':'pixel','reference':'','prediction':'20'},
              {'metric':'head','unit':'mm','reference':'10','prediction':'11'}]
        report=measurement_report(rows)['metrics']
        self.assertEqual(len(report),2);self.assertEqual(report[0]['mae'],2);self.assertEqual(report[0]['n_missing_pairs'],1)

    def test_quality_counts_only_active_measurements(self):
        report=data_quality([{'t':0,'elbow':90,'ready':True},{'t':.5,'elbow':90,'ready':True},
                             {'t':1,'elbow':None,'ready':False},{'t':1.5,'elbow':92,'ready':True}],.5)
        self.assertEqual(report['active_samples'],2);self.assertEqual(report['active_valid_counts']['elbow'],1)
        self.assertEqual(report['baseline_valid_counts']['elbow'],2);self.assertEqual(report['effective_capture_fps'],2)

    def test_group_split_and_bad_labels(self):
        import cv2
        import numpy as np
        parent=BACKEND.parent/'data/offline-checks';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            root=Path(folder);self.assertTrue(root.resolve().is_relative_to(parent.resolve()))
            rows=[]
            for i in range(6):
                image=root/f'{i}.jpg';label=root/f'{i}.txt'
                ok,encoded=cv2.imencode('.jpg',np.full((50,80,3),i*30,dtype=np.uint8));self.assertTrue(ok)
                image.write_bytes(encoded.tobytes());label.write_text('0 0.25 0.5 0.2 0.2\n1 0.75 0.5 0.2 0.2\n')
                rows.append({'image':image.name,'label':label.name,'group':f'session-{i//2}','split':''})
            manifest=root/'input.csv'
            with manifest.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=['image','label','group','split']);writer.writeheader();writer.writerows(rows)
            result=prepare(manifest,root/'dataset')
            groups={}
            for item in result['images']:groups.setdefault(item['group'],set()).add(item['split'])
            self.assertTrue(all(len(values)==1 for values in groups.values()))
            self.assertEqual(set(result['counts']),{'train','val','test'})
            with self.assertRaises(ValueError):prepare(manifest,root/'dataset')
            (root/'0.txt').write_text('0 2 0.5 0.2 0.2\n')
            with self.assertRaises(ValueError):prepare(manifest,root/'bad-dataset')

    def test_raw_recordings_and_path_boundary(self):
        import numpy as np
        from app import recordings
        parent=BACKEND.parent/'data/offline-checks';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(parent.resolve()))
            with patch.object(recordings,'RECORDINGS',Path(folder)/'recordings'):
                recorder=recordings.FrameRecorder(1,str(uuid4()),str(uuid4()))
                result=recorder.write({'top':np.zeros((20,30,3),dtype=np.uint8)},0)
                path=recordings.recorded_path(result['top'],1);self.assertTrue(path.is_file())
                with self.assertRaises(ValueError):recordings.recorded_path(result['top'],2)
                with self.assertRaises(ValueError):recordings.recorded_path('backend/app/main.py',1)
                with self.assertRaises(FileExistsError):recorder.write({'top':np.zeros((20,30,3),dtype=np.uint8)},0)


if __name__=='__main__':unittest.main(verbosity=2)
