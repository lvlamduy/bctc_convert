"use strict";

const state = {
  options: null,
  familyId: null,
  documents: [],
  documentSha: null,
  review: null,
  page: null,
  tableKey: null,
  zoom: 100,
};

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function statusClass(status) {
  return {
    READY: "status-ready",
    UNRESOLVED: "status-unresolved",
    NOT_OBSERVED: "status-not-observed",
  }[status] || "status-not-observed";
}

async function api(path) {
  const response = await fetch(path, {headers: {Accept: "application/json"}});
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function toast(message) {
  const element = byId("toast");
  element.textContent = message;
  element.classList.remove("is-hidden");
  window.clearTimeout(element._timer);
  element._timer = window.setTimeout(() => element.classList.add("is-hidden"), 4000);
}

function fillSelect(id, items, valueKey = "id", labelKey = "name") {
  const select = byId(id);
  const first = select.options[0];
  select.replaceChildren(first);
  for (const item of items) {
    const option = document.createElement("option");
    option.value = typeof item === "string" ? item : item[valueKey];
    option.textContent = typeof item === "string" ? item : item[labelKey];
    select.append(option);
  }
}

function setConnection(configuration) {
  const connection = byId("connection-state");
  if (configuration.ready) {
    connection.className = "connection is-ready";
    connection.lastElementChild.textContent = configuration.pdf_root
      ? "Dữ liệu và ảnh PDF sẵn sàng"
      : "Dữ liệu sẵn sàng · thiếu thư mục PDF";
  } else {
    connection.className = "connection is-error";
    connection.lastElementChild.textContent = "Chưa cấu hình đủ dữ liệu";
  }
}

function renderFamilies() {
  const query = byId("family-search").value.trim().toLocaleLowerCase("vi");
  const families = state.options.families.filter((family) =>
    !query || family.name.toLocaleLowerCase("vi").includes(query) || family.id.toLowerCase().includes(query)
  );
  byId("family-count").textContent = families.length;
  const list = byId("family-list");
  list.innerHTML = families.map((family) => `
    <button class="family-item ${family.id === state.familyId ? "is-active" : ""}"
            type="button" data-family-id="${escapeHtml(family.id)}">
      <strong><span class="family-order">${family.order}.</span> ${escapeHtml(family.name)}</strong>
      <small>
        <span class="family-status-link is-ready" data-family-status="READY"><b>${family.ready_count}</b> đã map</span>
        <span class="family-status-link" data-family-status="NOT_OBSERVED"><b>${family.not_observed_count}</b> không thấy</span>
        <span class="family-status-link is-unresolved" data-family-status="UNRESOLVED"><b>${family.unresolved_count}</b> vướng</span>
      </small>
    </button>`).join("") || '<div class="empty-list">Không tìm thấy family.</div>';
  list.querySelectorAll("[data-family-id]").forEach((button) => {
    button.addEventListener("click", () => selectFamily(button.dataset.familyId));
  });
  list.querySelectorAll("[data-family-status]").forEach((status) => {
    status.addEventListener("click", (event) => {
      event.stopPropagation();
      byId("filter-status").value = status.dataset.familyStatus;
      selectFamily(status.closest("[data-family-id]").dataset.familyId);
    });
  });
}

function filterParams() {
  const pairs = {
    family_id: state.familyId,
    bank: byId("filter-bank").value,
    year: byId("filter-year").value,
    period: byId("filter-period").value,
    scope: byId("filter-scope").value,
    assurance: byId("filter-assurance").value,
    status: byId("filter-status").value,
    query: byId("document-search").value.trim(),
  };
  return new URLSearchParams(Object.entries(pairs).filter(([, value]) => value));
}

async function selectFamily(familyId) {
  state.familyId = familyId;
  state.documentSha = null;
  state.review = null;
  renderFamilies();
  byId("review-view").classList.add("is-hidden");
  byId("empty-state").classList.remove("is-hidden");
  await loadDocuments();
}

async function loadDocuments() {
  const list = byId("document-list");
  list.innerHTML = '<div class="loading-row">Đang đọc danh sách PDF…</div>';
  try {
    const payload = await api(`/api/documents?${filterParams()}`);
    state.documents = payload.documents;
    renderDocuments();
  } catch (error) {
    list.innerHTML = `<div class="empty-list">${escapeHtml(error.message)}</div>`;
    toast(error.message);
  }
}

function renderDocuments() {
  byId("document-count").textContent = state.documents.length;
  const list = byId("document-list");
  list.innerHTML = state.documents.map((item) => `
    <button class="document-item ${item.source_sha256 === state.documentSha ? "is-active" : ""}"
            type="button" data-source-sha="${escapeHtml(item.source_sha256)}">
      <div class="document-item-header">
        <strong>${escapeHtml(item.bank)} · ${escapeHtml(item.period_label)}</strong>
        <span class="status-pill ${statusClass(item.status)}">${escapeHtml(item.status_label)}</span>
      </div>
      <p>${escapeHtml(item.filename)}</p>
      <small>${escapeHtml(item.scope_label)} · ${escapeHtml(item.assurance_label)} · ${item.mapping_count} mapping</small>
    </button>`).join("") || '<div class="empty-list">Không có PDF phù hợp bộ lọc.</div>';
  list.querySelectorAll("[data-source-sha]").forEach((button) => {
    button.addEventListener("click", () => loadReview(button.dataset.sourceSha));
  });
}

async function loadReview(sourceSha) {
  state.documentSha = sourceSha;
  renderDocuments();
  byId("empty-state").classList.remove("is-hidden");
  byId("empty-state").querySelector("h2").textContent = "Đang dựng màn hình đối chiếu…";
  try {
    state.review = await api(`/api/review/${encodeURIComponent(state.familyId)}/${encodeURIComponent(sourceSha)}`);
    state.page = state.review.pages[0]?.physical_page ?? null;
    state.tableKey = state.review.gemini_tables.find((table) => table.physical_page === state.page)?.key
      ?? state.review.gemini_tables[0]?.key
      ?? null;
    state.zoom = 100;
    renderReview();
  } catch (error) {
    toast(error.message);
    byId("empty-state").querySelector("h2").textContent = "Không đọc được kết quả";
  }
}

function renderReview() {
  const review = state.review;
  const document = review.document;
  byId("empty-state").classList.add("is-hidden");
  byId("review-view").classList.remove("is-hidden");
  byId("document-title").textContent = document.filename;
  byId("document-path").textContent = document.source_logical_name;
  byId("document-tags").innerHTML = [
    `<span class="status-pill ${statusClass(review.disposition.status)}">${escapeHtml(review.disposition.status_label)}</span>`,
    ...[document.bank, document.period_label, document.scope_label, document.assurance_label]
      .map((value) => `<span class="meta-tag">${escapeHtml(value)}</span>`),
  ].join("");
  byId("metric-family").textContent = review.family.name;
  byId("metric-mapping").textContent = review.disposition.mapping_count;
  byId("metric-pages").textContent = review.pages.length;

  const notice = byId("review-notice");
  const notices = [];
  if (review.disposition.reason_labels.length) notices.push(...review.disposition.reason_labels);
  if (!document.pdf_available) notices.push("Chưa tìm thấy file PDF gốc; dữ liệu Gemini và mapping vẫn xem được.");
  notice.textContent = notices.join(" · ");
  notice.classList.toggle("is-hidden", notices.length === 0);

  renderPageTabs();
  renderPageImage();
  renderTableSelector();
  renderGeminiTable();
  renderMappings();
  renderCoverage();
  renderDiagnostics();
}

function renderPageTabs() {
  const tabs = byId("page-tabs");
  tabs.innerHTML = state.review.pages.map((page) => `
    <button type="button" class="page-tab ${page.physical_page === state.page ? "is-active" : ""}"
            data-page="${page.physical_page}">Trang ${page.physical_page}</button>`).join("");
  tabs.classList.toggle("is-hidden", state.review.pages.length === 0);
  tabs.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      state.page = Number(button.dataset.page);
      state.tableKey = state.review.gemini_tables.find((table) => table.physical_page === state.page)?.key ?? null;
      state.zoom = 100;
      renderPageTabs();
      renderPageImage();
      renderTableSelector();
      renderGeminiTable();
    });
  });
}

