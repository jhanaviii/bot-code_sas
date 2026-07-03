"""
ClinGen — Clinical Trial Analysis Code Generator Backend API
Generates submission-ready SAS, R, and Python code compliant with
CDISC ADaM IG v1.3 / SDTM IG v3.4 and ICH E9 guidelines.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import logging
import time
from datetime import datetime
from functools import wraps

from generators.sas_generator import SASCodeGenerator
from generators.r_generator import RCodeGenerator
from generators.python_generator import PythonCodeGenerator
from validators.cdisc_validator import CDISCValidator

# ── App setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ARC")

# ── Paths & config ─────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "..", "output")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    OUTPUT_FOLDER=OUTPUT_FOLDER,
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50 MB
)

ALLOWED_UPLOAD_EXTENSIONS = {"xlsx", "xls", "csv", "docx", "pdf", "json", "sas7bdat", "xpt", "rtf"}
GENERATORS = {"sas": SASCodeGenerator, "r": RCodeGenerator, "python": PythonCodeGenerator}
FILE_EXTENSIONS = {"sas": ".sas", "r": ".R", "python": ".py"}


# ── Helpers ────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def err(message: str, status: int = 400):
    logger.warning("Client error %d: %s", status, message)
    return jsonify({"success": False, "error": message}), status


def timing(fn):
    """Decorator — logs endpoint execution time."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("%s completed in %.1f ms", fn.__name__, elapsed)
        return result
    return wrapper


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status":    "healthy",
        "version":   "2.0.0",
        "service":   "ARC",
        "timestamp": datetime.now().isoformat(),
        "languages": list(GENERATORS.keys()),
        "uptime_ts": _start_time,
    })


@app.route("/api/generate", methods=["POST"])
@timing
def generate_code():
    """
    Generate submission-ready analysis code.

    Required JSON fields: language, analysis_type, output_type, input_data, variables
    """
    data = request.get_json(silent=True)
    if not data:
        return err("Request body must be valid JSON.")

    # Validate required top-level fields
    required = ["language", "analysis_type", "output_type", "input_data", "variables"]
    missing  = [f for f in required if f not in data]
    if missing:
        return err(f"Missing required fields: {', '.join(missing)}")

    language = data["language"].lower()
    if language not in GENERATORS:
        return err(f"Unsupported language '{language}'. Choose: {', '.join(GENERATORS)}")

    analysis_type = data.get("analysis_type", "")
    if not analysis_type:
        return err("analysis_type is required.")

    logger.info("Generating %s code — analysis=%s output=%s", language, analysis_type, data.get("output_type"))

    try:
        generator = GENERATORS[language](data)

        # Optionally attach shell / spec metadata
        shell_meta = _load_file_metadata(generator, data.get("shell_file_id"), "parse_shell")
        spec_meta  = _load_file_metadata(generator, data.get("specification_file_id"), "parse_specification")

        generated_code = generator.generate(
            shell_metadata=shell_meta,
            spec_metadata=spec_meta,
        )

        # CDISC compliance validation
        validator        = CDISCValidator()
        validation_result = validator.validate(data, generated_code)

        # Persist to disk
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data['output_type']}_{analysis_type}_{ts}{FILE_EXTENSIONS[language]}"
        out_path = os.path.join(OUTPUT_FOLDER, filename)

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(generated_code)

        logger.info("Saved generated file: %s (%d chars)", filename, len(generated_code))

        return jsonify({
            "success":    True,
            "code":       generated_code,
            "filename":   filename,
            "language":   language,
            "validation": validation_result,
            "metadata": {
                "generated_at":    datetime.now().isoformat(),
                "analysis_type":   analysis_type,
                "output_type":     data.get("output_type"),
                "language":        language,
                "line_count":      generated_code.count("\n") + 1,
                "char_count":      len(generated_code),
                "submission_ready": validation_result.get("compliant", False),
            },
        })

    except Exception as exc:
        logger.exception("Code generation failed: %s", exc)
        return err(f"Code generation error: {exc}", 500)


