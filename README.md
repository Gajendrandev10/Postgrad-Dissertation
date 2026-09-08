# UAV Quantum Secure SOC Project

A postgraduate project combining OMNeT++ UAV traffic simulation, machine-learning threat detection, SOC alert exports and a representative ML-KEM-768/AES-256-GCM cryptography benchmark.

See [Code/readme.md](Code/readme.md) for completed work, folder contents, setup and limitations. The active notebook is [uav_soc_pqc_analysis.ipynb](Code/02_AI_Threat_Detection/uav_soc_pqc_analysis.ipynb).

## Included work

- Simulator source, network definition, configuration and traffic dataset.
- Isolation Forest and Random Forest analysis of 247 Send records.
- SOC alert exports and Wazuh configuration examples.
- Saved experiments, metrics, figures and PQC benchmark evidence.
- Local execution, validation and audit tools.

## Setup

Use a compatible Python environment and install the recorded analysis dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirement.txt
.venv/bin/python Code/tools/run_analysis.py --help
```

The dependency snapshot has not been verified in a fresh environment. OMNeT++ and its C++ toolchain are separate prerequisites for simulation. PQC additionally requires native liboqs and liboqs-python.

## Evidence and limitations

The saved reference experiment is [local_only_pqc_20260906](Code/06_Results/runs/local_only_pqc_20260906/). Results describe a controlled simulation, not operational UAV performance. The active notebook differs from the saved execution, and strict provenance validation reports input drift. Historical manifests remain unchanged.

The notebook retains Colab branches. Wazuh exports and sample configuration do not establish a verified live deployment. The PQC benchmark protects a representative payload, not individual SOC events.

Documentation is maintained locally and excluded from this repository. Dissertation utilities require those local assets; rebuilding additionally requires the deleted Markdown source to be restored. Virtual environments, native installations and compiled simulator binaries are excluded.
