"""Read the Android golden JPEG via ADB and verify the remote RGB/BGR boundary.

Run from services/api: python -m tools.check_android_color --adb PATH --serial SERIAL
Requires the Android ColorGoldenImageTest to have run on the device.
"""

import argparse
import json
import subprocess

import numpy as np

from app.image_color import decode_rgb, to_ultralytics_bgr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    args = parser.parse_args()
    jpeg = subprocess.check_output([
        args.adb, "-s", args.serial, "exec-out", "run-as", "it.polito.ppemobile", "cat",
        "files/diagnostics/color_golden_android.jpg",
    ])
    rgb = decode_rgb(jpeg)
    bgr = to_ultralytics_bgr(rgb)
    if rgb.shape != (32, 96, 3):
        raise ValueError(f"Unexpected Android JPEG shape: {rgb.shape}")
    samples = {
        "red": rgb[16, 16].tolist(),
        "green": rgb[16, 48].tolist(),
        "blue": rgb[16, 80].tolist(),
    }
    for label, expected in (("red", [255, 0, 0]), ("green", [0, 255, 0]), ("blue", [0, 0, 255])):
        if not np.allclose(samples[label], expected, atol=5):
            raise AssertionError(f"Android JPEG {label} patch changed channels: {samples[label]}")
    if not np.array_equal(bgr[:, :, ::-1], rgb):
        raise AssertionError("Ultralytics BGR boundary does not round-trip to decoded RGB")
    print(json.dumps({"valid": True, "androidJpegBytes": len(jpeg), "decodedRgbSamples": samples,
                      "ultralyticsBgrRedSample": bgr[16, 16].tolist()}, indent=2))


if __name__ == "__main__":
    main()
