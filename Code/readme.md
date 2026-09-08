# UAV security code and experiments

This codebase investigates a UAV security workflow combining OMNeT++ traffic simulation, machine-learning anomaly detection, SOC alert generation and a representative post-quantum cryptography demonstration. The results describe controlled simulation data, not demonstrated performance on operational UAV networks.

## Work completed

- Created an OMNeT++ UAV simulation and retained its traffic CSV, C++ source, network definition and configuration.
- Prepared 247 Send records from 494 simulator events, with 220 Normal and 27 Attack records. Retained the older 795-record exports separately as legacy evidence.
- Implemented a stratified training/test split with 172 training and 75 test records, using packet size, latency, packet loss and throughput as model features.
- Evaluated Isolation Forest and Random Forest and generated confusion matrices, classification metrics and ROC plots.
- Generated SOC alerts and Wazuh-oriented exports. In the saved reference run, the SOC produced 13 alerts: eight true attack alerts and five false alarms.
- Ran a representative ML-KEM-768 and AES-256-GCM demonstration with 200 successful benchmark iterations. This does not encrypt individual SOC events or establish authenticated UAV communications.
- Added a local notebook runner, run manifests, input/output hashes and validation scripts to make experiment provenance inspectable.
- Organised simulation, scripts, results and historical evidence under this folder and standardised active filenames.

## Folder guide

| Folder | Purpose |
| --- | --- |
| `01_OMNeT_Simulation` | Simulation sources, configuration and traffic data |
| `02_AI_Threat_Detection` | Active analysis notebook and legacy AI outputs |
| `03_PQC_Security` | Native installation record and legacy PQC benchmarks |
| `04_SOC_Outputs` | Legacy SOC exports |
| `05_Wazuh` | Wazuh configuration and sample rules |
| `06_Results` | Saved runs, manifests and current-run pointer |
| `07_Figures` | Legacy result plots |
| `99_Archive` | Earlier notebook snapshots |
| `tools` | Runner, validation and audit scripts |
| `tools/dissertation` | Document build, evidence analysis and checking scripts |
| `outputs` | Direct notebook output directories |

## Requirements and commands

`requirement.txt` includes the existing pinned analysis dependency snapshot in `requirements_analysis.txt`. Python and a compatible OMNeT++ installation with its C++ toolchain are required for the respective workflows. PQC additionally requires native liboqs and its Python wrapper; these are not installed by the analysis requirements file. The local installation record is `03_PQC_Security/local_installation.json`.

Run these commands from the workspace root:

```sh
.venv/bin/python -m pip install -r Code/requirement.txt
.venv/bin/python Code/tools/run_analysis.py --help
.venv/bin/python Code/tools/validate_current_run.py
```

The dependency snapshot is retained from the project environment; installation into a fresh environment has not been verified during this documentation update. The `.venv` and `.runtime` directories remain at workspace root.

The runner writes a new directory under `Code/06_Results/runs/`; direct notebook execution defaults to `Code/outputs/<run_id>`. Environment overrides can change these locations. Paths inside run manifests and `CURRENT_RUN.json` are relative to `Code`.

## Current limitations

The reference experiment is `06_Results/runs/local_only_pqc_20260906`. The active notebook differs from that saved execution and still contains Colab branches. Strict validation reports input drift; the saved manifests have not been rewritten to conceal it. Wazuh files do not establish a verified live UAV-to-Wazuh deployment.

The earlier Markdown cleanup removed the dissertation source `dissertation_draft.md`. The retained document build scripts require that source to be restored before rebuilding. Historical preservation audits can also flag deliberately deleted or renamed files.