function currentPage() {
  return state.review.pages.find((page) => page.physical_page === state.page);
}

function renderPageImage() {
  const page = currentPage();
  const image = byId("page-image");
  const placeholder = byId("image-placeholder");
  byId("zoom-label").textContent = `${state.zoom}%`;
  image.style.width = `${state.zoom}%`;
  if (!page?.image_available) {
    image.classList.add("is-hidden");
    placeholder.classList.remove("is-hidden");
    return;
  }
  placeholder.classList.add("is-hidden");
  image.classList.remove("is-hidden");
  image.src = `${page.image_url}?v=1`;
  image.alt = `Ảnh trang ${page.physical_page} của ${state.review.document.filename}`;
  image.onerror = () => {
    image.classList.add("is-hidden");
    placeholder.classList.remove("is-hidden");
  };
}

function pageTables() {
  return state.review.gemini_tables.filter((table) => table.physical_page === state.page);
}

function renderTableSelector() {
  const tables = pageTables();
  const selector = byId("table-selector");
  selector.innerHTML = tables.map((table, index) => `
    <button type="button" class="table-choice ${table.key === state.tableKey ? "is-active" : ""}"
            data-table-key="${escapeHtml(table.key)}">Bảng ${index + 1} · ${escapeHtml(table.table_id)}${table.selected ? " · đã chọn" : table.candidate_status === "UNRESOLVED" ? " · vướng" : ""}</button>`).join("");
  selector.classList.toggle("is-hidden", tables.length < 2);
  selector.querySelectorAll("[data-table-key]").forEach((button) => {
    button.addEventListener("click", () => {
      state.tableKey = button.dataset.tableKey;
      renderTableSelector();
      renderGeminiTable();
    });
  });
}

