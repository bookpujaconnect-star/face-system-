/**
 * Campus AI - Facial Enrollment & Biometrics Controller
 */

const EnrollmentController = {
  video: null,
  canvas: null,
  stream: null,
  capturedImageB64: null,
  selectedStudent: null,

  init() {
    this.video = document.getElementById("enroll-video");
    this.canvas = document.getElementById("enroll-canvas");
  },

  async startWebcam() {
    this.init();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 480, height: 480, facingMode: "user" },
        audio: false
      });
      this.video.srcObject = this.stream;
      await this.video.play();
      document.getElementById("btn-enroll-snap").disabled = false;
    } catch (err) {
      console.warn("Enrollment webcam failed:", err);
      alert("Could not access camera for enrollment. You can also upload a photo file.");
    }
  },

  stopWebcam() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    if (this.video) {
      this.video.srcObject = null;
    }
    document.getElementById("btn-enroll-snap").disabled = true;
  },

  captureSnapshot() {
    if (!this.video) return;
    const ctx = this.canvas.getContext("2d");
    this.canvas.width = 480;
    this.canvas.height = 480;
    ctx.drawImage(this.video, 0, 0, 480, 480);
    this.capturedImageB64 = this.canvas.toDataURL("image/jpeg", 0.90);

    const preview = document.getElementById("enroll-preview-img");
    preview.src = this.capturedImageB64;
    preview.classList.remove("d-none");
    this.video.classList.add("d-none");

    document.getElementById("btn-enroll-retake").classList.remove("d-none");
    document.getElementById("btn-enroll-snap").classList.add("d-none");

    this.validateQuality();
  },

  retakeSnapshot() {
    this.capturedImageB64 = null;
    document.getElementById("enroll-preview-img").classList.add("d-none");
    this.video.classList.remove("d-none");
    document.getElementById("btn-enroll-retake").classList.add("d-none");
    document.getElementById("btn-enroll-snap").classList.remove("d-none");
    document.getElementById("quality-results-box").classList.add("d-none");
    document.getElementById("btn-commit-enroll").disabled = true;
  },

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      this.capturedImageB64 = e.target.result;
      const preview = document.getElementById("enroll-preview-img");
      preview.src = this.capturedImageB64;
      preview.classList.remove("d-none");
      if (this.video) this.video.classList.add("d-none");

      document.getElementById("btn-enroll-retake").classList.remove("d-none");
      document.getElementById("btn-enroll-snap").classList.add("d-none");

      this.validateQuality();
    };
    reader.readAsDataURL(file);
  },

  async validateQuality() {
    if (!this.capturedImageB64) return;
    const box = document.getElementById("quality-results-box");
    box.classList.remove("d-none");
    box.innerHTML = `<div class="text-center py-2"><span class="spinner-border spinner-border-sm text-primary"></span> Validating facial image quality...</div>`;

    try {
      const resp = await API.validateQuality(this.capturedImageB64);
      if (resp.status === "warning") {
        box.innerHTML = `
          <div class="alert alert-warning py-2 mb-0 small">
            <strong>Notice:</strong> ${resp.issues.join(", ")}
          </div>
        `;
        document.getElementById("btn-commit-enroll").disabled = true;
        return;
      }

      const q = resp.quality;
      const isValid = q.is_valid;

      box.innerHTML = `
        <div class="p-3 rounded border ${isValid ? 'border-success' : 'border-danger'}" style="background: rgba(255,255,255,0.02)">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="fw-bold ${isValid ? 'text-success' : 'text-danger'}">
              ${isValid ? '✓ Quality Validation Passed' : '✗ Quality Validation Failed'}
            </span>
            <span class="badge ${isValid ? 'bg-success' : 'bg-danger'}">${q.overall_score}% Quality Score</span>
          </div>

          <div class="small text-muted mb-2">
            <span>Sharpness: <strong>${q.blur_variance.toFixed(1)}</strong></span> • 
            <span>Brightness: <strong>${q.brightness.toFixed(1)}</strong></span> • 
            <span>Resolution: <strong>${q.dimensions[0]}x${q.dimensions[1]}</strong> px</span>
          </div>

          ${q.issues.length > 0 ? `
            <div class="text-danger small mt-1">
              Issues: ${q.issues.join(" ")}
            </div>
          ` : '<div class="text-success small">Face resolution, sharpness, and illumination meet ISO/IEC standards.</div>'}
        </div>
      `;

      // Enable commit button if quality is valid and consent is checked
      this.checkCommitReadiness(isValid);
    } catch (err) {
      box.innerHTML = `<div class="alert alert-danger py-2 mb-0 small">Quality check error: ${err.message}</div>`;
      document.getElementById("btn-commit-enroll").disabled = true;
    }
  },

  checkCommitReadiness(isQualityValid = true) {
    const consent = document.getElementById("enroll-consent-check").checked;
    const studentSelected = document.getElementById("enroll-student-select").value;
    const btn = document.getElementById("btn-commit-enroll");

    btn.disabled = !(consent && studentSelected && this.capturedImageB64 && isQualityValid);
  },

  async commitEnrollment() {
    const studentId = document.getElementById("enroll-student-select").value;
    const consent = document.getElementById("enroll-consent-check").checked;

    if (!studentId || !this.capturedImageB64 || !consent) {
      alert("Please ensure a student is selected, face captured, and informed consent acknowledged.");
      return;
    }

    const btn = document.getElementById("btn-commit-enroll");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Generating 512-d FaceNet Embedding...`;

    try {
      const resp = await API.enrollStudent(studentId, this.capturedImageB64, consent);
      alert(resp.message || "Student enrolled successfully!");
      // Reset view
      this.retakeSnapshot();
      App.navigateTo("students");
    } catch (err) {
      alert(`Enrollment failed: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `Complete Facial Enrollment`;
    }
  }
};
