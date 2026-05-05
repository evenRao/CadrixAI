from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadrix_v2.registry import MODEL_REGISTRY


class RegistryTests(unittest.TestCase):
    def test_all_v2_models_are_implemented(self) -> None:
        for model_type, spec in MODEL_REGISTRY.items():
            self.assertTrue(spec.implemented, msg=f"{model_type} is still marked as a stub.")
            self.assertTrue(spec.parameter_definitions, msg=f"{model_type} is missing parameter definitions.")
            self.assertTrue(spec.examples, msg=f"{model_type} is missing example prompts.")


if __name__ == "__main__":
    unittest.main()