function currentTable() {
  return state.review.gemini_tables.find((table) => table.key === state.tableKey)
    || pageTables()[0]
    || null;
}

function renderGeminiTable(highlightRow = null) {
  const table = currentTable();
  const wrap = byId("gemini-table-wrap");
  if (!table) {
    byId("gemini-meta").textContent = "Không có bảng ứng viên";
    wrap.innerHTML = '<div class="empty-panel">Family này không có bảng Gemini được chọn trong PDF này.</div>';
    return;
  }
  const directlyMappedRows = new Set();
  const derivedMappedRows = new Set();
  for (const mapping of state.review.mappings) {
    for (const sourceRef of mapping.source_refs || []) {
      const sameTable = (!sourceRef.physical_page || sourceRef.physical_page === table.physical_page)
        && (!sourceRef.section_id || sourceRef.section_id === table.section_id)
        && (!sourceRef.table_id || sourceRef.table_id === table.table_id);
      if (sameTable && sourceRef.row_id) {
        (mapping.is_derived ? derivedMappedRows : directlyMappedRows).add(sourceRef.row_id);
      }
    }
    for (const value of mapping.values) {
      const sameTable = (!value.physical_page || value.physical_page === table.physical_page)
        && (!value.section_id || value.section_id === table.section_id)
        && (!value.table_id || value.table_id === table.table_id);
      if (!sameTable) continue;
      if (value.row_id && !value.row_id.startsWith("derived:")) directlyMappedRows.add(value.row_id);
      if (mapping.row_id && !mapping.row_id.startsWith("derived:")) directlyMappedRows.add(mapping.row_id);
      for (const rowId of mapping.derived_from_row_ids || []) derivedMappedRows.add(rowId);
    }
  }
  const mappedRows = new Set([...directlyMappedRows, ...derivedMappedRows]);
  byId("gemini-meta").textContent = `Trang ${table.physical_page} · ${mappedRows.size}/${table.rows.length} dòng có mapping`;
  const heading = table.table_title || table.section_title || "Bảng không có tiêu đề";
  wrap.innerHTML = `
    <div class="table-caption">
      <strong>${escapeHtml(heading)}</strong>
      <span>${escapeHtml(table.section_title || "")} ${table.unit ? `· Đơn vị: ${escapeHtml(table.unit)}` : ""}</span>
    </div>
    <table class="data-table">
      <thead><tr><th>Khoản mục Gemini</th>${table.columns.map((column) => `<th><span class="column-header">${headerMarkup(column.label)}</span></th>`).join("")}</tr></thead>
      <tbody>${table.rows.map((row) => `
        <tr data-row-id="${escapeHtml(row.id)}" class="${row.id === highlightRow ? "is-highlighted" : ""} ${mappedRows.has(row.id) || row.mapping_state === "CORROBORATING" ? "is-mapped" : row.mapping_state === "VISIBLE_UNMAPPED" ? "is-visible-unmapped" : "is-source-only"}">
          <td>${escapeHtml(row.label)}<span class="row-kind">${friendlyRowId(row.id)} · ${friendlyRowKind(row.row_kind)} · ${directlyMappedRows.has(row.id) ? "ĐÃ MAP TRỰC TIẾP" : derivedMappedRows.has(row.id) ? "ĐÃ MAP QUA QUY TẮC" : row.mapping_state === "CORROBORATING" ? `DÒNG ĐỐI CHIẾU · ID ${escapeHtml(row.schema_match?.report_norm_id)} ĐÃ MAP TỪ NGUỒN KHÁC` : row.mapping_state === "VISIBLE_UNMAPPED" ? `CÓ TRÊN PDF · CHƯA MAP VÀO ID ${escapeHtml(row.schema_match?.report_norm_id)}` : row.mapping_state === "STRUCTURAL" ? "DÒNG CẤU TRÚC, KHÔNG CÓ GIÁ TRỊ" : "CHỈ DÙNG ĐỐI CHIẾU (SOURCE_ONLY)"}</span></td>
          ${row.values.map((value) => `<td>${value == null ? '<span aria-label="trống">—</span>' : escapeHtml(value)}</td>`).join("")}
        </tr>`).join("")}</tbody>
    </table>`;
  if (highlightRow) wrap.querySelector(`[data-row-id="${CSS.escape(highlightRow)}"]`)?.scrollIntoView({block: "center"});
}

