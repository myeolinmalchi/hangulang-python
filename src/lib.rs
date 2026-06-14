use pyo3::exceptions::{PyOSError, PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBytes, PyModule};
use serde::Serialize;
use std::path::{Path, PathBuf};

use hangulang_engine::{ConvertError, ConvertOptions, ResourceAsset, ResourcePolicy};

#[derive(Serialize)]
struct AssetRef {
    id: String,
    path: String,
    uri: Option<String>,
    mime_type: String,
}

fn input_bytes(input: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    if let Ok(bytes) = input.downcast::<PyBytes>() {
        return Ok(bytes.as_bytes().to_vec());
    }

    let path = extract_path(input)?;
    validate_supported_extension(&path)?;

    std::fs::read(&path).map_err(|err| {
        PyOSError::new_err(format!(
            "parse_error: could not read input file {}: {err}",
            path.display()
        ))
    })
}

fn extract_path(input: &Bound<'_, PyAny>) -> PyResult<PathBuf> {
    if let Ok(path) = input.extract::<PathBuf>() {
        return Ok(path);
    }

    if let Ok(fspath) = input.call_method0("__fspath__") {
        if let Ok(path) = fspath.extract::<PathBuf>() {
            return Ok(path);
        }
    }

    Err(PyTypeError::new_err(
        "input must be a path-like object or bytes",
    ))
}

fn validate_supported_extension(path: &Path) -> PyResult<()> {
    let format = path
        .extension()
        .and_then(|extension| extension.to_str())
        .map(|extension| extension.to_ascii_lowercase());

    match format.as_deref() {
        Some("hwp") | Some("hwpx") => Ok(()),
        _ => Err(PyValueError::new_err(
            "unsupported_format: expected a .hwp or .hwpx input path",
        )),
    }
}

fn convert_options(
    include_locations: bool,
    asset_policy: Option<String>,
    uri_prefix: Option<String>,
) -> PyResult<ConvertOptions> {
    let mut opts = ConvertOptions {
        with_location: include_locations,
        ..ConvertOptions::default()
    };
    opts.resource_policy = resource_policy(asset_policy.as_deref(), uri_prefix.as_deref())?;
    Ok(opts)
}

fn resource_policy(policy: Option<&str>, uri_prefix: Option<&str>) -> PyResult<ResourcePolicy> {
    match policy.unwrap_or("inline") {
        "inline" => Ok(ResourcePolicy::inline()),
        "reference" => Ok(ResourcePolicy::uri_prefix(uri_prefix.unwrap_or(""))),
        "write" => Ok(ResourcePolicy::asset_dir(uri_prefix.unwrap_or(""))),
        "uri" => {
            let prefix = uri_prefix.unwrap_or("");
            if prefix.is_empty() {
                return Err(PyValueError::new_err(
                    "conversion_error: uri_prefix is required for uri asset policy",
                ));
            }
            Ok(ResourcePolicy::uri_prefix(prefix))
        }
        "ignore" => Err(PyValueError::new_err(
            "conversion_error: ignore asset policy is not supported by the Rust engine yet",
        )),
        other => Err(PyValueError::new_err(format!(
            "conversion_error: unknown asset policy {other}"
        ))),
    }
}

fn extract_policy_assets(data: &[u8]) -> Result<Vec<ResourceAsset>, ConvertError> {
    let opts = ConvertOptions {
        resource_policy: ResourcePolicy::asset_dir(""),
        ..ConvertOptions::default()
    };
    hangulang_engine::convert(data, &opts).map(|outcome| outcome.assets)
}

fn serialize_json<T: Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|err| {
        PyRuntimeError::new_err(format!(
            "conversion_error: could not serialize JSON output: {err}"
        ))
    })
}

fn write_asset(output_dir: &Path, asset: &ResourceAsset) -> PyResult<()> {
    let path = output_dir.join(&asset.path);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|err| {
            PyOSError::new_err(format!(
                "conversion_error: could not create asset output directory {}: {err}",
                parent.display()
            ))
        })?;
    }

    std::fs::write(&path, &asset.data).map_err(|err| {
        PyOSError::new_err(format!(
            "conversion_error: could not write asset file {}: {err}",
            path.display()
        ))
    })
}

