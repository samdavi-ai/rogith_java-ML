import json
import unittest
from pathlib import Path

import onnx
import onnxruntime as ort

from ml.scripts.prepare_dataset import parse_classes, source_group


ROOT = Path(__file__).resolve().parents[2]


class PipelineArtifactTests(unittest.TestCase):
    def test_class_ids_are_the_single_ordered_authority(self):
        classes = parse_classes(ROOT / "ml/classes.json")
        self.assertEqual([item["id"] for item in classes], list(range(6)))
        self.assertEqual([item["name"] for item in classes], [
            "battery_waste", "keyboard", "light_bulb", "mobile_phone", "mouse", "pcb"
        ])

    def test_roboflow_variants_share_source_family(self):
        self.assertEqual(source_group(Path("IMG_01_jpg.rf.abcdef123.jpg")), "IMG_01_jpg")
        self.assertEqual(source_group(Path("IMG_01_jpg.rf.123456789.jpg")), "IMG_01_jpg")

    def test_audit_has_clean_disjoint_family_splits_and_expected_counts(self):
        report = json.loads((ROOT / "ml/reports/dataset_report.json").read_text())
        self.assertEqual(report["sourceArchiveImages"], 2157)
        self.assertEqual(report["corruptImages"], [])
        self.assertEqual(report["exactDuplicateGroups"], [])
        self.assertEqual(report["sourceGroupCrossSplitLeaks"], [])
        self.assertGreater(report["selectedNearDuplicateEdgesGrouped"], 0)
        for split in ("train", "validation", "test"):
            self.assertEqual(set(report["classificationImagesBySplitAndClass"][split]), {
                "battery_waste", "keyboard", "light_bulb", "mobile_phone", "mouse", "pcb"
            })

    def test_onnx_contract_and_runtime_inference(self):
        model_path = ROOT / "ml/models/ewaste.onnx"
        self.assertTrue(model_path.is_file())
        onnx.checker.check_model(onnx.load(model_path))
        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.assertEqual(session.get_inputs()[0].shape[1:], [3, 224, 224])
        self.assertEqual(session.get_outputs()[0].shape[-1], 6)
        import numpy as np
        logits = session.run(None, {session.get_inputs()[0].name: np.zeros((1, 3, 224, 224), dtype=np.float32)})[0]
        self.assertEqual(logits.shape, (1, 6))
        self.assertTrue(np.isfinite(logits).all())


if __name__ == "__main__":
    unittest.main()