function filteredMappings() {
  const query = byId("mapping-search").value.trim().toLocaleLowerCase("vi");
  return state.review.mappings.filter((mapping) => !query || [
    mapping.report_norm_id,
    mapping.schema_name,
    mapping.source_label,
    mapping.role,
  ].some((value) => String(value ?? "").toLocaleLowerCase("vi").includes(query)));
}

function formattedCoefficient(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("vi-VN").format(value);
}

function friendlyRowId(rowId) {
  const match = /^r(\d+)$/.exec(rowId || "");
  return match ? `Dòng ${match[1]}` : rowId || "Dòng không đánh số";
}

function friendlyRowKind(rowKind) {
  return {
    ITEM: "Dòng chi tiết",
    TOTAL: "Dòng tổng",
    SUBTOTAL: "Dòng cộng nhóm",
    GROUP: "Tiêu đề nhóm",
  }[rowKind] || rowKind || "Chưa phân loại dòng";
}

function headerMarkup(header) {
  const lines = String(header || "Chưa xác định kỳ")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  return `<strong>${escapeHtml(lines[0] || "Chưa xác định kỳ")}</strong>${lines.slice(1).map((line) => `<small>${escapeHtml(line)}</small>`).join("")}`;
}

function mappingSourceDescription(mapping) {
  const policyNote = mapping.policy_overlay_label
    ? ` · ${escapeHtml(mapping.policy_overlay_label)}`
    : "";
  const exactRefs = mapping.source_refs || [];
  if (exactRefs.length) {
    const sources = exactRefs
      .map((ref) => {
        const hierarchy = (ref.hierarchy_path_exact || []).filter(Boolean).join(" › ");
        const label = hierarchy || ref.label_exact || "";
        return `${ref.physical_page ? `trang ${ref.physical_page}, ` : ""}${friendlyRowId(ref.row_id)}${label ? `: ${escapeHtml(label)}` : ""}`;
      })
      .join("; ");
    return (exactRefs.length === 1 ? `Nguồn trực tiếp: ${sources}` : `Tổng hợp/đối chiếu từ ${sources}`) + policyNote;
  }
  if (!mapping.is_derived) return `Nguồn trực tiếp: ${escapeHtml(mapping.source_label)}${policyNote}`;
  const source = mapping.derived_source_rows?.length
    ? mapping.derived_source_rows.map((row) => `${friendlyRowId(row.row_id)}: ${escapeHtml(row.label)}`).join(", ")
    : mapping.derived_from_row_ids.map(friendlyRowId).join(", ");
  return `Map qua quy tắc từ ${source}${policyNote}`;
}

