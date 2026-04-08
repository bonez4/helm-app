// ============================================================================
// IRR Daily Scale Report — Google Apps Script
// Creates a Gmail draft with the parsed scale report each day at 4:30 PM
// ============================================================================

// ─── Configuration ──────────────────────────────────────────────────────────

const CONFIG = {
  FOLDER_NAME: 'IRR Daily Scale Reports',
  SEND_FROM: 'jd1144inc@gmail.com',
  SEND_TO: 'tim@nantucketoasis.com,office@islandrubbishnantucket.com',
};

// ─── Main entry point (called by time trigger) ─────────────────────────────

function createDailyScaleReport() {
  const today = new Date();
  const file = findTodaysFile(today);
  if (!file) {
    Logger.log('No scale report file found for today: ' + formatSearchDate(today));
    return;
  }

  Logger.log('Found file: ' + file.getName());
  const xmlText = file.getBlob().getDataAsString();
  const rows = parseSpreadsheetML(xmlText);
  const data = parseReport(rows);

  // Save to Supabase
  saveReportToSupabase(data);
  Logger.log('Saved to Supabase.');

  // Load YTD totals
  const ytd = loadYTD();
  const email = generateEmail(data, ytd.ytd2026, ytd.ytd2025, ytd.vin2026, ytd.vin2025);

  // Create draft instead of sending
  GmailApp.createDraft(
    CONFIG.SEND_TO,
    email.subject,
    '', // plain-text fallback (empty — HTML is primary)
    { htmlBody: email.body }
  );

  Logger.log('Draft created: ' + email.subject);
}

// ─── File finder ────────────────────────────────────────────────────────────

function formatSearchDate(d) {
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const y = d.getFullYear();
  return {
    slash:    m + '/' + day + '/' + y,                                        // 4/8/2026
    slashPad: String(m).padStart(2,'0') + '/' + String(day).padStart(2,'0') + '/' + y, // 04/08/2026
    dash:     String(m).padStart(2,'0') + '-' + String(day).padStart(2,'0') + '-' + y, // 04-08-2026
    dashShort: m + '-' + day + '-' + y,                                       // 4-8-2026
  };
}

function findTodaysFile(today) {
  const folders = DriveApp.getFoldersByName(CONFIG.FOLDER_NAME);
  if (!folders.hasNext()) {
    Logger.log('Folder "' + CONFIG.FOLDER_NAME + '" not found in Drive.');
    return null;
  }
  const folder = folders.next();
  const dates = formatSearchDate(today);
  const patterns = [dates.slash, dates.slashPad, dates.dash, dates.dashShort];

  const files = folder.getFiles();
  while (files.hasNext()) {
    const f = files.next();
    const name = f.getName();
    for (const p of patterns) {
      if (name.indexOf(p) !== -1) return f;
    }
  }
  return null;
}

// ─── SpreadsheetML XML parser ───────────────────────────────────────────────

function parseSpreadsheetML(xmlText) {
  // Strip any processing instructions that XmlService can't handle
  xmlText = xmlText.replace(/<\?[^?]*\?>/g, '');

  // XmlService needs a clean root — SpreadsheetML uses namespaces heavily.
  // We'll regex-extract Row/Cell/Data instead for reliability.
  const result = [];
  const rowRegex = /<(?:ss:)?Row[^>]*>([\s\S]*?)<\/(?:ss:)?Row>/gi;
  let rowMatch;

  while ((rowMatch = rowRegex.exec(xmlText)) !== null) {
    const rowContent = rowMatch[1];
    const vals = [];
    const cellRegex = /<(?:ss:)?Cell[^>]*>[\s\S]*?<(?:ss:)?Data[^>]*>([\s\S]*?)<\/(?:ss:)?Data>[\s\S]*?<\/(?:ss:)?Cell>/gi;
    // Also handle cells with Index attribute (skipped columns)
    const cellIndexRegex = /<(?:ss:)?Cell\s[^>]*?ss:Index="(\d+)"[^>]*>/gi;

    // Parse all cells in order, respecting ss:Index for sparse rows
    const cellFullRegex = /<(?:ss:)?Cell([^>]*)>([\s\S]*?)<\/(?:ss:)?Cell>/gi;
    let cellMatch;
    let colIndex = 0;

    while ((cellMatch = cellFullRegex.exec(rowContent)) !== null) {
      const attrs = cellMatch[1];
      const cellContent = cellMatch[2];

      // Check for ss:Index attribute
      const idxMatch = attrs.match(/ss:Index="(\d+)"/);
      if (idxMatch) {
        const targetIdx = parseInt(idxMatch[1]) - 1; // Convert to 0-based
        while (colIndex < targetIdx) {
          vals.push('');
          colIndex++;
        }
      }

      // Extract Data content
      const dataMatch = cellContent.match(/<(?:ss:)?Data[^>]*>([\s\S]*?)<\/(?:ss:)?Data>/i);
      vals.push(dataMatch ? dataMatch[1].trim() : '');
      colIndex++;
    }

    result.push(vals);
  }
  return result;
}

