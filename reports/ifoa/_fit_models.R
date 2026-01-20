# =============================================================================
# IFoA Model Fitting Script
# =============================================================================
#
# This script fits multiple multinomial logistic regression models for
# economic status transitions. Designed to run overnight and save all results.
#
# Run from project root:
#   Rscript reports/ifoa/_fit_models.R
#
# Or in background:
#   nohup Rscript reports/ifoa/_fit_models.R > reports/ifoa/logs/model_fit.log 2>&1 &
#
# =============================================================================

library(here)
library(tidyverse)
library(haven)
library(nnet)
library(splines)

# Source package functions
cat("Loading package functions...\n")
r_files <- list.files(here::here("R"), pattern = "\\.R$", full.names = TRUE)
for (f in r_files) source(f)

# Load package data
load(here::here("data", "econActGroups.rda"))

# Create output directories
dir.create(here::here("reports/ifoa/models"), showWarnings = FALSE, recursive = TRUE)
dir.create(here::here("reports/ifoa/logs"), showWarnings = FALSE, recursive = TRUE)

# =============================================================================
# Data Extraction
# =============================================================================
#
# NOTE: The extraction function applies vartypes in alphabetical order of
# extracted variables, not the order specified. To avoid misalignment, we
# extract in two steps: core variables first, then add NS-SEC separately.
#
# =============================================================================

cat("Extracting data from UKHLS...\n")
cat("Start time:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")

# Step 1: Extract core variables (this works correctly)
varnames_core <- c("jbstat", "dvage", "sex", "sf12mcs_dv", "sf12pcs_dv")
vartypes_core <- c("labels", "values", "labels", "values", "values")

cat("Step 1: Extracting core variables...\n")
ind_data <- get_ind_level_vars_for_selected_waves(
  varnames = varnames_core,
  vartypes = vartypes_core,
  waves = letters[1:11],
  econLevel = 3,
  verbose = TRUE
)

cat("Core data extracted:", nrow(ind_data), "observations\n")

# Step 2: Extract NS-SEC separately and join
cat("Step 2: Extracting NS-SEC occupation data...\n")

nssec_data <- extract_ind_from_waves(
  varnames = c("jbnssec3_dv"),
  vartypes = c("labels"),
  verbose = TRUE,
  waves = letters[1:11]
) |>
  smartly_widen_ind_dataframe(
    varnames = c("jbnssec3_dv"),
    vartypes = c("labels")
  )

cat("NS-SEC data extracted:", nrow(nssec_data), "observations\n")

# Join NS-SEC to core data
ind_data <- ind_data |>
  left_join(nssec_data, by = c("pidp", "wave"))

cat("Combined data:", nrow(ind_data), "observations\n")

# =============================================================================
# Data Cleaning
# =============================================================================

cat("Cleaning data...\n")

ind_data_clean <- ind_data |>
  rename(
    age = dvage,
    nssec3 = jbnssec3_dv
  ) |>
  # Handle negative values (UKHLS missing codes)
  mutate(
    across(c(age, sf12mcs_dv, sf12pcs_dv), ~ ifelse(. < 0, NA, .))
  ) |>
  # Clean NS-SEC - extract meaningful categories
  mutate(
    nssec3 = case_when(
      str_detect(nssec3, "Management|management|professional|Professional") ~ "Management & Professional",
      str_detect(nssec3, "Intermediate|intermediate") ~ "Intermediate",
      str_detect(nssec3, "Routine|routine|manual|Manual") ~ "Routine & Manual",
      TRUE ~ NA_character_
    )
  ) |>
  # Working age only
  filter(between(age, 16, 64)) |>
  # Standardise health scores

  mutate(
    sf12mcs_std = standardise_scores(sf12mcs_dv),
    sf12pcs_std = standardise_scores(sf12pcs_dv)
  ) |>
  # Create wave number for trend analysis
  mutate(
    wave_num = match(wave, letters[1:13])
  )

# Complete cases for core variables (age, sex, this_status, next_status)
ind_data_core <- ind_data_clean |>
  filter(complete.cases(age, sex, this_status, next_status))

cat("After core filtering:", nrow(ind_data_core), "observations\n")

# Complete cases including health
ind_data_health <- ind_data_clean |>
  filter(complete.cases(age, sex, this_status, next_status, sf12mcs_std, sf12pcs_std))

cat("With health data:", nrow(ind_data_health), "observations\n")

# Complete cases including health and occupation
ind_data_full <- ind_data_clean |>
  filter(complete.cases(age, sex, this_status, next_status, sf12mcs_std, sf12pcs_std, nssec3))

cat("With health + occupation:", nrow(ind_data_full), "observations\n")

