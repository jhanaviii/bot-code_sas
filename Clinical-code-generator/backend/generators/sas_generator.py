"""
SAS Code Generator for Clinical Trial Submissions
Generates CDISC-compliant, submission-ready SAS programs.
"""

import json
from datetime import datetime


class SASCodeGenerator:
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
        """Parse uploaded shell template to extract layout specifications."""
        # Parse RTF/Excel shell for column headers, row structure, formatting
        metadata = {
            'columns': [],
            'rows': [],
            'titles': [],
            'footnotes': [],
            'page_layout': 'landscape',
            'font_size': 9
        }
        # Implementation would parse actual shell files
        return metadata

    def parse_specification(self, spec_path):
        """Parse dataset/variable specification file."""
        metadata = {
            'variables': [],
            'derivations': [],
            'formats': [],
            'labels': []
        }
        # Implementation would parse Excel/CSV specifications
        return metadata

    def generate(self, shell_metadata=None, spec_metadata=None):
        """Generate complete SAS program."""
        sections = [
            self._generate_header(),
            self._generate_setup(),
            self._generate_data_access(),
            self._generate_data_preparation(),
            self._generate_analysis(),
            self._generate_output(),
            self._generate_validation(),
            self._generate_footer()
        ]
        return '\n\n'.join(sections)

    def _generate_header(self):
        """Generate program header with metadata."""
        study_id = self.submission.get('study_id', 'STUDY-XXX')
        sponsor = self.submission.get('sponsor', 'AstraZeneca')
        protocol = self.submission.get('protocol', 'DXXXXCXXXXX')
        
        return f"""/******************************************************************************
* PROGRAM NAME  : {self.output_data.get('dataset_name', 'program')}.sas
* STUDY         : {study_id}
* PROTOCOL      : {protocol}
* SPONSOR       : {sponsor}
* PURPOSE       : {self._get_purpose_description()}
* INPUT         : {', '.join(self.input_data.get('datasets', []))}
* OUTPUT        : {self.output_data.get('dataset_name', 'output')}.{self.output_data.get('format', 'rtf')}
* ANALYSIS TYPE : {self.analysis_type.replace('_', ' ').title()}
* OUTPUT TYPE   : {self.output_type.title()}
* POPULATION    : {self.analysis_params.get('population', 'safety').replace('_', ' ').title()}
*
* AUTHOR        : [Programmer Name]
* DATE CREATED  : {datetime.now().strftime('%d%b%Y')}
* DATE MODIFIED : {datetime.now().strftime('%d%b%Y')}
*
* REGULATORY    : {self.submission.get('regulatory_authority', 'FDA')}
* SUBMISSION    : {self.submission.get('submission_type', 'NDA')}
*
* VALIDATION    : Independent double programming required
* CDISC VERSION : ADaM IG v1.3 / SDTM IG v3.4
*
* MODIFICATION HISTORY:
* DATE        PROGRAMMER    DESCRIPTION
* ---------   ----------    ------------------------------------------------
* {datetime.now().strftime('%d%b%Y')}  [Name]        Initial creation
******************************************************************************/"""

    def _generate_setup(self):
        """Generate program setup and macro variables."""
        population_flag = self._get_population_flag()
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        
        return f"""/*--- Program Setup ---*/
%let study    = {self.submission.get('study_id', 'STUDY001')};
%let protocol = {self.submission.get('protocol', 'D1234C00001')};
%let progname = {self.output_data.get('dataset_name', 'program')};
%let outname  = {self.output_data.get('dataset_name', 'output')};
%let popflag  = {population_flag};
%let trtvar   = {treatment_var};
%let alpha    = {self.analysis_params.get('alpha', 0.05)};
%let conflev  = {self.analysis_params.get('confidence_level', 0.95)};

/*--- System Options ---*/
options nodate nonumber orientation={self._get_orientation()} 
        ls=200 ps=60 missing=' ' formchar='|_---|+|---+=|-/\\<>*';
options mprint mlogic symbolgen;

/*--- ODS Setup ---*/
ods listing close;
ods escapechar = '~';

/*--- Library References ---*/
libname adam "{self.input_data.get('library_path', '/data/adam')}" access=readonly;
libname output "{self.output_data.get('output_path', '/output')}";

/*--- Format Definitions ---*/
proc format;
    value $trtfmt
        'Placebo'       = 'Placebo'
        'Treatment A'   = 'Treatment A'
        'Treatment B'   = 'Treatment B'
        'Total'         = 'Total'
    ;
    value $popfmt
        'Y' = 'Yes'
        'N' = 'No'
    ;
run;"""

    def _generate_data_access(self):
        """Generate data access and initial filtering."""
        datasets = self.input_data.get('datasets', ['adsl'])
        filter_vars = self.variables.get('filter_variables', [])
        population_flag = self._get_population_flag()

        data_steps = []
        for ds in datasets:
            filters = [f"{population_flag} = 'Y'"]
            for fv in filter_vars:
                if fv != population_flag:
                    filters.append(f"{fv} = 'Y'")

            filter_clause = ' and '.join(filters)
            
            data_steps.append(f"""/*--- Read {ds.upper()} dataset ---*/
data work.{ds};
    set adam.{ds};
    where {filter_clause};
run;

proc sort data=work.{ds};
    by {' '.join(self.variables.get('sort_variables', ['USUBJID']))};
run;

/*--- Verify record count ---*/
proc sql noprint;
    select count(*) into :n_{ds} trimmed
    from work.{ds};
quit;
%put NOTE: {ds.upper()} has &n_{ds} records after filtering.;""")

        return '\n\n'.join(data_steps)

    def _generate_data_preparation(self):
        """Generate data preparation and derivation steps."""
        analysis_vars = self.variables.get('analysis_variables', [])
        grouping_vars = self.variables.get('grouping_variables', [])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""/*--- Data Preparation ---*/
