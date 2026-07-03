"""
R Code Generator for Clinical Trial Submissions
Generates CDISC-compliant R programs using tidyverse and pharmaverse packages.
"""

from datetime import datetime


class RCodeGenerator:
    def __init__(self, config):
        self.config = config
        self.analysis_type = config.get('analysis_type', 'descriptive')
        self.output_type = config.get('output_type', 'table')
        self.input_data = config.get('input_data', {})
        self.output_data = config.get('output_data', {})
        self.variables = config.get('variables', {})
        self.analysis_params = config.get('analysis_parameters', {})
        self.submission = config.get('submission_details', {})

    def parse_shell(self, shell_path):
        metadata = {'columns': [], 'rows': [], 'titles': [], 'footnotes': []}
        return metadata

    def parse_specification(self, spec_path):
        metadata = {'variables': [], 'derivations': [], 'formats': []}
        return metadata

    def generate(self, shell_metadata=None, spec_metadata=None):
        sections = [
            self._generate_header(),
            self._generate_packages(),
            self._generate_setup(),
            self._generate_data_read(),
            self._generate_data_prep(),
            self._generate_analysis(),
            self._generate_output(),
            self._generate_validation()
        ]
        return '\n\n'.join(sections)

    def _generate_header(self):
        study_id = self.submission.get('study_id', 'STUDY-XXX')
        sponsor = self.submission.get('sponsor', 'AstraZeneca')
        protocol = self.submission.get('protocol', 'DXXXXCXXXXX')

        return f"""# ==============================================================================
# PROGRAM NAME  : {self.output_data.get('dataset_name', 'program')}.R
# STUDY         : {study_id}
# PROTOCOL      : {protocol}
# SPONSOR       : {sponsor}
# PURPOSE       : {self._get_purpose_description()}
# INPUT         : {', '.join(self.input_data.get('datasets', []))}
# OUTPUT        : {self.output_data.get('dataset_name', 'output')}.{self.output_data.get('format', 'rtf')}
# ANALYSIS TYPE : {self.analysis_type.replace('_', ' ').title()}
# OUTPUT TYPE   : {self.output_type.title()}
# POPULATION    : {self.analysis_params.get('population', 'safety').replace('_', ' ').title()}
#
# AUTHOR        : [Programmer Name]
# DATE CREATED  : {datetime.now().strftime('%d-%b-%Y')}
# DATE MODIFIED : {datetime.now().strftime('%d-%b-%Y')}
#
# REGULATORY    : {self.submission.get('regulatory_authority', 'FDA')}
# SUBMISSION    : {self.submission.get('submission_type', 'NDA')}
#
# PACKAGES      : tidyverse, haven, pharmaverse (admiral, rtables, tern)
# VALIDATION    : Independent double programming required
# =============================================================================="""

    def _generate_packages(self):
        base_packages = [
            'library(tidyverse)',
            'library(haven)',
            'library(labelled)'
        ]

        analysis_packages = {
            'descriptive': ['library(gtsummary)', 'library(rtables)', 'library(tern)'],
            'efficacy': ['library(emmeans)', 'library(lme4)', 'library(rtables)', 'library(tern)'],
            'safety': ['library(rtables)', 'library(tern)', 'library(admiral)'],
            'survival': ['library(survival)', 'library(survminer)', 'library(tern)', 'library(visR)'],
            'mixed_model': ['library(mmrm)', 'library(lme4)', 'library(emmeans)', 'library(rtables)'],
            'categorical': ['library(rtables)', 'library(tern)', 'library(exact2x2)'],
            'pk': ['library(PKNCA)', 'library(rtables)', 'library(tern)'],
            'subgroup': ['library(tern)', 'library(rtables)', 'library(forestplot)']
        }

        output_packages = {
            'table': ['library(r2rtf)', 'library(flextable)', 'library(officer)'],
            'figure': ['library(ggplot2)', 'library(cowplot)', 'library(patchwork)'],
            'listing': ['library(r2rtf)', 'library(rlistings)'],
            'dataset': ['library(xportr)', 'library(metacore)']
        }

        packages = base_packages + \
                   analysis_packages.get(self.analysis_type, []) + \
                   output_packages.get(self.output_type, [])

        return f"""# --- Load Required Packages ---
{chr(10).join(packages)}"""

    def _generate_setup(self):
        population_flag = self._get_population_flag()
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""# --- Program Setup ---
study_id    <- "{self.submission.get('study_id', 'STUDY001')}"
protocol    <- "{self.submission.get('protocol', 'D1234C00001')}"
prog_name   <- "{self.output_data.get('dataset_name', 'program')}"
output_name <- "{self.output_data.get('dataset_name', 'output')}"
pop_flag    <- "{population_flag}"
trt_var     <- "{treatment_var}"
alpha       <- {self.analysis_params.get('alpha', 0.05)}
conf_level  <- {self.analysis_params.get('confidence_level', 0.95)}

