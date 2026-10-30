/**
 * Google Apps Script for AutoPage MKII Coupon & Conflict Sync Engine
 * Handles:
 *  1. Sheet 'cp_data': Synchronizing learned and suggested CP/DC coupons with Marketplace isolation
 *  2. Sheet 'conflict_resolver': Recording candidates when multiple coupons match, enabling Admin resolution
 *
 * Safe Multi-User Concurrency with LockService.
 * Marketplace Isolation: composite match on (sku + marketplace + sale_price).
 * Backward Compatible: legacy rows with empty or "ALL" marketplace match gracefully and get migrated.
 */

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);

    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var targetSheetName = data.sheet || "cp_data";

    var parseSafeFloat = function(val) {
      if (val === undefined || val === null || val === "") return NaN;
      var clean = String(val).replace(/,/g, '').trim();
      return parseFloat(clean);
    };

    // ── Canonical helpers (order-insensitive: 'A B' == 'B A') ──
    var canonCp = function(s) {
      if (s === undefined || s === null) return "";
      var up = String(s).trim().toUpperCase();
      if (!up || ["-", "NAN", "NONE", "<NA>", "NULL"].indexOf(up) >= 0) return "";
      var toks = [];
      String(s).split(",").forEach(function(p) {
        p.split(/\s+/).forEach(function(t) {
          t = t.trim().toUpperCase();
          if (t) toks.push(t);
        });
      });
      toks = toks.filter(function(t) { return ["NAN", "NONE", "<NA>", "NULL", "-"].indexOf(t) < 0; });
      toks.sort();
      return toks.join(" ");
    };

    var canonAdj = function(s) {
      if (s === undefined || s === null) return "";
      var raw = String(s).trim();
      if (!raw || ["-", "NAN", "NONE", "<NA>", "NULL"].indexOf(raw.toUpperCase()) >= 0) return "";
      var toks = raw.split(/\s+/).filter(Boolean).map(function(t) {
        return (/^\d+\.0$/.test(t)) ? t.slice(0, -2) : t;
      });
      toks.sort(function(a, b) {
        var fa = parseFloat(String(a).replace(/,/g, "")), fb = parseFloat(String(b).replace(/,/g, ""));
        if (!isNaN(fa) && !isNaN(fb)) return fa - fb;
        return String(a).localeCompare(String(b));
      });
      return toks.join(" ");
    };

    var normAdj = function(v) {
      if (v === undefined || v === null) return "";
      var parts = String(v).trim().split(/\s+/).filter(Boolean).map(function(t) {
        return (/^\d+\.0$/.test(t)) ? t.slice(0, -2) : t;
      });
      var s = parts.join(" ");
      if (!s || ["-", "NAN", "NONE", "<NA>", "NULL"].indexOf(s.toUpperCase()) >= 0) return "";
      return s;
    };

    var normCpRaw = function(v) {
      if (v === undefined || v === null) return "";
      var s = String(v).trim().toUpperCase();
      if (!s || ["-", "NAN", "NONE", "<NA>", "NULL"].indexOf(s) >= 0) return "";
      return String(v).trim().toUpperCase();
    };

    // ══════════════════════════════════════════════════════════════
    // กรณีที่ 1: บันทึกข้อมูลลงแท็บ conflict_resolver (Dynamic Candidates + Marketplace Isolation)
    // ══════════════════════════════════════════════════════════════
    if (targetSheetName === "conflict_resolver") {
      var confSheet = ss.getSheetByName("conflict_resolver");
      if (!confSheet) {
        confSheet = ss.insertSheet("conflict_resolver");
        var confHeaders = [
          "sku", "marketplace", "sale_price", "candidates", "candidates_count",
          "candidate_1", "candidate_2", "candidate_3",
          "suggested_winner", "reason", "admin_selection", "status", "last_updated"
        ];
        confSheet.getRange(1, 1, 1, confHeaders.length).setValues([confHeaders]);
      }

      var cLastCol = confSheet.getLastColumn();
      var cLastRow = confSheet.getLastRow();
      var cHeaders = confSheet.getRange(1, 1, 1, cLastCol).getValues()[0].map(function(h) { return String(h).trim().toLowerCase(); });
      var cColMap = {};
      cHeaders.forEach(function(h, idx) { cColMap[h] = idx; });

      // dynamic column expansion (กันข้อมูลหาย)
      Object.keys(data).forEach(function(k) {
        var nk = String(k).trim().toLowerCase();
        if (nk === "sheet" || nk === "action") return;
        if (cColMap[nk] === undefined) {
          cLastCol++;
          confSheet.getRange(1, cLastCol).setValue(nk);
          cColMap[nk] = cLastCol - 1;
          cHeaders.push(nk);
        }
      });

      var tSku = String(data.sku || "").trim().toUpperCase();
      var tMp = String(data.marketplace || "").trim().toUpperCase();
      var tPrice = parseSafeFloat(data.sale_price);
      var nowStr = data.last_updated || Utilities.formatDate(new Date(), "Asia/Bangkok", "dd/MM/yyyy HH:mm:ss");

      var candidatesText = "";
      var candidatesCount = 0;
      if (Array.isArray(data.candidates)) {
        candidatesCount = data.candidates.length;
        candidatesText = data.candidates.join("\n");
      } else if (data.candidates) {
        candidatesText = String(data.candidates);
        candidatesCount = data.candidates_count || candidatesText.split("\n").length;
      } else {
        var legacyCands = [data.candidate_1, data.candidate_2, data.candidate_3].filter(Boolean);
        candidatesText = legacyCands.join("\n");
        candidatesCount = legacyCands.length;
      }

      var foundRow = -1;
      var fallbackRow = -1;
      var skuIdx = cColMap["sku"];
      var mpIdx = cColMap["marketplace"];
      var priceIdx = cColMap["sale_price"];

      cLastRow = confSheet.getLastRow();
      if (cLastRow > 1 && skuIdx !== undefined) {
        var rows = confSheet.getRange(2, 1, cLastRow - 1, cLastCol).getValues();
        for (var i = 0; i < rows.length; i++) {
          var rSku = String(rows[i][skuIdx] || "").trim().toUpperCase();
          var rPrice = priceIdx !== undefined ? parseSafeFloat(rows[i][priceIdx]) : NaN;
          var rMp = mpIdx !== undefined ? String(rows[i][mpIdx] || "").trim().toUpperCase() : "";

          var isSkuMatch = (rSku === tSku);
          var isPriceMatch = (isNaN(tPrice) || isNaN(rPrice) || Math.abs(rPrice - tPrice) <= 0.05);

          if (isSkuMatch && isPriceMatch) {
            // Marketplace Isolation
            if (tMp && rMp === tMp) {
              foundRow = i + 2;
              break;
            } else if (!tMp || !rMp || rMp === "ALL") {
              if (fallbackRow < 0) fallbackRow = i + 2;
            }
          }
        }

        if (foundRow < 0 && fallbackRow > 0) {
          foundRow = fallbackRow;
        }

        if (foundRow > 0) {
          // batch update ทั้งแถวครั้งเดียว
          var upd = rows[foundRow - 2].slice();
          var setC = function(name, val) {
            if (cColMap[name] !== undefined) upd[cColMap[name]] = val;
          };

          // อัปเดต marketplace หากแถวเดิมเป็นค่าว่างหรือ ALL
          if (cColMap["marketplace"] !== undefined && tMp) {
            if (!upd[cColMap["marketplace"]] || String(upd[cColMap["marketplace"]]).trim().toUpperCase() === "ALL") {
              upd[cColMap["marketplace"]] = tMp;
            }
          }

          setC("candidates", candidatesText);
          setC("candidates_count", candidatesCount);
          if (data.candidate_1 !== undefined) setC("candidate_1", data.candidate_1);
          if (data.candidate_2 !== undefined) setC("candidate_2", data.candidate_2);
          if (data.candidate_3 !== undefined) setC("candidate_3", data.candidate_3);
          if (data.suggested_winner !== undefined && data.suggested_winner !== "") setC("suggested_winner", data.suggested_winner);
          if (data.reason !== undefined && data.reason !== "") setC("reason", data.reason);
          if (data.admin_selection !== undefined && data.admin_selection !== "") setC("admin_selection", data.admin_selection);
          if (!(data.status === "PENDING" && String(upd[cColMap["status"]] || "") !== "")) {
            if (data.status !== undefined && data.status !== "") setC("status", data.status);
          }
          Object.keys(data).forEach(function(k) {
            var nk = String(k).trim().toLowerCase();
            if (["sku", "marketplace", "sale_price", "candidates", "candidates_count", "candidate_1", "candidate_2", "candidate_3",
                 "suggested_winner", "reason", "admin_selection", "status", "last_updated", "sheet", "action"].indexOf(nk) >= 0) return;
            if (cColMap[nk] !== undefined && data[k] !== undefined && data[k] !== "") upd[cColMap[nk]] = data[k];
          });
          setC("last_updated", nowStr);
          confSheet.getRange(foundRow, 1, 1, cLastCol).setValues([upd]);
          SpreadsheetApp.flush();
          return ContentService.createTextOutput(JSON.stringify({
            status: "success",
            action: "updated",
            row: foundRow,
            marketplace: tMp || upd[cColMap["marketplace"]] || ""
          })).setMimeType(ContentService.MimeType.JSON);
        }
      }

      var newRow = cHeaders.map(function(h) {
        if (h === "sku") return tSku;
        if (h === "marketplace") return tMp;
        if (h === "sale_price") return isNaN(tPrice) ? "" : tPrice;
        if (h === "candidates") return candidatesText;
        if (h === "candidates_count") return candidatesCount;
        if (h === "last_updated") return nowStr;
        if (h === "status") return data.status || "PENDING";
        return data[h] !== undefined ? data[h] : "";
      });
      confSheet.appendRow(newRow);
      SpreadsheetApp.flush();
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "inserted",
        row: confSheet.getLastRow(),
        marketplace: tMp
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // ══════════════════════════════════════════════════════════════
    // กรณีที่ 2: บันทึกข้อมูลลงแท็บหลัก cp_data (Marketplace Isolation)
    // ══════════════════════════════════════════════════════════════
    var sheet = ss.getSheetByName("cp_data") || ss.getActiveSheet() || ss.getSheets()[0];
    var lastCol = sheet.getLastColumn();
    var lastRow = sheet.getLastRow();

    if (lastCol === 0) {
      var defaultHeaders = [
        "sku", "marketplace", "sale_price", "cp_name", "usage_start_date", "usage_end_date",
        "addtion_cp", "oc_amount", "dc_amount", "couponDetailCash", "couponDetailDisc",
        "last_order_id", "last_used_cp", "last_actual_price", "last_updated",
        "last_adjustment_method", "suggested_cp", "suggested_usage_start_date",
        "suggested_usage_end_date", "suggested_remark",
        "suggested_oc_amount", "suggested_dc_amount", "pattern_discount"
      ];
      sheet.getRange(1, 1, 1, defaultHeaders.length).setValues([defaultHeaders]);
      lastCol = defaultHeaders.length;
      lastRow = 1;
    }

    var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
    var colMap = {};
    headers.forEach(function(h, idx) { colMap[String(h).trim().toLowerCase()] = idx; });

    var dataNorm = {};
    Object.keys(data).forEach(function(k) { dataNorm[String(k).trim().toLowerCase()] = data[k]; });

    Object.keys(dataNorm).forEach(function(normKey) {
      var nk = normKey;
      if (nk === 'expected_price') nk = 'sale_price';
      if (nk === 'suggested_oc') nk = 'suggested_oc_amount';
      if (nk === 'suggested_dc') nk = 'suggested_dc_amount';
      if (nk === 'action' || nk === 'sheet') return;
      if (colMap[nk] === undefined) {
        lastCol++;
        sheet.getRange(1, lastCol).setValue(nk);
        colMap[nk] = lastCol - 1;
        headers.push(nk);
      }
    });

    var targetSku = String(dataNorm["sku"] || "").trim().toUpperCase();
    var targetMp = String(dataNorm["marketplace"] || "").trim().toUpperCase();
    var targetPrice = parseSafeFloat(dataNorm["sale_price"] !== undefined ? dataNorm["sale_price"] : dataNorm["expected_price"]);
    var targetCp = normCpRaw(dataNorm["suggested_cp"] || dataNorm["cp_name"] || "");
    var targetOc = normAdj(dataNorm["oc_amount"] || "");
    var targetDc = normAdj(dataNorm["dc_amount"] || "");
    var targetSuggOc = normAdj(dataNorm["suggested_oc_amount"] || dataNorm["suggested_oc"] || "");
    var targetSuggDc = normAdj(dataNorm["suggested_dc_amount"] || dataNorm["suggested_dc"] || "");

    var targetCpCanon = canonCp(targetCp);
    var targetOcCanon = canonAdj(targetOc);
    var targetDcCanon = canonAdj(targetDc);
    var targetSuggOcCanon = canonAdj(targetSuggOc);
    var targetSuggDcCanon = canonAdj(targetSuggDc);

    var nowStr2 = dataNorm["last_updated"] || Utilities.formatDate(new Date(), "Asia/Bangkok", "dd/MM/yyyy HH:mm:ss");

    var skuColIdx = colMap["sku"];
    var mpColIdx = colMap["marketplace"];
    var priceColIdx = colMap["sale_price"] !== undefined ? colMap["sale_price"] : colMap["expected_price"];
    var cpColIdx = colMap["cp_name"];
    var suggCpColIdx = colMap["suggested_cp"];
    var ocColIdx = colMap["oc_amount"];
    var dcColIdx = colMap["dc_amount"];
    var suggOcColIdx = colMap["suggested_oc_amount"] !== undefined ? colMap["suggested_oc_amount"] : colMap["suggested_oc"];
    var suggDcColIdx = colMap["suggested_dc_amount"] !== undefined ? colMap["suggested_dc_amount"] : colMap["suggested_dc"];

    var foundRow2 = -1;
    var fallbackRow2 = -1;

    if (lastRow > 1 && skuColIdx !== undefined) {
      var sheetData = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
      for (var r = 0; r < sheetData.length; r++) {
        var rowSku = String(sheetData[r][skuColIdx] || "").trim().toUpperCase();
        var rowPrice = priceColIdx !== undefined ? parseSafeFloat(sheetData[r][priceColIdx]) : NaN;
        var rowMp = mpColIdx !== undefined ? String(sheetData[r][mpColIdx] || "").trim().toUpperCase() : "";

        var isSkuMatch = (rowSku === targetSku);
        var isPriceMatch = isNaN(targetPrice) || isNaN(rowPrice) || Math.abs(rowPrice - targetPrice) <= 0.05;

        if (isSkuMatch && isPriceMatch) {
          var rowCp = cpColIdx !== undefined ? normCpRaw(sheetData[r][cpColIdx]) : "";
          var rowSuggCp = suggCpColIdx !== undefined ? normCpRaw(sheetData[r][suggCpColIdx]) : "";
          var rowOc = ocColIdx !== undefined ? normAdj(sheetData[r][ocColIdx]) : "";
          var rowDc = dcColIdx !== undefined ? normAdj(sheetData[r][dcColIdx]) : "";
          var rowSuggOc = suggOcColIdx !== undefined ? normAdj(sheetData[r][suggOcColIdx]) : "";
          var rowSuggDc = suggDcColIdx !== undefined ? normAdj(sheetData[r][suggDcColIdx]) : "";

          // order-insensitive: 'A B' == 'B A'
          var isPlaceholder = (!canonCp(rowCp) && !canonCp(rowSuggCp) && !canonAdj(rowOc) && !canonAdj(rowDc) && !canonAdj(rowSuggOc) && !canonAdj(rowSuggDc));
          var isSameCp = (targetCpCanon !== "" && (canonCp(rowCp) === targetCpCanon || canonCp(rowSuggCp) === targetCpCanon));
          var isBothEmptyCp = (targetCpCanon === "" && canonCp(rowCp) === "" && canonCp(rowSuggCp) === "");
          var isSameAdj = (canonAdj(rowOc) === targetOcCanon && canonAdj(rowDc) === targetDcCanon
            && canonAdj(rowSuggOc) === targetSuggOcCanon && canonAdj(rowSuggDc) === targetSuggDcCanon);
          var isAutoAdj = (String(rowOc).trim().toUpperCase() === "AUTO" || String(rowDc).trim().toUpperCase() === "AUTO");

          if (isPlaceholder || ((isSameCp || isBothEmptyCp) && (isSameAdj || isAutoAdj))) {
            // Marketplace Isolation Matching:
            // 1. Exact match (SHOPEE == SHOPEE) -> foundRow2 ทันที
            // 2. Fallback match (แถวเดิมยังไม่มี MP หรือเป็น ALL) -> จด fallbackRow2 ไว้ แล้วหาต่อ
            // 3. หากเป็น Marketplace อื่น (เช่น TIKTOK vs SHOPEE) -> ไม่ match เด็ดขาด (ป้องกันการทับกัน)
            if (targetMp && rowMp === targetMp) {
              foundRow2 = r + 2;
              break;
            } else if (!targetMp || !rowMp || rowMp === "ALL") {
              if (fallbackRow2 < 0) fallbackRow2 = r + 2;
            }
          }
        }
      }

      if (foundRow2 < 0 && fallbackRow2 > 0) {
        foundRow2 = fallbackRow2;
      }

      if (foundRow2 > 0) {
        // batch update ทั้งแถวครั้งเดียว
        var updRow = sheetData[foundRow2 - 2].slice();
        var writeTo = function(colKey, val) {
          if (colMap[colKey] !== undefined) updRow[colMap[colKey]] = val;
        };

        // อัปเดต marketplace หากแถวเดิมเป็นค่าว่างหรือ ALL
        if (colMap['marketplace'] !== undefined && targetMp) {
          if (!updRow[colMap['marketplace']] || String(updRow[colMap['marketplace']]).trim().toUpperCase() === "ALL") {
            updRow[colMap['marketplace']] = targetMp;
          }
        }

        Object.keys(dataNorm).forEach(function(normKey) {
          var targetColKey = normKey;
          if (targetColKey === 'expected_price' && colMap['sale_price'] !== undefined) targetColKey = 'sale_price';
          if (targetColKey === 'suggested_oc' && colMap['suggested_oc_amount'] !== undefined) targetColKey = 'suggested_oc_amount';
          if (targetColKey === 'suggested_dc' && colMap['suggested_dc_amount'] !== undefined) targetColKey = 'suggested_dc_amount';
          if (targetColKey === 'start_date' && colMap['usage_start_date'] !== undefined) targetColKey = 'usage_start_date';
          if (targetColKey === 'end_date' && colMap['usage_end_date'] !== undefined) targetColKey = 'usage_end_date';
          if (targetColKey === 'order_id' && colMap['last_order_id'] !== undefined) targetColKey = 'last_order_id';
          if (targetColKey === 'action' || targetColKey === 'sheet') return;
          if (colMap[targetColKey] !== undefined && dataNorm[normKey] !== undefined && dataNorm[normKey] !== "") {
            updRow[colMap[targetColKey]] = dataNorm[normKey];
          }
        });
        if (colMap['last_updated'] !== undefined) updRow[colMap['last_updated']] = nowStr2;
        sheet.getRange(foundRow2, 1, 1, lastCol).setValues([updRow]);

        SpreadsheetApp.flush();
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          action: "updated",
          row: foundRow2,
          sku: targetSku,
          marketplace: targetMp || updRow[colMap['marketplace']] || "",
          last_updated: nowStr2
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }

    var getVal = function(keyAliases, defaultVal) {
      for (var a = 0; a < keyAliases.length; a++) {
        var alias = keyAliases[a].toLowerCase();
        if (dataNorm[alias] !== undefined && dataNorm[alias] !== null && dataNorm[alias] !== "") {
          return dataNorm[alias];
        }
      }
      return defaultVal !== undefined ? defaultVal : "";
    };

    var newRow = headers.map(function(h) {
      var k = String(h).trim().toLowerCase();
      if (k === 'sku') return targetSku;
      if (k === 'marketplace') return targetMp;
      if (k === 'sale_price' || k === 'expected_price') return isNaN(targetPrice) ? getVal(['sale_price', 'expected_price'], '') : targetPrice;
      if (k === 'last_updated') return nowStr2;
      if (k === 'usage_start_date' || k === 'start_date') return getVal(['usage_start_date', 'start_date']);
      if (k === 'usage_end_date' || k === 'end_date') return getVal(['usage_end_date', 'end_date']);
      if (k === 'suggested_cp') return getVal(['suggested_cp']);
      if (k === 'suggested_usage_start_date') return getVal(['suggested_usage_start_date', 'suggested_start_date']);
      if (k === 'suggested_usage_end_date') return getVal(['suggested_usage_end_date', 'suggested_end_date']);
      if (k === 'suggested_remark') return getVal(['suggested_remark', 'remark']);
      if (k === 'suggested_oc_amount' || k === 'suggested_oc') return targetSuggOc;
      if (k === 'suggested_dc_amount' || k === 'suggested_dc') return targetSuggDc;
      if (k === 'last_order_id' || k === 'order_id') return getVal(['last_order_id', 'order_id']);
      if (k === 'last_used_cp') return getVal(['last_used_cp']);
      if (k === 'last_adjustment_method') return getVal(['last_adjustment_method']);
      if (k === 'last_actual_price') return getVal(['last_actual_price']);
      if (k === 'cp_name') return getVal(['cp_name']);
      if (k === 'oc_amount') return targetOc;
      if (k === 'dc_amount') return targetDc;
      return getVal([k], "");
    });

    sheet.appendRow(newRow);
    SpreadsheetApp.flush();

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      action: "inserted",
      row: sheet.getLastRow(),
      sku: targetSku,
      marketplace: targetMp,
      last_updated: nowStr2
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: "error", message: err.toString()})).setMimeType(ContentService.MimeType.JSON);
  } finally {
    try {
      lock.releaseLock();
    } catch (ignoreLockErr) {}
  }
}