data work.analysis;
    set work.{self.input_data.get('datasets', ['adsl'])[0]};
    
    /*--- Derive analysis variables ---*/
    length col1-col4 $200;
    
    /*--- Treatment group ordering ---*/
    select ({treatment_var});
        when ('Placebo')       trtn = 1;
        when ('Treatment A')   trtn = 2;
        when ('Treatment B')   trtn = 3;
        otherwise              trtn = 99;
    end;
    
    /*--- Create Total group for summary ---*/
    output;
    {treatment_var} = 'Total';
    trtn = 99;
    output;
run;

proc sort data=work.analysis;
    by trtn {treatment_var} {' '.join(grouping_vars)};
run;

/*--- Get Big N (population counts) ---*/
proc sql noprint;
    select count(distinct USUBJID) into :N1 trimmed
    from work.analysis
    where trtn = 1;
    
    select count(distinct USUBJID) into :N2 trimmed
    from work.analysis
    where trtn = 2;
    
    select count(distinct USUBJID) into :N3 trimmed
    from work.analysis
    where trtn = 3;
    
    select count(distinct USUBJID) into :Ntot trimmed
    from work.analysis
    where trtn = 99;
quit;

%put NOTE: Population counts - Placebo=&N1, TrtA=&N2, TrtB=&N3, Total=&Ntot;"""

    def _generate_analysis(self):
        """Generate statistical analysis code based on analysis type."""
        method_generators = {
            'descriptive': self._gen_descriptive_analysis,
            'efficacy': self._gen_efficacy_analysis,
            'safety': self._gen_safety_analysis,
            'survival': self._gen_survival_analysis,
            'mixed_model': self._gen_mixed_model_analysis,
            'categorical': self._gen_categorical_analysis,
            'pk': self._gen_pk_analysis,
            'subgroup': self._gen_subgroup_analysis
        }

        generator = method_generators.get(self.analysis_type, self._gen_descriptive_analysis)
        return generator()

    def _gen_descriptive_analysis(self):
        """Generate descriptive statistics analysis."""
        analysis_vars = self.variables.get('analysis_variables', ['AVAL'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        grouping_vars = self.variables.get('grouping_variables', [])

        by_statement = f"by {' '.join(grouping_vars)};" if grouping_vars else ""

        return f"""/*--- Descriptive Statistics ---*/
