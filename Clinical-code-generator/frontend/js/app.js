/**
 * arc_gen — Analysis and Reporting Code Generator
 * Frontend application logic
 * Generates SAS, R, and Python simultaneously
 * Contextual UI — options appear based on analysis type selection
 */

const API_BASE = 'http://localhost:5001/api';

// ── Context Maps — define what's relevant per analysis type ────────────────

const ANALYSIS_CONFIG = {
  descriptive: {
    label: 'Descriptive Statistics',
    outputTypes: ['table', 'listing', 'dataset'],
    methods: [
      { v: 'anova', l: 'ANOVA / ANCOVA' },
      { v: 'wilcoxon', l: 'Wilcoxon Rank-Sum' },
    ],
    populations: [
      { v: 'safety', l: 'Safety Population (SAFFL)' },
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
    ],
    datasets: 'adsl',
    placeholders: {
      analysisVars: 'AVAL, CHG, PCHG',
      groupingVars: 'TRTA, AVISIT',
      filterVars: 'SAFFL',
      sortVars: 'USUBJID, AVISITN',
    },
    showCovariates: false,
    showSubgroup: false,
  },
  efficacy: {
    label: 'Efficacy Analysis',
    outputTypes: ['table', 'figure', 'dataset'],
    methods: [
      { v: 'anova', l: 'ANOVA / ANCOVA' },
      { v: 'mmrm', l: 'MMRM' },
    ],
    populations: [
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
      { v: 'per_protocol', l: 'Per Protocol (PPROTFL)' },
    ],
    datasets: 'adsl, adeff',
    placeholders: {
      analysisVars: 'AVAL, CHG',
      groupingVars: 'TRTA, AVISIT',
      filterVars: 'ITTFL, ANL01FL',
      sortVars: 'USUBJID, AVISITN',
    },
    showCovariates: true,
    showSubgroup: false,
  },
  safety: {
    label: 'Safety Analysis',
    outputTypes: ['table', 'listing', 'figure'],
    methods: [
      { v: 'chi_square', l: 'Chi-Square Test' },
      { v: 'fisher_exact', l: 'Fisher\'s Exact Test' },
      { v: 'cmh', l: 'Cochran-Mantel-Haenszel' },
    ],
    populations: [
      { v: 'safety', l: 'Safety Population (SAFFL)' },
    ],
    datasets: 'adsl, adae',
    placeholders: {
      analysisVars: 'AEDECOD, AEBODSYS',
      groupingVars: 'TRTA',
      filterVars: 'SAFFL',
      sortVars: 'USUBJID, AESTDTC',
    },
    showCovariates: false,
    showSubgroup: false,
  },
  survival: {
    label: 'Survival Analysis',
    outputTypes: ['table', 'figure', 'dataset'],
    methods: [
      { v: 'kaplan_meier', l: 'Kaplan-Meier' },
      { v: 'cox_regression', l: 'Cox Proportional Hazards' },
      { v: 'log_rank', l: 'Log-Rank Test' },
    ],
    populations: [
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
      { v: 'per_protocol', l: 'Per Protocol (PPROTFL)' },
    ],
    datasets: 'adsl, adtte',
    placeholders: {
      analysisVars: 'AVAL, CNSR',
      groupingVars: 'TRTA',
      filterVars: 'ITTFL',
      sortVars: 'USUBJID',
    },
    showCovariates: true,
    showSubgroup: false,
  },
  mixed_model: {
    label: 'Mixed Models (MMRM)',
    outputTypes: ['table', 'figure'],
    methods: [
      { v: 'mmrm', l: 'Mixed Model Repeated Measures' },
    ],
    populations: [
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
    ],
    datasets: 'adsl, adeff',
    placeholders: {
      analysisVars: 'AVAL, CHG',
      groupingVars: 'TRTA, AVISIT',
      filterVars: 'ITTFL, ANL01FL',
      sortVars: 'USUBJID, AVISITN',
    },
    showCovariates: true,
    showSubgroup: false,
  },
  categorical: {
    label: 'Categorical Analysis',
    outputTypes: ['table', 'figure'],
    methods: [
      { v: 'chi_square', l: 'Chi-Square Test' },
      { v: 'fisher_exact', l: 'Fisher\'s Exact Test' },
      { v: 'cmh', l: 'Cochran-Mantel-Haenszel' },
      { v: 'logistic_regression', l: 'Logistic Regression' },
    ],
    populations: [
      { v: 'safety', l: 'Safety Population (SAFFL)' },
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
    ],
    datasets: 'adsl, adrs',
    placeholders: {
      analysisVars: 'AVALC, RSRESP',
      groupingVars: 'TRTA',
      filterVars: 'ITTFL',
      sortVars: 'USUBJID',
    },
    showCovariates: false,
    showSubgroup: false,
  },
  pk: {
    label: 'Pharmacokinetics',
    outputTypes: ['table', 'listing', 'dataset'],
    methods: [
      { v: 'anova', l: 'ANOVA (log-transformed)' },
      { v: 'wilcoxon', l: 'Wilcoxon Rank-Sum' },
    ],
    populations: [
      { v: 'pk', l: 'PK Population (PKFL)' },
    ],
    datasets: 'adsl, adpc, adpp',
    placeholders: {
      analysisVars: 'AVAL (Cmax, AUC, Tmax)',
      groupingVars: 'TRTA, PARAMCD',
      filterVars: 'PKFL',
      sortVars: 'USUBJID, PCTPTNUM',
    },
    showCovariates: false,
    showSubgroup: false,
  },
  subgroup: {
    label: 'Subgroup Analysis',
    outputTypes: ['figure', 'table'],
    methods: [
      { v: 'cox_regression', l: 'Cox Proportional Hazards' },
      { v: 'anova', l: 'ANOVA / ANCOVA' },
      { v: 'logistic_regression', l: 'Logistic Regression' },
    ],
    populations: [
      { v: 'itt', l: 'Intent-to-Treat (ITTFL)' },
      { v: 'full_analysis', l: 'Full Analysis Set (FASFL)' },
      { v: 'safety', l: 'Safety Population (SAFFL)' },
    ],
    datasets: 'adsl, adtte',
    placeholders: {
      analysisVars: 'AVAL, CHG',
      groupingVars: 'TRTA',
      filterVars: 'ITTFL',
      sortVars: 'USUBJID',
    },
    showCovariates: true,
    showSubgroup: true,
  },
};

