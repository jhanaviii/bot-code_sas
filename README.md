# ClinGen — Clinical Trial Analysis Code Generator

> **Submission-ready SAS, R, and Python code for clinical trials — generated in seconds.**  
> CDISC ADaM IG v1.3 · SDTM IG v3.4 · ICH E9 compliant · Supports FDA, EMA, PMDA, NMPA, Health Canada

---

## What Is This?

ClinGen is a web-based tool designed for **clinical programmers and biostatisticians** working on health-authority submissions. You fill in your study parameters through a clean UI, click **Generate Code**, and receive production-quality analysis code in SAS, R, or Python — complete with:

- Proper program headers (study ID, protocol, sponsor, regulatory authority)
- CDISC-compliant dataset access and population-flag filtering
- Statistical analysis logic (ANCOVA, MMRM, Kaplan-Meier, Cox, etc.)
- Submission-format output (RTF, XPT, PDF, XLSX)
- Automatic CDISC compliance validation with a checklist of passed checks, warnings, and errors

No AI inference engine is required. The code is generated deterministically from your parameters by a set of specialized generator classes — meaning the output is predictable, auditable, and safe for regulatory submissions.

---

## Architecture Overview

```
design-bot/
└── Clinical-code-generator/
    ├── backend/                    Python Flask REST API
    │   ├── app.py                  Main API server (port 5000)
    │   ├── generators/
    │   │   ├── sas_generator.py    Generates SAS programs (~789 lines of output)
    │   │   ├── r_generator.py      Generates R scripts (tidyverse / pharmaverse)
    │   │   └── python_generator.py Generates Python scripts (pandas / statsmodels)
    │   ├── validators/
    │   │   └── cdisc_validator.py  Checks code against CDISC standards
    │   └── requirements.txt
    ├── frontend/
    │   ├── index.html              Single-page application
    │   ├── css/styles.css          Professional dark-glass UI theme
    │   └── js/app.js               Frontend logic and API integration
    ├── uploads/                    Temporary storage for uploaded shells/specs
    └── output/                     Generated code files saved here
```

### How The Request Flows

```
Browser                  Flask API (port 5000)             Disk
  │                             │                            │
  ├─ POST /api/generate ───────>│                            │
  │  { language, analysis_type  │                            │
  │    output_type, variables,  │                            │
  │    parameters, submission } │                            │
  │                             ├── pick generator ──────────┤
  │                             │   (SAS / R / Python)       │
  │                             │                            │
  │                             ├── generator.generate() ────┤
  │                             │   ┌──────────────────┐     │
  │                             │   │ _generate_header │     │
  │                             │   │ _generate_setup  │     │
  │                             │   │ _generate_data   │     │
  │                             │   │ _generate_analysis│    │
  │                             │   │ _generate_output │     │
  │                             │   │ _generate_footer │     │
  │                             │   └──────────────────┘     │
  │                             │                            │
  │                             ├── CDISCValidator.validate()─┤
  │                             │   checks required variables │
  │                             │   population flags, metadata│
  │                             │                            │
  │                             ├── save to output/ ─────────>│
  │                             │                            │
  │<── JSON response ───────────┤                            │
  │  { code, validation,        │                            │
  │    metadata, filename }     │                            │
```

---

## Backend — Flask API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Returns API version, status, supported languages |
| `POST` | `/api/generate` | **Main endpoint** — generates analysis code |
| `POST` | `/api/upload/shell` | Upload an output shell template (RTF/Excel/PDF/DOCX) |
| `POST` | `/api/upload/specification` | Upload a variable specification (Excel/CSV/JSON) |
| `GET`  | `/api/download/<filename>` | Download a previously generated file |
| `GET`  | `/api/templates` | Full catalogue of analysis types, populations, methods |
| `GET`  | `/api/outputs` | List all generated output files on disk |

### POST `/api/generate` — Request Schema