// ─── Core report parser (ported from HTML tool) ─────────────────────────────

var ROLLOFF_SVC = ['ROLLOFF DELIVERY', 'ROLLOFF DOUBLE DROP', 'EMPTY ROLLOFF', 'EMPTY ROLL-OFF'];

function parseReport(rows) {
  var reportDate = null;
  var firstRow = rows[0] ? rows[0].join(' ') : '';
  var dateMatch = firstRow.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
  if (dateMatch) reportDate = dateMatch[1];

  // Build ticket-level map
  var tickets = {};
  var currentCode = null;
  var parentCode = null;
  var codeStack = [];

  for (var i = 0; i < rows.length; i++) {
    var vals = rows[i];
    var nonEmpty = vals.filter(function(v) { return v && v.trim(); });
    if (!nonEmpty.length) continue;
    var first = nonEmpty[0];

    var isHeader = (
      first.indexOf(' - ') !== -1 &&
      first.indexOf('Totals') === -1 &&
      first.indexOf('Tickets:') === -1 &&
      first.indexOf('TIPFEES') === -1 &&
      first.indexOf('ROLLOFFS') === -1 &&
      first.indexOf('No Order') === -1 &&
      first.indexOf('Page ') !== 0 &&
      first.indexOf('Date Range') === -1 &&
      first.trim() !== 'Date' &&
      first.indexOf('Report') === -1
    );
    var isTotals = (
      first.indexOf(' - ') !== -1 && first.indexOf('Totals') !== -1 &&
      first.indexOf('TIPFEES') === -1 && first.indexOf('Non Order') === -1
    );

    if (isHeader) {
      var code = first.split(' - ')[0].trim();
      codeStack.push(code);
      currentCode = code;
      parentCode = codeStack.length > 1 ? codeStack[0] : null;
    }
    if (isTotals) {
      var code = first.split(' - ')[0].trim();
      var idx = codeStack.lastIndexOf(code);
      if (idx !== -1) codeStack.splice(idx, 1);
      currentCode = codeStack.length > 0 ? codeStack[codeStack.length - 1] : null;
      parentCode = codeStack.length > 1 ? codeStack[0] : null;
    }

    var effectiveCode = (parentCode && parentCode.indexOf('ZZ') === 0) ? parentCode : currentCode;
    if (!effectiveCode) continue;

    var flatUpper = vals.join(' ').toUpperCase();
    var dataVals = vals.filter(function(v) { return v !== null && v !== '' && v !== undefined; });

    // Tonnage line
    if (flatUpper.indexOf('REIS SITE TRANSFER FEE') !== -1) {
      var fi = -1;
      for (var k = 0; k < dataVals.length; k++) {
        if (dataVals[k] && dataVals[k].indexOf('REIS SITE TRANSFER FEE') !== -1) { fi = k; break; }
      }
      if (fi !== -1 && fi + 2 < dataVals.length) {
        var ticket = dataVals[1] || '?';
        var net = parseFloat(dataVals[fi + 2]) || 0;
        if (!tickets[ticket]) tickets[ticket] = { tons: 0, service: null, code: effectiveCode };
        tickets[ticket].tons += net;
        if (!tickets[ticket].service) tickets[ticket].code = effectiveCode;
      }
    }

    // Service charge line
    for (var s = 0; s < ROLLOFF_SVC.length; s++) {
      if (flatUpper.indexOf(ROLLOFF_SVC[s]) !== -1) {
        var ticket = dataVals[1] || '?';
        if (!tickets[ticket]) tickets[ticket] = { tons: 0, service: null, code: effectiveCode };
        tickets[ticket].service = ROLLOFF_SVC[s];
        tickets[ticket].code = effectiveCode;
        break;
      }
    }
  }

  // Categorize at ticket level
  var buckets = {
    reis:    { label: 'Reis Rolloff', tons: 0, tickets: 0, tipRevenue: 0, rolloffFees: 0, deliveries: 0, empties: 0, doubleDrops: 0 },
    pile:    { label: 'Pile Pickups (Reis)', tons: 0, tickets: 0, tipRevenue: 0 },
    island:  { label: 'Island Rubbish', tons: 0, tickets: 0, tipRevenue: 0, rolloffFees: 0 },
    santos:  { label: 'East End', tons: 0, tickets: 0, tipRevenue: 0, rolloffFees: 0 },
    vinagro: { label: 'VINAGRO Output', tons: 0, tickets: 0 },
    walkin:  { label: 'Walk-In / Drive-Through', tons: 0, tickets: 0, tipRevenue: 0 },
  };

  var ticketKeys = Object.keys(tickets);
  for (var ti = 0; ti < ticketKeys.length; ti++) {
    var ticketNum = ticketKeys[ti];
    var t = tickets[ticketNum];
    var tCode = t.code;
    if (tCode === 'ZZISLAND') {
      buckets.island.tons += t.tons;
      buckets.island.tickets++;
    } else if (tCode === 'ZZEASTEND') {
      buckets.santos.tons += t.tons;
      buckets.santos.tickets++;
    } else if (tCode === 'ZZDELTA') {
      buckets.pile.tons += t.tons;
      buckets.pile.tickets++;
    } else if (tCode === 'ZZREIS') {
      buckets.vinagro.tons += t.tons;
      buckets.vinagro.tickets++;
    } else if (tCode.indexOf('ZZ') === 0) {
      buckets.walkin.tons += t.tons;
      buckets.walkin.tickets++;
    } else if (t.service !== null) {
      buckets.reis.tons += t.tons;
      buckets.reis.tickets++;
      if (t.service.indexOf('DELIVERY') !== -1) buckets.reis.deliveries++;
      else if (t.service.indexOf('DOUBLE DROP') !== -1) buckets.reis.doubleDrops++;
      else if (t.service.indexOf('EMPTY') !== -1) buckets.reis.empties++;
    } else {
      buckets.walkin.tons += t.tons;
      buckets.walkin.tickets++;
    }
  }

  // Revenue pass — re-scan rows for dollar amounts per ticket
  currentCode = null;
  parentCode = null;
  var revStack = [];

  for (var i = 0; i < rows.length; i++) {
    var vals = rows[i];
    var nonEmpty = vals.filter(function(v) { return v && v.trim(); });
    if (!nonEmpty.length) continue;
    var first = nonEmpty[0];

    var isHdr = (first.indexOf(' - ') !== -1 && first.indexOf('Totals') === -1 && first.indexOf('Tickets:') === -1
      && first.indexOf('TIPFEES') === -1 && first.indexOf('ROLLOFFS') === -1 && first.indexOf('No Order') === -1
      && first.indexOf('Page ') !== 0 && first.indexOf('Date Range') === -1
      && first.trim() !== 'Date' && first.indexOf('Report') === -1);
    var isTot = (first.indexOf(' - ') !== -1 && first.indexOf('Totals') !== -1
      && first.indexOf('TIPFEES') === -1 && first.indexOf('Non Order') === -1);

    if (isHdr) {
      var code = first.split(' - ')[0].trim();
      revStack.push(code);
      currentCode = code;
      parentCode = revStack.length > 1 ? revStack[0] : null;
    }
    if (isTot) {
      var code = first.split(' - ')[0].trim();
      var idx = revStack.lastIndexOf(code);
      if (idx !== -1) revStack.splice(idx, 1);
      currentCode = revStack.length > 0 ? revStack[revStack.length - 1] : null;
      parentCode = revStack.length > 1 ? revStack[0] : null;
    }

    var revCode = (parentCode && parentCode.indexOf('ZZ') === 0) ? parentCode : currentCode;
    if (!revCode) continue;

    var flatUpper = vals.join(' ').toUpperCase();
    var dataVals = vals.filter(function(v) { return v !== null && v !== '' && v !== undefined; });

    // Tip fee revenue
    if (flatUpper.indexOf('REIS SITE TRANSFER FEE') !== -1) {
      var fi = -1;
      for (var k = 0; k < dataVals.length; k++) {
        if (dataVals[k] && dataVals[k].indexOf('REIS SITE TRANSFER FEE') !== -1) { fi = k; break; }
      }
      if (fi !== -1 && fi + 2 < dataVals.length) {
        var ticket = dataVals[1] || '?';
        var net = parseFloat(dataVals[fi + 2]) || 0;
        var rateStr = dataVals[fi + 3] || '';
        var rateMatch = rateStr.match(/\$([0-9.]+)/);
        if (rateMatch && tickets[ticket]) {
          var rev = net * parseFloat(rateMatch[1]);
          var rCode = tickets[ticket].code;
          var svc = tickets[ticket].service;
          if (rCode === 'ZZISLAND') {
            buckets.island.tipRevenue += rev;
          } else if (rCode === 'ZZEASTEND') {
            buckets.santos.tipRevenue += rev;
          } else if (rCode === 'ZZDELTA') {
            buckets.pile.tipRevenue += rev;
          } else if (rCode === 'ZZREIS') {
            // VINAGRO — no external revenue
          } else if (rCode.indexOf('ZZ') === 0) {
            buckets.walkin.tipRevenue += rev;
          } else if (svc !== null) {
            buckets.reis.tipRevenue += rev;
          } else {
            buckets.walkin.tipRevenue += rev;
          }
        }
      }
    }

    // Rolloff service fees for Reis only
    for (var s = 0; s < ROLLOFF_SVC.length; s++) {
      if (flatUpper.indexOf(ROLLOFF_SVC[s]) !== -1 && revCode.indexOf('ZZ') !== 0) {
        var dv = vals.filter(function(v) { return v !== null && v !== '' && v !== undefined; });
        for (var j = dv.length - 1; j >= 0; j--) {
          var amt = parseFloat(dv[j]);
          if (!isNaN(amt) && amt > 0) {
            buckets.reis.rolloffFees += amt;
            break;
          }
        }
        break;
      }
    }
  }

  return { date: reportDate, buckets: buckets, tickets: tickets };
}

