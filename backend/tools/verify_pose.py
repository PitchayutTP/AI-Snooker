"""Offline checks for bent-stance pose visibility, with no camera or database."""
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.pose import measure_pose


class PoseChecks(unittest.TestCase):
    def points(self):
        return [SimpleNamespace(x=.1+i*.02, y=.2+i*.01, visibility=.95, presence=.95)
                for i in range(33)]

    def measure(self, points, hand='RIGHT', threshold=.5):
        return measure_pose(points, 1280, 720, hand, threshold, 1)

    def test_far_shoulder_can_be_hidden_for_either_hand(self):
        for hand, hidden in [('RIGHT', 11), ('LEFT', 12)]:
            with self.subTest(hand=hand):
                points=self.points();points[hidden].visibility=0
                measured, visible, issues=self.measure(points,hand)
                self.assertEqual(issues, [])
                self.assertNotIn(hidden, visible)
                self.assertTrue(all(measured[key] is not None for key in ['elbow','knee_shooting']))

    def test_moderate_current_detection_is_not_a_cached_joint(self):
        points=self.points();points[12].visibility=.6
        self.assertIsNotNone(self.measure(points)[0]['elbow'])
        self.assertIsNone(self.measure(points,threshold=.7)[0]['elbow'])
        points[12].visibility=.2
        measured, visible, issues=self.measure(points)
        self.assertIsNone(measured['elbow'])
        self.assertNotIn(12,visible)
        self.assertIn('ยังตรวจไม่พบไหล่ฝั่งถือคิวชัดเจน',issues)

    def test_head_and_bridge_missing_do_not_block_m1_but_still_block_m2(self):
        points=self.points()
        for index in [0,11,13,15]:points[index].presence=0
        measured, _, issues=self.measure(points)
        self.assertEqual(issues,[])
        self.assertTrue(all(measured[key] is not None for key in ['elbow','knee_shooting']))
        _, _, issues=measure_pose(points,1280,720,'RIGHT',.5,2)
        self.assertIn('ยังตรวจไม่พบศีรษะชัดเจน',issues)
        self.assertIn('ยังตรวจไม่พบข้อมือสะพานมือชัดเจน',issues)

    def test_knees_follow_shooting_hand(self):
        points=self.points()
        for index,xy in {24:(.7,.4),26:(.7,.6),28:(.7,.8),
                         23:(.3,.4),25:(.2,.6),27:(.3,.8)}.items():
            points[index].x,points[index].y=xy
        right,_,_=self.measure(points)
        left,_,_=self.measure(points,'LEFT')
        self.assertAlmostEqual(right['knee_shooting'],180)
        self.assertLess(left['knee_shooting'],180)
        self.assertNotIn('knee_support',right);self.assertNotIn('knee_support',left)

    def test_missing_knee_is_not_a_straight_leg(self):
        points=self.points();points[26].visibility=0
        measured,_,issues=self.measure(points)
        self.assertIsNone(measured['knee_shooting'])
        self.assertIn('ยังตรวจไม่พบเข่าฝั่งแทงชัดเจน',issues)

    def test_range_summary_does_not_hide_bad_posture_in_mean(self):
        from app.metrics import summarize,evaluate
        from app.criteria_templates import m1_timed_template
        definition=m1_timed_template();definition['approved']=True
        rows=[{'t':i*.1,'elbow':90.,'knee_shooting':170.} for i in range(151)]
        self.assertEqual(evaluate(summarize(rows),definition,14)[0],'PASS')
        rows[80]['elbow']=110.
        measured=summarize(rows)
        self.assertLess(measured['elbow_mean'],100.)
        self.assertEqual(evaluate(measured,definition,14)[0],'FAIL')
        for row in rows: row['knee_shooting']=None
        self.assertEqual(evaluate(summarize(rows),definition,14)[0],'INVALID')

    def test_support_leg_is_not_required_for_either_hand(self):
        for hand,indices in [('RIGHT',[23,25,27]),('LEFT',[24,26,28])]:
            with self.subTest(hand=hand):
                points=self.points()
                for index in indices:points[index].visibility=0
                measured,visible,issues=self.measure(points,hand)
                self.assertEqual(issues,[])
                self.assertIsNotNone(measured['elbow']);self.assertIsNotNone(measured['knee_shooting'])
                self.assertTrue(all(index not in visible for index in indices))

    def test_small_projected_arm_is_rejected_with_diagnostics(self):
        points=self.points();points[14].x=points[12].x+.001;points[14].y=points[12].y+.001
        measured,_,issues=self.measure(points)
        self.assertIsNone(measured['elbow'])
        self.assertFalse(measured['elbow_detail']['valid'])
        self.assertLess(measured['elbow_detail']['upper_arm_px'],measured['elbow_detail']['minimum_segment_px'])
        self.assertTrue(any('ซ้อนกัน' in issue for issue in issues))

    def test_elbow_preview_is_bounded_stable_and_removed_when_joints_missing(self):
        import numpy as np
        from app.elbow_preview import ElbowPreview
        preview=ElbowPreview();frame=np.zeros((720,1280,3),dtype=np.uint8)
        points={12:[400,200],14:[500,300],16:[600,200]}
        a=preview.render(frame,points,'RIGHT')
        b=preview.render(frame,{index:[xy[0]+1,xy[1]] for index,xy in points.items()},'RIGHT')
        self.assertEqual(a['source_box'],b['source_box'])
        self.assertTrue(a['image'])
        left,top,right,bottom=a['source_box']
        self.assertTrue(0<=left<right<=1280 and 0<=top<bottom<=720)
        self.assertIsNone(preview.render(frame,{12:[400,200]},'RIGHT'))

    def test_invalid_or_outside_frame_points_are_missing(self):
        for field, value in [('x',math.nan),('x',1.1),('presence',None),('y',-.1)]:
            with self.subTest(field=field,value=value):
                points=self.points();setattr(points[12],field,value)
                self.assertIsNone(self.measure(points)[0]['elbow'])

    def test_m1_smoothing_reduces_jitter_without_filling_missing_points(self):
        from app.smoothing import MovingAverage,LandmarkAverage
        import statistics
        angles=MovingAverage(7,.25);overlay=LandmarkAverage(7,.25)
        raw=[];filtered=[]
        for i in range(30):
            value=90+(4 if i%2 else -4)
            row=angles.apply({'t':i/30,'elbow':value,'knee_shooting':170+(2 if i%2 else -2)})
            self.assertEqual(row['raw_measurements']['elbow'],value)
            raw.append(value);filtered.append(row['elbow'])
            overlay.apply({12:[value,20]},i/30)
        self.assertLess(statistics.stdev(filtered[7:]),statistics.stdev(raw[7:]))
        self.assertIsNone(angles.apply({'t':1,'elbow':None})['elbow'])
        self.assertEqual(overlay.apply({},1),{})
        self.assertEqual(overlay.apply({12:[100,40]},1.03),{12:[100,40]})
        self.assertEqual(overlay.apply({12:[200,80]},2),{12:[200,80]})

    def test_robust_filter_rejects_spike_but_tracks_sustained_change(self):
        from app.smoothing import MovingAverage,LandmarkAverage
        robust=MovingAverage(5,.25,'MEDIAN_EMA',.35)
        overlay=LandmarkAverage(5,.25,'MEDIAN_EMA',.35)
        for i in range(12):
            value=150 if i==8 else 90
            row=robust.apply({'t':i/30,'elbow':value,'knee_shooting':170,'knee_support':155})
            point=overlay.apply({12:[value,20]},i/30)
            self.assertEqual(row['raw_measurements']['elbow'],value)
            self.assertAlmostEqual(row['elbow'],90)
            self.assertAlmostEqual(point[12][0],90)
        for i in range(12,90):
            row=robust.apply({'t':i/30,'elbow':110})
        self.assertGreater(row['elbow'],109)
        self.assertLessEqual(row['elbow'],110)
        self.assertIsNone(robust.apply({'t':3,'elbow':None})['elbow'])
        self.assertEqual(robust.apply({'t':3.03,'elbow':75})['elbow'],75)
        self.assertEqual(robust.apply({'t':4,'elbow':120})['elbow'],120)
        self.assertEqual(overlay.apply({},3),{})
        self.assertEqual(overlay.apply({12:[50,40]},3.03),{12:[50,40]})

    def test_robust_filter_is_quieter_than_previous_seven_frame_average(self):
        import statistics
        from app.smoothing import MovingAverage
        old=MovingAverage(7,.25);new=MovingAverage(5,.25,'MEDIAN_EMA',.35)
        a=[];b=[]
        for i in range(150):
            sample={'t':i/30,'elbow':90+4*math.sin(i*.65)+(15 if i%23==0 else 0)}
            a.append(old.apply(dict(sample))['elbow'])
            b.append(new.apply(dict(sample))['elbow'])
        self.assertLess(statistics.stdev(b[30:]),statistics.stdev(a[30:]))

    def test_strong_preset_is_quieter_and_still_tracks_a_real_change(self):
        import statistics
        from app.smoothing import MovingAverage
        previous=MovingAverage(5,.25,'MEDIAN_EMA',.35)
        strong=MovingAverage(15,.25,'MEDIAN_EMA',.8)
        a=[];b=[]
        for i in range(180):
            sample={'t':i/30,'elbow':90+5*math.sin(i*.25)}
            a.append(previous.apply(dict(sample))['elbow'])
            b.append(strong.apply(dict(sample))['elbow'])
        self.assertLess(statistics.stdev(b[60:]),statistics.stdev(a[60:]))
        for i in range(180,300):row=strong.apply({'t':i/30,'elbow':110})
        self.assertGreater(row['elbow'],109)
        self.assertIsNone(strong.apply({'t':10,'elbow':None})['elbow'])

    def test_display_hold_preserves_full_precision_measurements(self):
        from app.smoothing import MovingAverage
        readout=MovingAverage(1,.75,display_deadband=.25)
        first=readout.apply({'t':0,'elbow':99.9})
        next_frame=readout.apply({'t':.1,'elbow':100.1})
        self.assertEqual(first['angle_display']['elbow'],99.9)
        self.assertEqual(next_frame['angle_display']['elbow'],99.9)
        self.assertEqual(next_frame['elbow'],100.1)
        self.assertEqual(next_frame['raw_measurements']['elbow'],100.1)
        from app.metrics import evaluate
        self.assertEqual(evaluate({'elbow_max':next_frame['elbow']},
            {'approved':True,'rules':{'elbow_max':{'max':100}}})[0],'FAIL')
        changed=readout.apply({'t':.2,'elbow':100.3})
        self.assertEqual(changed['angle_display']['elbow'],100.3)
        self.assertIsNone(readout.apply({'t':.3,'elbow':None})['angle_display']['elbow'])
        self.assertEqual(readout.apply({'t':.4,'elbow':90})['angle_display']['elbow'],90)

    def test_overlay_holds_small_motion_but_cumulative_motion_is_visible(self):
        from app.smoothing import LandmarkAverage
        overlay=LandmarkAverage(1,.75,display_deadband=1.5)
        self.assertEqual(overlay.apply({12:[10,20]},0),{12:[10,20]})
        for i in range(1,4):
            self.assertEqual(overlay.apply({12:[10+i*.4,20]},i*.1),{12:[10,20]})
        self.assertAlmostEqual(overlay.apply({12:[11.6,20]},.4)[12][0],11.6)
        self.assertEqual(overlay.apply({},.5),{})
        self.assertEqual(overlay.apply({12:[30,20]},.6),{12:[30,20]})

    def test_slow_pose_frames_do_not_reset_filter_until_configured_gap(self):
        from app.smoothing import MovingAverage,LandmarkAverage
        angles=MovingAverage(15,.75,'MEDIAN_EMA',.8)
        points=LandmarkAverage(15,.75,'MEDIAN_EMA',.8)
        angles.apply({'t':0,'elbow':90});points.apply({12:[90,20]},0)
        self.assertLess(angles.apply({'t':.4,'elbow':110})['elbow'],110)
        self.assertLess(points.apply({12:[110,20]},.4)[12][0],110)
        self.assertEqual(angles.apply({'t':2,'elbow':120})['elbow'],120)
        self.assertEqual(points.apply({12:[120,20]},2)[12][0],120)


if __name__=='__main__':
    unittest.main(verbosity=2)