const OUTPUT_TYPE_META = {
  table:   { icon: 'fa-table',      label: 'Table',   formats: [{v:'rtf',l:'RTF'},{v:'pdf',l:'PDF'},{v:'xlsx',l:'Excel (XLSX)'},{v:'html',l:'HTML'}] },
  figure:  { icon: 'fa-chart-line',  label: 'Figure',  formats: [{v:'pdf',l:'PDF'},{v:'png',l:'PNG'},{v:'svg',l:'SVG'},{v:'rtf',l:'RTF'}] },
  listing: { icon: 'fa-list-alt',    label: 'Listing', formats: [{v:'rtf',l:'RTF'},{v:'pdf',l:'PDF'},{v:'xlsx',l:'Excel (XLSX)'}] },
  dataset: { icon: 'fa-database',    label: 'Dataset', formats: [{v:'xpt',l:'XPT (Transport)'},{v:'sas7bdat',l:'SAS Dataset'},{v:'csv',l:'CSV'},{v:'rds',l:'RDS (R)'}] },
};

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  activeLanguage: 'sas',
  analysisType: '',
  outputType: '',
  shellFileId: null,
  specFileId: null,
  results: { sas: null, r: null, python: null },
};

// ── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initSectionCollapse();
  initAnalysisGrid();
  initTabNavigation();
  initOutputLangTabs();
  initFileUploads();
  initGenerateButton();
  initToolbarActions();
  checkApiHealth();
});

