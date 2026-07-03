/******************************************************************************
* PROGRAM NAME  : t_ae_summary.sas
* STUDY         : STUDY-001
* PROTOCOL      : D1234C00001
* SPONSOR       : AstraZeneca
* PURPOSE       : Statistical analysis
* INPUT         : adsl, adae
* OUTPUT        : t_ae_summary.rtf
* ANALYSIS TYPE : 
* OUTPUT TYPE   : Table
* POPULATION    : Safety
*
* AUTHOR        : [Programmer Name]
* DATE CREATED  : 08Jun2026
* DATE MODIFIED : 08Jun2026
*
* REGULATORY    : FDA
* SUBMISSION    : NDA
*
* VALIDATION    : Independent double programming required
* CDISC VERSION : ADaM IG v1.3 / SDTM IG v3.4
*
* MODIFICATION HISTORY:
* DATE        PROGRAMMER    DESCRIPTION
* ---------   ----------    ------------------------------------------------
* 08Jun2026  [Name]        Initial creation
******************************************************************************/

/*--- Program Setup ---*/
%let study    = STUDY-001;
%let protocol = D1234C00001;
%let progname = t_ae_summary;
%let outname  = t_ae_summary;
%let popflag  = SAFFL;
%let trtvar   = TRTA;
%let alpha    = 0.05;
%let conflev  = 0.95;

/*--- System Options ---*/
options nodate nonumber orientation=landscape 
        ls=200 ps=60 missing=' ' formchar='|_---|+|---+=|-/\<>*';
options mprint mlogic symbolgen;

/*--- ODS Setup ---*/
ods listing close;
ods escapechar = '~';

/*--- Library References ---*/
libname adam "/data/adam" access=readonly;
libname output "/output/tables";

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
run;

/*--- Read ADSL dataset ---*/
data work.adsl;
    set adam.adsl;
    where SAFFL = 'Y';
run;

proc sort data=work.adsl;
    by USUBJID AVISITN;
run;

/*--- Verify record count ---*/
proc sql noprint;
    select count(*) into :n_adsl trimmed
    from work.adsl;
quit;
%put NOTE: ADSL has &n_adsl records after filtering.;

/*--- Read ADAE dataset ---*/
data work.adae;
    set adam.adae;
    where SAFFL = 'Y';
run;

proc sort data=work.adae;
    by USUBJID AVISITN;
run;

/*--- Verify record count ---*/
proc sql noprint;
    select count(*) into :n_adae trimmed
    from work.adae;
quit;
%put NOTE: ADAE has &n_adae records after filtering.;

/*--- Data Preparation ---*/
data work.analysis;
    set work.adsl;
    
    /*--- Derive analysis variables ---*/
    length col1-col4 $200;
    
    /*--- Treatment group ordering ---*/
    select (TRTA);
        when ('Placebo')       trtn = 1;
        when ('Treatment A')   trtn = 2;
        when ('Treatment B')   trtn = 3;
        otherwise              trtn = 99;
    end;
    
    /*--- Create Total group for summary ---*/
    output;
    TRTA = 'Total';
    trtn = 99;
    output;
run;

proc sort data=work.analysis;
    by trtn TRTA TRTA AVISIT;
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

%put NOTE: Population counts - Placebo=&N1, TrtA=&N2, TrtB=&N3, Total=&Ntot;

/*--- Descriptive Statistics ---*/
proc means data=work.analysis nway noprint;
    class TRTA trtn TRTA AVISIT;
    var AVAL CHG;
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
    by trtn TRTA;
run;

/*--- Transpose for report layout ---*/
proc transpose data=work.stats_fmt out=work.stats_t (drop=_name_) prefix=col;
    by TRTA AVISIT /* row identifiers */;
    id trtn;
    var n_c mean_sd median_c q1q3 minmax;
run;

/*--- Generate Output Table ---*/
ods rtf file="&outpath./&outname..rtf"
    style=journal
    bodytitle;

ods rtf text="~S={just=center font_weight=bold font_size=10pt}
AstraZeneca";
ods rtf text="~S={just=center font_size=9pt}
Protocol: D1234C00001";
ods rtf text="~S={just=center font_size=9pt}
Population: Safety Population";

title1 "Table X.X.X";
title2 "Analysis Summary";
title3 "Safety Population";

footnote1 "Source: adsl, adae";
footnote2 "Program: &progname..sas  Output: &outname..rtf";
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

ods rtf close;
ods listing;

/*--- Validation Checks ---*/

/*--- Check for missing critical variables ---*/
proc sql;
    select count(*) as n_missing_usubjid
    from work.analysis
    where USUBJID is missing;
    
    select count(*) as n_missing_trt
    from work.analysis
    where TRTA is missing;
quit;

/*--- Verify population counts match ---*/
%macro verify_counts;
    proc sql noprint;
        select count(distinct USUBJID) into :check_n trimmed
        from work.analysis
        where SAFFL = 'Y';
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
%put NOTE: Output:  &outname..rtf;
%put NOTE: Status:  COMPLETE;
%put NOTE: ========================================;

/*--- End of Program ---*/
/*
REVIEWER NOTES:
1. This program generates table output for  analysis
2. Population: safety (SAFFL = 'Y')
3. Statistical method: anova
4. Alpha level: 0.05
5. Regulatory target: FDA
*/