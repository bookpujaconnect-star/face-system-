/**
 * Campus AI - Centralized REST API Client
 */

const API = {
  getToken() {
    return localStorage.getItem("campus_ai_token");
  },

  setToken(token) {
    localStorage.setItem("campus_ai_token", token);
  },

  clearToken() {
    localStorage.removeItem("campus_ai_token");
    localStorage.removeItem("campus_ai_user");
  },

  getUser() {
    const u = localStorage.getItem("campus_ai_user");
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    localStorage.setItem("campus_ai_user", JSON.stringify(user));
  },

  async request(endpoint, options = {}) {
    const token = this.getToken();
    const headers = options.headers || {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(endpoint, {
        ...options,
        headers
      });

      if (response.status === 401 && !endpoint.includes("/api/auth/login")) {
        this.clearToken();
        if (typeof App !== "undefined" && App.updateSignInButtonState) {
          App.updateSignInButtonState();
        }
        throw new Error("Session expired. Please sign in again.");
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth
  login(email, password) {
    return this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },

  getProfile() {
    return this.request("/api/auth/me");
  },

  getPublicInfo() {
    return this.request("/api/public/info");
  },

  // Students
  getStudents(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/students?${qs}`);
  },

  createStudent(studentData) {
    return this.request("/api/students", {
      method: "POST",
      body: JSON.stringify(studentData)
    });
  },

  updateStudent(studentId, updates) {
    return this.request(`/api/students/${studentId}`, {
      method: "PUT",
      body: JSON.stringify(updates)
    });
  },

  deleteStudent(studentId) {
    return this.request(`/api/students/${studentId}`, {
      method: "DELETE"
    });
  },

  seedSyntheticStudents() {
    return this.request("/api/students/seed-synthetic", {
      method: "POST"
    });
  },

  // Biometrics
  validateQuality(imageB64) {
    return this.request("/api/biometrics/validate-quality", {
      method: "POST",
      body: JSON.stringify({ image: imageB64 })
    });
  },

  enrollStudent(studentId, imageB64, consentGiven) {
    return this.request("/api/biometrics/enroll", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        image: imageB64,
        consent_given: consentGiven
      })
    });
  },

  deleteBiometrics(studentId) {
    return this.request("/api/biometrics/delete", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId })
    });
  },

  // Camera & Detection
  processFrame(imageB64, cameraId, cameraName, nightVision = false) {
    return this.request("/api/camera/process-frame", {
      method: "POST",
      body: JSON.stringify({
        image: imageB64,
        camera_id: cameraId,
        camera_name: cameraName,
        night_vision: nightVision
      })
    });
  },

  getCameraSources() {
    return this.request("/api/camera/sources");
  },

  // Entries
  getEntries(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/entries?${qs}`);
  },

  getRecentEntries(limit = 10) {
    return this.request(`/api/entries/recent?limit=${limit}`);
  },

  // Unknowns
  getUnknowns(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/unknowns?${qs}`);
  },

  verifyUnknown(logId, status, studentId, notes) {
    return this.request(`/api/unknowns/${logId}/verify`, {
      method: "POST",
      body: JSON.stringify({ status, student_id: studentId, notes })
    });
  },

  deleteAllUnknowns() {
    return this.request("/api/unknowns/all", {
      method: "DELETE"
    });
  },

  deleteUnknown(logId) {
    return this.request(`/api/unknowns/${logId}`, {
      method: "DELETE"
    });
  },

  // Analytics & Metrics
  getDashboardAnalytics() {
    return this.request("/api/analytics/dashboard");
  },

  getSystemMetrics() {
    return this.request("/api/evaluation/system-metrics");
  },

  // Research Evaluation
  runBenchmarks(identities = 10) {
    return this.request("/api/evaluation/run-benchmarks", {
      method: "POST",
      body: JSON.stringify({ identities })
    });
  },

  getLatestBenchmarkResults() {
    return this.request("/api/evaluation/latest-results");
  },

  // Settings
  getSettings() {
    return this.request("/api/settings");
  },

  updateSettings(settingsData) {
    return this.request("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settingsData)
    });
  }
};
