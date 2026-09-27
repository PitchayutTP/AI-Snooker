"""Evaluate manually matched predictions without inventing labels.

CSV columns: reference,prediction,reference_event,predicted_event
Numeric blanks are missing. Event values: 0/1/blank. Events must already
have been matched with the documented temporal/spatial tolerance.
"""
import csv
import json
import math
import statistics
import sys

def evaluate_rows(rows):
    errors=[]; tp=fp=fn=tn=0; event_missing=0
    for r in rows:
        try:
            a,b=float(r['reference']),float(r['prediction'])
            if math.isfinite(a) and math.isfinite(b): errors.append(abs(a-b))
        except (ValueError,KeyError): pass
        a,b=r.get('reference_event'),r.get('predicted_event')
        if a not in ['0','1'] or b not in ['0','1']:
            event_missing+=1; continue
        tp+=a=='1' and b=='1'; fp+=a=='0' and b=='1'
        fn+=a=='1' and b=='0'; tn+=a=='0' and b=='0'
    return {'n_total':len(rows),'n_numeric_valid':len(errors),'n_numeric_missing':len(rows)-len(errors),
            'mae':statistics.mean(errors) if errors else None,
            'tp':tp,'fp':fp,'fn':fn,'tn':tn,'event_missing':event_missing,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None}

if __name__=='__main__':
    with open(sys.argv[1],encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    print(json.dumps(evaluate_rows(rows),indent=2))