@app.route("/api/generate-all", methods=["POST"])
@timing
def generate_all_languages():
    """
    Generate submission-ready code in ALL three languages simultaneously.
    Returns SAS, R, and Python code in a single response.

    Required JSON fields: analysis_type, output_type, input_data, variables
    """
    data = request.get_json(silent=True)
    if not data:
        return err("Request body must be valid JSON.")

    # Validate required top-level fields (language NOT required here)
    required = ["analysis_type", "output_type", "input_data", "variables"]
    missing  = [f for f in required if f not in data]
    if missing:
        return err(f"Missing required fields: {', '.join(missing)}")

    analysis_type = data.get("analysis_type", "")
    if not analysis_type:
        return err("analysis_type is required.")

    logger.info("Generating ALL languages — analysis=%s output=%s", analysis_type, data.get("output_type"))

    results = {}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for language in ["sas", "r", "python"]:
        try:
            # Build per-language payload (inject language into data copy)
            lang_data = {**data, "language": language}

            generator = GENERATORS[language](lang_data)

            # Optionally attach shell / spec metadata
            shell_meta = _load_file_metadata(generator, data.get("shell_file_id"), "parse_shell")
            spec_meta  = _load_file_metadata(generator, data.get("specification_file_id"), "parse_specification")

            generated_code = generator.generate(
                shell_metadata=shell_meta,
                spec_metadata=spec_meta,
            )

            # CDISC compliance validation
            validator         = CDISCValidator()
            validation_result = validator.validate(lang_data, generated_code)

            # Persist to disk
            filename = f"{data['output_type']}_{analysis_type}_{ts}{FILE_EXTENSIONS[language]}"
            out_path = os.path.join(OUTPUT_FOLDER, filename)

            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(generated_code)

            logger.info("Saved %s file: %s (%d chars)", language.upper(), filename, len(generated_code))

            results[language] = {
                "code":       generated_code,
                "filename":   filename,
                "validation": validation_result,
                "metadata": {
                    "generated_at":    datetime.now().isoformat(),
                    "analysis_type":   analysis_type,
                    "output_type":     data.get("output_type"),
                    "language":        language,
                    "line_count":      generated_code.count("\n") + 1,
                    "char_count":      len(generated_code),
                    "submission_ready": validation_result.get("compliant", False),
                },
            }

        except Exception as exc:
            logger.exception("Generation failed for %s: %s", language, exc)
            results[language] = {
                "code":       "",
                "filename":   None,
                "error":      str(exc),
                "validation": {"compliant": False, "checks": [], "warnings": [], "errors": [str(exc)]},
                "metadata": {
                    "generated_at":  datetime.now().isoformat(),
                    "analysis_type": analysis_type,
                    "output_type":   data.get("output_type"),
                    "language":      language,
                    "line_count":    0,
                    "char_count":    0,
                    "submission_ready": False,
                },
            }

    return jsonify({
        "success": True,
        "results": results,
    })


def _load_file_metadata(generator, file_id, method_name):
    """Load optional shell/spec file and call the appropriate parser."""
    if not file_id:
        return None
    path = os.path.join(UPLOAD_FOLDER, secure_filename(file_id))
    if not os.path.exists(path):
        logger.warning("Referenced file not found: %s", file_id)
        return None
    parser = getattr(generator, method_name, None)
    if callable(parser):
        try:
            return parser(path)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", file_id, exc)
    return None


@app.route("/api/upload/<upload_type>", methods=["POST"])
@timing
def upload_file(upload_type: str):
    """
    Upload a reference file (output shell or variable specification).
    upload_type: 'shell' | 'specification'
    """
    if upload_type not in ("shell", "specification"):
        return err(f"Unknown upload type '{upload_type}'.")

    if "file" not in request.files:
        return err("No file provided in request.")

    file = request.files["file"]
    if not file.filename:
        return err("File has no name.")

    if not allowed_file(file.filename):
        exts = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        return err(f"File type not allowed. Accepted: {exts}")

    filename   = secure_filename(file.filename)
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{upload_type}_{ts}_{filename}"
    save_path  = os.path.join(UPLOAD_FOLDER, saved_name)
    file.save(save_path)

    size_kb = os.path.getsize(save_path) / 1024
    logger.info("Uploaded %s: %s (%.1f KB)", upload_type, saved_name, size_kb)

    return jsonify({
        "success":     True,
        "file_id":     saved_name,
        "filename":    filename,
        "type":        upload_type,
        "size_kb":     round(size_kb, 1),
        "uploaded_at": datetime.now().isoformat(),
    })


@app.route("/api/download/<filename>", methods=["GET"])
def download_code(filename: str):
    """Download a previously generated code file."""
    safe_name = secure_filename(filename)
    filepath  = os.path.join(OUTPUT_FOLDER, safe_name)
    if not os.path.exists(filepath):
        return err("File not found.", 404)
    return send_file(filepath, as_attachment=True)