// ─── Email generator (ported from HTML tool) ────────────────────────────────

function formatDatePretty(dateStr) {
  if (!dateStr) return 'Today';
  var d = new Date(dateStr);
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  return days[d.getDay()] + ', ' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
}

function fmt(n, decimals) {
  if (decimals === undefined) decimals = 2;
  return n.toFixed(decimals);
}

function fmtMoney(n) {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── Supabase YTD loader ────────────────────────────────────────────────────

var SB_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co';
var SB_KEY  = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I';

function supabaseGet(table, query) {
  var url = SB_URL + '/rest/v1/' + table + '?' + query;
  var resp = UrlFetchApp.fetch(url, {
    headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY },
    muteHttpExceptions: true
  });
  return JSON.parse(resp.getContentText());
}

function loadYTD() {
  var seeds = supabaseGet('irr_ytd_seeds', 'select=*');
  var ytd2026 = 0, ytd2025 = 0, vin2026 = 0, vin2025 = 0;
  for (var i = 0; i < seeds.length; i++) {
    if (seeds[i].year === 2026) { ytd2026 = parseFloat(seeds[i].inbound_tons) || 0; vin2026 = parseFloat(seeds[i].vinagro_tons) || 0; }
    if (seeds[i].year === 2025) { ytd2025 = parseFloat(seeds[i].inbound_tons) || 0; vin2025 = parseFloat(seeds[i].vinagro_tons) || 0; }
  }
  // Add daily reports after seed date for 2026
  var seed2026 = null;
  for (var i = 0; i < seeds.length; i++) { if (seeds[i].year === 2026) seed2026 = seeds[i]; }
  if (seed2026) {
    var dailies = supabaseGet('irr_reports', 'select=total_inbound_tons,vinagro_tons&report_date=gt.' + seed2026.through_date);
    for (var i = 0; i < dailies.length; i++) {
      ytd2026 += parseFloat(dailies[i].total_inbound_tons) || 0;
      vin2026 += parseFloat(dailies[i].vinagro_tons) || 0;
    }
  }
  return { ytd2026: ytd2026, ytd2025: ytd2025, vin2026: vin2026, vin2025: vin2025 };
}