# Save cleaned datasets
saveRDS(ind_data_core, here::here("reports/ifoa/models/data_core.rds"))
saveRDS(ind_data_health, here::here("reports/ifoa/models/data_health.rds"))
saveRDS(ind_data_full, here::here("reports/ifoa/models/data_full.rds"))

cat("Cleaned datasets saved.\n\n")

# =============================================================================
# Model Fitting
# =============================================================================

# Common settings
MAXIT <- 1000  # May need to increase if models don't converge

fit_and_save <- function(formula, data, name, maxit = MAXIT) {
  cat("Fitting model:", name, "\n")
  cat("  Formula:", deparse(formula), "\n")
  cat("  N =", nrow(data), "\n")
  cat("  Start:", format(Sys.time(), "%H:%M:%S"), "\n")

  start_time <- Sys.time()

  tryCatch({
    mod <- nnet::multinom(
      formula,
      data = data,
      maxit = maxit,
      trace = TRUE  # Show convergence progress
    )

    end_time <- Sys.time()
    duration <- difftime(end_time, start_time, units = "mins")

    cat("  Finished:", format(end_time, "%H:%M:%S"), "\n")
    cat("  Duration:", round(as.numeric(duration), 1), "minutes\n")
    cat("  Converged:", mod$convergence == 0, "\n")
    cat("  AIC:", AIC(mod), "\n")
    cat("  BIC:", BIC(mod), "\n\n")

    # Save model
    saveRDS(mod, here::here("reports/ifoa/models", paste0(name, ".rds")))

    # Return summary info
    list(
      name = name,
      converged = mod$convergence == 0,
      aic = AIC(mod),
      bic = BIC(mod),
      duration_mins = as.numeric(duration),
      n = nrow(data)
    )
  }, error = function(e) {
    cat("  ERROR:", e$message, "\n\n")
    list(
      name = name,
      converged = FALSE,
      aic = NA,
      bic = NA,
      duration_mins = NA,
      n = nrow(data),
      error = e$message
    )
  })
}

# Store results
results <- list()

# =============================================================================
# Model 1: Foundational (demographic only)
# =============================================================================

results[[1]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5),
  data = ind_data_core,
  name = "mod_01_foundation"
)

# =============================================================================
# Model 2: Foundation + Year trend
# =============================================================================

results[[2]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + wave_num,
  data = ind_data_core,
  name = "mod_02_foundation_year"
)

# =============================================================================
# Model 3: Foundation + Health (SF-12)
# =============================================================================

results[[3]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + sf12mcs_std + sf12pcs_std,
  data = ind_data_health,
  name = "mod_03_health"
)

# =============================================================================
# Model 4: Foundation + Health + Year
# =============================================================================

results[[4]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + sf12mcs_std + sf12pcs_std + wave_num,
  data = ind_data_health,
  name = "mod_04_health_year"
)

# =============================================================================
# Model 5: Foundation + Health + Occupation (NS-SEC 3)
# =============================================================================

results[[5]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + sf12mcs_std + sf12pcs_std + nssec3,
  data = ind_data_full,
  name = "mod_05_health_nssec"
)

# =============================================================================
# Model 6: Foundation + Health + Occupation + Year
# =============================================================================

results[[6]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + sf12mcs_std + sf12pcs_std + nssec3 + wave_num,
  data = ind_data_full,
  name = "mod_06_health_nssec_year"
)

# =============================================================================
# Model 7: Health × Occupation interaction
# =============================================================================

results[[7]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + (sf12mcs_std + sf12pcs_std) * nssec3,
  data = ind_data_full,
  name = "mod_07_health_nssec_interact"
)

# =============================================================================
# Model 8: Full model with all interactions
# =============================================================================

results[[8]] <- fit_and_save(
  next_status ~ this_status * sex + bs(age, 5) + (sf12mcs_std + sf12pcs_std) * nssec3 + wave_num,
  data = ind_data_full,
  name = "mod_08_full"
)

# =============================================================================
# Summary
# =============================================================================

cat("\n")
cat("=" |> rep(70) |> paste(collapse = ""), "\n")
cat("MODEL COMPARISON SUMMARY\n")
cat("=" |> rep(70) |> paste(collapse = ""), "\n\n")

results_df <- bind_rows(results)
saveRDS(results_df, here::here("reports/ifoa/models/model_comparison.rds"))

# Print comparison table
results_df |>
  select(name, n, converged, aic, bic, duration_mins) |>
  arrange(bic) |>
  print(n = 20)

cat("\nBest model by BIC:", results_df$name[which.min(results_df$bic)], "\n")
cat("Best model by AIC:", results_df$name[which.min(results_df$aic)], "\n")

cat("\n")
cat("All models saved to: reports/ifoa/models/\n")
cat("Finished:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