function mappingValueCell(mapping, value) {
  if (!value) return '<span class="empty-mapping-cell">—</span>';
  const source = value.source_text != null
    ? `PDF: ${escapeHtml(value.source_text)}`
    : value.display_source_text != null
      ? `PDF ${friendlyRowId(value.display_source_row_id)}: ${escapeHtml(value.display_source_text)} · đã kiểm tra bằng quy tắc`
      : mapping.is_derived
        ? `Không có một ô nguồn duy nhất: ${escapeHtml(value.state_label)}`
        : "PDF không có text số riêng";
  return `
    <span class="mapped-coefficient">${formattedCoefficient(value.coefficient)}</span>
    <small class="mapped-source">${source}${value.physical_page ? ` · trang ${value.physical_page}` : ""}</small>
    ${value.state ? `<details class="technical-state"><summary>Chi tiết kỹ thuật</summary><span>${escapeHtml(value.state_label)}</span><code>${escapeHtml(value.state)}</code></details>` : ""}`;
}

function renderMappings() {
  const mappings = filteredMappings();
  const periodHeaders = [...new Set(
    state.review.mappings.flatMap((mapping) => mapping.values.map((value) => value.header)).filter(Boolean)
  )];
  byId("mapping-meta").textContent = `${mappings.length}/${state.review.mappings.length} khoản mục`;
  const list = byId("mapping-list");
  list.innerHTML = mappings.length && periodHeaders.length ? `
    <table class="mapping-table">
      <thead><tr>
        <th>Khoản mục schema / ReportNormId</th>
        ${periodHeaders.map((header) => `<th><span class="column-header">${headerMarkup(header)}</span></th>`).join("")}
      </tr></thead>
      <tbody>${mappings.map((mapping, index) => `
        <tr tabindex="0" data-mapping-index="${mapping.mapping_ordinal ?? index}" title="Nhấn để đối chiếu dòng nguồn bên Gemini">
          <td>
            <span class="mapping-schema-name">${escapeHtml(mapping.schema_name)}</span>
            <span class="norm-id">ID ${escapeHtml(mapping.report_norm_id)}</span>
            <small class="mapping-source">${mappingSourceDescription(mapping)}${mapping.role ? ` · Vai trò: ${escapeHtml(mapping.role)}` : ""}</small>
          </td>
          ${periodHeaders.map((header) => `<td>${mappingValueCell(mapping, mapping.values.find((value) => value.header === header))}</td>`).join("")}
        </tr>`).join("")}</tbody>
    </table>` : '<div class="empty-panel">Không có mapping hoặc chưa xác định được cột kỳ.</div>';
  list.querySelectorAll("[data-mapping-index]").forEach((row) => {
    row.addEventListener("click", () => focusMapping(row.dataset.mappingIndex));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") focusMapping(row.dataset.mappingIndex);
    });
  });
}

function focusMapping(ordinal) {
  const mapping = state.review.mappings.find((item, index) => String(item.mapping_ordinal ?? index) === String(ordinal));
  if (!mapping) return;
  const value = mapping.source_refs?.find((item) => item.physical_page || item.page_json_version_id)
    || mapping.values.find((item) => item.physical_page || item.page_json_version_id)
    || {};
  if (value.physical_page && state.review.pages.some((page) => page.physical_page === value.physical_page)) {
    state.page = value.physical_page;
  }
  const matchingTable = state.review.gemini_tables.find((table) =>
    table.physical_page === state.page
    && (!value.section_id || table.section_id === value.section_id)
    && (!value.table_id || table.table_id === value.table_id)
  );
  if (matchingTable) state.tableKey = matchingTable.key;
  renderPageTabs();
  renderPageImage();
  renderTableSelector();
  const rowId = value.row_id && !value.row_id.startsWith("derived:")
    ? value.row_id
    : mapping.derived_from_row_ids?.[0] || mapping.row_id;
  renderGeminiTable(rowId);
  toast(`Đã đối chiếu ${friendlyRowId(rowId)} với ReportNormId ${mapping.report_norm_id}`);
}

