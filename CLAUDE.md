# CLAUDE.md - Project Documentation for AI Assistants

## Project Overview

This is a **Public Health Scotland research repository** for modeling the drivers of economic inactivity, particularly examining how health factors influence transitions between employment states. The project combines an R package with Quarto-based analysis notebooks and reports.

**Primary Research Question**: How do health conditions affect transitions between economic activity states (especially Employed ↔ Long-term Sick)?

**Data Source**: UK Household Longitudinal Study (UKHLS) "Understanding Society" - Waves 1-13 (2009-2022)

## Repository Structure

```
economic_inactivity/
├── R/                      # Core package functions (load via devtools::load_all())
├── tests/testthat/         # Unit tests (100+ tests, run with testthat)
├── notebooks/              # 90+ exploratory analysis notebooks (.qmd)
├── reports/                # Technical papers and formal reports
│   ├── technical-paper/    # Main methodological paper
│   └── ifoa/               # Institute and Faculty of Actuaries collaboration
├── papers/                 # Research papers in development
├── apps/                   # Shiny applications
├── data/                   # Bundled package data (.rda files)
├── data-raw/               # Source data and processing scripts
├── big_data/               # UKHLS data (not in git - requires separate download)
└── support/                # Analysis outputs (CSVs)
```

## How to Use This Package

### Loading Package Functions

All notebooks and reports use this pattern:
```r
library(here)
library(tidyverse)
devtools::load_all(here::here("R"))
```

### Key Exported Functions

**Data Extraction** (from `R/ukhls_data_extractors.R`):
- `read_and_slim_data(filepath, varnames)` - Read Stata file, extract specific variables
- `extract_vars_and_make_long(filepath, varnames, extract_what)` - Extract and pivot to long format
- `convert_varname_selection_to_regex(varnames)` - Build regex for wave-prefixed variables

**Data Reshaping** (from `R/ukhls_data_reshapers.R`):
- `get_ind_level_vars_for_selected_waves(...)` - Main wrapper for individual-level extraction
- `simplify_econ_status_categories(df, col, level)` - Recode jbstat (levels 1-4)
- `smartly_widen_ind_dataframe(df)` - Convert long to wide format
- `pull_next_wave_status(df)` - Get economic status from next wave (for transitions)

**Modeling** (from `R/model_helpers.R`):
- `calculate_baseline_counterfactual_distribution(model, data, ...)` - PAF/SAF calculations
- `plot_scenario_comparisons(results)` - Visualize baseline vs counterfactual
- `make_tabular_summary(results)` - Format results tables

**Utilities** (from `R/ukhls_helpers.R`):
- `return_labels_as_factors(df)` - Convert haven_labelled to character
- `standardise_scores(x)` - Z-score standardization

### Economic Status Categories

The `simplify_econ_status_categories()` function uses `data/econActGroups.rda` to recode `jbstat`:

| Level | Categories |
|-------|-----------|
| 1 | Active, Inactive |
| 2 | Employed, Unemployed, Inactive |
| 3 | Employed, Unemployed, LT Sick, Student, Carer, Retired, Other |
| 4 | Original categories with tidied labels |

**For IFoA work**: Level 3 is most relevant (distinguishes Long-term Sick from other inactive).

## UKHLS Data Structure

### File Location
```
big_data/UKDA-6614-stata/stata/stata13_se/ukhls/
```

### File Naming Convention
- Wave prefix: a=1, b=2, ..., m=13
- Individual response: `{wave}_indresp.dta`
- Household response: `{wave}_hhresp.dta`

### Key Variables

**Currently Used**:
| Variable | Description | Type |
|----------|-------------|------|
| `jbstat` | Economic activity status | Categorical |
| `dvage` | Age | Numeric |
| `sex` | Sex (1=Male, 2=Female) | Categorical |
| `sf12mcs_dv` | SF-12 Mental Component Score | Numeric (0-100) |
| `sf12pcs_dv` | SF-12 Physical Component Score | Numeric (0-100) |
| `health` | Limiting long-term illness | Binary |
| `hiqual_dv` | Highest qualification | Categorical |

**Available for Occupation Analysis (NS-SEC)**:
| Variable | Description | Categories |
|----------|-------------|------------|
| `jbnssec3_dv` | NS-SEC 3-class | Management & professional, Intermediate, Routine |
| `jbnssec5_dv` | NS-SEC 5-class | Adds: Small employers & own account, Lower supervisory & technical |
| `jbnssec8_dv` | NS-SEC 8-class | Full NS-SEC classification |

