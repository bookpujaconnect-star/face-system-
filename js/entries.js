/**
 * Campus AI - Entry History & Export Controller
 */

const EntriesController = {
  currentEntries: [],

  async loadEntries() {
    const reg_no = document.getElementById("entry-search-reg")?.value || "";
    const department = document.getElementById("entry-filter-dept")?.value || "All";
    const camera_id = document.getElementById("entry-filter-camera")?.value || "All";
    const start_date = document.getElementById("entry-start-date")?.value || "";
    const end_date = document.getElementById("entry-end-date")?.value || "";

    const tbody = document.getElementById("entries-table-body");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Loading entry history...</td></tr>`;

    try {
      const resp = await API.getEntries({
        reg_no: reg_no.trim() || undefined,
        department: department !== "All" ? department : undefined,
        camera_id: camera_id !== "All" ? camera_id : undefined,
        start_date: start_date || undefined,
        end_date: end_date || undefined,
        limit: 100
      });

      this.currentEntries = resp.entries || [];

      if (this.currentEntries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No entry identification events found matching criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.currentEntries.map(e => `
        <tr>
          <td>
            <div class="fw-bold text-white">${e.formatted_date}</div>
            <div class="small text-muted font-monospace">${e.formatted_time}</div>
          </td>
          <td>
            <div class="d-flex align-items-center gap-2">
              ${e.snapshot_url ? `<img src="${e.snapshot_url}" class="rounded" style="width: 32px; height: 32px; object-fit: cover;" alt="Snapshot"/>` : ''}
              <div>
                <div class="fw-bold text-white">${e.student_name}</div>
                <div class="small text-muted font-monospace">${e.reg_no}</div>
              </div>
            </div>
          </td>
          <td>${e.department}</td>
          <td>${e.camera_name || e.camera_id}</td>
          <td>
            <span class="badge badge-custom badge-success">${(e.similarity_score * 100).toFixed(1)}%</span>
          </td>
          <td>
            <span class="text-info small font-monospace">${e.response_time_ms} ms</span>
          </td>
          <td>
            <span class="badge badge-custom badge-success">✓ Verified Entry</span>
          </td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Error loading entry logs: ${err.message}</td></tr>`;
    }
  },

  exportCSV() {
    const dept = document.getElementById("entry-filter-dept")?.value || "All";
    const start = document.getElementById("entry-start-date")?.value || "";
    const end = document.getElementById("entry-end-date")?.value || "";

    const params = new URLSearchParams();
    if (dept !== "All") params.append("department", dept);
    if (start) params.append("start_date", start);
    if (end) params.append("end_date", end);

    window.location.href = `/api/entries/export?${params.toString()}`;
  }
};
