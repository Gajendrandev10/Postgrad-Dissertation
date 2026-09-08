"""Descriptive dissertation calculations only; does not change saved runs."""
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[3] / "Code"
RUN = ROOT / '06_Results/runs/local_only_pqc_20260906'
OUT = Path(__file__).resolve().parents[3] / "Documentation/02_Dissertation/support"

def rows(name):
    with (RUN / name).open(newline='') as f:
        return list(csv.DictReader(f))

def confusion(records, prediction):
    counts = dict(TN=0, FP=0, FN=0, TP=0)
    for r in records:
        y, p = int(r['label']), int(prediction(r))
        counts[('TN', 'FP', 'FN', 'TP')[2*y+p]] += 1
    return counts

def wilson(k, n):
    z = 1.959963984540054
    p = k/n
    centre = (p+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [centre-half, centre+half]

def quantile(values, p):
    v = sorted(values)
    index = (len(v)-1)*p
    lo = int(index)
    return v[lo]+(v[min(lo+1,len(v)-1)]-v[lo])*(index-lo)

def main():
    pred=rows('uav_test_predictions.csv')
    bench=rows('pqc_benchmark_results.csv')
    alerts=rows('soc_alerts.csv')
    manifest=json.loads((RUN/'run_manifest.json').read_text())
    data={
        'scope':'Post hoc descriptive calculations from the preserved run; no retraining or new observations.',
        'source_run':str(RUN.relative_to(ROOT)),
        'outputs_match_manifest':{k:hashlib.sha256((RUN/k).read_bytes()).hexdigest()==v for k,v in manifest['outputs'].items()},
        'inputs_match_manifest':{k:hashlib.sha256((ROOT/k.replace('UAV_OMNeT_AI_SOC_PQC_Colab_FIXED.ipynb', 'uav_soc_pqc_analysis.ipynb').replace('requirements-analysis.txt', 'requirements_analysis.txt')).read_bytes()).hexdigest()==v for k,v in manifest['inputs'].items()},
        'confusion':{},
        'pqc':{},
        'wilson_95_illustrative':{'attack_recall_8_of_8':wilson(8,8),'rf_accuracy_75_of_75':wilson(75,75)},
        'severity_counts':{k:sum(r['severity']==k for r in alerts) for k in sorted({r['severity'] for r in alerts})},
        'false_alert_ids':[int(r['source_record_id']) for r in alerts if int(r['ground_truth_label'])==0],
    }
    policies={
        'Isolation Forest':lambda r:int(r['isolation_forest_prediction']),
        'Random Forest':lambda r:int(r['random_forest_prediction']),
        'Union':lambda r:int(r['isolation_forest_prediction']) or int(r['random_forest_prediction']),
        'Intersection (post hoc)':lambda r:int(r['isolation_forest_prediction']) and int(r['random_forest_prediction']),
        'Always normal (reference)':lambda r:0,
        'Latency > 90 (generator-informed diagnostic)':lambda r:float(r['avg_latency_ms'])>90,
    }
    for name,fn in policies.items(): data['confusion'][name]=confusion(pred,fn)
    for k in ['keygen_ms','encapsulation_ms','decapsulation_ms','aes_encrypt_ms','aes_decrypt_ms']:
        v=[float(r[k]) for r in bench]
        data['pqc'][k]={'mean':statistics.mean(v),'median':statistics.median(v),'p95':quantile(v,.95),'max':max(v)}
    data['sum_of_timed_stage_means_ms']=sum(v['mean'] for v in data['pqc'].values())
    data['message_sizes']={k:sorted({int(r[k]) for r in bench}) for k in ['public_key_bytes','kem_ciphertext_bytes','shared_secret_bytes','plaintext_bytes','encrypted_message_bytes']}
    assert all(data['outputs_match_manifest'].values())
    assert data['confusion']['Isolation Forest']==dict(TN=62,FP=5,FN=0,TP=8)
    assert data['confusion']['Random Forest']==dict(TN=67,FP=0,FN=0,TP=8)
    assert len(pred)==75 and len(bench)==200 and len(alerts)==13
    (OUT/'evidence_analysis.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))

if __name__=='__main__': main()