```json
{
  "language": "sas | r | python",
  "analysis_type": "descriptive | efficacy | safety | survival | mixed_model | categorical | pk | subgroup",
  "output_type": "table | figure | listing | dataset",

  "input_data": {
    "datasets": ["adsl", "adae"],
    "format": "adam | sdtm | raw",
    "library_path": "/data/study123/adam"
  },

  "output_data": {
    "dataset_name": "t_ae_summary",
    "format": "rtf | pdf | xlsx | xpt | sas7bdat | csv",
    "output_path": "/output/tables"
  },

  "variables": {
    "analysis_variables":  ["AVAL", "CHG"],
    "grouping_variables":  ["TRTA", "AVISIT"],
    "filter_variables":    ["SAFFL"],
    "sort_variables":      ["USUBJID", "AVISITN"]
  },

  "analysis_parameters": {
    "statistical_method": "anova | chi_square | cox_regression | kaplan_meier | mmrm | ...",
    "alpha": 0.05,
    "confidence_level": 0.95,
    "population": "safety | itt | per_protocol | full_analysis | pk",
    "treatment_variable": "TRTA",
    "covariates": ["BASE", "SITEID"],
    "subgroup_variables": ["SEX", "AGEGR1", "RACE"]
  },

  "submission_details": {
    "study_id": "STUDY-001",
    "sponsor": "AstraZeneca",
    "protocol": "D1234C00001",
    "regulatory_authority": "FDA | EMA | PMDA | NMPA | HC",
    "submission_type": "NDA | BLA | MAA | sNDA"
  },

  "shell_file_id": null,
  "specification_file_id": null
}
```

### Response

```json
{
  "success": true,
  "code": "/* Full SAS program text */",
  "filename": "table_safety_20260608_143022.sas",
  "language": "sas",
  "validation": {
    "compliant": true,
    "checks":   ["✓ Population flag SAFFL used", "✓ Output title present", ...],
    "warnings": [],
    "errors":   []
  },
  "metadata": {
    "generated_at":    "2026-06-08T14:30:22.123456",
    "analysis_type":   "safety",
    "output_type":     "table",
    "language":        "sas",
    "line_count":      312,
    "char_count":      14280,
    "submission_ready": true
  }
}
```

---

## Code Generators

Each generator follows the same six-phase pipeline:

```
generate()
 ├── _generate_header()      Program ID, study/protocol/sponsor, date, purpose
 ├── _generate_setup()       %LET macros / variables / imports / CONFIG dict
 ├── _generate_data_access() LIBNAME / haven::read_sas / pd.read_sas, filters
 ├── _generate_analysis()    Statistical procedure code (analysis-type specific)
 ├── _generate_output()      PROC REPORT / flextable / openpyxl output formatting
 └── _generate_footer()      QC notes, reviewer section, program end
```

### Analysis Types

| Type | SAS | R | Python |
|------|-----|---|--------|
| Descriptive | `PROC MEANS` | `gtsummary::tbl_summary` | `pandas.describe` + custom |
| Efficacy | `PROC MIXED` ANCOVA | `mmrm` + `emmeans` | `statsmodels OLS` |
| Safety | `PROC SQL` + `PROC REPORT` | `dplyr` + `rtables` | `pandas groupby` |
| Survival | `PROC LIFETEST` + `PROC PHREG` | `survminer::ggsurvplot` + `coxph` | `lifelines` KM + CoxPH |
| Mixed Model | `PROC MIXED` MMRM | `mmrm` package | `statsmodels MixedLM` |
| Categorical | `PROC FREQ` + CMH | `gtsummary` + CMH | `scipy.stats` chi2/fisher |
| PK | `PROC MEANS` + geometric mean | `PKNCA` / `NonCompart` | `pandas` + geometric CV |
| Subgroup | Macro forest plot | `ggplot2` forest | `matplotlib` forest |

### CDISC Validator

The validator checks generated code against CDISC standards:

- **Required variables** — confirms ADaM dataset variables (STUDYID, USUBJID, PARAMCD, etc.) are referenced for each dataset type (ADSL, ADAE, ADTTE, ADLB)
- **Population flags** — verifies the correct flag (SAFFL, ITTFL, PPROTFL, PKFL, FASFL) is used for the selected population
- **Output metadata** — checks for title, footnote, source, and program name in the generated output
- **Regulatory compliance** — validates XPT format requirement for FDA, traceability markers for all authorities