function coverageValues(values) {
  return (values || []).map((value) => value == null ? "—" : value).join(" · ");
}

function renderCoverage() {
  const coverage = state.review.coverage || {};
  const summary = coverage.summary || {};
  const visible = coverage.visible_unmapped || [];
  const notSeen = coverage.not_seen || [];
  const structural = coverage.structural_context || [];
  const corroborating = coverage.corroborating || [];
  const unresolved = coverage.unresolved_tables || [];
  const sourceOnly = coverage.source_only || [];
  const content = byId("coverage-content");

  const visibleSection = visible.length ? `
    <section class="coverage-section coverage-visible">
      <h4>Có trên PDF nhưng chưa map <span>${visible.length}</span></h4>
      <p>Đây là các dòng số đã khớp được một khoản mục schema, nhưng bảng chưa vượt qua điều kiện cấu trúc hoặc không phải candidate được chọn.</p>
      <div class="coverage-table-wrap"><table class="coverage-table">
        <thead><tr><th>Trang / khoản mục PDF</th><th>Schema phù hợp</th><th>Khoản mục cha</th><th>Lý do đang vướng</th></tr></thead>
        <tbody>${visible.map((item) => `<tr tabindex="0" data-coverage-page="${item.physical_page}" data-coverage-table="${escapeHtml(item.table_id)}" data-coverage-section="${escapeHtml(item.section_id)}" data-coverage-row="${escapeHtml(item.row_id)}">
          <td><strong>Trang ${item.physical_page} · ${escapeHtml(item.source_label)}</strong><small>${escapeHtml(coverageValues(item.values))}</small></td>
          <td><strong>ID ${item.report_norm_id} · ${escapeHtml(item.schema_name)}</strong><small>Vai trò nhận diện: ${escapeHtml(item.role)}</small></td>
          <td>${item.schema_parent_id ? `<strong>ID ${item.schema_parent_id}</strong><small>${escapeHtml(item.schema_parent_name || "Chưa có tên")}</small>` : "—"}</td>
          <td>${escapeHtml(item.explanation)}${item.candidate_reason_labels?.length ? `<ul>${item.candidate_reason_labels.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>` : ""}</td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>` : `
    <section class="coverage-section coverage-clear">
      <h4>Có trên PDF nhưng chưa map <span>0</span></h4>
      <p>Chưa phát hiện dòng nào vừa khớp duy nhất với schema vừa bị bỏ khỏi mapping.</p>
    </section>`;

  const structuralSection = structural.length ? `
    <section class="coverage-section coverage-structural">
      <h4>Nút cha cấu trúc liên quan <span>${structural.length}</span></h4>
      ${structural.map((item) => `<div class="structural-note"><strong>ID ${item.report_norm_id} · ${escapeHtml(item.schema_name)}</strong><span>${escapeHtml(item.explanation)}</span></div>`).join("")}
    </section>` : "";

  const corroboratingSection = corroborating.length ? `
    <details class="coverage-section coverage-clear">
      <summary>Dòng đối chiếu — ID đã map từ nguồn khác <span>${corroborating.length}</span></summary>
      <p>Các dòng này khớp schema, nhưng cùng ID đã được lấy từ một bảng hoặc ô nguồn có thẩm quyền khác. Đây không phải khoản mục chưa map.</p>
      <ul class="coverage-list compact">${corroborating.map((item) => `<li><strong>Trang ${item.physical_page} · ${escapeHtml(item.source_label)}</strong><span>ID ${item.report_norm_id} · ${escapeHtml(item.schema_name)} · ${escapeHtml(item.explanation)}</span></li>`).join("")}</ul>
    </details>` : "";

  const unresolvedSection = unresolved.length ? `
    <section class="coverage-section coverage-unresolved">
      <h4>Bảng đang vướng <span>${unresolved.length}</span></h4>
      <ul class="coverage-list">${unresolved.map((item) => `<li><strong>Trang ${item.physical_page} · ${escapeHtml(item.table_title || `${item.section_id}/${item.table_id}`)}</strong>${item.reason_labels?.length ? `<span>${item.reason_labels.map(escapeHtml).join("; ")}</span>` : ""}</li>`).join("")}</ul>
    </section>` : `
    <section class="coverage-section coverage-clear"><h4>Bảng đang vướng <span>0</span></h4><p>Không có candidate bảng nào ở trạng thái cần kiểm tra.</p></section>`;

  const notSeenSection = `
    <details class="coverage-section coverage-not-seen" ${state.review.disposition.status === "NOT_OBSERVED" ? "open" : ""}>
      <summary>Khoản mục schema chưa thấy trong PDF này <span>${notSeen.length}</span></summary>
      <p>Danh sách này chỉ có nghĩa là không thấy trong phạm vi PDF/bảng đang xét; không phải lỗi mapping và không phải bằng chứng thiếu schema.</p>
      ${notSeen.length ? `<div class="schema-chip-list">${notSeen.map((item) => `<span><b>ID ${item.report_norm_id}</b> ${escapeHtml(item.schema_name)}${item.schema_parent_id ? `<small>Cha: ID ${item.schema_parent_id} · ${escapeHtml(item.schema_parent_name || "")}</small>` : ""}</span>`).join("")}</div>` : "<p>Tất cả khoản mục schema đã cấu hình đều đã được nhìn thấy hoặc map.</p>"}
    </details>`;

  const sourceOnlySection = `
    <details class="coverage-section coverage-source-only">
      <summary>Nhìn thấy nhưng chỉ giữ để đối chiếu / nghi family khác <span>${sourceOnly.length}</span></summary>
      <p>Không tự động coi các dòng này là thiếu schema. Chúng có thể là dòng tổng, dòng ngoài mục tiêu, hoặc thuộc family khác.</p>
      ${sourceOnly.length ? `<ul class="coverage-list compact">${sourceOnly.map((item) => `<li><strong>Trang ${item.physical_page} · ${escapeHtml(item.source_label)}</strong><span>${escapeHtml(item.classification)} · ${escapeHtml(item.explanation)}</span></li>`).join("")}</ul>` : ""}
    </details>`;

  content.innerHTML = `
    <div class="coverage-summary">
      <span><b>${summary.mapped_schema_items || 0}</b> khoản mục đã map</span>
      <span class="is-visible"><b>${summary.visible_unmapped_items || 0}</b> có trên PDF nhưng chưa map</span>
      <span><b>${summary.not_seen_schema_items || 0}</b> chưa thấy</span>
      <span class="is-unresolved"><b>${summary.unresolved_tables || 0}</b> bảng vướng</span>
    </div>
    ${visibleSection}${corroboratingSection}${structuralSection}${unresolvedSection}${notSeenSection}${sourceOnlySection}`;

  content.querySelectorAll("[data-coverage-page]").forEach((row) => {
    const focus = () => {
      state.page = Number(row.dataset.coveragePage);
      const table = state.review.gemini_tables.find((item) =>
        item.physical_page === state.page
        && item.section_id === row.dataset.coverageSection
        && item.table_id === row.dataset.coverageTable
      );
      if (table) state.tableKey = table.key;
      renderPageTabs();
      renderPageImage();
      renderTableSelector();
      renderGeminiTable(row.dataset.coverageRow);
      toast(`Đã mở trang ${state.page}, ${friendlyRowId(row.dataset.coverageRow)}`);
    };
    row.addEventListener("click", focus);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") focus();
    });
  });
}

function setupPdfPanning() {
  const canvas = byId("pdf-canvas");
  let start = null;
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || byId("page-image").classList.contains("is-hidden")) return;
    start = {x: event.clientX, y: event.clientY, left: canvas.scrollLeft, top: canvas.scrollTop};
    canvas.classList.add("is-panning");
    canvas.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!start) return;
    canvas.scrollLeft = start.left - (event.clientX - start.x);
    canvas.scrollTop = start.top - (event.clientY - start.y);
  });
  const stop = (event) => {
    if (!start) return;
    start = null;
    canvas.classList.remove("is-panning");
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  };
  canvas.addEventListener("pointerup", stop);
  canvas.addEventListener("pointercancel", stop);
}

function setupPanelResizing() {
  const grid = document.querySelector(".comparison-grid");
  const handles = [...grid.querySelectorAll("[data-resize-handle]")];
  const panels = [grid.querySelector(".pdf-panel"), grid.querySelector(".gemini-panel"), grid.querySelector(".mapping-panel")];
  const reset = () => { grid.style.gridTemplateColumns = ""; };
  for (const handle of handles) {
    handle.addEventListener("dblclick", reset);
    handle.addEventListener("pointerdown", (event) => {
      if (window.innerWidth <= 850) return;
      const index = Number(handle.dataset.resizeHandle);
      const initialWidths = panels.map((panel) => panel.getBoundingClientRect().width);
      const pairTotal = initialWidths[index] + initialWidths[index + 1];
      const startX = event.clientX;
      handle.classList.add("is-dragging");
      handle.setPointerCapture(event.pointerId);
      const move = (moveEvent) => {
        const pointerDelta = moveEvent.clientX - startX;
        const left = Math.max(
          260,
          Math.min(pairTotal - 280, initialWidths[index] + pointerDelta),
        );
        const nextWidths = [...initialWidths];
        nextWidths[index] = left;
        nextWidths[index + 1] = pairTotal - left;
        grid.style.gridTemplateColumns = `${nextWidths[0]}px 8px ${nextWidths[1]}px 8px ${nextWidths[2]}px`;
      };
      const stop = () => {
        handle.classList.remove("is-dragging");
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", stop);
        handle.removeEventListener("pointercancel", stop);
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", stop);
      handle.addEventListener("pointercancel", stop);
      event.preventDefault();
    });
  }
  window.addEventListener("resize", debounce(reset, 150));
}

function renderDiagnostics() {
  const disposition = state.review.disposition;
  const candidates = state.review.candidates;
  const content = byId("diagnostic-content");
  const reasons = disposition.reason_labels.length
    ? `<ul class="diagnostic-list">${disposition.reason_labels.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>`
    : '<p>Không có lý do unresolved ở cấp PDF/family.</p>';
  const candidateRows = candidates.length
    ? `<p>${candidates.length} ứng viên bảng; ${candidates.reduce((sum, item) => sum + Number(item.mapping_count || 0), 0)} mapping ở các ứng viên.</p>`
    : "<p>Không có ứng viên bảng, phù hợp với trạng thái NOT_OBSERVED.</p>";
  content.innerHTML = reasons + candidateRows;
}

function debounce(callback, wait = 250) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), wait);
  };
}

async function initialize() {
  try {
    state.options = await api("/api/options");
    setConnection(state.options.configuration);
    fillSelect("filter-bank", state.options.banks);
    fillSelect("filter-year", state.options.years);
    fillSelect("filter-period", state.options.periods);
    fillSelect("filter-scope", state.options.scopes);
    fillSelect("filter-assurance", state.options.assurance);
    state.familyId = state.options.default_family;
    renderFamilies();
    await loadDocuments();
  } catch (error) {
    setConnection({ready: false});
    byId("family-list").innerHTML = `<div class="empty-list">${escapeHtml(error.message)}</div>`;
    toast(error.message);
  }
}

byId("family-search").addEventListener("input", renderFamilies);
byId("mapping-search").addEventListener("input", renderMappings);
for (const id of ["filter-bank", "filter-year", "filter-period", "filter-scope", "filter-assurance", "filter-status"]) {
  byId(id).addEventListener("change", loadDocuments);
}
byId("document-search").addEventListener("input", debounce(loadDocuments));
byId("clear-filters").addEventListener("click", () => {
  for (const id of ["filter-bank", "filter-year", "filter-period", "filter-scope", "filter-assurance", "filter-status"]) byId(id).value = "";
  byId("document-search").value = "";
  loadDocuments();
});
byId("zoom-in").addEventListener("click", () => {
  state.zoom = Math.min(180, state.zoom + 15);
  renderPageImage();
});
byId("zoom-out").addEventListener("click", () => {
  state.zoom = Math.max(55, state.zoom - 15);
  renderPageImage();
});

initialize();
setupPdfPanning();
setupPanelResizing();