function saveReportToSupabase(data) {
  var date = data.date;
  if (!date) return;
  var parts = date.split('/');
  var isoDate = parts[2] + '-' + ('0'+parts[0]).slice(-2) + '-' + ('0'+parts[1]).slice(-2);
  var b = data.buckets;
  var totalTons = b.reis.tons + b.pile.tons + b.island.tons + b.santos.tons + b.walkin.tons;
  var totalTickets = b.reis.tickets + b.pile.tickets + b.island.tickets + b.santos.tickets + b.walkin.tickets;

  var row = {
    report_date: isoDate,
    reis_tons: b.reis.tons, reis_tickets: b.reis.tickets,
    reis_deliveries: b.reis.deliveries || 0, reis_empties: b.reis.empties || 0, reis_double_drops: b.reis.doubleDrops || 0,
    pile_tons: b.pile.tons, pile_tickets: b.pile.tickets,
    island_tons: b.island.tons, island_tickets: b.island.tickets,
    santos_tons: b.santos.tons, santos_tickets: b.santos.tickets,
    walkin_tons: b.walkin.tons, walkin_tickets: b.walkin.tickets,
    vinagro_tons: b.vinagro.tons, vinagro_loads: b.vinagro.tickets,
    total_inbound_tons: totalTons, total_inbound_tickets: totalTickets
  };

  var url = SB_URL + '/rest/v1/irr_reports?on_conflict=report_date';
  UrlFetchApp.fetch(url, {
    method: 'post',
    headers: {
      'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY,
      'Content-Type': 'application/json', 'Prefer': 'resolution=merge-duplicates'
    },
    payload: JSON.stringify(row),
    muteHttpExceptions: true
  });
}

