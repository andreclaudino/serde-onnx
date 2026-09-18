"""Regenerate the ONNX fixtures under tests/fixtures/.

The 3 models follow exactly the public skl2onnx / ONNX Model Zoo examples
(documented patterns on the WEB) and only use operators typed by serde-onnx:

- 01_scaler_iris.onnx      : Scaler (ai.onnx.ml)
  Source: https://onnx.ai/sklearn-onnx/pipeline.html (StandardScaler pipeline)
- 02_logreg_iris_pipe.onnx : Scaler + LinearClassifier + Normalizer
  Source: https://onnx.ai/sklearn-onnx/auto_examples/plot_convert_model.html (logreg_iris.onnx)
- 03_rf_iris.onnx          : TreeEnsembleClassifier + Cast + ZipMap
  Source: https://onnx.ai/sklearn-onnx/auto_examples/plot_convert_model.html (rf_iris.onnx)

Model Zoo mirror: https://huggingface.co/onnxmodelzoo (its vision/NLP models use
Gemm/Conv/etc., outside the typed scope — hence the sklearn patterns above, with
opsets within the codec caps: IR<=10, ai.onnx<=25, ai.onnx.ml<=5).

Usage:  python3 tests/fixtures/generate_web_models.py [out_dir]
"""

import sys
from pathlib import Path

import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    X, y = load_iris(return_X_y=True)
    X = X.astype(np.float32)

    scaler = StandardScaler().fit(X)
    m1 = convert_sklearn(
        scaler, "scaler_iris", [("input", FloatTensorType([None, 4]))], target_opset=12
    )
    (out_dir / "01_scaler_iris.onnx").write_bytes(m1.SerializeToString())

    pipe = Pipeline(
        [("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=500))]
    ).fit(X, y)
    m2 = convert_sklearn(
        pipe,
        "logreg_iris_pipe",
        [("input", FloatTensorType([None, 4]))],
        target_opset=12,
        options={type(pipe.named_steps["clf"]): {"zipmap": False}},
    )
    (out_dir / "02_logreg_iris_pipe.onnx").write_bytes(m2.SerializeToString())

    rf = RandomForestClassifier(n_estimators=10, random_state=0).fit(X, y)
    m3 = convert_sklearn(
        rf, "rf_iris", [("input", FloatTensorType([None, 4]))], target_opset=12
    )
    (out_dir / "03_rf_iris.onnx").write_bytes(m3.SerializeToString())

    print(f"fixtures written to {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent)