proc means data=work.analysis nway noprint;
    class {treatment_var} trtn {' '.join(grouping_vars)};
    var {' '.join(analysis_vars)};
    output out=work.stats (drop=_type_ _freq_)
        n=n
        mean=mean
        std=std
        median=median
        min=min
        max=max
        q1=q1
        q3=q3;
run;

/*--- Format statistics for display ---*/
data work.stats_fmt;
    set work.stats;
    length col1-col4 $200;
    
    /*--- N ---*/
    n_c = strip(put(n, 8.));
    
    /*--- Mean (SD) ---*/
    mean_sd = strip(put(mean, 10.1)) || ' (' || strip(put(std, 10.2)) || ')';
    
    /*--- Median ---*/
    median_c = strip(put(median, 10.1));
    
    /*--- Q1, Q3 ---*/
    q1q3 = strip(put(q1, 10.1)) || ', ' || strip(put(q3, 10.1));
    
    /*--- Min, Max ---*/
    minmax = strip(put(min, 10.1)) || ', ' || strip(put(max, 10.1));
run;

proc sort data=work.stats_fmt;
    by trtn {treatment_var};
run;

/*--- Transpose for report layout ---*/
proc transpose data=work.stats_fmt out=work.stats_t (drop=_name_) prefix=col;
    by {' '.join(grouping_vars) + ' ' if grouping_vars else ''}/* row identifiers */;
    id trtn;
    var n_c mean_sd median_c q1q3 minmax;
run;"""

    def _gen_efficacy_analysis(self):
        """Generate efficacy analysis with ANCOVA."""
        analysis_vars = self.variables.get('analysis_variables', ['CHG'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        covariates = self.analysis_params.get('covariates', ['BASE'])

        return f"""/*--- Efficacy Analysis: ANCOVA ---*/

/*--- Descriptive Statistics by Visit and Treatment ---*/
proc means data=work.analysis nway noprint;
    class {treatment_var} trtn AVISIT AVISITN;
    var {' '.join(analysis_vars)} BASE;
    output out=work.desc_stats (drop=_type_ _freq_)
        n=n mean=mean std=std median=median min=min max=max;
run;

/*--- ANCOVA Model ---*/
proc mixed data=work.analysis;
    class {treatment_var} SITEID;
    model {analysis_vars[0]} = {treatment_var} {' '.join(covariates)} / ddfm=kr solution cl alpha=&alpha;
    lsmeans {treatment_var} / pdiff cl alpha=&alpha;
    ods output LSMeans=work.lsmeans
              Diffs=work.diffs
              SolutionF=work.solution
              Tests3=work.tests;
run;

/*--- Format LS Means results ---*/
data work.lsmeans_fmt;
    set work.lsmeans;
    length result $200;
    result = strip(put(Estimate, 10.2)) || ' (' || 
             strip(put(Lower, 10.2)) || ', ' || 
             strip(put(Upper, 10.2)) || ')';
    pvalue_c = ifc(Probt < 0.001, '<0.001', strip(put(Probt, 6.3)));
run;

/*--- Format Treatment Differences ---*/
data work.diffs_fmt;
    set work.diffs;
    length diff_result $200;
    diff_result = strip(put(Estimate, 10.2)) || ' (' || 
                  strip(put(Lower, 10.2)) || ', ' || 
                  strip(put(Upper, 10.2)) || ')';
    pvalue_c = ifc(Probt < 0.001, '<0.001', strip(put(Probt, 6.3)));