**Note**: NS-SEC variables have missing value codes: -9 (missing), -8 (inapplicable), -7 (proxy), -2 (refusal), -1 (don't know)

## Model Specifications

### Foundational Model
```r
next_status ~ this_status * sex + splines::bs(age, df = 5)
```

### Extended Model (Discrete Health)
```r
next_status ~ this_status * sex + splines::bs(age, df = 5) + health
```

### Extended Model (Continuous Health)
```r
next_status ~ this_status * sex + splines::bs(age, df = 5) + sf12mcs_dv_std + sf12pcs_dv_std
```

### Modeling Notes
- Uses `nnet::multinom()` for multinomial logistic regression
- Default: `maxit = 1000` for convergence (often needs more)
- For testing/development: use `maxit = 100` to check code runs
- **Caching**: Models are computationally expensive. Use `#| cache: true` in Quarto chunks
- **Pattern**: Fit models in separate cached chunks, then reference in later chunks
- Model comparison via AIC/BIC

### Quarto/Knitr Model Fitting Pattern

For reliable model fitting in Quarto reports:
```r
#| label: fit-model
#| cache: true
#| include: false

model <- nnet::multinom(
  next_status ~ this_status * sex + splines::bs(age, 5) + sf12mcs_dv + sf12pcs_dv,
  data = ind_data_standardised,
  maxit = 1000
)
```

Then reference `model` in subsequent chunks for tables/plots.

## Quarto Report Patterns

### Standard YAML Frontmatter
```yaml
---
title: "Report Title"
author:
  - "Jon Minton"
  - "Collaborators"
format:
  html:
    toc: true
    code-fold: true
  pdf:
    toc: true
  docx:
    toc: true
bibliography: references.bib
echo: false
warning: false
message: false
---
```

### Package Loading Chunk
```r
#| label: setup
#| include: false

library(here)
library(tidyverse)
library(nnet)
library(knitr)
library(kableExtra)
devtools::load_all(here::here("R"))

base_dir_location <- "big_data/UKDA-6614-stata/stata/stata13_se/ukhls"
```

### Modular Include Pattern
```
{{< include abstract.qmd >}}
{{< include methods.qmd >}}
{{< include results.qmd >}}
```

## Conceptual Overview: EdinbR Presentation

**Location**: [presentations/241123_edinbr.qmd](presentations/241123_edinbr.qmd)

This RevealJS presentation (given to Edinburgh R User Group, November 2024) provides the best conceptual introduction to the modeling framework. **Read this first** to understand the "why" behind the code.

### Key Concepts Explained

1. **GLM Framework**: Separates stochastic component ($Y_i \sim f(\theta_i, \alpha)$) from systematic component ($\theta_i = g(X_i, \beta)$). Reference: King, Tomz & Wittenberg (2000).

2. **Path Dependency / Markov Modeling**:
   - Swap $Y$ for $Y_{T+1}$ on response side
   - Include $Y_T$ on predictor side
   - This is why `this_status` is essential - it encodes the Markov property

3. **Counterfactual Logic**:
   - Split predictors into $X^*$ (controls) and $Z$ (exposures of interest)
   - $H_0 := (X^*, Z_{observed})$ - Baseline scenario
   - $H_1 := (X^*, Z_{modified})$ - Counterfactual scenario
   - Compare $Y|H_0$ vs $Y|H_1$ to estimate effect of $Z$

4. **Continuous Exposures**: Standardised, then moved 1 SD in the "good" direction for counterfactuals

5. **Model Validation**: Foundational model validated via AIC/BIC before adding exposure terms

### Workflow Diagram (from presentation)
```
Data → Foundational Model + Exposure Model
           ↓
    Compare via AIC/BIC
           ↓
    Validated Exposure Model
           ↓
Baseline Data → Predictions (Y|H0)
Counterfactual Data → Predictions (Y|H1)
           ↓
    Compare Results → Report
```

### Example Findings (from presentation)
| Exposure Removed | Effect on LT Sick Population |
|------------------|------------------------------|
| Clinical depression | ~10% reduction |
| MH & PH improved 1 SD | ~30% reduction |

## Sister Project

**econ-inact-handbook** (`/Users/JonMinton/repos/econ-inact-handbook/`)
- Documentation and tutorial website
- Published via Quarto
- Contains worked examples of PAF calculations
- Reference for understanding the modeling approach

## Testing

Run tests with:
```r
devtools::test()
```

All 100+ tests should pass. Tests cover:
- Data extraction functions
- Data reshaping functions
- Model helper functions
- Utility functions

## IFoA Collaboration Notes

### Proposed Analysis Scope
1. **Transitions of interest**: Employed → LT Sick, LT Sick → Employed
2. **Stratification**: Age, Sex, Wave/Year
3. **Potential addition**: Occupation class (NS-SEC)

### NS-SEC Recommendation for IFoA Work
Use **NS-SEC 3-class** (`jbnssec3_dv`) for balance between detail and statistical power:
- Management & professional
- Intermediate
- Routine

This avoids sparse cells while maintaining meaningful occupational distinction.

### Researcher Degrees of Freedom - Key Decisions to Document
1. **Transition definition**: Adjacent waves only vs. any gap
2. **Age range**: 16-64 (working age) vs. broader
3. **Missing data handling**: Complete cases vs. imputation
4. **Model specification**: Which covariates to include
5. **NS-SEC grouping**: 3-class vs. 5-class vs. 8-class

## Publication Notes

### Technical Paper Status

**Location**: [reports/technical-paper/main.qmd](reports/technical-paper/main.qmd)

The technical paper "Simulating the impact of changes to health on economic status using multinomial logistic regression and the UK Household Longitudinal Study" is well-developed and ready for submission consideration.

**Target Journal**: **Quality & Quantity** (Springer)
- International Journal of Methodology
- Impact Factor: ~2.0
- Accepts detailed methodological treatments without strict word limits
- Appendices and technical detail are welcome, not discouraged

**Rationale for Q&Q over higher-IF journals (e.g., JECH)**:
- Paper is a *methods paper with illustrative findings*, not a *findings paper with methods*
- Full technical detail can be retained (appendices, vignettes, model selection)
- Reproducibility and code availability are valued as central, not supplementary
- Less revision likely required; paper can remain intact as intended
- For future high-visibility empirical papers, the IFoA work or others using this framework could target JECH

**Pre-submission checklist**:
- [ ] Confirm paper renders to PDF/DOCX without errors
- [ ] Update "results run correctly as of" date
- [ ] Contact co-authors re: submission and affiliations
- [ ] Gather ORCID iDs
- [ ] Prepare data availability statement (UK Data Service UKHLS access)
- [ ] Check Q&Q specific formatting requirements
- [ ] Draft cover letter emphasising methodological contribution and reproducibility

**Note**: Jon has moved to a new role; this is no longer his primary research area. Publication in Q&Q offers a pragmatic path to getting this work into the literature while preserving its methodological integrity.

## Contact

Jon Minton - jon.minton@phs.scot
