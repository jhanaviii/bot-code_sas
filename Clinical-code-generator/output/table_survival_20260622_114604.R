# ==============================================================================
# PROGRAM NAME  : t_ae_summary.R
# STUDY         : STUDY-001
# PROTOCOL      : D1234C00001
# SPONSOR       : AstraZeneca
# PURPOSE       : Time-to-event survival analysis
# INPUT         : adsl, adae
# OUTPUT        : t_ae_summary.rtf
# ANALYSIS TYPE : Survival
# OUTPUT TYPE   : Table
# POPULATION    : Safety
#
# AUTHOR        : [Programmer Name]
# DATE CREATED  : 22-Jun-2026
# DATE MODIFIED : 22-Jun-2026
#
# REGULATORY    : FDA
# SUBMISSION    : NDA
#
# PACKAGES      : tidyverse, haven, pharmaverse (admiral, rtables, tern)
# VALIDATION    : Independent double programming required
# ==============================================================================

# --- Load Required Packages ---
library(tidyverse)
library(haven)
library(labelled)
library(survival)
library(survminer)
library(tern)
library(visR)
library(r2rtf)
library(flextable)
library(officer)

# --- Program Setup ---
study_id    <- "STUDY-001"
protocol    <- "D1234C00001"
prog_name   <- "t_ae_summary"
output_name <- "t_ae_summary"
pop_flag    <- "SAFFL"
trt_var     <- "TRTA"
alpha       <- 0.05
conf_level  <- 0.95

# --- Path Configuration ---
adam_path   <- "/data/adam"
output_path <- "/output/tables"

# --- Treatment Order ---
trt_levels <- c("Placebo", "Treatment A", "Treatment B", "Total")
trt_n_labels <- c()  # Will be populated after data read

# --- Read Input Datasets ---
# Read ADSL
adsl <- read_sas(file.path(adam_path, "adsl.sas7bdat")) %>%
    filter(SAFFL == "Y") %>%
    mutate(
        TRTA = factor(
            TRTA,
            levels = trt_levels
        )
    )

cat(sprintf("NOTE: ADSL has %d records after filtering.\n", nrow(adsl)))
# Read ADAE
adae <- read_sas(file.path(adam_path, "adae.sas7bdat")) %>%
    filter(SAFFL == "Y") %>%
    mutate(
        TRTA = factor(
            TRTA,
            levels = trt_levels
        )
    )

cat(sprintf("NOTE: ADAE has %d records after filtering.\n", nrow(adae)))

# --- Get Population Counts (Big N) ---
big_n <- adsl %>%
    distinct(USUBJID, .keep_all = TRUE) %>%
    count(TRTA, name = "N") %>%
    mutate(
        N_label = sprintf("%s\n(N=%d)", TRTA, N)
    )

cat("NOTE: Population counts:\n")
print(big_n)

# --- Data Preparation ---
analysis_data <- adsl %>%
    # Add treatment numeric ordering
    mutate(
        TRTN = case_when(
            TRTA == "Placebo"      ~ 1L,
            TRTA == "Treatment A"  ~ 2L,
            TRTA == "Treatment B"  ~ 3L,
            TRUE                              ~ 99L
        )
    ) %>%
    arrange(TRTN, USUBJID, AVISITN)

# --- Create Total group ---
analysis_with_total <- bind_rows(
    analysis_data,
    analysis_data %>% mutate(TRTA = "Total", TRTN = 99L)
)

cat(sprintf("NOTE: Analysis dataset has %d records (including Total).\n", 
    nrow(analysis_with_total)))

# --- Survival Analysis ---

# Kaplan-Meier estimation
km_fit <- survfit(
    Surv(AVAL, 1 - CNSR) ~ TRTA,
    data = analysis_data,
    conf.type = "log-log"
)

# KM Summary
km_summary <- summary(km_fit, times = c(90, 180, 270, 365))
cat("\nKaplan-Meier Estimates:\n")
print(km_summary)

# Log-rank test
logrank_test <- survdiff(
    Surv(AVAL, 1 - CNSR) ~ TRTA,
    data = analysis_data
)
cat("\nLog-Rank Test:\n")
print(logrank_test)

# Cox Proportional Hazards
cox_model <- coxph(
    Surv(AVAL, 1 - CNSR) ~ TRTA,
    data = analysis_data,
    ties = "efron"
)

cox_summary <- summary(cox_model, conf.int = 0.95)
cat("\nCox PH Model:\n")
print(cox_summary)

# Hazard Ratio
hr_result <- data.frame(
    HR       = exp(coef(cox_model)),
    HR_lower = exp(confint(cox_model))[, 1],
    HR_upper = exp(confint(cox_model))[, 2],
    p_value  = summary(cox_model)$coefficients[, "Pr(>|z|)"]
) %>%
    mutate(
        hr_ci = sprintf("%.3f (%.3f, %.3f)", HR, HR_lower, HR_upper),
        p_value_c = ifelse(p_value < 0.001, "<0.001", sprintf("%.3f", p_value))
    )

# KM Plot
km_plot <- ggsurvplot(
    km_fit,
    data = analysis_data,
    risk.table = TRUE,
    pval = TRUE,
    conf.int = TRUE,
    xlab = "Time (Days)",
    ylab = "Survival Probability",
    title = "Kaplan-Meier Survival Curve",
    legend.title = "Treatment",
    palette = c("#0072B2", "#D55E00", "#009E73"),
    ggtheme = theme_classic()
)

# --- Generate Table Output ---

# Using r2rtf for submission-ready RTF output
output_file <- file.path(output_path, paste0(output_name, ".rtf"))

result_df %>%
    r2rtf::rtf_title(
        title = "Table X.X.X",
        subtitle = "Time-to-event survival analysis"
    ) %>%
    r2rtf::rtf_colheader(
        colheader = "Statistic | Placebo\n(N={N1}) | Treatment A\n(N={N2}) | Treatment B\n(N={N3})",
        col_rel_width = c(3, 2, 2, 2)
    ) %>%
    r2rtf::rtf_body(
        col_rel_width = c(3, 2, 2, 2),
        text_justification = c("l", "c", "c", "c")
    ) %>%
    r2rtf::rtf_footnote(
        footnote = c(
            "Source: adsl, adae",
            "Program: {prog_name}.R  Output: {output_name}.rtf",
            paste0("Generated: ", format(Sys.time(), "%d%b%Y %H:%M"))
        )
    ) %>%
    r2rtf::rtf_encode() %>%
    r2rtf::write_rtf(output_file)

cat(sprintf("NOTE: Output written to %s\n", output_file))

# --- Validation Checks ---

# Check for missing critical variables
n_missing_usubjid <- sum(is.na(analysis_data$USUBJID))
n_missing_trt <- sum(is.na(analysis_data$TRTA))

cat(sprintf("\nValidation Results:\n"))
cat(sprintf("  Missing USUBJID: %d\n", n_missing_usubjid))
cat(sprintf("  Missing Treatment: %d\n", n_missing_trt))
cat(sprintf("  Total subjects: %d\n", n_distinct(analysis_data$USUBJID)))

# Session info for reproducibility
cat("\n--- Session Info ---\n")
sessionInfo()

cat("\n========================================\n")
cat(sprintf("Program: %s.R\n", prog_name))
cat(sprintf("Output:  %s.rtf\n", output_name))
cat("Status:  COMPLETE\n")
cat("========================================\n")