# --- Path Configuration ---
adam_path   <- "{self.input_data.get('library_path', '/data/adam')}"
output_path <- "{self.output_data.get('output_path', '/output')}"

# --- Treatment Order ---
trt_levels <- c("Placebo", "Treatment A", "Treatment B", "Total")
trt_n_labels <- c()  # Will be populated after data read"""

    def _generate_data_read(self):
        datasets = self.input_data.get('datasets', ['adsl'])
        population_flag = self._get_population_flag()
        filter_vars = self.variables.get('filter_variables', [])

        read_blocks = []
        for ds in datasets:
            filters = [f'{population_flag} == "Y"']
            for fv in filter_vars:
                if fv != population_flag:
                    filters.append(f'{fv} == "Y"')

            filter_expr = ' & '.join(filters) if filters else 'TRUE'

            read_blocks.append(f"""# Read {ds.upper()}
{ds} <- read_sas(file.path(adam_path, "{ds}.sas7bdat")) %>%
    filter({filter_expr}) %>%
    mutate(
        {self.analysis_params.get('treatment_variable', 'TRTA')} = factor(
            {self.analysis_params.get('treatment_variable', 'TRTA')},
            levels = trt_levels
        )
    )

cat(sprintf("NOTE: {ds.upper()} has %d records after filtering.\\n", nrow({ds})))""")

        return f"""# --- Read Input Datasets ---
{chr(10).join(read_blocks)}

# --- Get Population Counts (Big N) ---
big_n <- {datasets[0]} %>%
    distinct(USUBJID, .keep_all = TRUE) %>%
    count({self.analysis_params.get('treatment_variable', 'TRTA')}, name = "N") %>%
    mutate(
        N_label = sprintf("%s\\n(N=%d)", {self.analysis_params.get('treatment_variable', 'TRTA')}, N)
    )

cat("NOTE: Population counts:\\n")
print(big_n)"""

    def _generate_data_prep(self):
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        grouping_vars = self.variables.get('grouping_variables', [])

        return f"""# --- Data Preparation ---
analysis_data <- {self.input_data.get('datasets', ['adsl'])[0]} %>%
    # Add treatment numeric ordering
    mutate(
        TRTN = case_when(
            {treatment_var} == "Placebo"      ~ 1L,
            {treatment_var} == "Treatment A"  ~ 2L,
            {treatment_var} == "Treatment B"  ~ 3L,
            TRUE                              ~ 99L
        )
    ) %>%
    arrange(TRTN, {', '.join(self.variables.get('sort_variables', ['USUBJID']))})

# --- Create Total group ---
analysis_with_total <- bind_rows(
    analysis_data,
    analysis_data %>% mutate({treatment_var} = "Total", TRTN = 99L)
)

cat(sprintf("NOTE: Analysis dataset has %d records (including Total).\\n", 
    nrow(analysis_with_total)))"""

    def _generate_analysis(self):
        method_generators = {
            'descriptive': self._gen_descriptive_r,
            'efficacy': self._gen_efficacy_r,
            'safety': self._gen_safety_r,
            'survival': self._gen_survival_r,
            'mixed_model': self._gen_mmrm_r,
            'categorical': self._gen_categorical_r,
            'pk': self._gen_pk_r,
            'subgroup': self._gen_subgroup_r
        }
        generator = method_generators.get(self.analysis_type, self._gen_descriptive_r)
        return generator()

    def _gen_descriptive_r(self):
        analysis_vars = self.variables.get('analysis_variables', ['AVAL'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""# --- Descriptive Statistics ---
desc_stats <- analysis_with_total %>%
    group_by({treatment_var}, TRTN) %>%
    summarise(
        across(
            c({', '.join(analysis_vars)}),
            list(
                n      = ~sum(!is.na(.)),
                mean   = ~mean(., na.rm = TRUE),
                sd     = ~sd(., na.rm = TRUE),
                median = ~median(., na.rm = TRUE),
                min    = ~min(., na.rm = TRUE),
                max    = ~max(., na.rm = TRUE),
                q1     = ~quantile(., 0.25, na.rm = TRUE),
                q3     = ~quantile(., 0.75, na.rm = TRUE)
            ),
            .names = "{{.col}}_{{.fn}}"
        ),
        .groups = "drop"
    ) %>%
    arrange(TRTN)

# --- Format for display ---
desc_formatted <- desc_stats %>%
    mutate(
        n_c      = sprintf("%d", {analysis_vars[0]}_n),
        mean_sd  = sprintf("%.1f (%.2f)", {analysis_vars[0]}_mean, {analysis_vars[0]}_sd),
        median_c = sprintf("%.1f", {analysis_vars[0]}_median),
        q1_q3    = sprintf("%.1f, %.1f", {analysis_vars[0]}_q1, {analysis_vars[0]}_q3),
        min_max  = sprintf("%.1f, %.1f", {analysis_vars[0]}_min, {analysis_vars[0]}_max)
    ) %>%
    select({treatment_var}, TRTN, n_c, mean_sd, median_c, q1_q3, min_max)

# --- Using rtables for submission-ready output ---
lyt <- basic_table() %>%
    split_cols_by("{treatment_var}") %>%
    add_colcounts() %>%
    analyze(
        vars = c({', '.join([f'"{v}"' for v in analysis_vars])}),
        afun = function(x) {{
            in_rows(
                "n"           = rcell(sum(!is.na(x)), format = "xx"),
                "Mean (SD)"   = rcell(c(mean(x, na.rm=TRUE), sd(x, na.rm=TRUE)), format = "xx.x (xx.xx)"),
                "Median"      = rcell(median(x, na.rm=TRUE), format = "xx.x"),
                "Q1, Q3"      = rcell(c(quantile(x, 0.25, na.rm=TRUE), quantile(x, 0.75, na.rm=TRUE)), format = "xx.x, xx.x"),
                "Min, Max"    = rcell(c(min(x, na.rm=TRUE), max(x, na.rm=TRUE)), format = "xx.x, xx.x")
            )
        }}
    )

result_table <- build_table(lyt, analysis_with_total)
print(result_table)"""

    def _gen_efficacy_r(self):
        analysis_vars = self.variables.get('analysis_variables', ['CHG'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        covariates = self.analysis_params.get('covariates', ['BASE'])

        return f"""# --- Efficacy Analysis: ANCOVA ---

# Fit ANCOVA model
ancova_model <- lm(
    {analysis_vars[0]} ~ {treatment_var} + {' + '.join(covariates)},
    data = analysis_data
)

# Model summary
model_summary <- summary(ancova_model)
cat("\\nANCOVA Model Summary:\\n")
print(model_summary)

# LS Means
lsmeans_result <- emmeans(ancova_model, specs = ~ {treatment_var})
lsmeans_df <- as.data.frame(lsmeans_result) %>%
    mutate(
        lsmean_ci = sprintf("%.2f (%.2f, %.2f)", emmean, lower.CL, upper.CL)
    )

# Pairwise comparisons
contrasts_result <- pairs(lsmeans_result, adjust = "none")
contrasts_df <- as.data.frame(contrasts_result) %>%
    mutate(
        diff_ci = sprintf("%.2f (%.2f, %.2f)", estimate, lower.CL, upper.CL),
        p_value_c = ifelse(p.value < 0.001, "<0.001", sprintf("%.3f", p.value))
    )

cat("\\nLS Means:\\n")
print(lsmeans_df)
cat("\\nTreatment Differences:\\n")
print(contrasts_df)"""

    def _gen_safety_r(self):
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""# --- Safety Analysis: Adverse Event Summary ---

# Overall AE incidence
ae_overall <- adae %>%
    group_by({treatment_var}) %>%
    summarise(
        n_subjects = n_distinct(USUBJID),
        n_events   = n(),
        .groups    = "drop"
    ) %>%
    left_join(big_n, by = "{treatment_var}") %>%
    mutate(
        pct = (n_subjects / N) * 100,
        col = sprintf("%d (%.1f%%)", n_subjects, pct)
    )

# AE by SOC and PT
ae_soc_pt <- adae %>%
    group_by({treatment_var}, AEBODSYS, AEDECOD) %>%
    summarise(
        n_subjects = n_distinct(USUBJID),
        n_events   = n(),
        .groups    = "drop"
    ) %>%
    left_join(big_n, by = "{treatment_var}") %>%
    mutate(
        pct = (n_subjects / N) * 100,
        col = sprintf("%d (%.1f%%)", n_subjects, pct)
    ) %>%
    arrange(desc(n_subjects), AEBODSYS, AEDECOD)

# Using rtables for AE table
lyt_ae <- basic_table() %>%
    split_cols_by("{treatment_var}") %>%
    add_colcounts() %>%
    split_rows_by("AEBODSYS", label_pos = "topleft", split_label = "System Organ Class") %>%
    summarize_num_patients(var = "USUBJID", .stats = c("unique", "nonunique")) %>%
    analyze("AEDECOD", afun = function(x, .N_col) {{
        in_rows(
            rcell(length(unique(x)), format = "xx"),
            .labels = "n (%)"
        )
    }})

ae_table <- build_table(lyt_ae, adae)
print(ae_table)"""

    def _gen_survival_r(self):
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""# --- Survival Analysis ---

# Kaplan-Meier estimation
km_fit <- survfit(
    Surv(AVAL, 1 - CNSR) ~ {treatment_var},
    data = analysis_data,
    conf.type = "log-log"
)

# KM Summary
km_summary <- summary(km_fit, times = c(90, 180, 270, 365))
cat("\\nKaplan-Meier Estimates:\\n")
print(km_summary)

# Log-rank test
logrank_test <- survdiff(
    Surv(AVAL, 1 - CNSR) ~ {treatment_var},
    data = analysis_data
)
cat("\\nLog-Rank Test:\\n")
print(logrank_test)

# Cox Proportional Hazards
cox_model <- coxph(
    Surv(AVAL, 1 - CNSR) ~ {treatment_var},
    data = analysis_data,
    ties = "efron"
)

cox_summary <- summary(cox_model, conf.int = {self.analysis_params.get('confidence_level', 0.95)})
cat("\\nCox PH Model:\\n")
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
)"""

    def _gen_mmrm_r(self):
        analysis_vars = self.variables.get('analysis_variables', ['CHG'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        covariates = self.analysis_params.get('covariates', ['BASE'])

        return f"""# --- Mixed Model Repeated Measures (MMRM) ---

# Fit MMRM using mmrm package
mmrm_fit <- mmrm(
    formula = {analysis_vars[0]} ~ {treatment_var} * AVISIT + {' + '.join(covariates)} +
        us(AVISIT | USUBJID),
    data = analysis_data,
    method = "Kenward-Roger"
)

# Model summary
cat("\\nMMRM Model Summary:\\n")
summary(mmrm_fit)

# LS Means by treatment and visit
lsmeans_mmrm <- emmeans(mmrm_fit, ~ {treatment_var} | AVISIT)
lsmeans_df <- as.data.frame(lsmeans_mmrm)

# Treatment differences at each visit
diffs_mmrm <- pairs(lsmeans_mmrm, adjust = "none")
diffs_df <- as.data.frame(diffs_mmrm) %>%
    mutate(
        diff_ci = sprintf("%.2f (%.2f, %.2f)", estimate, lower.CL, upper.CL),
        p_value_c = ifelse(p.value < 0.001, "<0.001", sprintf("%.3f", p.value))
    )

cat("\\nLS Means by Visit:\\n")
print(lsmeans_df)
cat("\\nTreatment Differences by Visit:\\n")
print(diffs_df)"""

    def _gen_categorical_r(self):
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        return f"""# --- Categorical Analysis ---

# Frequency table
freq_table <- analysis_data %>%
    count({treatment_var}, AVALC) %>%
    left_join(big_n, by = "{treatment_var}") %>%
    mutate(
        pct = (n / N) * 100,
        col = sprintf("%d (%.1f%%)", n, pct)
    )

# Chi-square test
chisq_result <- chisq.test(table(analysis_data${treatment_var}, analysis_data$AVALC))

# Fisher's exact test
fisher_result <- fisher.test(table(analysis_data${treatment_var}, analysis_data$AVALC))

cat(sprintf("Chi-square p-value: %.4f\\n", chisq_result$p.value))
cat(sprintf("Fisher's exact p-value: %.4f\\n", fisher_result$p.value))"""

    def _gen_pk_r(self):
        return """# --- Pharmacokinetic Analysis ---

# PK parameter summary
pk_summary <- analysis_data %>%
    group_by(TRTA, PARAM, PARAMCD) %>%
    summarise(
        n      = sum(!is.na(AVAL)),
        mean   = mean(AVAL, na.rm = TRUE),
        sd     = sd(AVAL, na.rm = TRUE),
        cv     = sd(AVAL, na.rm = TRUE) / mean(AVAL, na.rm = TRUE) * 100,
        median = median(AVAL, na.rm = TRUE),
        min    = min(AVAL, na.rm = TRUE),
        max    = max(AVAL, na.rm = TRUE),
        gmean  = exp(mean(log(AVAL[AVAL > 0]), na.rm = TRUE)),
        gcv    = sqrt(exp(var(log(AVAL[AVAL > 0]), na.rm = TRUE)) - 1) * 100,
        .groups = "drop"
    )

print(pk_summary)"""

    def _gen_subgroup_r(self):
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        subgroups = self.analysis_params.get('subgroup_variables', ['SEX', 'AGEGR1', 'RACE'])

        return f"""# --- Subgroup Analysis ---

subgroup_results <- map_dfr(c({', '.join([f'"{sg}"' for sg in subgroups])}), function(sg) {{
    formula_str <- paste0("CHG ~ {treatment_var} * ", sg, " + BASE")
    model <- lm(as.formula(formula_str), data = analysis_data)
    
    emm <- emmeans(model, ~ {treatment_var} | !!sym(sg))
    diffs <- as.data.frame(pairs(emm, adjust = "none"))
    
    diffs %>%
        mutate(subgroup_var = sg) %>%
        rename(category = !!sym(sg))
}})

# Forest plot
forest_plot <- ggplot(subgroup_results, aes(x = estimate, y = category)) +
    geom_point(size = 3) +
    geom_errorbarh(aes(xmin = lower.CL, xmax = upper.CL), height = 0.2) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
    facet_grid(subgroup_var ~ ., scales = "free_y", space = "free_y") +
    labs(x = "Treatment Difference (95% CI)", y = "") +
    theme_minimal()

print(forest_plot)"""

    def _generate_output(self):
        output_generators = {
            'table': self._gen_table_output_r,
            'figure': self._gen_figure_output_r,
            'listing': self._gen_listing_output_r,
            'dataset': self._gen_dataset_output_r
        }
        generator = output_generators.get(self.output_type, self._gen_table_output_r)
        return generator()

    def _gen_table_output_r(self):
        return f"""# --- Generate Table Output ---

# Using r2rtf for submission-ready RTF output
output_file <- file.path(output_path, paste0(output_name, ".rtf"))

result_df %>%
    r2rtf::rtf_title(
        title = "Table X.X.X",
        subtitle = "{self._get_purpose_description()}"
    ) %>%
    r2rtf::rtf_colheader(
        colheader = "Statistic | Placebo\\n(N={{N1}}) | Treatment A\\n(N={{N2}}) | Treatment B\\n(N={{N3}})",
        col_rel_width = c(3, 2, 2, 2)
    ) %>%
    r2rtf::rtf_body(
        col_rel_width = c(3, 2, 2, 2),
        text_justification = c("l", "c", "c", "c")
    ) %>%
    r2rtf::rtf_footnote(
        footnote = c(
            "Source: {', '.join(self.input_data.get('datasets', ['adsl']))}",
            "Program: {{prog_name}}.R  Output: {{output_name}}.rtf",
            paste0("Generated: ", format(Sys.time(), "%d%b%Y %H:%M"))
        )
    ) %>%
    r2rtf::rtf_encode() %>%
    r2rtf::write_rtf(output_file)

cat(sprintf("NOTE: Output written to %s\\n", output_file))"""

    def _gen_figure_output_r(self):
        return f"""# --- Generate Figure Output ---

output_file <- file.path(output_path, paste0(output_name, ".pdf"))

final_plot <- km_plot +
    labs(
        title = "Figure X.X.X",
        subtitle = "{self._get_purpose_description()}",
        caption = paste0(
            "Source: {', '.join(self.input_data.get('datasets', ['adsl']))}\\n",
            "Program: ", prog_name, ".R\\n",
            "Generated: ", format(Sys.time(), "%d%b%Y")
        )
    )

ggsave(
    output_file,
    plot = final_plot,
    width = 10,
    height = 7,
    units = "in",
    dpi = 300
)

cat(sprintf("NOTE: Figure written to %s\\n", output_file))"""

    def _gen_listing_output_r(self):
        return f"""# --- Generate Listing Output ---

output_file <- file.path(output_path, paste0(output_name, ".rtf"))

listing_data %>%
    select(USUBJID, SITEID, {', '.join(self.variables.get('analysis_variables', ['AVAL']))}) %>%
    arrange(USUBJID) %>%
    r2rtf::rtf_title(title = "Listing X.X.X") %>%
    r2rtf::rtf_body(text_font_size = 8) %>%
    r2rtf::rtf_encode() %>%
    r2rtf::write_rtf(output_file)

cat(sprintf("NOTE: Listing written to %s\\n", output_file))"""

    def _gen_dataset_output_r(self):
        return f"""# --- Generate Analysis Dataset ---

# Apply metadata and export as XPT
output_file <- file.path(output_path, paste0(output_name, ".xpt"))

final_dataset %>%
    xportr::xportr_type(metacore) %>%
    xportr::xportr_length(metacore) %>%
    xportr::xportr_label(metacore) %>%
    xportr::xportr_format(metacore) %>%
    xportr::xportr_write(output_file)

cat(sprintf("NOTE: Dataset written to %s\\n", output_file))"""

    def _generate_validation(self):
        return f"""# --- Validation Checks ---

# Check for missing critical variables
n_missing_usubjid <- sum(is.na(analysis_data$USUBJID))
n_missing_trt <- sum(is.na(analysis_data${self.analysis_params.get('treatment_variable', 'TRTA')}))

cat(sprintf("\\nValidation Results:\\n"))
cat(sprintf("  Missing USUBJID: %d\\n", n_missing_usubjid))
cat(sprintf("  Missing Treatment: %d\\n", n_missing_trt))
cat(sprintf("  Total subjects: %d\\n", n_distinct(analysis_data$USUBJID)))

# Session info for reproducibility
cat("\\n--- Session Info ---\\n")
sessionInfo()

cat("\\n========================================\\n")
cat(sprintf("Program: %s.R\\n", prog_name))
cat(sprintf("Output:  %s.{self.output_data.get('format', 'rtf')}\\n", output_name))
cat("Status:  COMPLETE\\n")
cat("========================================\\n")"""

    # Helper methods
    def _get_population_flag(self):
        pop_flags = {
            'safety': 'SAFFL', 'itt': 'ITTFL', 'per_protocol': 'PPROTFL',
            'pk': 'PKFL', 'full_analysis': 'FASFL'
        }
        return pop_flags.get(self.analysis_params.get('population', 'safety'), 'SAFFL')

    def _get_purpose_description(self):
        descriptions = {
            'descriptive': 'Generate descriptive statistics summary',
            'efficacy': 'Primary efficacy endpoint analysis',
            'safety': 'Safety summary of adverse events',
            'survival': 'Time-to-event survival analysis',
            'mixed_model': 'Mixed model repeated measures analysis',
            'categorical': 'Categorical data analysis',
            'pk': 'Pharmacokinetic parameter summary',
            'subgroup': 'Subgroup analysis with forest plot'
        }
        return descriptions.get(self.analysis_type, 'Statistical analysis')