"""Golden-image check for the pinned Ultralytics NumPy BGR input contract."""

import io
from types import SimpleNamespace
import unittest

import numpy as np
from PIL import Image

from app.backend import UltralyticsBackend
from app.image_color import decode_rgb, to_ultralytics_bgr


class ColorContractTest(unittest.TestCase):
    def test_rgb_jpeg_is_converted_to_bgr_at_model_boundary(self):
        image = Image.new("RGB", (96, 32))
        for x in range(96):
            color = (255, 0, 0) if x < 32 else (0, 255, 0) if x < 64 else (0, 0, 255)
            for y in range(32):
                image.putpixel((x, y), color)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=100, subsampling=0)
        rgb = decode_rgb(output.getvalue())
        self.assertEqual(rgb.shape, (32, 96, 3))
        np.testing.assert_allclose(rgb[16, 16], [255, 0, 0], atol=3)
        np.testing.assert_allclose(rgb[16, 48], [0, 255, 0], atol=3)
        np.testing.assert_allclose(rgb[16, 80], [0, 0, 255], atol=3)

        class FakeModel:
            source = None
            options = None

            def predict(self, *, source, **options):
                self.source = source
                self.options = options
                return [SimpleNamespace(boxes=None, names={}, speed={})]

        backend = object.__new__(UltralyticsBackend)
        backend.model = FakeModel()
        backend.settings = SimpleNamespace(input_size=640, confidence=.25, iou=.45, device="cpu")
        backend.predict(rgb)
        bgr = backend.model.source
        self.assertTrue(bgr.flags.c_contiguous)
        self.assertIs(backend.model.options["rect"], False)
        np.testing.assert_array_equal(bgr[16, 16], rgb[16, 16, ::-1])
        np.testing.assert_array_equal(bgr[16, 80], rgb[16, 80, ::-1])
        # Ultralytics reverses NumPy BGR back to RGB before model invocation.
        np.testing.assert_array_equal(bgr[:, :, ::-1], rgb)

    def test_wrong_shape_or_type_is_rejected(self):
        with self.assertRaises(ValueError):
            to_ultralytics_bgr(np.zeros((4, 4, 4), dtype=np.uint8))
        with self.assertRaises(ValueError):
            to_ultralytics_bgr(np.zeros((4, 4, 3), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