// ── Theme Toggle ───────────────────────────────────────────────────────────
function initThemeToggle() {
  const btn  = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-icon');
  const saved = localStorage.getItem('arcgen-theme') || 'dark';

  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved, icon);

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next    = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('arcgen-theme', next);
    updateThemeIcon(next, icon);
    updateHljsTheme(next);
  });
}

function updateThemeIcon(theme, icon) {
  icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

function updateHljsTheme(theme) {
  const link = document.getElementById('hljs-theme');
  link.href = theme === 'light'
    ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css'
    : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css';
  const codeEl = document.getElementById('generated-code');
  if (codeEl && codeEl.textContent) hljs.highlightElement(codeEl);
}

// ── Section collapse ───────────────────────────────────────────────────────
function initSectionCollapse() {
  document.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      header.closest('.panel-section').classList.toggle('collapsed');
    });
  });
}

// ── Analysis type grid — THE MAIN DRIVER ───────────────────────────────────
function initAnalysisGrid() {
  document.querySelectorAll('.analysis-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.analysis-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.analysisType = card.dataset.analysis;
      state.outputType = ''; // reset output type
      onAnalysisTypeChanged(state.analysisType);
    });
  });
}

function onAnalysisTypeChanged(type) {
  const config = ANALYSIS_CONFIG[type];
  if (!config) return;

  // Show all context sections with animation
  document.querySelectorAll('.context-section').forEach(el => {
    el.style.display = '';
  });

  // Populate Output Type grid
  renderOutputTypeGrid(config.outputTypes);

  // Populate Statistical Method dropdown
  renderMethodDropdown(config.methods);

  // Populate Population dropdown
  renderPopulationDropdown(config.populations);

  // Set dataset placeholder
  document.getElementById('input-datasets').placeholder = config.datasets;

  // Set variable placeholders
  document.getElementById('analysis-vars').placeholder = config.placeholders.analysisVars;
  document.getElementById('grouping-vars').placeholder = config.placeholders.groupingVars;
  document.getElementById('filter-vars').placeholder = config.placeholders.filterVars;
  document.getElementById('sort-vars').placeholder = config.placeholders.sortVars;

  // Show/hide covariates
  document.getElementById('group-covariates').style.display = config.showCovariates ? '' : 'none';

  // Show/hide subgroup variables
  document.getElementById('group-subgroup-vars').style.display = config.showSubgroup ? '' : 'none';

  // Reset output format
  document.getElementById('output-format').innerHTML = '<option value="" disabled selected>— Select —</option>';

  toast(`${config.label} selected — configure options below`, 'success');
}

// ── Output type grid (dynamic) ─────────────────────────────────────────────
function renderOutputTypeGrid(types) {
  const grid = document.getElementById('output-type-grid');
  grid.innerHTML = types.map(t => {
    const meta = OUTPUT_TYPE_META[t];
    return `<button class="output-type-btn" data-output="${t}">
      <i class="fas ${meta.icon}"></i> ${meta.label}
    </button>`;
  }).join('');

  // Attach click handlers
  grid.querySelectorAll('.output-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      grid.querySelectorAll('.output-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.outputType = btn.dataset.output;
      updateFormatOptions(state.outputType);
    });
  });
}

function updateFormatOptions(type) {
  const sel = document.getElementById('output-format');
  const meta = OUTPUT_TYPE_META[type];
  if (!meta) return;
  sel.innerHTML = '<option value="" disabled selected>— Select —</option>' +
    meta.formats.map(f => `<option value="${f.v}">${f.l}</option>`).join('');
}

// ── Statistical method dropdown (dynamic) ──────────────────────────────────
function renderMethodDropdown(methods) {
  const sel = document.getElementById('stat-method');
  sel.innerHTML = '<option value="" disabled selected>— Select —</option>' +
    methods.map(m => `<option value="${m.v}">${m.l}</option>`).join('');
}

