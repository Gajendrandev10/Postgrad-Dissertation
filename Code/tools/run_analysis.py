#!/usr/bin/env python3
"""Execute the project notebook unchanged in a local kernel and record provenance."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / '02_AI_Threat_Detection/uav_soc_pqc_analysis.ipynb'
SOURCE = ROOT / '01_OMNeT_Simulation/UAV_SOC_Project/simulations/uav_traffic.csv'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=datetime.now(timezone.utc).strftime('send247_%Y%m%dT%H%M%SZ'))
    parser.add_argument('--pqc', action='store_true', help='Run local ML-KEM benchmark as well as AI/SOC')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.run_id):
        parser.error('run-id must contain only letters, digits, underscores and hyphens')
    output = ROOT / '06_Results/runs' / args.run_id
    if output.exists():
        parser.error(f'Run directory already exists: {output}; use a new run-id')
    runtime = ROOT.parent / '.runtime'
    runtime.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({
        'UAV_INPUT_CSV': str(SOURCE), 'UAV_OUTPUT_DIR': str(output),
        'UAV_RUN_ID': args.run_id, 'UAV_RUN_PQC': '1' if args.pqc else '0',
        'MPLCONFIGDIR': str(runtime / 'matplotlib'),
        'IPYTHONDIR': str(runtime / 'ipython'),
        'JUPYTER_RUNTIME_DIR': str(runtime / 'jupyter'),
        'MPLBACKEND': 'module://matplotlib_inline.backend_inline',
    })
    os.environ.update({k: v for k, v in env.items() if k in ['IPYTHONDIR', 'JUPYTER_RUNTIME_DIR']})
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager

    kernels = runtime / 'kernels'
    spec = kernels / 'uav-project'
    spec.mkdir(parents=True, exist_ok=True)
    (spec / 'kernel.json').write_text(json.dumps({
        'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        'display_name': 'UAV project virtual environment', 'language': 'python'
    }))
    manager = KernelManager(kernel_name='uav-project',
                            kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None
    started = datetime.now(timezone.utc).isoformat()
    print('Executing', NOTEBOOK.relative_to(ROOT), '->', output.relative_to(ROOT), flush=True)
    client = NotebookClient(notebook, km=manager, timeout=600,
                            resources={'metadata': {'path': str(ROOT)}})
    client.execute(env=env, cwd=str(ROOT))
    nbformat.write(notebook, output / 'executed_notebook.ipynb')
    environment = {
        'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
        'packages': dict(sorted((d.metadata['Name'], d.version) for d in distributions()))
    }
    (output / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    inputs = [SOURCE, NOTEBOOK, ROOT / 'tools/run_analysis.py',
              ROOT / '01_OMNeT_Simulation/UAV_SOC_Project/src/UAVNode.cc',
              ROOT / '01_OMNeT_Simulation/UAV_SOC_Project/src/UAVNetwork.ned',
              ROOT / '01_OMNeT_Simulation/UAV_SOC_Project/simulations/omnetpp.ini',
              ROOT / 'requirements_analysis.txt']
    manifest = {
        'run_id': args.run_id, 'started_at': started,
        'completed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'AI/SOC with local PQC benchmark' if args.pqc else 'AI/SOC analysis; PQC not run',
        'inputs': {str(p.relative_to(ROOT)): digest(p) for p in inputs},
        'outputs': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    }
    (output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Publish the current pointer only when independent data/metric validation passes.
    from validate_current_run import validate_run
    validate_run(output)
    pointer = ROOT / '06_Results/CURRENT_RUN.json'
    temporary = pointer.with_suffix('.tmp')
    temporary.write_text(json.dumps({'run_id': args.run_id, 'path': str(output.relative_to(ROOT)),
                                     'manifest_sha256': digest(output / 'run_manifest.json')}, indent=2) + '\n')
    temporary.replace(pointer)
    print('Published validated current run:', output.relative_to(ROOT), flush=True)


if __name__ == '__main__':
    main()
