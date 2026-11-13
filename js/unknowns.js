/**
 * Campus AI - Unknown Person Monitoring & Manual Verification Controller
 */

const UnknownsController = {
  currentUnknowns: [],
  selectedLogId: null,

  async loadUnknowns() {
    const verified = document.getElementById("unknown-filter-verified")?.value || "All";
    const tbody = document.getElementById("unknowns-table-body");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Loading unmatched detections...</td></tr>`;

    try {
      const params = { limit: 50 };
      if (verified !== "All") params.verified = verified;

      const resp = await API.getUnknowns(params);
      this.currentUnknowns = resp.unknowns || [];

      if (this.currentUnknowns.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-5 text-muted">No unmatched detections recorded. All individuals were reliably identified.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.currentUnknowns.map(u => `
        <tr>
          <td>
            <div class="fw-bold text-white">${u.formatted_date}</div>
            <div class="small text-muted font-monospace">${u.formatted_time}</div>
          </td>
          <td>
            <div class="rounded border border-secondary" style="width: 50px; height: 50px; overflow: hidden; background: #000;">
              ${u.snapshot_url ? `<img src="${u.snapshot_url}" style="width: 100%; height: 100%; object-fit: cover;" alt="Unknown Face"/>` : '<i data-lucide="help-circle" class="p-2"></i>'}
            </div>
          </td>
          <td>${u.camera_name || u.camera_id}</td>
          <td>
            <span class="badge badge-custom badge-danger">${(u.best_similarity * 100).toFixed(1)}% match</span>
            <div class="small text-muted mt-1">Below threshold</div>
          </td>
          <td>
            <span class="badge badge-custom ${u.verified ? 'badge-success' : 'badge-warning'}">
              ${u.verification_status}
            </span>
            ${u.notes ? `<div class="small text-muted mt-1">${u.notes}</div>` : ''}
          </td>
          <td>
            <div class="d-flex align-items-center gap-2">
              ${!u.verified ? `
                <button class="btn btn-sm btn-outline-primary py-1 px-2" onclick="UnknownsController.openVerifyModal('${u.id}')" title="Manually verify person identity">
                  <i data-lucide="check-circle" style="width: 14px;" class="me-1"></i> Verify
                </button>
              ` : `<span class="text-muted small">Reviewed</span>`}
              <button class="btn btn-sm btn-outline-danger py-1 px-2 border-0" onclick="UnknownsController.handleDeleteOne('${u.id}')" title="Delete this detection record">
                <i data-lucide="trash-2" style="width: 14px;"></i>
              </button>
            </div>
          </td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-danger">Error loading unknowns: ${err.message}</td></tr>`;
    }
  },

  openVerifyModal(logId) {
    this.selectedLogId = logId;
    const u = this.currentUnknowns.find(x => x.id === logId);
    if (!u) return;

    const img = document.getElementById("verify-unknown-preview");
    if (img && u.snapshot_url) img.src = u.snapshot_url;

    document.getElementById("verify-notes-input").value = "";
    new bootstrap.Modal(document.getElementById("modal-verify-unknown")).show();
  },

  async submitVerification() {
    if (!this.selectedLogId) return;

    const status = document.getElementById("verify-status-select").value;
    const notes = document.getElementById("verify-notes-input").value.trim();

    try {
      await API.verifyUnknown(this.selectedLogId, status, null, notes);
      alert(`Person verified as: ${status}`);
      bootstrap.Modal.getInstance(document.getElementById("modal-verify-unknown")).hide();
      this.loadUnknowns();
    } catch (err) {
      alert(`Verification error: ${err.message}`);
    }
  },

  async handleDeleteAll() {
    if (!confirm("Are you sure you want to delete ALL unmatched / unknown person detection records? This cannot be undone.")) return;

    try {
      const resp = await API.deleteAllUnknowns();
      alert(resp.message || "All unknown records deleted successfully.");
      this.loadUnknowns();
    } catch (err) {
      alert(`Error deleting records: ${err.message}`);
    }
  },

  async handleDeleteOne(logId) {
    if (!confirm("Delete this unknown detection record?")) return;

    try {
      await API.deleteUnknown(logId);
      this.loadUnknowns();
    } catch (err) {
      alert(`Error deleting record: ${err.message}`);
    }
  }
};