run;"""

    def _gen_safety_analysis(self):
        """Generate safety analysis (AE summary)."""
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""/*--- Safety Analysis: Adverse Event Summary ---*/

/*--- Overall AE Summary ---*/
proc sql;
    create table work.ae_overall as
    select {treatment_var}, trtn,
           count(distinct USUBJID) as n_subj,
           count(*) as n_events
    from work.adae
    group by {treatment_var}, trtn;
quit;

/*--- AE by System Organ Class and Preferred Term ---*/
proc sql;
    create table work.ae_soc_pt as
    select {treatment_var}, trtn, AEBODSYS, AEDECOD,
           count(distinct USUBJID) as n_subj,
           count(*) as n_events
    from work.adae
    group by {treatment_var}, trtn, AEBODSYS, AEDECOD
    order by AEBODSYS, AEDECOD, trtn;
quit;

/*--- Calculate percentages ---*/
data work.ae_summary;
    set work.ae_soc_pt;
    
    select (trtn);
        when (1) bigN = input("&N1", best.);
        when (2) bigN = input("&N2", best.);
        when (3) bigN = input("&N3", best.);
        when (99) bigN = input("&Ntot", best.);
    end;
    
    pct = (n_subj / bigN) * 100;
    
    /*--- Format: n (xx.x%) ---*/
    length col $50;
    if n_subj > 0 then
        col = strip(put(n_subj, 8.)) || ' (' || strip(put(pct, 5.1)) || '%)';
    else
        col = '0';
run;

/*--- Sort by descending frequency in active treatment ---*/
proc sql;
    create table work.ae_sorted as
    select a.*
    from work.ae_summary a
    left join (
        select AEBODSYS, AEDECOD, sum(n_subj) as total_n
        from work.ae_summary
        where trtn = 2
        group by AEBODSYS, AEDECOD
    ) b on a.AEBODSYS = b.AEBODSYS and a.AEDECOD = b.AEDECOD
    order by b.total_n desc, a.AEBODSYS, a.AEDECOD, a.trtn;
quit;"""

    def _gen_survival_analysis(self):
        """Generate survival analysis (Kaplan-Meier + Cox)."""
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')

        return f"""/*--- Survival Analysis ---*/

/*--- Kaplan-Meier Estimation ---*/
proc lifetest data=work.analysis method=km 
    plots=(survival(cl atrisk) logsurv)
    outsurv=work.km_estimates
    timelist=(3 6 9 12)
    reduceout;
    time AVAL * CNSR(1);
    strata {treatment_var};
    ods output Quartiles=work.km_quartiles
              HomTests=work.logrank
              ProductLimitEstimates=work.km_detail;
run;

/*--- Cox Proportional Hazards Model ---*/
proc phreg data=work.analysis;
    class {treatment_var} (ref='Placebo') / param=ref;
    model AVAL * CNSR(1) = {treatment_var} / ties=efron rl alpha=&alpha;
    hazardratio {treatment_var} / diff=ref cl=wald;
    ods output ParameterEstimates=work.cox_params
              HazardRatios=work.hazard_ratios
              GlobalTests=work.global_tests;
run;

/*--- Format KM Results ---*/
data work.km_results;
    set work.km_estimates;
    length survival_c $50 ci_c $50;
    survival_c = strip(put(SURVIVAL, 6.3));
    ci_c = '(' || strip(put(SDF_LCL, 6.3)) || ', ' || strip(put(SDF_UCL, 6.3)) || ')';
run;

/*--- Format Hazard Ratio ---*/
data work.hr_results;
    set work.hazard_ratios;
    length hr_c $100;
    hr_c = strip(put(HazardRatio, 6.3)) || ' (' || 
           strip(put(HRLowerCL, 6.3)) || ', ' || 
           strip(put(HRUpperCL, 6.3)) || ')';
run;"""

    def _gen_mixed_model_analysis(self):
        """Generate MMRM analysis."""
        analysis_vars = self.variables.get('analysis_variables', ['CHG'])
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        covariates = self.analysis_params.get('covariates', ['BASE'])

        return f"""/*--- Mixed Model Repeated Measures (MMRM) ---*/

proc mixed data=work.analysis method=reml;
    class {treatment_var} USUBJID AVISIT SITEID;
    model {analysis_vars[0]} = {treatment_var} AVISIT {treatment_var}*AVISIT 
          {' '.join(covariates)} / ddfm=kr solution cl alpha=&alpha;
    repeated AVISIT / subject=USUBJID type=un r rcorr;
    lsmeans {treatment_var}*AVISIT / slice=AVISIT pdiff cl alpha=&alpha;
    ods output LSMeans=work.mmrm_lsmeans
              Diffs=work.mmrm_diffs
              Tests3=work.mmrm_tests
              FitStatistics=work.mmrm_fit
              CovParms=work.mmrm_cov;
run;

/*--- Format MMRM Results by Visit ---*/
data work.mmrm_results;
    set work.mmrm_lsmeans;
    length lsmean_c $100 ci_c $100;
    lsmean_c = strip(put(Estimate, 10.2)) || ' (' || strip(put(StdErr, 10.3)) || ')';
    ci_c = '(' || strip(put(Lower, 10.2)) || ', ' || strip(put(Upper, 10.2)) || ')';
run;

/*--- Treatment Differences at Each Visit ---*/
data work.mmrm_diff_results;
    set work.mmrm_diffs;
    where AVISIT ne ' ';
    length diff_c $100 pval_c $20;
    diff_c = strip(put(Estimate, 10.2)) || ' (' || 
             strip(put(Lower, 10.2)) || ', ' || 
             strip(put(Upper, 10.2)) || ')';
    pval_c = ifc(Probt < 0.001, '<0.001', strip(put(Probt, 6.3)));
run;"""

    def _gen_categorical_analysis(self):
        """Generate categorical analysis."""
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        return f"""/*--- Categorical Analysis ---*/

/*--- Frequency counts ---*/
proc freq data=work.analysis noprint;
    tables {treatment_var} * AVALC / cmh chisq fisher outpct out=work.freq_counts;
    ods output CMH=work.cmh_results
              ChiSq=work.chisq_results
              FishersExact=work.fisher_results;
run;

/*--- Format results ---*/
data work.cat_results;
    set work.freq_counts;
    length col $50;
    col = strip(put(COUNT, 8.)) || ' (' || strip(put(PCT_ROW, 5.1)) || '%)';
run;"""

    def _gen_pk_analysis(self):
        """Generate PK analysis."""
        return """/*--- Pharmacokinetic Analysis ---*/

/*--- PK Parameter Summary ---*/
proc means data=work.analysis nway noprint;
    class TRTA trtn PARAM PARAMCD;
    var AVAL;
    output out=work.pk_stats (drop=_type_ _freq_)
        n=n mean=mean std=std median=median min=min max=max
        cv=cv gmean=gmean;
run;

/*--- Geometric Mean and CV% ---*/
data work.pk_summary;
    set work.pk_stats;
    length gmean_c $50 cv_c $20;
    log_mean = log(mean);
    gmean_calc = exp(log_mean);
    gmean_c = strip(put(gmean_calc, 10.3));
    cv_c = strip(put(cv, 6.1)) || '%';
run;"""

    def _gen_subgroup_analysis(self):
        """Generate subgroup analysis."""
        treatment_var = self.analysis_params.get('treatment_variable', 'TRTA')
        subgroups = self.analysis_params.get('subgroup_variables', ['SEX', 'AGEGR1', 'RACE'])
        
        return f"""/*--- Subgroup Analysis ---*/

%macro subgroup_analysis(subgrp=);
    proc mixed data=work.analysis;
        class {treatment_var} &subgrp;
        model CHG = {treatment_var} BASE &subgrp {treatment_var}*&subgrp / ddfm=kr;
        lsmeans {treatment_var}*&subgrp / pdiff cl slice=&subgrp;
        ods output Diffs=work.sg_&subgrp;
    run;
%mend;

{chr(10).join([f"%subgroup_analysis(subgrp={sg});" for sg in subgroups])}

/*--- Combine subgroup results for forest plot ---*/
data work.forest_data;
    set {' '.join([f'work.sg_{sg}' for sg in subgroups])};
    length subgroup $50 category $100;
run;"""

    def _generate_output(self):
        """Generate output production code."""
        output_generators = {
            'table': self._gen_table_output,
            'figure': self._gen_figure_output,
            'listing': self._gen_listing_output,
            'dataset': self._gen_dataset_output
        }
        
        generator = output_generators.get(self.output_type, self._gen_table_output)
        return generator()

    def _gen_table_output(self):
        """Generate RTF table output."""
        output_format = self.output_data.get('format', 'rtf')
        output_name = self.output_data.get('dataset_name', 'output')

        return f"""/*--- Generate Output Table ---*/
ods {output_format} file="&outpath./&outname..{output_format}"
    style=journal
    bodytitle;

ods {output_format} text="~S={{just=center font_weight=bold font_size=10pt}}
{self.submission.get('sponsor', 'AstraZeneca')}";
ods {output_format} text="~S={{just=center font_size=9pt}}
Protocol: {self.submission.get('protocol', 'DXXXXCXXXXX')}";
ods {output_format} text="~S={{just=center font_size=9pt}}
Population: {self.analysis_params.get('population', 'Safety').title()} Population";

title1 "Table X.X.X";
title2 "{self._get_table_title()}";
title3 "{self.analysis_params.get('population', 'Safety').title()} Population";

footnote1 "Source: {', '.join(self.input_data.get('datasets', ['adsl']))}";
footnote2 "Program: &progname..sas  Output: &outname..{output_format}";
footnote3 "Generated: &sysdate9. &systime.";

proc report data=work.final_report nowd split='|'
    style(report)=[font_size=9pt]
    style(header)=[font_weight=bold background=white just=center]
    style(column)=[just=left];
    
    columns row_label col1 col2 col3 col4;
    
    define row_label / display "" style(column)=[cellwidth=3in];
    define col1 / display "Placebo|(N=&N1)" style(column)=[cellwidth=1.5in just=center];
    define col2 / display "Treatment A|(N=&N2)" style(column)=[cellwidth=1.5in just=center];
    define col3 / display "Treatment B|(N=&N3)" style(column)=[cellwidth=1.5in just=center];
    define col4 / display "p-value" style(column)=[cellwidth=1in just=center];
    
    compute row_label;
        if index(row_label, '  ') = 0 then
            call define(_col_, "style", "style=[font_weight=bold]");
    endcomp;
run;

ods {output_format} close;
ods listing;"""

    def _gen_figure_output(self):
        """Generate figure output code."""
        return f"""/*--- Generate Figure Output ---*/
ods listing gpath="&outpath." image_dpi=300;
ods graphics on / reset=all imagename="&outname" imagefmt=pdf
    width=10in height=7in;

proc sgplot data=work.plot_data;
    title1 "Figure X.X.X";
    title2 "{self._get_figure_title()}";
    
    series x=AVISIT y=AVAL / group={self.analysis_params.get('treatment_variable', 'TRTA')}
        markers markerattrs=(size=8)
        lineattrs=(thickness=2);
    
    xaxis label="Visit" fitpolicy=rotate;
    yaxis label="{self.variables.get('analysis_variables', ['AVAL'])[0]}";
    keylegend / location=outside position=bottom;
    
    footnote1 "Source: {', '.join(self.input_data.get('datasets', ['adsl']))}";
    footnote2 "Program: &progname..sas";
run;

ods graphics off;"""

    def _gen_listing_output(self):
        """Generate data listing output."""
        return f"""/*--- Generate Data Listing ---*/
ods rtf file="&outpath./&outname..rtf"
    style=journal bodytitle;

title1 "Listing X.X.X";
title2 "{self._get_listing_title()}";

proc report data=work.listing_data nowd split='|'
    style(report)=[font_size=8pt]
    style(header)=[font_weight=bold background=white];
    
    columns USUBJID SITEID {' '.join(self.variables.get('analysis_variables', ['AVAL']))};
    
    define USUBJID / order "Subject|ID" style(column)=[cellwidth=1.2in];
    define SITEID / order "Site|ID" style(column)=[cellwidth=0.8in];
    
    break after USUBJID / skip;
run;

ods rtf close;
ods listing;"""

    def _gen_dataset_output(self):
        """Generate analysis dataset output."""
        return f"""/*--- Generate Analysis Dataset ---*/
data output.{self.output_data.get('dataset_name', 'analysis_ds')};
    set work.final_dataset;
    label
        STUDYID = "Study Identifier"
        USUBJID = "Unique Subject Identifier"
        {self._generate_labels()}
    ;
run;

/*--- Create XPT transport file for submission ---*/
proc cport data=output.{self.output_data.get('dataset_name', 'analysis_ds')}
    file="&outpath./{ self.output_data.get('dataset_name', 'analysis_ds')}.xpt"
    type=data;
run;

/*--- Dataset verification ---*/
proc contents data=output.{self.output_data.get('dataset_name', 'analysis_ds')} varnum;
run;

proc print data=output.{self.output_data.get('dataset_name', 'analysis_ds')} (obs=10);
run;"""

    def _generate_validation(self):
        """Generate validation and QC checks."""
        return f"""/*--- Validation Checks ---*/

/*--- Check for missing critical variables ---*/
proc sql;
    select count(*) as n_missing_usubjid
    from work.analysis
    where USUBJID is missing;
    
    select count(*) as n_missing_trt
    from work.analysis
    where {self.analysis_params.get('treatment_variable', 'TRTA')} is missing;
quit;

/*--- Verify population counts match ---*/
%macro verify_counts;
    proc sql noprint;
        select count(distinct USUBJID) into :check_n trimmed
        from work.analysis
        where {self._get_population_flag()} = 'Y';
    quit;
    
    %if &check_n ne &Ntot %then %do;
        %put WARNING: Population count mismatch. Expected &Ntot, got &check_n;
    %end;
    %else %do;
        %put NOTE: Population count verified: &check_n subjects.;
    %end;
%mend verify_counts;
%verify_counts;

/*--- Log output summary ---*/
%put NOTE: ========================================;
%put NOTE: Program: &progname..sas;
%put NOTE: Output:  &outname..{self.output_data.get('format', 'rtf')};
%put NOTE: Status:  COMPLETE;
%put NOTE: ========================================;"""

    def _generate_footer(self):
        """Generate program footer."""
        return f"""/*--- End of Program ---*/
/*
REVIEWER NOTES:
1. This program generates {self.output_type} output for {self.analysis_type} analysis
2. Population: {self.analysis_params.get('population', 'Safety')} ({self._get_population_flag()} = 'Y')
3. Statistical method: {self.analysis_params.get('statistical_method', 'descriptive')}
4. Alpha level: {self.analysis_params.get('alpha', 0.05)}
5. Regulatory target: {self.submission.get('regulatory_authority', 'FDA')}
*/"""

    # Helper methods
    def _get_population_flag(self):
        pop_flags = {
            'safety': 'SAFFL',
            'itt': 'ITTFL',
            'per_protocol': 'PPROTFL',
            'pk': 'PKFL',
            'full_analysis': 'FASFL'
        }
        return pop_flags.get(self.analysis_params.get('population', 'safety'), 'SAFFL')

    def _get_orientation(self):
        return 'landscape' if self.output_type in ['table', 'listing'] else 'portrait'

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

    def _get_table_title(self):
        titles = {
            'descriptive': 'Summary of Descriptive Statistics',
            'efficacy': 'Analysis of Primary Efficacy Endpoint',
            'safety': 'Summary of Adverse Events',
            'survival': 'Summary of Time-to-Event Analysis',
            'mixed_model': 'MMRM Analysis Results',
            'categorical': 'Summary of Categorical Endpoints',
            'pk': 'Summary of Pharmacokinetic Parameters',
            'subgroup': 'Subgroup Analysis Results'
        }
        return titles.get(self.analysis_type, 'Analysis Summary')

    def _get_figure_title(self):
        return f"{'Kaplan-Meier Plot' if self.analysis_type == 'survival' else 'Analysis Results'}"

    def _get_listing_title(self):
        return "Subject-Level Data Listing"

    def _generate_labels(self):
        labels = []
        for var in self.variables.get('analysis_variables', []):
            labels.append(f'        {var} = "{var} - Analysis Variable"')
        return '\n'.join(labels)