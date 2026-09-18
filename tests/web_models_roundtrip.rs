#![cfg(all(feature = "export", feature = "import"))]

//! Roundtrip of 3 real-world ONNX models (skl2onnx / ONNX Model Zoo doc patterns),
//! with fixtures versioned under `tests/fixtures`
//! (regenerate via `tests/fixtures/generate_web_models.py`).
//!
//! - `01_scaler_iris.onnx`: Scaler (ai.onnx.ml)
//! - `02_logreg_iris_pipe.onnx`: Scaler + LinearClassifier + Normalizer
//! - `03_rf_iris.onnx`: TreeEnsembleClassifier + Cast + ZipMap
//!
//! Web sources: `plot_convert_model` and `pipeline` from the skl2onnx docs, plus
//! the Model Zoo (`github.com/onnx/models`, HF mirror `onnxmodelzoo`).
//! Opsets stay within the codec caps (IR<=10, ai.onnx<=25, ai.onnx.ml<=5).

use serde_onnx::import::DecodedModel;
use serde_onnx::proto::encode_model;
use std::path::PathBuf;

fn model_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
}

fn check_roundtrip(file: &str, min_typed: usize) {
    let path = model_dir().join(file);
    assert!(path.exists(), "missing model: {}", path.display());
    let bytes = std::fs::read(&path).expect("read onnx");
    let d1 = DecodedModel::decode_bytes(&bytes).expect("decode original");
    assert!(!d1.payloads.is_empty(), "{file}: no nodes decoded");
    let n_typed = d1.typed().count();
    let n_raw = d1.raw_nodes().count();
    println!(
        "{file}: {} nodes ({} typed, {} raw) warnings={}",
        d1.payloads.len(),
        n_typed,
        n_raw,
        d1.warnings.len()
    );
    for (i, p) in d1.typed() {
        let n = p.node();
        println!("  typed[{i}]: {}::{}", n.domain, n.op_type);
    }
    for (i, n) in d1.raw_nodes() {
        println!("  raw[{i}]: {}::{}", n.domain, n.op_type);
    }
    assert!(
        n_typed >= min_typed,
        "{file}: expected >= {min_typed} typed nodes, got {n_typed}"
    );
    // Reserialize and compare: bytes -> model -> bytes -> model must be equivalent.
    let re_bytes = encode_model(&d1.model);
    assert!(!re_bytes.is_empty());
    // Expose the reserialized model to the functional (onnxruntime) CI check:
    // `SERDE_ONNX_ROUNDTRIP_OUT=/tmp/rt cargo test --test web_models_roundtrip`
    if let Ok(out) = std::env::var("SERDE_ONNX_ROUNDTRIP_OUT") {
        let dest = PathBuf::from(out).join(file);
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent).expect("create roundtrip output dir");
        }
        std::fs::write(&dest, &re_bytes).expect("write reserialized model");
    }
    let d2 = DecodedModel::decode_bytes(&re_bytes).expect("decode reserialized");
    assert_eq!(
        d1.model, d2.model,
        "{file}: reserialized model differs from the original"
    );
    assert_eq!(d1.payloads.len(), d2.payloads.len());
    // Re-reserialization must be stable (idempotent).
    let re_bytes2 = encode_model(&d2.model);
    let d3 = DecodedModel::decode_bytes(&re_bytes2).expect("decode 2nd roundtrip");
    assert_eq!(d2.model, d3.model, "{file}: second roundtrip diverged");
    assert!(
        d1.warnings.is_empty(),
        "{file}: unexpected warnings: {:?}",
        d1.warnings
    );
}

#[test]
fn web_model_01_scaler_roundtrip_equivalent() {
    check_roundtrip("01_scaler_iris.onnx", 1);
}

#[test]
fn web_model_02_logreg_pipeline_roundtrip_equivalent() {
    check_roundtrip("02_logreg_iris_pipe.onnx", 3);
}

#[test]
fn web_model_03_randomforest_roundtrip_equivalent() {
    check_roundtrip("03_rf_iris.onnx", 3);
}
