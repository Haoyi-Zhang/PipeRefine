"""Owned metadata/file-set controls; no target, payload or native hardware input.

SPDX-License-Identifier: MIT
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from timeline_check import check_client_record
from check import Invalid, certificate_ranks
from timeline import translate_case


class WorkflowControls(unittest.TestCase):
    def test_bibliography_check_only_consumes_selected_output(self):
        with tempfile.TemporaryDirectory(prefix='owned-bibliography-') as tmp:
            output=Path(tmp)
            data=json.loads((ROOT/'bibliography-results/summary.json').read_text())
            data['entries']=70  # A recording counter-observation, no scientific input change.
            (output/'summary.json').write_text(json.dumps(data),encoding='utf-8')
            flags=['-B','-S']+(['-'+'O'*sys.flags.optimize] if sys.flags.optimize else [])
            result=subprocess.run([sys.executable,*flags,str(ROOT/'run_bibliography.py'),
                '--output',str(output),'--check-only'],cwd=ROOT,capture_output=True,timeout=20,
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertNotEqual(result.returncode,0,'selected output must not be ignored')

    def test_scientific_comparison_requires_same_file_set(self):
        # Import declarations only. The stand-in enables the old POSIX-only module
        # to expose compare_tree on Windows; no resource operation is invoked.
        spec=importlib.util.spec_from_file_location('owned_reproduction',ROOT/'reproduce.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'resource':types.ModuleType('resource')}):
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='owned-file-set-') as tmp:
            a,b=Path(tmp)/'observed',Path(tmp)/'retained'
            a.mkdir();b.mkdir();(b/'missing.certificate.json').write_text('{}')
            with self.assertRaises(RuntimeError):
                module.compare_tree(a,b,['*.certificate.json'])

    def test_client_record_binding_rejects_equal_typed_substitutes(self):
        case=json.loads((ROOT/'timeline-inputs/timeline-identical.json').read_text())
        record=json.loads((ROOT/'timeline-results/timeline-identical.clients.json').read_text())
        translated=translate_case(case)
        cert=json.loads((ROOT/'timeline-results/timeline-identical.certificate.json').read_text())
        values=cert['valuations'];ranks=certificate_ranks(translated,cert,values)
        initial=translated['implementation']['initial']*translated['specification']['states']+translated['specification']['initial']
        for field in ('valuation float','safe Boolean'):
            changed=copy.deepcopy(record)
            if field=='valuation float': changed['valuations'][0]['p']=0.0
            else: changed['safe_valuation_ids'][0]=False
            with self.subTest(field=field),self.assertRaises(Invalid):
                check_client_record(case,values,cert['safe_valuation_ids'],changed,ranks,initial)


if __name__=='__main__': unittest.main()