// ── Population dropdown (dynamic) ──────────────────────────────────────────
function renderPopulationDropdown(populations) {
  const sel = document.getElementById('population');
  sel.innerHTML = '<option value="" disabled selected>— Select —</option>' +
    populations.map(p => `<option value="${p.v}">${p.l}</option>`).join('');
}

// ── Tab navigation (Code / Validation / Metadata) ──────────────────────────
function initTabNavigation() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
    });
  });
}

function switchToTab(tabName) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  if (btn) btn.click();
}

// ── Output Language Tabs ───────────────────────────────────────────────────
function initOutputLangTabs() {
  document.querySelectorAll('.output-lang-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.output-lang-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.activeLanguage = tab.dataset.lang;
      showLanguageCode(state.activeLanguage);
    });
  });
}

function showLanguageCode(lang) {
  const result = state.results[lang];
  if (!result || !result.code) return;

  const codeEl = document.getElementById('generated-code');
  codeEl.className = `language-${lang === 'r' ? 'r' : lang}`;
  codeEl.textContent = result.code;
  hljs.highlightElement(codeEl);

  const lines = result.code.split('\n').length;
  const bytes = new TextEncoder().encode(result.code).length;
  document.getElementById('code-lines').innerHTML =
    `<i class="fas fa-align-left"></i> ${lines.toLocaleString()} lines`;
  document.getElementById('code-size').innerHTML =
    `<i class="fas fa-weight-scale"></i> ${formatBytes(bytes)}`;

  displayValidation(result.validation);
}

// ── File uploads ───────────────────────────────────────────────────────────
function initFileUploads() {
  setupUploadZone('shell-upload-area', 'shell-file', 'shell');
  setupUploadZone('spec-upload-area',  'spec-file',  'specification');
}

function setupUploadZone(zoneId, inputId, type) {
  const zone  = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', e => { if (e.target.files[0]) uploadFile(e.target.files[0], type); });

  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file, type);
  });
}

