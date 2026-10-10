"""Keep per-model API panels separate from genuinely host-wide telemetry."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "observability/grafana/dashboards/ppe-remote-inference.json"
PROMETHEUS = ROOT / "observability/prometheus/prometheus.yml"
MODELS = {"yolo26n-640", "yolo26n-960", "yolo26s-640", "yolo26m-640", "yolo26l-640"}


class DashboardContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        cls.panels = {panel["id"]: panel for panel in cls.dashboard["panels"]}

    def test_each_api_target_has_a_stable_model_label(self):
        config = PROMETHEUS.read_text(encoding="utf-8")
        labels = re.findall(r'model_service: "([a-z0-9-]+)"', config)
        self.assertEqual(MODELS, set(labels))
        self.assertEqual(len(MODELS), len(labels))

    def test_api_and_container_panels_follow_selected_model(self):
        self.assertEqual("model_service", self.dashboard["templating"]["list"][0]["name"])
        for panel_id in (1, 2, 3, 4, 5, 7, 8, 16, 17, 18):
            for target in self.panels[panel_id]["targets"]:
                self.assertIn('model_service=\"${model_service}\"', target["expr"])
        for panel_id in (10, 14, 15, 20):
            for target in self.panels[panel_id]["targets"]:
                self.assertIn("ppe-${model_service}-inference-api", target["expr"])

    def test_shared_gpu_panels_do_not_claim_per_model_attribution(self):
        for panel_id in (6, 12, 13):
            self.assertNotIn("${model_service}", json.dumps(self.panels[panel_id]))
            self.assertTrue(any(word in self.panels[panel_id]["title"] for word in ("host-wide", "all services")))
        self.assertIn("model_service", self.panels[19]["targets"][0]["expr"])


if __name__ == "__main__":
    unittest.main()