// ─── Email generator (simplified — no breakdown/revenue) ────────────────────

function generateEmail(data, ytd2026, ytd2025, vin2026, vin2025) {
  var date = data.date;
  var buckets = data.buckets;
  var reis = buckets.reis;
  var pile = buckets.pile;
  var island = buckets.island;
  var santos = buckets.santos;
  var vinagro = buckets.vinagro;
  var walkin = buckets.walkin;

  var totalTons = reis.tons + pile.tons + island.tons + santos.tons + walkin.tons;
  var totalTickets = reis.tickets + pile.tickets + island.tickets + santos.tickets + walkin.tickets;

  var displayDate = formatDatePretty(date);
  var subject = 'IRR Scale Report \u2014 ' + (date || 'Today');

  function R(label, val, bold) {
    var style = 'padding:3px 0;color:#222;font-size:14px;' + (bold ? 'font-weight:bold;' : '');
    return '<tr>' +
      '<td style="' + style + '">' + label + '</td>' +
      '<td style="' + style + 'text-align:right;">' + val + '</td>' +
      '</tr>';
  }

  function H(text) {
    return '<tr><td colspan="2" style="padding:16px 0 4px 0;">' +
      '<span style="font-weight:bold;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;color:#000;">' + text + '</span>' +
      '</td></tr>';
  }

  function S() {
    return '<tr><td colspan="2" style="padding:6px 0;"></td></tr>';
  }

  var body = '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;max-width:500px;line-height:1.6;">' +
    '<p style="margin:0 0 6px 0;color:#222;">Good afternoon,</p>' +
    '<p style="margin:0 0 16px 0;color:#222;">Below is the scale summary for ' + displayDate + '.</p>' +
    '<table style="width:100%;border-collapse:collapse;">' +

    H('IRR Companies') +
    R('Reis Rolloff', reis.tickets + ' tickets &nbsp; ' + fmt(reis.tons) + ' tons') +
    R('Pile Pickups (Reis)', pile.tickets + ' tickets &nbsp; ' + fmt(pile.tons) + ' tons') +
    R('Island Rubbish', island.tickets + ' tickets &nbsp; ' + fmt(island.tons) + ' tons') +
    R('East End', santos.tickets + ' tickets &nbsp; ' + fmt(santos.tons) + ' tons') +

    H('External') +
    R('Walk-In / Drive-Through', walkin.tickets + ' tickets &nbsp; ' + fmt(walkin.tons) + ' tons') +

    S() +
    '<tr>' +
      '<td style="padding:4px 0;font-weight:bold;font-size:14px;color:#000;border-top:2px solid #000;">Total</td>' +
      '<td style="padding:4px 0;font-weight:bold;font-size:14px;color:#000;text-align:right;border-top:2px solid #000;">' + totalTickets + ' tickets &nbsp; ' + fmt(totalTons) + ' tons</td>' +
    '</tr>' +

    H('Vinagro Output (Outbound)') +
    R('Loads', vinagro.tickets) +
    R('Total Tons', fmt(vinagro.tons)) +

    H('Year-to-Date Comparison') +
    R('2026 Inbound YTD', fmt(ytd2026) + ' tons', true) +
    R('2025 Inbound YTD (same period)', fmt(ytd2025) + ' tons') +

    S() +
    R('2026 Vinagro YTD', fmt(vin2026) + ' tons', true) +
    R('2025 Vinagro YTD (same period)', fmt(vin2025) + ' tons') +

    '</table></div>';

  return { subject: subject, body: body };
}

