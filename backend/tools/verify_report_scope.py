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
from app.metrics import data_quality,evaluate
from app.criteria_templates import m1_timed_template,training_template
from tools.evaluate_trial import detection_report,tracking_report,measurement_report
from tools.prepare_dataset import prepare


class ReportScopeChecks(unittest.TestCase):
    def test_m2_complete_normalized_criteria(self):
        from app.vision import delivery_ratios
        definition=training_template(2);definition['approved']=True
        samples=[{'t':i*.1,'cue':[[100,50],[0,50]]} for i in range(11)]
        raw={'cue_deviation_max':3,'head_max':3,'bridge_max':3,'center_aim_error':3,'follow_through':10}
        ratios=delivery_ratios(samples,1,raw,{})
        self.assertEqual(evaluate(ratios,definition,1)[0],'PASS')
        scaled=[{**s,'cue':[[x*2,y*2] for x,y in s['cue']]} for s in samples]
        self.assertEqual(ratios,delivery_ratios(scaled,1,{k:v*2 for k,v in raw.items()},{}))
        self.assertEqual(evaluate({**ratios,'follow_through_ratio':.09},definition,1)[0],'FAIL')
        self.assertEqual(evaluate({**ratios,'center_aim_ratio':None},definition,1)[0],'INVALID')
        self.assertTrue(all(value is None for value in delivery_ratios([],1,raw,{}).values()))
        config={'mode':'LIVE','purpose':'ASSESSMENT','required':['side','top'],'ball_detector':'HSV','calibration_image_size':[1280,720],'delivery_ball_timing':True,'side_ball_center':[100,50]}
        self.assertIsNone(assessment_problem(definition,config))
        self.assertIsNotNone(assessment_problem(definition,{**config,'delivery_ball_timing':False}))
        self.assertIsNotNone(assessment_problem(definition,{**config,'side_ball_center':None}))
        self.assertIsNotNone(assessment_problem({**definition,'validation_scope':'REPORT'},config))
        self.assertEqual(protocol_result({'PASS':4,'FAIL':1,'INVALID':10},definition,config,'COMPLETED')['status'],'PASS')
        self.assertEqual(protocol_result({'PASS':3,'FAIL':2},definition,config,'COMPLETED')['status'],'FAIL')

    def test_m3_fraction_thresholds_and_prototype_scope(self):
        for fraction in [1.,.75,.5,.25]:
            definition=training_template(3,fraction);definition['approved']=True
            self.assertEqual(evaluate({'fraction_error':.1},definition,1)[0],'PASS')
            self.assertEqual(evaluate({'fraction_error':.1001},definition,1)[0],'FAIL')
            self.assertEqual(evaluate({'fraction_error':None},definition,1)[0],'INVALID')
            config={'mode':'LIVE','required':['top'],'ball_detector':'HSV','calibration_image_size':[1280,720]}
            self.assertIsNone(assessment_problem(definition,config))
            self.assertIsNotNone(assessment_problem(definition,{**config,'calibration_image_size':[]}))

    def test_completion_signatures_and_latest_result(self):
        from app.completion import latest_assessment,completion_signature
        base={'exercise_id':3,'status':'COMPLETED','mode':'LIVE','started_at':'2026-01-01',
              'criteria':training_template(3,1.),'config':{'exercise_id':3,'ball_detector':'HSV','table_size':[3569,1778]},
              'protocol_result':{'purpose':'ASSESSMENT','status':'PASS'}}
        other=deepcopy(base);other['exercise_id']=4;other['config']['exercise_id']=4;other['criteria']['source']='different fraction'
        self.assertEqual(completion_signature(base),completion_signature(other))
        other['config']['ball_detector']='YOLO'
        self.assertNotEqual(completion_signature(base),completion_signature(other))
        failed=deepcopy(base);failed['started_at']='2026-01-02';failed['protocol_result']['status']='FAIL'
        self.assertEqual(latest_assessment([failed,base])['latest_assessment_status'],'FAIL')
        failed['status']='ABORTED'
        self.assertEqual(latest_assessment([failed,base])['latest_assessment_status'],'PASS')

    def test_timed_m1_template(self):
        definition=m1_timed_template();definition['approved']=True
        values={'elbow_min':80,'elbow_max':100,'knee_shooting_min':160,'knee_shooting_max':180}
        self.assertEqual(evaluate(values,definition,6.99)[0],'INVALID')
        self.assertEqual(evaluate(values,definition,7)[0],'PASS')
        self.assertNotIn('elbow_sd',definition['rules'])
        self.assertNotIn('torso_min',definition['rules'])
        self.assertNotIn('torso_max',definition['rules'])
        self.assertNotIn('knee_support_min',definition['rules'])
        self.assertNotIn('knee_support_max',definition['rules'])
        for key in values:
            bad=values[key] + (-.01 if key.endswith('_min') else .01)
            self.assertEqual(evaluate({**values,key:bad},definition,7)[0],'FAIL',key)
            self.assertEqual(evaluate({**values,key:None},definition,7)[0],'INVALID',key)
        config={'mode':'LIVE','m1_auto_seconds':8,'baseline_seconds':1,'smoothing_window':15,'smoothing_method':'MEDIAN_EMA','smoothing_tau_seconds':.8,'smoothing_max_gap_s':.75,'smoothing_for_evaluation':True}
        self.assertIsNone(assessment_problem(definition,config))
        self.assertIsNotNone(assessment_problem(definition,{**config,'smoothing_for_evaluation':False}))
        self.assertIsNotNone(assessment_problem(definition,{**config,'smoothing_method':'MEAN'}))
        self.assertIsNotNone(assessment_problem(definition,{**config,'smoothing_max_gap_s':.25}))
        self.assertIsNotNone(assessment_problem(definition,{**config,'m1_auto_seconds':15}))
        config={'mode':'LIVE','purpose':'ASSESSMENT'}
        self.assertEqual(protocol_result({'PASS':1},definition,config,'COMPLETED')['status'],'PASS')
        self.assertEqual(protocol_result({'FAIL':1},definition,config,'COMPLETED')['status'],'FAIL')

    def test_runtime_stops_timed_m1_without_frontend(self):
        from app.runtime import Runtime
        class Source:
            def __init__(self,config): self.t=-1
            def read(self):
                self.t+=1
                return {'t':self.t,'source':'LIVE','ready':True,'error':'test end' if self.t==20 else None}
            def close(self): pass
        instance=Runtime()
        with patch('app.runtime.LiveSource',Source):
            # Hold the lock until the attempt is armed so the first sample is recorded.
            with instance.lock:
                instance.start({'mode':'LIVE','m1_auto_seconds':8})
                instance.begin('test-attempt')
            instance.thread.join(timeout=3)
        self.assertFalse(instance.thread.is_alive())
        self.assertEqual(len(instance.samples),9)
        self.assertEqual(instance.samples[-1]['t']-instance.samples[0]['t'],8)
        self.assertFalse(instance.collecting)
        self.assertTrue(instance.recording_limit_reached)
        self.assertEqual(instance.snapshot()['attempt_elapsed_s'],8)
        instance.stop()

    def test_retired_m1_criteria_are_not_available_for_new_training(self):
        for version in ['m1-stability-v1','m1-posture-v2','m1-elbow-legs-8s-v9']:
            old={'approved':True,'template_version':version,'rules':{'elbow_sd':{'max':5}},
                 'protocol':{'required_valid_attempts':1,'minimum_pass_rate':1}}
            self.assertIsNotNone(assessment_problem(old,{'mode':'LIVE'}))
            # Completed history uses its saved definition, without reopening training.
            self.assertEqual(protocol_result({'PASS':1},old,{'mode':'LIVE','purpose':'ASSESSMENT'},'COMPLETED')['status'],'PASS')

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