fn asset_refs(
    assets: Vec<ResourceAsset>,
    policy: &str,
    output_dir: Option<&str>,
    uri_prefix: Option<&str>,
) -> PyResult<Vec<AssetRef>> {
    let output_dir = output_dir.map(PathBuf::from);
    let mut refs = Vec::with_capacity(assets.len());

    for asset in assets {
        if policy == "write" {
            let Some(output_dir) = output_dir.as_deref() else {
                return Err(PyValueError::new_err(
                    "conversion_error: output_dir is required for write asset policy",
                ));
            };
            write_asset(output_dir, &asset)?;
        }

        let uri = match policy {
            "inline" => Some(hangulang_engine::resources::data_uri(&asset.mime, &asset.data)),
            "write" | "uri" => Some(join_uri(uri_prefix.unwrap_or(""), &asset.path)),
            "reference" => Some(asset.path.clone()),
            _ => None,
        };

        refs.push(AssetRef {
            id: asset.path.clone(),
            path: asset.path,
            uri,
            mime_type: asset.mime,
        });
    }

    Ok(refs)
}

fn join_uri(prefix: &str, path: &str) -> String {
    let prefix = prefix.trim_end_matches('/');
    if prefix.is_empty() {
        path.to_string()
    } else {
        format!("{prefix}/{path}")
    }
}

fn map_convert_error(err: ConvertError) -> PyErr {
    match err {
        ConvertError::UnsupportedFormat(_)
        | ConvertError::EncryptedDocument
        | ConvertError::DistributionDocumentUnsupported => {
            PyValueError::new_err(format!("unsupported_format: {err}"))
        }
        ConvertError::Parse(_) => PyValueError::new_err(format!("parse_error: {err}")),
        ConvertError::Xml(_) | ConvertError::Json(_) => {
            PyRuntimeError::new_err(format!("conversion_error: {err}"))
        }
    }
}

#[pyfunction]
#[pyo3(signature = (input, include_locations=false, asset_policy=None, uri_prefix=None))]
fn convert_to_doclang(
    input: &Bound<'_, PyAny>,
    include_locations: bool,
    asset_policy: Option<String>,
    uri_prefix: Option<String>,
) -> PyResult<String> {
    let data = input_bytes(input)?;
    let opts = convert_options(include_locations, asset_policy, uri_prefix)?;
    hangulang_engine::convert(&data, &opts)
        .map(|outcome| outcome.xml)
        .map_err(map_convert_error)
}

#[pyfunction]
#[pyo3(signature = (input, include_locations=false, asset_policy=None, uri_prefix=None))]
fn convert_to_markdown(
    input: &Bound<'_, PyAny>,
    include_locations: bool,
    asset_policy: Option<String>,
    uri_prefix: Option<String>,
) -> PyResult<String> {
    let data = input_bytes(input)?;
    let opts = convert_options(include_locations, asset_policy, uri_prefix)?;
    hangulang_engine::convert_to_markdown(&data, &opts)
        .map(|outcome| outcome.markdown)
        .map_err(map_convert_error)
}

#[pyfunction]
#[pyo3(signature = (input, include_locations=false, asset_policy=None, uri_prefix=None))]
fn convert_to_payload_json(
    input: &Bound<'_, PyAny>,
    include_locations: bool,
    asset_policy: Option<String>,
    uri_prefix: Option<String>,
) -> PyResult<String> {
    let data = input_bytes(input)?;
    let opts = convert_options(include_locations, asset_policy, uri_prefix)?;
    hangulang_engine::convert_to_json(&data, &opts).map_err(map_convert_error)
}

#[pyfunction]
#[pyo3(signature = (input, asset_policy=None, output_dir=None, uri_prefix=None))]
fn extract_assets_json(
    input: &Bound<'_, PyAny>,
    asset_policy: Option<String>,
    output_dir: Option<String>,
    uri_prefix: Option<String>,
) -> PyResult<String> {
    let policy = asset_policy.unwrap_or_else(|| "reference".to_string());
    if policy == "ignore" {
        return serialize_json(&Vec::<AssetRef>::new());
    }

    match policy.as_str() {
        "inline" | "reference" | "write" => {}
        "uri" => {
            if uri_prefix.as_deref().unwrap_or("").is_empty() {
                return Err(PyValueError::new_err(
                    "conversion_error: uri_prefix is required for uri asset policy",
                ));
            }
        }
        other => {
            return Err(PyValueError::new_err(format!(
                "conversion_error: unknown asset policy {other}"
            )));
        }
    }

    if policy == "write" && output_dir.as_deref().unwrap_or("").is_empty() {
        return Err(PyValueError::new_err(
            "conversion_error: output_dir is required for write asset policy",
        ));
    }

    let data = input_bytes(input)?;
    let assets = extract_policy_assets(&data).map_err(map_convert_error)?;
    let refs = asset_refs(assets, &policy, output_dir.as_deref(), uri_prefix.as_deref())?;
    serialize_json(&refs)
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(convert_to_doclang, m)?)?;
    m.add_function(wrap_pyfunction!(convert_to_markdown, m)?)?;
    m.add_function(wrap_pyfunction!(convert_to_payload_json, m)?)?;
    m.add_function(wrap_pyfunction!(extract_assets_json, m)?)?;
    Ok(())
}
