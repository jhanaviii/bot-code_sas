# ==============================================================================
# PROGRAM NAME  : t_ae_summary.R
# STUDY         : STUDY-001
# PROTOCOL      : D1234C00001
# SPONSOR       : AstraZeneca
# PURPOSE       : Safety summary of adverse events
# INPUT         : adsl, adae
# OUTPUT        : t_ae_summary.rtf
# ANALYSIS TYPE : Safety
# OUTPUT TYPE   : Table
# POPULATION    : Safety
#
# AUTHOR        : [Programmer Name]
# DATE CREATED  : 11-Jun-2026
# DATE MODIFIED : 11-Jun-2026
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
library(rtables)
library(tern)
library(admiral)
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

# --- Safety Analysis: Adverse Event Summary ---

# Overall AE incidence
ae_overall <- adae %>%
    group_by(TRTA) %>%
    summarise(
        n_subjects = n_distinct(USUBJID),
        n_events   = n(),
        .groups    = "drop"
    ) %>%
    left_join(big_n, by = "TRTA") %>%
    mutate(
        pct = (n_subjects / N) * 100,
        col = sprintf("%d (%.1f%%)", n_subjects, pct)
    )

# AE by SOC and PT
ae_soc_pt <- adae %>%
    group_by(TRTA, AEBODSYS, AEDECOD) %>%
    summarise(
        n_subjects = n_distinct(USUBJID),
        n_events   = n(),
        .groups    = "drop"
    ) %>%
    left_join(big_n, by = "TRTA") %>%
    mutate(
        pct = (n_subjects / N) * 100,
        col = sprintf("%d (%.1f%%)", n_subjects, pct)
    ) %>%
    arrange(desc(n_subjects), AEBODSYS, AEDECOD)

# Using rtables for AE table
lyt_ae <- basic_table() %>%
    split_cols_by("TRTA") %>%
    add_colcounts() %>%
    split_rows_by("AEBODSYS", label_pos = "topleft", split_label = "System Organ Class") %>%
    summarize_num_patients(var = "USUBJID", .stats = c("unique", "nonunique")) %>%
    analyze("AEDECOD", afun = function(x, .N_col) {
        in_rows(
            rcell(length(unique(x)), format = "xx"),
            .labels = "n (%)"
        )
    })

ae_table <- build_table(lyt_ae, adae)
print(ae_table)

# --- Generate Table Output ---

# Using r2rtf for submission-ready RTF output
output_file <- file.path(output_path, paste0(output_name, ".rtf"))

result_df %>%
    r2rtf::rtf_title(
        title = "Table X.X.X",
        subtitle = "Safety summary of adverse events"
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