@app.route("/api/templates", methods=["GET"])
def get_templates():
    """Return the catalogue of available analysis templates and valid options."""
    return jsonify({
        "analysis_types": [
            {"id": "descriptive",  "name": "Descriptive Statistics",  "description": "n, mean, SD, median, quartiles, min, max"},
            {"id": "efficacy",     "name": "Efficacy Analysis",        "description": "Primary/secondary endpoint ANCOVA with LS means"},
            {"id": "safety",       "name": "Safety Analysis",          "description": "AE summaries by SOC/PT, incidence rates"},
            {"id": "survival",     "name": "Survival Analysis",        "description": "Kaplan-Meier, Cox regression, log-rank test"},
            {"id": "mixed_model",  "name": "Mixed Models (MMRM)",      "description": "Mixed-model repeated measures with unstructured covariance"},
            {"id": "categorical",  "name": "Categorical Analysis",     "description": "CMH, chi-square, Fisher's exact, logistic regression"},
            {"id": "pk",           "name": "Pharmacokinetics",         "description": "PK parameter summaries, geometric means"},
            {"id": "subgroup",     "name": "Subgroup Analysis",        "description": "Forest plots, interaction tests"},
        ],
        "output_types": [
            {"id": "table",   "name": "Summary Table",  "formats": ["rtf", "pdf", "xlsx", "html"]},
            {"id": "figure",  "name": "Figure / Graph", "formats": ["pdf", "png", "svg", "rtf"]},
            {"id": "listing", "name": "Data Listing",   "formats": ["rtf", "pdf", "xlsx"]},
            {"id": "dataset", "name": "Analysis Dataset","formats": ["xpt", "sas7bdat", "csv", "rds"]},
        ],
        "populations": [
            {"id": "safety",        "name": "Safety Population",   "flag": "SAFFL"},
            {"id": "itt",           "name": "Intent-to-Treat",     "flag": "ITTFL"},
            {"id": "per_protocol",  "name": "Per Protocol",        "flag": "PPROTFL"},
            {"id": "pk",            "name": "PK Population",       "flag": "PKFL"},
            {"id": "full_analysis", "name": "Full Analysis Set",   "flag": "FASFL"},
        ],
        "statistical_methods": [
            {"id": "anova",               "name": "ANOVA / ANCOVA"},
            {"id": "chi_square",          "name": "Chi-Square Test"},
            {"id": "fisher_exact",        "name": "Fisher's Exact Test"},
            {"id": "cox_regression",      "name": "Cox Proportional Hazards"},
            {"id": "kaplan_meier",        "name": "Kaplan-Meier Estimation"},
            {"id": "log_rank",            "name": "Log-Rank Test"},
            {"id": "mmrm",                "name": "Mixed Model Repeated Measures"},
            {"id": "logistic_regression", "name": "Logistic Regression"},
            {"id": "cmh",                "name": "Cochran-Mantel-Haenszel"},
            {"id": "wilcoxon",            "name": "Wilcoxon Rank-Sum Test"},
        ],
        "regulatory_authorities": [
            {"id": "FDA",  "name": "FDA (US)"},
            {"id": "EMA",  "name": "EMA (EU)"},
            {"id": "PMDA", "name": "PMDA (Japan)"},
            {"id": "NMPA", "name": "NMPA (China)"},
            {"id": "HC",   "name": "Health Canada"},
        ],
        "languages": [
            {"id": "sas",    "name": "SAS",    "version": "9.4+"},
            {"id": "r",      "name": "R",      "version": "4.0+"},
            {"id": "python", "name": "Python", "version": "3.9+"},
        ],
    })


@app.route("/api/outputs", methods=["GET"])
def list_outputs():
    """List all previously generated output files."""
    try:
        files = []
        for fname in sorted(os.listdir(OUTPUT_FOLDER), reverse=True):
            fpath = os.path.join(OUTPUT_FOLDER, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                files.append({
                "filename":    fname,
                "size_kb":     round(stat.st_size / 1024, 1),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        return jsonify({"success": True, "files": files, "count": len(files)})
    except Exception as exc:
        return err(str(exc), 500)


# ── Error handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(413)
def too_large(_):
    return jsonify({"success": False, "error": "File exceeds 50 MB limit"}), 413


@app.errorhandler(500)
def internal_error(exc):
    logger.exception("Unhandled error: %s", exc)
    return jsonify({"success": False, "error": "Internal server error"}), 500


# ── Entry point ────────────────────────────────────────────────────────────
_start_time = datetime.now().isoformat()

if __name__ == "__main__":
    logger.info("ARC backend starting on http://0.0.0.0:5001")
    app.run(debug=True, host="0.0.0.0", port=5001, use_reloader=False)