---

## Frontend — SPA

The single-page application (`index.html`) is built with vanilla JavaScript and renders entirely in the browser — no bundler, no framework, no build step.

### Panel Structure

```
┌────────────────────────────────────────────────────────────────────┐
│  Header: ClinGen logo · CDISC badge · API status · Settings        │
├──────────────────────────┬─────────────────────────────────────────┤
│  Config Panel (360px)    │  Output Panel                           │
│  ─────────────────────   │  ────────────────────────────────────── │
│  ▸ Language (SAS/R/Py)  │  Tabs: Generated Code | Validation |    │
│  ▸ Analysis Type grid   │        Metadata                         │
│  ▸ Output Type grid     │                                          │
│  ▸ Input Data           │  Code Tab:                               │
│  ▸ Variables            │    Lang badge · line/byte stats          │
│  ▸ Parameters           │    Syntax-highlighted code block         │
│  ▸ Submission Details   │    (JetBrains Mono, highlight.js)        │
│  ▸ Upload Files         │                                          │
│  ──────────────────────  │  Validation Tab:                         │
│  [✦ Generate Code]      │    Compliance summary banner             │
│                          │    Checks / Warnings / Errors lists     │
│                          │                                          │
│                          │  Metadata Tab:                           │
│                          │    Submission-ready badge                │
│                          │    Generation details grid               │
├──────────────────────────┴─────────────────────────────────────────┤
│  Footer: version · CDISC ADaM · SDTM · ICH E9                     │
└────────────────────────────────────────────────────────────────────┘
```

### UI Design System

- **Theme**: Dark glass — deep navy backgrounds with subtle grid overlay
- **Accent**: Blue-to-purple gradient (`#4f8ef7 → #8b6cf7`)
- **Typography**: Inter (UI) + JetBrains Mono (code)
- **Borders**: 7% white opacity with blue tint on hover/focus
- **States**: Animated pulse for live API status, loading spinner on generate, success/error toasts

---

## Running Locally

### Prerequisites

- Python 3.9+
- Node.js 16+ (only needed for `live-server`)

### Backend

```bash
cd Clinical-code-generator/backend
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

### Frontend

```bash
cd Clinical-code-generator
npx live-server frontend --port=3000
# → http://localhost:3000
```

Or open `frontend/index.html` directly in a browser — it works without a dev server (CORS is enabled on the backend).

### Running Both Together

```bash
cd bot-for-sas/Clinical-code-generator
npm install
npm start          # uses concurrently to launch both
```

---

## Supported Regulatory Submissions

| Authority | Region | Format Requirements |
|-----------|--------|---------------------|
| FDA | United States | XPT v5 transport files, CDISC SDTM/ADaM, eCTD |
| EMA | European Union | CDISC SDTM/ADaM, NeeS/eCTD |
| PMDA | Japan | CDISC SDTM/ADaM with Japanese labelling |
| NMPA | China | CDISC preferred, local format accepted |
| Health Canada | Canada | CDISC SDTM/ADaM, eCTD |

---

## Population Flags (CDISC ADaM)

| Population | Flag | Description |
|------------|------|-------------|
| Safety | `SAFFL` | All subjects who received ≥1 dose |
| Intent-to-Treat | `ITTFL` | All randomised subjects |
| Per Protocol | `PPROTFL` | Subjects without major protocol deviations |
| Full Analysis Set | `FASFL` | ITT-equivalent per ICH E9 |
| PK | `PKFL` | Subjects with evaluable PK data |

---

## Project Status

- Core generation engine: **complete** — SAS, R, Python generators all functional
- CDISC validation: **complete** — ADaM IG v1.3 / SDTM IG v3.4 checks
- Frontend UI: **complete** — professional dark-glass design, fully interactive
- File upload / shell parsing: **complete** — RTF, Excel, PDF, DOCX, JSON
- Output download: **complete** — generated files persisted and downloadable
- Regulatory authority targeting: **complete** — FDA, EMA, PMDA, NMPA, HC

---

## License

Internal tooling — not yet open-sourced.
