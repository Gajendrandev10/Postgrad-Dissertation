#!/usr/bin/env python3
"""Read-only preservation and consistency audit; does not execute experiments."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]

def rows(relative):
    with (ROOT / relative).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))

def main():
    failures = []
    def check(condition, message):
        print(('PASS: ' if condition else 'FAIL: ') + message)
        if not condition:
            failures.append(message)

    manifest = json.loads((ROOT.parent / 'Documentation/01_Project_Documentation/organization_manifest.json').read_text())
    damaged = []
    for item in manifest['files']:
        relative = Path(item['path'])
        parent = ROOT.parent / 'Documentation' if relative.parts[0] in ['00_Project_Documentation', '08_Dissertation', '09_References', '10_Templates', 'Skills', 'dissertation_assignment_brief.md', 'dissertation_formatting_guidance.md'] else ROOT
        if relative.parts[0] in {'.DS_Store', '.vscode', 'AGENTS.md', 'README.md', '.gitignore'}:
            parent = ROOT.parent
        if parent == ROOT.parent / 'Documentation':
            names = {'00_Project_Documentation': '01_Project_Documentation', '08_Dissertation': '02_Dissertation', '09_References': '03_References', '10_Templates': '04_Templates', 'Skills': '05_Skills'}
            relative = Path(names.get(relative.parts[0], relative.parts[0]), *relative.parts[1:])
        filename_aliases = {'requirements-analysis.txt': 'requirements_analysis.txt', 'UAV_OMNeT_AI_SOC_PQC_Colab_FIXED.ipynb': 'uav_soc_pqc_analysis.ipynb', 'LOCAL_MACOS_SETUP.md': 'local_macos_setup.md', 'Hand book.md': 'dissertation_assignment_brief.md', 'report (2).md': 'dissertation_formatting_guidance.md', 'FOLDER_RELOCATION.md': 'folder_relocation.md', 'FILE_MOVES.csv': 'file_moves.csv', 'FOLDER_RELOCATION.json': 'folder_relocation.json', 'FILE_INVENTORY.md': 'file_inventory.md', 'RESULTS_FIX.md': 'results_fix.md', 'PROJECT_REVIEW.md': 'project_review.md', 'DOCUMENTATION_RENUMBERING.json': 'documentation_renumbering.json', 'UPDATE_ROADMAP.md': 'update_roadmap.md', 'ORGANIZATION_MANIFEST.json': 'organization_manifest.json', 'FOLDER_RELOCATION_REFINEMENT.json': 'folder_relocation_refinement.json', 'SKILL (1).md': 'humanizer_skill.md', 'UAV_Cybersecurity_Dissertation_Draft.docx': 'uav_cybersecurity_dissertation_draft.docx', 'DRAFT_REVIEW.md': 'draft_review.md', 'Adel_Latham_Crockett_2017.pdf': 'adel_latham_crockett_2017.pdf', 'Bitcoin_Artefacts_Dissertation_2019.pdf': 'bitcoin_artefacts_dissertation_2019.pdf', '7Z10SS_template.zip': 'mmu_latex_dissertation_template_7z10ss.zip', 'MMU_Dissertation_Template.docx': 'mmu_dissertation_template.docx'}
        relative = relative.with_name(filename_aliases.get(relative.name, relative.name))
        path = parent / relative
        if item['path'] == '02_AI_Threat_Detection/UAV_OMNeT_AI_SOC_PQC_Colab_FIXED.ipynb':
            archived = ROOT / '99_Archive/Before_Results_Fix/UAV_OMNeT_AI_SOC_PQC_Colab_FIXED.ipynb'
            if archived.exists():
                path = archived
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            damaged.append(item['path'])
    check(not damaged, f"Preservation of {len(manifest['files'])} original files")
    for path in damaged:
        print('  Changed or missing:', path)

    raw = rows('01_OMNeT_Simulation/UAV_SOC_Project/simulations/uav_traffic.csv')
    send = [r for r in raw if r['Event'] == 'Send']
    counts = collections.Counter(r['Label'] for r in send)
    check(len(raw) == 494 and len(send) == 247 and counts == {'Normal': 220, 'Attack': 27},
          'Original simulation snapshot has 494 events and 247 Send rows (220 Normal, 27 Attack)')
    dataset = rows('02_AI_Threat_Detection/legacy_run/omnet_uav_ai_dataset.csv')
    predictions = rows('02_AI_Threat_Detection/legacy_run/uav_test_predictions.csv')
    comparison = rows('06_Results/legacy_run/model_comparison.csv')
    summary = json.loads((ROOT / '06_Results/legacy_run/framework_summary.json').read_text())
    check(len(dataset) == summary['dataset_rows'] and len(predictions) == summary['test_rows'],
          'Legacy summary counts match legacy dataset and predictions')
    for model, column in [('Isolation Forest', 'isolation_forest_prediction'),
                          ('Random Forest', 'random_forest_prediction')]:
        c = collections.Counter((int(r['label']), int(r[column])) for r in predictions)
        tn, fp, fn, tp = c[0, 0], c[0, 1], c[1, 0], c[1, 1]
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        actual = {'Accuracy': (tn + tp) / len(predictions), 'Precision': precision,
                  'Recall': recall, 'F1 Score': 2 * precision * recall / (precision + recall) if precision + recall else 0}
        saved = next(r for r in comparison if r['Model'] == model)
        check(all(math.isclose(v, float(saved[k]), abs_tol=1e-12) for k, v in actual.items()),
              f'{model} legacy metrics match predictions: TN={tn}, FP={fp}, FN={fn}, TP={tp}')
    benchmark = rows('03_PQC_Security/legacy_run/pqc_benchmark_results.csv')
    saved_stats = rows('03_PQC_Security/legacy_run/pqc_performance_summary.csv')
    stats_functions = {'mean': statistics.mean, 'median': statistics.median,
                       'std': statistics.stdev, 'min': min, 'max': max}
    valid = True
    for record in saved_stats:
        for column in ['keygen_ms', 'encapsulation_ms', 'decapsulation_ms', 'aes_encrypt_ms', 'aes_decrypt_ms']:
            value = stats_functions[record['']]([float(r[column]) for r in benchmark])
            valid = valid and math.isclose(value, float(record[column]), rel_tol=1e-9, abs_tol=1e-12)
    check(valid and len(benchmark) == 200, 'Legacy PQC summary statistics match 200 benchmark rows')
    events = [json.loads(line) for line in (ROOT / '04_SOC_Outputs/legacy_run/uav_soc_events.json').read_text().splitlines() if line.strip()]
    alerts = rows('04_SOC_Outputs/legacy_run/soc_alerts.csv')
    check(len(events) == len(predictions) and len(alerts) == summary['soc_alerts_generated'],
          f'Legacy export counts: {len(events)} test events and {len(alerts)} SOC alerts')
    pointer = ROOT / '06_Results/CURRENT_RUN.json'
    if pointer.exists():
        from validate_current_run import validate_run
        current = json.loads(pointer.read_text())
        directory = ROOT / current['path']
        try:
            check(hashlib.sha256((directory / 'run_manifest.json').read_bytes()).hexdigest() == current['manifest_sha256'],
                  'Current run pointer matches its manifest')
            validate_run(directory)
        except (ValueError, OSError, KeyError) as exc:
            check(False, 'Current-run validation: ' + str(exc))
    else:
        check(False, 'No validated current-run pointer exists')
    print('NOTE: 795-row legacy outputs are preserved historical evidence, not current results.')
    print('LIMIT: this audit does not execute simulations, training, PQC or live Wazuh services.')
    return 1 if failures else 0

if __name__ == '__main__':
    sys.exit(main())