async function uploadFile(file, type) {
  const statusId = type === 'shell' ? 'shell-status' : 'spec-status';
  const zoneId   = type === 'shell' ? 'shell-upload-area' : 'spec-upload-area';
  const statusEl = document.getElementById(statusId);
  const zoneEl   = document.getElementById(zoneId);

  setUploadStatus(statusEl, 'Uploading…', '');

  try {
    const fd = new FormData();
    fd.append('file', file);

    const res  = await fetch(`${API_BASE}/upload/${type}`, { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success) {
      if (type === 'shell') state.shellFileId = data.file_id;
      else                  state.specFileId  = data.file_id;
      zoneEl.classList.add('uploaded');
      setUploadStatus(statusEl, `✓ ${data.filename}`, 'success');
      toast(`${data.filename} uploaded`, 'success');
    } else {
      setUploadStatus(statusEl, `✗ ${data.error}`, 'error');
    }
  } catch (err) {
    setUploadStatus(statusEl, `✗ ${err.message}`, 'error');
  }
}

function setUploadStatus(el, msg, cls) {
  el.textContent = msg;
  el.className = `upload-status ${cls}`;
}

// ── Generate ───────────────────────────────────────────────────────────────
function initGenerateButton() {
  document.getElementById('generate-btn').addEventListener('click', generateAllCode);
}

function validateBeforeGenerate() {
  const errors = [];
  if (!state.analysisType) errors.push('Analysis Type');
  if (!state.outputType)   errors.push('Output Type');

  const datasets = document.getElementById('input-datasets')?.value?.trim();
  if (!datasets) errors.push('Datasets');

  if (errors.length > 0) {
    toast(`Please select: ${errors.join(', ')}`, 'error');
    return false;
  }
  return true;
}

async function generateAllCode() {
  if (!validateBeforeGenerate()) return;

  const btn = document.getElementById('generate-btn');
  btn.classList.add('loading');
  btn.innerHTML = '<span class="spin"><i class="fas fa-circle-notch"></i></span> Generating SAS, R & Python…';

  const payload = buildPayload();

  try {
    const res = await fetch(`${API_BASE}/generate-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.success) {
      state.results.sas    = data.results.sas    || null;
      state.results.r      = data.results.r      || null;
      state.results.python = data.results.python || null;

      updateLangTabStatus('sas',    state.results.sas);
      updateLangTabStatus('r',      state.results.r);
      updateLangTabStatus('python', state.results.python);

      displayCodeFromResults(state.activeLanguage);
      displayValidation(state.results[state.activeLanguage]?.validation);
      displayAllMetadata(state.results);

      const successCount = ['sas','r','python'].filter(l => state.results[l]?.code).length;
      toast(`Code generated in ${successCount}/3 languages`, 'success');
    } else {
      displayError(data.error || 'Unknown error from server');
      toast(data.error || 'Generation failed', 'error');
    }
  } catch (err) {
    displayError(`Connection error: ${err.message}. Ensure the backend is running on port 5001.`);
    toast('Backend unavailable', 'error');
  } finally {
    btn.classList.remove('loading');
    btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Generate All Code';
  }
}

function updateLangTabStatus(lang, result) {
  const statusEl = document.getElementById(`status-${lang}`);
  if (!statusEl) return;
  statusEl.className = 'output-lang-status';

  if (!result || result.error) {
    statusEl.classList.add('has-error');
  } else if (result.validation?.compliant) {
    statusEl.classList.add('valid');
  } else {
    statusEl.classList.add('invalid');
  }
}

function displayCodeFromResults(lang) {
  const result = state.results[lang];
  const codeEl       = document.getElementById('generated-code');
  const codeArea     = document.getElementById('code-area');
  const placeholder  = document.getElementById('code-placeholder');
  const pre          = codeArea.querySelector('pre');

  if (!result || !result.code) {
    codeEl.className = 'language-plaintext';
    codeEl.textContent = result?.error
      ? `/* ERROR generating ${lang.toUpperCase()} code */\n/* ${result.error} */`
      : `/* No ${lang.toUpperCase()} code generated */`;
    placeholder.style.display = 'none';
    pre.style.display = 'block';
    hljs.highlightElement(codeEl);
    return;
  }

  codeEl.className = `language-${lang}`;
  codeEl.textContent = result.code;
  hljs.highlightElement(codeEl);

  placeholder.style.display = 'none';
  pre.style.display = 'block';

  const lines = result.code.split('\n').length;
  const bytes = new TextEncoder().encode(result.code).length;
  document.getElementById('code-lines').innerHTML =
    `<i class="fas fa-align-left"></i> ${lines.toLocaleString()} lines`;
  document.getElementById('code-size').innerHTML =
    `<i class="fas fa-weight-scale"></i> ${formatBytes(bytes)}`;

  displayValidation(result.validation);
  switchToTab('code');
}

function buildPayload() {
  const gv  = id => document.getElementById(id)?.value || '';
  const gl  = id => gv(id).split(',').map(s => s.trim()).filter(Boolean);

  return {
    analysis_type: state.analysisType,
    output_type:   state.outputType,
    input_data: {
      datasets:     gl('input-datasets'),
      format:       gv('data-format'),
      library_path: gv('library-path'),
    },
    output_data: {
      dataset_name: gv('output-name'),
      format:       gv('output-format'),
      output_path:  gv('output-path'),
    },
    variables: {
      analysis_variables: gl('analysis-vars'),
      grouping_variables: gl('grouping-vars'),
      filter_variables:   gl('filter-vars'),
      sort_variables:     gl('sort-vars'),
      subgroup_variables: gl('subgroup-vars'),
    },
    analysis_parameters: {
      statistical_method: gv('stat-method'),
      confidence_level:   parseFloat(gv('conf-level')) || 0.95,
      alpha:              parseFloat(gv('alpha'))       || 0.05,
      population:         gv('population'),
      treatment_variable: gv('trt-var') || '',
      covariates:         gl('covariates'),
    },
    submission_details: {
      study_id:             gv('study-id'),
      sponsor:              gv('sponsor'),
      protocol:             gv('protocol'),
      regulatory_authority: gv('reg-authority'),
      submission_type:      gv('submission-type'),
    },
    shell_file_id:         state.shellFileId,
    specification_file_id: state.specFileId,
  };
}

// ── Display helpers ────────────────────────────────────────────────────────
function formatBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b/1024).toFixed(1)} KB`;
  return `${(b/1048576).toFixed(1)} MB`;
}

function displayError(msg) {
  const codeEl      = document.getElementById('generated-code');
  const codeArea    = document.getElementById('code-area');
  const placeholder = document.getElementById('code-placeholder');
  const pre         = codeArea.querySelector('pre');

  codeEl.className = 'language-plaintext';
  codeEl.textContent = `/* ══════════════════════════════════════════════\n   ERROR\n   ${msg}\n══════════════════════════════════════════════ */`;
  hljs.highlightElement(codeEl);
  placeholder.style.display = 'none';
  pre.style.display = 'block';
}

// ── Validation ─────────────────────────────────────────────────────────────
function displayValidation(validation) {
  if (!validation) return;

  const container = document.getElementById('validation-results');
  const checks    = validation.checks   || [];
  const warnings  = validation.warnings || [];
  const errors    = validation.errors   || [];
  const total     = warnings.length + errors.length;

  const badge = document.getElementById('validation-badge');
  if (total > 0) {
    badge.textContent = total;
    badge.style.display = 'inline-flex';
  } else {
    badge.style.display = 'none';
  }

  let html = `<div class="validation-summary ${validation.compliant ? 'compliant' : 'non-compliant'} fade-in-up">
    <div class="validation-summary-icon">
      <i class="fas fa-${validation.compliant ? 'circle-check' : 'circle-exclamation'}"></i>
    </div>
    <div>
      <div class="validation-summary-title">
        ${validation.compliant ? 'CDISC Compliant' : 'Compliance Issues Found'}
      </div>
      <div class="validation-summary-desc">
        ${checks.length} checks passed · ${warnings.length} warnings · ${errors.length} errors
        <span style="margin-left:8px;opacity:0.7">(${state.activeLanguage.toUpperCase()})</span>
      </div>
    </div>
  </div>`;

  if (checks.length) {
    html += `<div class="fade-in-up">
      <div class="validation-section-title">Checks Passed (${checks.length})</div>
      <div class="validation-items">
        ${checks.map(c => `<div class="v-item check"><i class="fas fa-check"></i>${c}</div>`).join('')}
      </div>
    </div>`;
  }
  if (warnings.length) {
    html += `<div class="fade-in-up">
      <div class="validation-section-title">Warnings (${warnings.length})</div>
      <div class="validation-items">
        ${warnings.map(w => `<div class="v-item warning"><i class="fas fa-triangle-exclamation"></i>${w}</div>`).join('')}
      </div>
    </div>`;
  }
  if (errors.length) {
    html += `<div class="fade-in-up">
      <div class="validation-section-title">Errors (${errors.length})</div>
      <div class="validation-items">
        ${errors.map(e => `<div class="v-item error"><i class="fas fa-circle-xmark"></i>${e}</div>`).join('')}
      </div>
    </div>`;
  }

  container.innerHTML = html;
}

// ── Metadata ───────────────────────────────────────────────────────────────
function displayAllMetadata(results) {
  const container = document.getElementById('metadata-results');
  const readyCount = ['sas','r','python'].filter(l => results[l]?.metadata?.submission_ready).length;
  const allReady   = readyCount === 3;

  let html = `
    <div class="submission-ready-banner ${allReady ? 'ready' : 'review'} fade-in-up">
      <i class="fas fa-${allReady ? 'circle-check' : 'triangle-exclamation'}"></i>
      <div>
        <div class="submission-ready-text">${allReady ? 'All Languages Submission Ready' : `${readyCount}/3 Languages Ready`}</div>
        <div class="submission-ready-sub">
          ${allReady
            ? 'All SAS, R, and Python code passes CDISC compliance checks.'
            : 'Some languages have validation issues. Review the Validation tab per language.'}
        </div>
      </div>
    </div>`;

  const langNames = { sas: 'SAS', r: 'R', python: 'Python' };
  for (const lang of ['sas', 'r', 'python']) {
    const r = results[lang];
    if (!r || !r.metadata) continue;
    const m = r.metadata;
    html += `
    <div class="fade-in-up" style="margin-top:4px">
      <div class="validation-section-title">${langNames[lang]} Output</div>
      <div class="metadata-grid">
        <div class="metadata-card">
          <div class="metadata-card-label">File</div>
          <div class="metadata-card-value accent" style="word-break:break-all;font-size:11.5px">${r.filename || '—'}</div>
        </div>
        <div class="metadata-card">
          <div class="metadata-card-label">Lines / Size</div>
          <div class="metadata-card-value">${m.line_count?.toLocaleString() || 0} lines · ${formatBytes(m.char_count || 0)}</div>
        </div>
        <div class="metadata-card">
          <div class="metadata-card-label">Compliant</div>
          <div class="metadata-card-value ${m.submission_ready ? 'success' : 'warning'}">
            ${m.submission_ready ? '✓ Yes' : '⚠ Review'}
          </div>
        </div>
        <div class="metadata-card">
          <div class="metadata-card-label">Generated At</div>
          <div class="metadata-card-value">${m.generated_at ? new Date(m.generated_at).toLocaleTimeString() : '—'}</div>
        </div>
      </div>
    </div>`;
  }

  container.innerHTML = html;
}

// ── Toolbar ────────────────────────────────────────────────────────────────
function initToolbarActions() {
  document.getElementById('copy-btn').addEventListener('click', async () => {
    const code = state.results[state.activeLanguage]?.code;
    if (!code) { toast('Nothing to copy yet', 'error'); return; }
    try {
      await navigator.clipboard.writeText(code);
      const btn = document.getElementById('copy-btn');
      btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
      btn.classList.add('success');
      setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-copy"></i> Copy';
        btn.classList.remove('success');
      }, 2000);
      toast(`Copied ${state.activeLanguage.toUpperCase()} code`, 'success');
    } catch {
      toast('Copy failed — try manually', 'error');
    }
  });

  document.getElementById('download-btn').addEventListener('click', () => {
    const result = state.results[state.activeLanguage];
    if (!result?.code) { toast('Nothing to download yet', 'error'); return; }
    downloadBlob(result.code, result.filename || `generated.${state.activeLanguage}`);
    toast(`Downloaded ${result.filename}`, 'success');
  });

  document.getElementById('download-all-btn').addEventListener('click', () => {
    let count = 0;
    for (const lang of ['sas', 'r', 'python']) {
      const result = state.results[lang];
      if (result?.code && result.filename) {
        setTimeout(() => downloadBlob(result.code, result.filename), count * 200);
        count++;
      }
    }
    if (count === 0) toast('Nothing to download yet', 'error');
    else toast(`Downloading ${count} files…`, 'success');
  });
}

function downloadBlob(content, filename) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── API Health ─────────────────────────────────────────────────────────────
async function checkApiHealth() {
  const statusEl   = document.getElementById('api-status');
  const statusText = document.getElementById('api-status-text');

  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      statusEl.classList.add('connected');
      statusText.textContent = `API v${data.version || '1.0'} · Online`;
    } else {
      statusEl.classList.remove('connected');
      statusText.textContent = 'API Error';
    }
  } catch {
    statusEl.classList.remove('connected');
    statusText.textContent = 'API Offline';
  }
  setTimeout(checkApiHealth, 30_000);
}

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const icons = { success: 'circle-check', error: 'circle-xmark' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="fas fa-${icons[type] || 'circle-info'}"></i> ${message}`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}