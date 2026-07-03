# Clinical Trial Analysis Code Generator

A web-based tool that generates **submission-ready** SAS, R, and Python code for clinical trial analysis, compliant with CDISC standards (ADaM/SDTM) and health authority requirements (FDA, EMA, PMDA).

## Features

- **Multi-language support**: SAS, R, Python
- **Analysis types**: Descriptive, Efficacy, Safety, Survival, MMRM, Categorical, PK, Subgroup
- **Output types**: Tables, Figures, Listings, Datasets
- **CDISC compliance**: ADaM IG v1.3, SDTM IG v3.4
- **Regulatory targeting**: FDA, EMA, PMDA, NMPA, Health Canada
- **Shell upload**: Upload RTF/Excel mock-ups to match output layout
- **Specification upload**: Upload variable/dataset specifications
- **Validation**: Automatic CDISC compliance checking

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+

### Installation

```bash
# Clone and navigate
cd clinical-code-generator

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
npm install