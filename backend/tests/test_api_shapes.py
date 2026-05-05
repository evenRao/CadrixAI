from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from cadrix_v2.app import capabilities_v2, generate_v2, plan_v2
from cadrix_v2.schemas import GenerateRequestV2, PlanRequestV2
from starlette.requests import Request


def make_request() -> Request:
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("localhost", 8000),
        "method": "POST",
        "path": "/v2/generate",
        "headers": [],
        "app": main.app,
        "router": main.app.router,
    }
    return Request(scope)


class ApiShapeTests(unittest.TestCase):
    def test_capabilities_shape(self) -> None:
        response = capabilities_v2()
        self.assertTrue(response.supported)
        self.assertIn("Phone Stand", response.highlighted_builds)

    def test_plan_shape(self) -> None:
        response = plan_v2(PlanRequestV2(prompt="Make a phone stand for a 75mm wide phone."))
        self.assertIn("success", response.model_dump())
        self.assertIn("parameters", response.model_dump())
        self.assertIn("warnings", response.model_dump())

    def test_generate_shape(self) -> None:
        response = generate_v2(
            GenerateRequestV2(prompt="Simple gear with 24 teeth, 40mm diameter, and 5mm bore."),
            make_request(),
        )
        payload = response.model_dump()
        self.assertIn("files", payload)
        self.assertIn("metadata", payload)
        self.assertIn("parameters", payload)
        self.assertTrue(payload["success"])


if __name__ == "__main__":
    unittest.main()
