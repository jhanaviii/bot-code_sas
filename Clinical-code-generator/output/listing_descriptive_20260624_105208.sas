/******************************************************************************
* PROGRAM NAME  : .sas
* STUDY         : 
* PROTOCOL      : 
* SPONSOR       : 
* PURPOSE       : Generate descriptive statistics summary
* INPUT         : adsl
* OUTPUT        : .pdf
* ANALYSIS TYPE : Descriptive
* OUTPUT TYPE   : Listing
* POPULATION    : 
*
* AUTHOR        : [Programmer Name]
* DATE CREATED  : 24Jun2026
* DATE MODIFIED : 24Jun2026
*
* REGULATORY    : 
* SUBMISSION    : 
*
* VALIDATION    : Independent double programming required
* CDISC VERSION : ADaM IG v1.3 / SDTM IG v3.4
*
* MODIFICATION HISTORY:
* DATE        PROGRAMMER    DESCRIPTION
* ---------   ----------    ------------------------------------------------
* 24Jun2026  [Name]        Initial creation
******************************************************************************/

/*--- Program Setup ---*/
%let study    = ;
%let protocol = ;
%let progname = ;
%let outname  = ;
%let popflag  = SAFFL;
%let trtvar   = ;
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
libname adam "" access=readonly;
libname output "";

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
    by ;
run;

/*--- Verify record count ---*/
proc sql noprint;
    select count(*) into :n_adsl trimmed
    from work.adsl;
quit;
%put NOTE: ADSL has &n_adsl records after filtering.;

/*--- Data Preparation ---*/
data work.analysis;
    set work.adsl;
    
    /*--- Derive analysis variables ---*/
    length col1-col4 $200;
    
    /*--- Treatment group ordering ---*/
    select ();
        when ('Placebo')       trtn = 1;
        when ('Treatment A')   trtn = 2;
        when ('Treatment B')   trtn = 3;
        otherwise              trtn = 99;
    end;
    
    /*--- Create Total group for summary ---*/
    output;
     = 'Total';
    trtn = 99;
    output;
run;

proc sort data=work.analysis;
    by trtn  ;
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
    class  trtn ;
    var ;
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
    by trtn ;
run;

/*--- Transpose for report layout ---*/
proc transpose data=work.stats_fmt out=work.stats_t (drop=_name_) prefix=col;
    by /* row identifiers */;
    id trtn;
    var n_c mean_sd median_c q1q3 minmax;
run;

/*--- Generate Data Listing ---*/
ods rtf file="&outpath./&outname..rtf"
    style=journal bodytitle;

title1 "Listing X.X.X";
title2 "Subject-Level Data Listing";

proc report data=work.listing_data nowd split='|'
    style(report)=[font_size=8pt]
    style(header)=[font_weight=bold background=white];
    
    columns USUBJID SITEID ;
    
    define USUBJID / order "Subject|ID" style(column)=[cellwidth=1.2in];
    define SITEID / order "Site|ID" style(column)=[cellwidth=0.8in];
    
    break after USUBJID / skip;
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
    where  is missing;
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
%put NOTE: Output:  &outname..pdf;
%put NOTE: Status:  COMPLETE;
%put NOTE: ========================================;

/*--- End of Program ---*/
/*
REVIEWER NOTES:
1. This program generates listing output for descriptive analysis
2. Population:  (SAFFL = 'Y')
3. Statistical method: 
4. Alpha level: 0.05
5. Regulatory target: 
*/