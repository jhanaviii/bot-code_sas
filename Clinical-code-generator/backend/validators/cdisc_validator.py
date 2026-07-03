"""
CDISC Compliance Validator
Validates generated code against CDISC standards and regulatory requirements.
"""


class CDISCValidator:
    def __init__(self):
        self.adam_required_vars = {
            'adsl': ['STUDYID', 'USUBJID', 'SUBJID', 'SITEID', 'ARM', 'TRT01A', 'TRT01P',
                     'SAFFL', 'ITTFL', 'AGE', 'SEX', 'RACE'],
            'adae': ['STUDYID', 'USUBJID', 'AETERM', 'AEDECOD', 'AEBODSYS',
                     'AESTDTC', 'AEENDTC', 'AESEV', 'AESER', 'AEREL'],
            'adtte': ['STUDYID', 'USUBJID', 'PARAMCD', 'PARAM', 'AVAL', 'CNSR',
                      'STARTDT', 'ADT'],
            'adlb': ['STUDYID', 'USUBJID', 'PARAMCD', 'PARAM', 'AVAL', 'BASE',
                     'CHG', 'AVISIT', 'AVISITN', 'ANL01FL']
        }

    def validate(self, config, generated_code):
        """Run all validation checks."""
        results = {
            'compliant': True,
            'checks': [],
            'warnings': [],
            'errors': []
        }

        # Check 1: Required variables referenced
        self._check_required_variables(config, generated_code, results)

        # Check 2: Population flag usage
        self._check_population_flag(config, generated_code, results)

        # Check 3: Output metadata
        self._check_output_metadata(config, generated_code, results)

        # Check 4: Regulatory compliance
        self._check_regulatory_compliance(config, generated_code, results)

        # Check 5: Traceability
        self._check_traceability(config, generated_code, results)

        results['compliant'] = len(results['errors']) == 0
        return results

    def _check_required_variables(self, config, code, results):
        datasets = config.get('input_data', {}).get('datasets', [])
        for ds in datasets:
            if ds in self.adam_required_vars:
                for var in self.adam_required_vars[ds][:5]:  # Check first 5 critical vars
                    if var in code or var.lower() in code.lower():
                        results['checks'].append(f"✓ {ds}.{var} referenced")
                    else:
                        results['warnings'].append(
                            f"⚠ {ds}.{var} not explicitly referenced in code"
                        )

    def _check_population_flag(self, config, code, results):
        pop = config.get('analysis_parameters', {}).get('population', 'safety')
        pop_flags = {
            'safety': 'SAFFL', 'itt': 'ITTFL', 'per_protocol': 'PPROTFL',
            'pk': 'PKFL', 'full_analysis': 'FASFL'
        }
        flag = pop_flags.get(pop, 'SAFFL')
        if flag in code:
            results['checks'].append(f"✓ Population flag {flag} used correctly")
        else:
            results['errors'].append(f"✗ Population flag {flag} not found in code")

    def _check_output_metadata(self, config, code, results):
        required_elements = ['title', 'footnote', 'source', 'program']
        for elem in required_elements:
            if elem.lower() in code.lower():
                results['checks'].append(f"✓ Output contains {elem}")
            else:
                results['warnings'].append(f"⚠ Output may be missing {elem}")

    def _check_regulatory_compliance(self, config, code, results):
        authority = config.get('submission_details', {}).get('regulatory_authority', 'FDA')
        if authority == 'FDA':
            if 'xpt' in code.lower() or 'transport' in code.lower() or 'xport' in code.lower():
                results['checks'].append("✓ XPT transport format referenced (FDA requirement)")
        results['checks'].append(f"✓ Targeting {authority} submission standards")

    def _check_traceability(self, config, code, results):
        if 'study' in code.lower() and 'protocol' in code.lower():
            results['checks'].append("✓ Study and protocol identifiers present")
        else:
            results['warnings'].append("⚠ Missing study/protocol traceability")