function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetParam = (e && e.parameter && e.parameter.sheet) ? e.parameter.sheet : "cp_data";
  var mpFilter = (e && e.parameter && e.parameter.marketplace) ? String(e.parameter.marketplace).trim().toUpperCase() : "";
  var sheet = ss.getSheetByName(sheetParam) || ss.getActiveSheet() || ss.getSheets()[0];
  var data = sheet.getDataRange().getDisplayValues();

  if (data.length <= 1) {
    return ContentService.createTextOutput(JSON.stringify([])).setMimeType(ContentService.MimeType.JSON);
  }

  var headers = data[0];
  var mpIdx = -1;
  for (var h = 0; h < headers.length; h++) {
    if (String(headers[h]).trim().toLowerCase() === "marketplace") {
      mpIdx = h;
      break;
    }
  }

  var rows = [];
  for (var i = 1; i < data.length; i++) {
    if (mpFilter && mpIdx >= 0) {
      var rowMp = String(data[i][mpIdx] || "").trim().toUpperCase();
      // คืนค่าเฉพาะ marketplace ที่ตรงกัน หรือเป็น global row (ว่าง / ALL)
      if (rowMp && rowMp !== "ALL" && rowMp !== mpFilter) {
        continue;
      }
    }
    var rowData = {};
    for (var j = 0; j < headers.length; j++) {
      rowData[headers[j]] = data[i][j];
    }
    rows.push(rowData);
  }

  return ContentService.createTextOutput(JSON.stringify(rows)).setMimeType(ContentService.MimeType.JSON);
}
