"""Regression tests prevent old data and mismatched evidence entering a current run."""
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from validate_current_run import ROOT, validate_run


class CurrentRunTests(unittest.TestCase):
    def setUp(self):
        pointer = json.loads((ROOT / '06_Results/CURRENT_RUN.json').read_text())
        self.temp = tempfile.TemporaryDirectory(prefix='uav-regression-')
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        shutil.copytree(ROOT / pointer['path'], self.run)

    def rehash(self, name):
        # Simulate an internally hashed export from the wrong pipeline, not just file damage.
        path = self.run / 'run_manifest.json'
        manifest = json.loads(path.read_text())
        manifest['outputs'][name] = hashlib.sha256((self.run / name).read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))

    def test_current_run_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            summary = validate_run(self.run)
        self.assertEqual(summary['dataset_rows'], 247)

    def test_legacy_dataset_rejected_even_with_valid_hash(self):
        name = 'omnet_uav_ai_dataset.csv'
        shutil.copy2(ROOT / '02_AI_Threat_Detection/legacy_run' / name, self.run / name)
        self.rehash(name)
        with self.assertRaisesRegex(ValueError, 'schema'):
            validate_run(self.run)

    def test_source_feature_change_rejected(self):
        name = 'omnet_uav_ai_dataset.csv'
        with (self.run / name).open(newline='') as handle:
            reader = csv.DictReader(handle)
            headers, rows = reader.fieldnames, list(reader)
        rows[0]['packet_size'] = str(float(rows[0]['packet_size']) + 100)
        with (self.run / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        self.rehash(name)
        with self.assertRaisesRegex(ValueError, 'features differ from raw source'):
            validate_run(self.run)

    def test_old_metrics_rejected(self):
        name = 'model_comparison.csv'
        shutil.copy2(ROOT / '06_Results/legacy_run' / name, self.run / name)
        self.rehash(name)
        with self.assertRaisesRegex(ValueError, 'metrics do not match predictions'):
            validate_run(self.run)

    def test_missing_alert_rejected(self):
        name = 'uav_soc_events.json'
        lines = (self.run / name).read_text().splitlines()
        (self.run / name).write_text('\n'.join(lines[:-1]) + '\n')
        self.rehash(name)
        with self.assertRaisesRegex(ValueError, 'SOC alert counts mismatch'):
            validate_run(self.run)


if __name__ == '__main__':
    unittest.main()
