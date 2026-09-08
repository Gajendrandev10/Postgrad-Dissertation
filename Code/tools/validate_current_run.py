#!/usr/bin/env python3
"""Validate current-run provenance, source rows, splits, metrics and SOC exports."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ['packet_size', 'avg_latency_ms', 'packet_loss_pct', 'throughput']
COLUMNS = ['source_record_id', 'simulation_time', 'uav_name', 'uav_id', *FEATURES, 'label', 'attack_type']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal_number(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12)


def auc(truth, scores):
    positives = [s for y, s in zip(truth, scores) if y == 1]
    negatives = [s for y, s in zip(truth, scores) if y == 0]
    return sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives) / (len(positives) * len(negatives))


def validate_run(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    for path, expected in manifest['inputs'].items():
        require(sha(ROOT / path.replace('UAV_OMNeT_AI_SOC_PQC_Colab_FIXED.ipynb', 'uav_soc_pqc_analysis.ipynb').replace('requirements-analysis.txt', 'requirements_analysis.txt')) == expected, 'Input changed since execution: ' + path)
    for path, expected in manifest['outputs'].items():
        require(sha(directory / path) == expected, 'Output changed since execution: ' + path)
    source = ROOT / '01_OMNeT_Simulation/UAV_SOC_Project/simulations/uav_traffic.csv'
    _, raw = read_csv(source)
    sent = {i: row for i, row in enumerate(raw) if row['Event'] == 'Send'}
    headers, data = read_csv(directory / 'omnet_uav_ai_dataset.csv')
    require(headers == COLUMNS, 'Current dataset schema differs from notebook schema')
    require(len(raw) == 494 and len(sent) == len(data) == 247, 'Current dataset must contain exactly 247 Send records')
    ids = [int(r['source_record_id']) for r in data]
    require(len(set(ids)) == len(ids) and set(ids) == set(sent), 'Prepared rows must map one-to-one to raw Send records')
    mapping = {name: i + 1 for i, name in enumerate(sorted({r['UAV'] for r in sent.values()}))}
    raw_names = {'simulation_time': 'Time', 'packet_size': 'PacketSize', 'avg_latency_ms': 'Latency',
                 'packet_loss_pct': 'PacketLoss', 'throughput': 'Throughput'}
    for row in data:
        original = sent[int(row['source_record_id'])]
        require(all(equal_number(row[k], original[v]) for k, v in raw_names.items()), 'Prepared features differ from raw source')
        require(row['uav_name'] == original['UAV'] and int(row['uav_id']) == mapping[original['UAV']], 'UAV identity mismatch')
        require(int(row['label']) == int(original['Label'] == 'Attack'), 'Ground truth mismatch')
        expected_type = 'Normal' if original['Label'] == 'Normal' else 'OMNeT++ abnormal communication behaviour'
        require(row['attack_type'] == expected_type, 'Unsupported attack type in current dataset')
    require(collections.Counter(r['label'] for r in data) == {'0': 220, '1': 27}, 'Current class counts mismatch')
    _, splits = read_csv(directory / 'split_membership.csv')
    require(len(splits) == 247 and {int(r['source_record_id']) for r in splits} == set(ids), 'Split membership has missing or duplicate records')
    require({r['split'] for r in splits} == {'train', 'test'}, 'Unknown split label')
    train_ids = {int(r['source_record_id']) for r in splits if r['split'] == 'train'}
    test_ids = {int(r['source_record_id']) for r in splits if r['split'] == 'test'}
    require(len(train_ids) == 172 and len(test_ids) == 75 and not train_ids & test_ids, 'Train/test split is incomplete or overlapping')
    _, predictions = read_csv(directory / 'uav_test_predictions.csv')
    require(len(predictions) == 75 and {int(r['source_record_id']) for r in predictions} == test_ids, 'Test predictions mismatch split')
    prepared = {int(r['source_record_id']): r for r in data}
    for row in predictions:
        require(all(row[k] == prepared[int(row['source_record_id'])][k] for k in COLUMNS), 'Prediction row differs from modelling row')
    summary = json.loads((directory / 'framework_summary.json').read_text())
    require(summary['run_id'] == manifest['run_id'], 'Run ID mismatch')
    require(summary['source_sha256'] == sha(source), 'Summary input fingerprint mismatch')
    require(summary['dataset_rows'] == 247 and summary['training_rows'] == 172 and summary['test_rows'] == 75, 'Summary dataset/split counts mismatch')
    require(summary['raw_csv_rows'] == 494 and summary['real_normal_rows'] == 220 and summary['real_attack_rows'] == 27, 'Summary raw/class counts mismatch')
    require(summary['real_model_features'] == FEATURES and summary['synthetic_attack_rows_added'] == 0, 'Feature list or augmentation mismatch')
    pqc_done = summary['pqc']['status'] == 'completed'
    require(summary['pqc']['status'] in ('not_run', 'completed'), 'Unknown PQC status')
    if pqc_done:
        _, trials = read_csv(directory / 'pqc_benchmark_results.csv')
        require(len(trials) == summary['pqc']['iterations'] == 200, 'PQC trial count mismatch')
        require(all(r['success'] == 'True' and r['algorithm'] == 'ML-KEM-768' for r in trials), 'PQC benchmark failure')
        require(summary['pqc']['representative_demo_verified'] is True, 'PQC payload verification failed')
        require(equal_number(summary['pqc']['success_rate_pct'], 100), 'PQC success rate mismatch')
        for field in ('keygen_ms', 'encapsulation_ms', 'decapsulation_ms', 'aes_encrypt_ms', 'aes_decrypt_ms'):
            require(equal_number(sum(float(r[field]) for r in trials)/len(trials), summary['pqc']['mean_' + field]), 'PQC timing mismatch')
    else:
        require(summary['pqc']['representative_demo_verified'] is None, 'Unexecuted PQC must not claim verification')
    _, comparison = read_csv(directory / 'model_comparison.csv')
    truth = [int(r['label']) for r in predictions]
    report = (directory / 'classification_report.txt').read_text()
    require('Controlled OMNeT++ simulation results' in report, 'Classification report lacks scope')
    for name, key, column, score in [
        ('Isolation Forest', 'isolation_forest', 'isolation_forest_prediction', 'anomaly_score'),
        ('Random Forest', 'random_forest', 'random_forest_prediction', 'random_forest_attack_probability')
    ]:
        predicted = [int(r[column]) for r in predictions]
        require(set(predicted) <= {0, 1}, 'Invalid prediction class')
        counts = collections.Counter(zip(truth, predicted))
        tn, fp, fn, tp = counts[0, 0], counts[0, 1], counts[1, 0], counts[1, 1]
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        expected = {'accuracy': (tn + tp) / 75, 'precision': precision, 'recall': recall,
                    'f1_score': f1, 'roc_auc': auc(truth, [float(r[score]) for r in predictions])}
        row = next(r for r in comparison if r['Model'] == name)
        names = {'accuracy': 'Accuracy', 'precision': 'Precision', 'recall': 'Recall', 'f1_score': 'F1 Score', 'roc_auc': 'ROC-AUC'}
        require(all(equal_number(value, summary[key][k]) and equal_number(value, row[names[k]]) for k, value in expected.items()), name + ' metrics do not match predictions')
    _, alerts = read_csv(directory / 'soc_alerts.csv')
    events = [json.loads(line) for line in (directory / 'uav_soc_events.json').read_text().splitlines() if line.strip()]
    expected_alert_ids = {int(r['source_record_id']) for r in predictions
                          if int(r['isolation_forest_prediction']) or int(r['random_forest_prediction'])}
    require(len(alerts) == len(events) == len(expected_alert_ids) == summary['soc_alerts_generated'], 'SOC alert counts mismatch')
    require({int(r['source_record_id']) for r in alerts} == {r['source_record_id'] for r in events} == expected_alert_ids, 'SOC alerts differ from model decisions')
    by_id = {int(r['source_record_id']): r for r in predictions}
    alert_by_id = {int(r['source_record_id']): r for r in alerts}
    for event in events:
        row = by_id[event['source_record_id']]
        require(event['run_id'] == summary['run_id'] and event['pqc_status'] == summary['pqc']['status'], 'SOC provenance mismatch')
        require(event['pqc_representative_demo_verified'] == summary['pqc']['representative_demo_verified'], 'SOC event falsely claims PQC verification')
        require(all(equal_number(event[k], row[k]) for k in FEATURES), 'SOC features differ from prediction')
        require(int(event['ground_truth_label']) == int(row['label']), 'SOC ground truth mismatch')
        require(all(str(event[k]) == v for k, v in alert_by_id[event['source_record_id']].items()), 'Alert CSV differs from NDJSON event')
    _, combined = read_csv(directory / 'uav_soc_pqc_wazuh_output.csv')
    require(len(combined) == 75 and {int(r['source_record_id']) for r in combined} == test_ids, 'Wazuh CSV record mismatch')
    require(all(r['pqc_status'] == summary['pqc']['status'] and r['run_id'] == summary['run_id'] for r in combined), 'Wazuh CSV scope mismatch')
    require(all(all(r[k] == by_id[int(r['source_record_id'])][k] for k in by_id[int(r['source_record_id'])]) for r in combined), 'Wazuh CSV differs from predictions')
    executed = json.loads((directory / 'executed_notebook.ipynb').read_text())
    template = json.loads((ROOT / '02_AI_Threat_Detection/uav_soc_pqc_analysis.ipynb').read_text())
    require(len(executed['cells']) == len(template['cells']), 'Executed notebook structure differs')
    require(all(''.join(a['source']) == ''.join(b['source']) for a, b in zip(executed['cells'], template['cells'])), 'Executed notebook differs from current source')
    code = [c for c in executed['cells'] if c['cell_type'] == 'code']
    require(len(code) == sum(c['cell_type'] == 'code' for c in template['cells']) and all(c['execution_count'] is not None for c in code), 'Notebook execution incomplete')
    require(not any(o['output_type'] == 'error' for c in code for o in c['outputs']), 'Notebook contains execution errors')
    print(f"PASS: {summary['run_id']}: 247 source-matched rows, 172 train, 75 test, {len(alerts)} alerts; metrics and provenance verified")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path)
    args = parser.parse_args()
    if args.run_dir:
        directory = args.run_dir
    else:
        pointer = json.loads((ROOT / '06_Results/CURRENT_RUN.json').read_text())
        directory = ROOT / pointer['path']
        require(sha(directory / 'run_manifest.json') == pointer['manifest_sha256'], 'Current pointer manifest mismatch')
    validate_run(directory)


if __name__ == '__main__':
    main()
