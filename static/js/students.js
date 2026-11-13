/**
 * Campus AI - Student Management Controller
 */

const StudentsController = {
  currentStudents: [],

  async loadStudents() {
    const search = document.getElementById("student-search-input")?.value || "";
    const memberType = document.getElementById("student-type-filter")?.value || "All";
    const department = document.getElementById("student-dept-filter")?.value || "All";
    const status = document.getElementById("student-status-filter")?.value || "All";

    const tbody = document.getElementById("students-table-body");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Loading member directory...</td></tr>`;

    try {
      const resp = await API.getStudents({ search, member_type: memberType, department, status, limit: 100 });
      this.currentStudents = resp.students || [];

      // Update member count badge
      const countBadge = document.getElementById("total-students-count-badge");
      if (countBadge) countBadge.innerText = `${resp.total} Members`;

      if (this.currentStudents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-muted">No records found. Click <strong>Add Student</strong> or <strong>Add Faculty</strong> to begin.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.currentStudents.map(s => `
        <tr>
          <td>
            <div class="d-flex align-items-center gap-3">
              <div class="avatar-sm rounded-circle bg-secondary d-flex align-items-center justify-content-center text-white" style="width: 36px; height: 36px; overflow: hidden;">
                ${s.photo_url ? `<img src="${s.photo_url}" style="width: 100%; height: 100%; object-fit: cover;" alt="${s.name}"/>` : `<i data-lucide="${s.member_type === 'Faculty' ? 'graduation-cap' : 'user'}" style="width: 18px;"></i>`}
              </div>
              <div>
                <div class="fw-bold text-white">${s.name}</div>
                <div class="text-muted small">${s.email || 'No email provided'}</div>
              </div>
            </div>
          </td>
          <td>
            ${s.member_type === 'Faculty' 
              ? `<span class="badge px-2 py-1 small fw-semibold" style="background-color: #8b5cf6; color: #fff;">Faculty</span>`
              : `<span class="badge bg-primary px-2 py-1 small fw-semibold">Student</span>`}
          </td>
          <td><span class="font-monospace fw-bold text-primary">${s.reg_no}</span></td>
          <td>${s.department}</td>
          <td>${s.designation || s.academic_year || 'Member'}</td>
          <td>
            ${s.is_enrolled 
              ? `<span class="badge badge-custom badge-success">✓ Enrolled (512-d)</span>` 
              : `<span class="badge badge-custom badge-warning">Pending Face</span>`}
          </td>
          <td>
            <span class="badge badge-custom ${s.status === 'Active' ? 'badge-info' : 'badge-danger'}">${s.status}</span>
          </td>
          <td>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-primary" onclick="StudentsController.openEditModal('${s.id}')" title="Edit Record">
                <i data-lucide="edit-2" style="width: 14px;"></i>
              </button>
              ${s.is_enrolled ? `
                <button class="btn btn-sm btn-outline-warning" onclick="StudentsController.purgeBiometrics('${s.id}', '${s.name}')" title="Erase Biometrics (GDPR)">
                  <i data-lucide="shield-alert" style="width: 14px;"></i>
                </button>
              ` : `
                <button class="btn btn-sm btn-outline-success" onclick="StudentsController.navigateToEnroll('${s.id}')" title="Enroll Facial Biometrics">
                  <i data-lucide="camera" style="width: 14px;"></i>
                </button>
              `}
              <button class="btn btn-sm btn-outline-danger" onclick="StudentsController.deleteStudent('${s.id}', '${s.name}')" title="Delete Record">
                <i data-lucide="trash-2" style="width: 14px;"></i>
              </button>
            </div>
          </td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();

      // Also populate the enrollment dropdown selector
      this.populateEnrollmentDropdown();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger">Error loading records: ${err.message}</td></tr>`;
    }
  },

  populateEnrollmentDropdown() {
    const select = document.getElementById("enroll-student-select");
    if (!select) return;

    select.innerHTML = `<option value="">-- Select Member to Enroll --</option>` +
      this.currentStudents.map(s => `
        <option value="${s.id}">${s.member_type === 'Faculty' ? '[Faculty]' : '[Student]'} ${s.name} (${s.reg_no}) - ${s.is_enrolled ? '[Currently Enrolled]' : '[Not Enrolled]'}</option>
      `).join("");
  },

  navigateToEnroll(studentId) {
    App.navigateTo("enrollment");
    setTimeout(() => {
      const select = document.getElementById("enroll-student-select");
      if (select) {
        select.value = studentId;
        EnrollmentController.checkCommitReadiness();
      }
    }, 200);
  },

  async handleCreateStudent(event) {
    event.preventDefault();
    const memberType = document.getElementById("new-stu-type")?.value || "Student";
    const yearOrDesig = document.getElementById("new-stu-year").value;
    const data = {
      reg_no: document.getElementById("new-stu-reg").value.trim(),
      name: document.getElementById("new-stu-name").value.trim(),
      email: document.getElementById("new-stu-email").value.trim(),
      department: document.getElementById("new-stu-dept").value,
      academic_year: yearOrDesig,
      designation: yearOrDesig,
      member_type: memberType,
      phone: document.getElementById("new-stu-phone").value.trim(),
      biometric_consent: document.getElementById("new-stu-consent").checked
    };

    try {
      await API.createStudent(data);
      alert(`${memberType} created successfully!`);
      bootstrap.Modal.getInstance(document.getElementById("modal-register-student")).hide();
      document.getElementById("form-register-student").reset();
      this.loadStudents();
    } catch (err) {
      alert(`Error creating record: ${err.message}`);
    }
  },

  openEditModal(studentId) {
    const s = this.currentStudents.find(x => x.id === studentId);
    if (!s) return;

    document.getElementById("edit-stu-id").value = s.id;
    document.getElementById("edit-stu-reg").value = s.reg_no;
    document.getElementById("edit-stu-name").value = s.name;
    document.getElementById("edit-stu-email").value = s.email;
    document.getElementById("edit-stu-dept").value = s.department;
    document.getElementById("edit-stu-year").value = s.academic_year;
    document.getElementById("edit-stu-phone").value = s.phone;
    document.getElementById("edit-stu-status").value = s.status;

    new bootstrap.Modal(document.getElementById("modal-edit-student")).show();
  },

  async handleUpdateStudent(event) {
    event.preventDefault();
    const studentId = document.getElementById("edit-stu-id").value;
    const updates = {
      reg_no: document.getElementById("edit-stu-reg").value.trim(),
      name: document.getElementById("edit-stu-name").value.trim(),
      email: document.getElementById("edit-stu-email").value.trim(),
      department: document.getElementById("edit-stu-dept").value,
      academic_year: document.getElementById("edit-stu-year").value,
      phone: document.getElementById("edit-stu-phone").value.trim(),
      status: document.getElementById("edit-stu-status").value
    };

    try {
      await API.updateStudent(studentId, updates);
      alert("Student record updated!");
      bootstrap.Modal.getInstance(document.getElementById("modal-edit-student")).hide();
      this.loadStudents();
    } catch (err) {
      alert(`Update error: ${err.message}`);
    }
  },

  async deleteStudent(studentId, studentName) {
    if (!confirm(`Are you sure you want to permanently delete student ${studentName}?`)) return;
    try {
      await API.deleteStudent(studentId);
      this.loadStudents();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  },

  async purgeBiometrics(studentId, studentName) {
    if (!confirm(`Are you sure you want to completely erase facial biometric embeddings for ${studentName} under data privacy laws?`)) return;
    try {
      await API.deleteBiometrics(studentId);
      alert(`Biometric data purged.`);
      this.loadStudents();
    } catch (err) {
      alert(`Purge failed: ${err.message}`);
    }
  },

  async handleBulkImport(event) {
    event.preventDefault();
    const fileInput = document.getElementById("bulk-import-file");
    if (!fileInput.files.length) {
      alert("Please choose a CSV or Excel file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const btn = document.getElementById("btn-submit-import");
    btn.disabled = true;
    btn.innerText = "Importing...";

    try {
      const resp = await API.request("/api/students/import", {
        method: "POST",
        body: formData
      });
      alert(resp.message || "Import completed successfully!");
      bootstrap.Modal.getInstance(document.getElementById("modal-import-students")).hide();
      fileInput.value = "";
      this.loadStudents();
    } catch (err) {
      alert(`Import error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerText = "Upload & Import Records";
    }
  },

  async handleSeedSynthetic() {
    if (!confirm("Populate database with 8 synthetic student records and enrolled FaceNet embeddings across 5 departments?")) return;
    try {
      const resp = await API.seedSyntheticStudents();
      alert(resp.message || "Synthetic students created!");
      this.loadStudents();
    } catch (err) {
      alert(`Seeding failed: ${err.message}`);
    }
  }
};