// ─── Manual test function ───────────────────────────────────────────────────

function testWithSpecificDate() {
  // Change this date to test with a specific file
  var testDate = new Date();
  var file = findTodaysFile(testDate);
  if (!file) {
    Logger.log('No file found for ' + formatSearchDate(testDate).slash);
    return;
  }
  Logger.log('Found: ' + file.getName());
  var xmlText = file.getBlob().getDataAsString();
  var rows = parseSpreadsheetML(xmlText);
  Logger.log('Parsed ' + rows.length + ' rows');
  var data = parseReport(rows);
  Logger.log('Tickets found: ' + Object.keys(data.tickets).length);

  saveReportToSupabase(data);
  var ytd = loadYTD();
  var email = generateEmail(data, ytd.ytd2026, ytd.ytd2025, ytd.vin2026, ytd.vin2025);
  Logger.log('Subject: ' + email.subject);
  Logger.log('YTD 2026: ' + ytd.ytd2026 + ' | YTD 2025: ' + ytd.ytd2025);

  // Create the draft
  GmailApp.createDraft(
    CONFIG.SEND_TO,
    email.subject,
    '',
    { htmlBody: email.body }
  );
  Logger.log('Draft created successfully.');
}

// ─── Trigger installer ─────────────────────────────────────────────────────

function installDailyTrigger() {
  // Remove any existing triggers for this function
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'createDailyScaleReport') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  // Create new daily trigger at 4:30 PM
  ScriptApp.newTrigger('createDailyScaleReport')
    .timeBased()
    .everyDays(1)
    .atHour(16)
    .nearMinute(30)
    .create();

  Logger.log('Daily trigger installed for 4:30 PM.');
}
