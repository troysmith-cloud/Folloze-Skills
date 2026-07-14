const TEMPLATE_SPREADSHEET_ID = '1IQNrquCt4rRdaUcSAiUvMLf1Icu6YOzuikSQLYpIvyQ';
const CUSTOMER_FORM_TAB = 'Customer Program Form';
const PROGRAMS_KPIS_TAB = 'Programs and KPIs';

function doGet() {
  return htmlResponse_('Program KPI Sheet Builder', '<p>This endpoint creates a customer workbook from a posted Folloze Program KPI board payload.</p>');
}

function doPost(e) {
  try {
    const payloadText = e && e.parameter && e.parameter.payload ? e.parameter.payload : '{}';
    const payload = JSON.parse(payloadText);
    const result = createCustomerProgramWorkbook_(payload);
    return redirectResponse_(result.url);
  } catch (err) {
    return htmlResponse_('Sheet builder error', `<p>${escapeHtml_(err && err.message ? err.message : String(err))}</p>`);
  }
}

function createCustomerProgramWorkbook_(payload) {
  const customerName = cleanName_(payload.customerName || 'Customer');
  const title = `${customerName} Program KPI Waterfall`;
  const copy = DriveApp.getFileById(TEMPLATE_SPREADSHEET_ID).makeCopy(title);
  const spreadsheet = SpreadsheetApp.openById(copy.getId());

  spreadsheet.rename(title);
  populateCustomerProgramForm_(spreadsheet, payload);
  populateProgramsAndKpis_(spreadsheet, payload);

  return {
    id: spreadsheet.getId(),
    url: spreadsheet.getUrl(),
    title
  };
}

function populateCustomerProgramForm_(spreadsheet, payload) {
  const sheet = getOrCreateSheet_(spreadsheet, CUSTOMER_FORM_TAB);
  const form = payload.outputTabs && payload.outputTabs.customerProgramForm ? payload.outputTabs.customerProgramForm : {};
  const headers = form.headers || [];
  const rows = form.rows || [];
  const width = Math.max(headers.length, ...rows.map(row => row.length), 1);
  const maxRows = Math.max(sheet.getMaxRows() - 3, rows.length, 1);

  ensureSheetSize_(sheet, Math.max(rows.length + 3, 4), width);
  sheet.getRange(1, 1).setValue(`${payload.customerName || 'Customer'} Program Waterfall Form`);
  sheet.getRange(2, 1).setValue('Created from the Folloze Deployment Planning & Program Workspace.');
  sheet.getRange(3, 1, maxRows + 1, width).clearContent();
  if (headers.length) sheet.getRange(3, 1, 1, width).setValues([padRow_(headers, width)]);
  if (rows.length) sheet.getRange(4, 1, rows.length, width).setValues(rows.map(row => padRow_(row, width)));
  sheet.autoResizeColumns(1, Math.min(width, 26));
}

function populateProgramsAndKpis_(spreadsheet, payload) {
  const sheet = getOrCreateSheet_(spreadsheet, PROGRAMS_KPIS_TAB);
  const programsTab = payload.outputTabs && payload.outputTabs.programsAndKpis ? payload.outputTabs.programsAndKpis : {};
  const sections = programsTab.sections || [];
  const rows = [];

  sections.forEach((program, index) => {
    if (index > 0) rows.push([]);
    rows.push([program.heading || `Segment/ Program ${index + 1}: ${program.programName || 'Program'}`, program.programName || '', '', '', '', 'Channels', program.channelsText || '']);
    rows.push(['Description:', program.description || '', '', '', '', 'Period', [program.programYear, program.quarter].filter(Boolean).join(' ')]);
    rows.push(['', '', 'Benchmarks']);
    rows.push([`Target Funnel Model: ${program.programName || ''}`, '', 'Parameters']);
    rows.push(['Total Addressable Market (TAM, expressed in number of accounts)']);
    (program.metrics || []).forEach(metric => rows.push(metric));
    rows.push(['Primary Content / Messaging', program.primaryContent || '']);
    rows.push(['Secondary Content / Messaging', program.secondaryContent || '']);
    rows.push(['Channels', program.channelsText || '']);
  });

  if (!rows.length) rows.push(['No programs exported from the board yet.']);
  const width = Math.max(...rows.map(row => row.length), 8);
  const requiredRows = Math.max(rows.length, 1);
  ensureSheetSize_(sheet, requiredRows, width);
  sheet.getRange(1, 1, sheet.getMaxRows(), Math.min(sheet.getMaxColumns(), width)).clearContent();
  sheet.getRange(1, 1, requiredRows, width).setValues(rows.map(row => padRow_(row, width)));
  sheet.autoResizeColumns(1, Math.min(width, 8));
}

function getOrCreateSheet_(spreadsheet, name) {
  return spreadsheet.getSheetByName(name) || spreadsheet.insertSheet(name);
}

function ensureSheetSize_(sheet, rowCount, columnCount) {
  if (sheet.getMaxRows() < rowCount) {
    sheet.insertRowsAfter(sheet.getMaxRows(), rowCount - sheet.getMaxRows());
  }
  if (sheet.getMaxColumns() < columnCount) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), columnCount - sheet.getMaxColumns());
  }
}

function padRow_(row, width) {
  const result = row.slice(0, width);
  while (result.length < width) result.push('');
  return result;
}

function cleanName_(name) {
  return String(name || 'Customer').replace(/[\\/:*?"<>|#\\[\\]]/g, '').trim() || 'Customer';
}

function redirectResponse_(url) {
  return HtmlService
    .createHtmlOutput(`<p>Customer workbook created. Opening <a href="${escapeHtml_(url)}" target="_top">the Google Sheet</a>.</p><script>window.top.location.replace(${JSON.stringify(url)});</script>`)
    .setTitle('Customer workbook created');
}

function htmlResponse_(title, body) {
  return HtmlService
    .createHtmlOutput(`<h1>${escapeHtml_(title)}</h1>${body}`)
    .setTitle(title);
}

function escapeHtml_(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
