"""Functional parity: original (tests/fixtures) vs reserialized (SERDE_ONNX_ROUNDTRIP_OUT).

For each model, validate with onnx.checker and compare onnxruntime outputs
(original vs reserialized) over the iris dataset — they must be bit-identical.

Usage:
  SERDE_ONNX_ROUNDTRIP_OUT=/tmp/rt cargo test --features export,import --test web_models_roundtrip
  python3 scripts/check_parity.py --fixtures tests/fixtures --roundtrip /tmp/rt
"""

import argparse
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as rt
from sklearn.datasets import load_iris

FILES = [
    "01_scaler_iris.onnx",
    "02_logreg_iris_pipe.onnx",
    "03_rf_iris.onnx",
]


def compare(orig: Path, reser: Path, X: np.ndarray) -> None:
    onnx.checker.check_model(onnx.load(str(orig)))
    onnx.checker.check_model(onnx.load(str(reser)))
    so = rt.InferenceSession(str(orig), providers=["CPUExecutionProvider"])
    sr = rt.InferenceSession(str(reser), providers=["CPUExecutionProvider"])
    assert [o.name for o in so.get_outputs()] == [o.name for o in sr.get_outputs()]
    assert [i.name for i in so.get_inputs()] == [i.name for i in sr.get_inputs()]
    inp = so.get_inputs()[0].name
    for i, (a, b) in enumerate(zip(so.run(None, {inp: X}), sr.run(None, {inp: X}))):
        if isinstance(a, np.ndarray):
            diff = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))
            print(f"  out{i}: shape {a.shape} max|diff|={diff:.3e}")
            assert diff == 0.0, f"numeric divergence in {orig.name} out{i}"
        else:  # sequence output (ZipMap)
            assert a == b, f"divergence in {orig.name} out{i}"
            print(f"  out{i}: seq len {len(a)} identical")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="tests/fixtures")
    ap.add_argument("--roundtrip", required=True)
    args = ap.parse_args()
    X = load_iris(return_X_y=True)[0].astype(np.float32)
    for f in FILES:
        print(f"== {f} vs reserialized")
        compare(Path(args.fixtures) / f, Path(args.roundtrip) / f, X)
    print("functional parity OK: identical outputs on all 3 models")


if __name__ == "__main__":
    main()
