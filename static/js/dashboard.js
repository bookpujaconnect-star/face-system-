/**
 * Campus AI - Master Application Controller
 * Handles Dual Panels (Kiosk Scanner & Admin Suite) and Dark/Light Theme Switching
 */

const App = {
  currentPanel: "kiosk", // "kiosk" (default landing page) or "admin"
  currentAdminView: "dashboard",
  theme: "dark",
  charts: {},

  async init() {
    // 1. Initialize Theme from localStorage
    const savedTheme = localStorage.getItem("campus_theme") || "dark";
    this.setTheme(savedTheme);

    // 2. Fetch public institution name and campus branding immediately
    try {
      const pub = await API.getPublicInfo();
      if (pub && pub.institution_name) {
        this.updateInstitutionBranding(pub.institution_name, pub.campus_location);
      }
    } catch (e) {
      console.warn("Public info fetch error:", e);
    }

    // 3. Start Live Clock on Kiosk
    this.startKioskClock();

    // 4. Load recent entry history on Kiosk and continuously refresh
    this.loadKioskRecentEntries();
    setInterval(() => this.loadKioskRecentEntries(), 3500);

    // 5. Default view: Gate Entrance Camera Scanning Tool (Panel 1)
    this.showKioskPanel();

    // 6. Start DB latency poller
    this.startTelemetryPoller();

    if (window.lucide) lucide.createIcons();
  },

  setTheme(themeName) {
    this.theme = themeName;
    document.documentElement.setAttribute("data-theme", themeName);
    localStorage.setItem("campus_theme", themeName);

    // Update theme toggle button label/icon
    const themeBtn = document.getElementById("btn-theme-toggle");
    if (themeBtn) {
      if (themeName === "light") {
        themeBtn.innerHTML = `<i data-lucide="moon" style="width: 15px;"></i> Dark Mode`;
      } else {
        themeBtn.innerHTML = `<i data-lucide="sun" style="width: 15px;"></i> Light Mode`;
      }
      if (window.lucide) lucide.createIcons();
    }
  },

  toggleTheme() {
    const nextTheme = (this.theme === "dark") ? "light" : "dark";
    this.setTheme(nextTheme);
  },

  updateInstitutionBranding(name, location) {
    if (name) {
      document.querySelectorAll(".dyn-institution-name").forEach(el => el.innerText = name);
      document.title = `${name} | Campus Entry Monitoring`;
    }
    if (location) {
      document.querySelectorAll(".dyn-campus-location").forEach(el => el.innerText = location);
    }
  },

  startKioskClock() {
    const updateTime = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const dateStr = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
      const clockEl = document.getElementById("kiosk-live-clock");
      if (clockEl) clockEl.innerText = `${timeStr} • ${dateStr}`;
    };
    updateTime();
    setInterval(updateTime, 1000);
  },

  async loadKioskRecentEntries() {
    try {
      const resp = await API.getRecentEntries(6);
      const list = document.getElementById("kiosk-detections-list");
      if (!list || !resp.entries || resp.entries.length === 0) return;

      list.innerHTML = resp.entries.map(e => `
        <div class="recognition-alert-card identified mb-2">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge badge-custom badge-success">✓ SIGNED IN</span>
                <span class="fw-bold">${e.student_name}</span>
              </div>
              <div class="small text-muted mt-1">
                <span><strong>Reg:</strong> ${e.reg_no}</span> • 
                <span>${e.department}</span>
              </div>
              <div class="small text-muted mt-1">
                <span>Confidence: <strong>${(e.similarity_score * 100).toFixed(1)}%</strong></span> • 
                <span>Time: ${e.formatted_time}</span>
              </div>
            </div>
            <span class="badge bg-secondary small">${e.camera_name || 'Gate'}</span>
          </div>
        </div>
      `).join("");
    } catch (e) {
      console.warn("Could not load initial kiosk entries:", e);
    }
  },

  /* ========================================================= */
  /* PANEL NAVIGATION (KIOSK vs ADMIN)                         */
  /* ========================================================= */
  showKioskPanel() {
    this.currentPanel = "kiosk";
    document.getElementById("kiosk-panel").classList.remove("d-none");
    document.getElementById("admin-panel").classList.add("d-none");

    // Automatically initialize and start webcam on kiosk
    setTimeout(() => {
      CameraController.startWebcam();
    }, 200);

    if (window.lucide) lucide.createIcons();
    this.updateSignInButtonState();
  },

  updateSignInButtonState() {
    const token = API.getToken();
    const btn = document.getElementById("btn-kiosk-signin");
    if (btn) {
      if (token) {
        btn.innerHTML = `<i data-lucide="layout-dashboard" style="width: 16px;"></i> <span>Admin Portal</span>`;
      } else {
        btn.innerHTML = `<i data-lucide="log-in" style="width: 16px;"></i> <span>Admin Sign In</span>`;
      }
      if (window.lucide) lucide.createIcons();
    }
  },

  showLoginModal() {
    const modalEl = document.getElementById("modal-admin-login");
    if (!modalEl) return;
    const err = document.getElementById("admin-login-error");
    if (err) err.classList.add("d-none");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  },

  showLoginView() {
    this.showLoginModal();
  },

  async showAdminPanel() {
    const token = API.getToken();
    if (!token) {
      this.showLoginModal();
      return;
    }

    // Use cached user if available for instant UI transition
    const cachedUser = API.getUser();
    if (cachedUser) {
      const nameEl = document.getElementById("admin-display-name");
      if (nameEl) nameEl.innerText = cachedUser.name || "Administrator";
      const roleEl = document.getElementById("admin-role-badge");
      if (roleEl) roleEl.innerText = (cachedUser.role || "ADMIN").toUpperCase();
    }

    // Stop kiosk camera stream to avoid multi-stream collisions and free connection
    CameraController.stopWebcam();

    // Force close any open modals & cleanly remove modal backdrops
    const modalEl = document.getElementById("modal-admin-login");
    if (modalEl) {
      const inst = bootstrap.Modal.getInstance(modalEl);
      if (inst) inst.hide();
    }
    document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");

    // Switch panels
    this.currentPanel = "admin";
    document.getElementById("kiosk-panel").classList.add("d-none");
    document.getElementById("admin-panel").classList.remove("d-none");

    // Navigate to admin dashboard
    this.navigateTo(this.currentAdminView || "dashboard");
    this.updateSignInButtonState();
    if (window.lucide) lucide.createIcons();

    // Background verify token
    try {
      const profile = await API.getProfile();
      API.setUser(profile.user);
      const nameEl = document.getElementById("admin-display-name");
      if (nameEl) nameEl.innerText = profile.user.name || "Administrator";
    } catch (err) {
      console.warn("Session check warning:", err);
      if (err.message && err.message.includes("401")) {
        API.clearToken();
        this.updateSignInButtonState();
        this.showLoginModal();
      }
    }
  },

  async handleAdminLogin(event) {
    event.preventDefault();
    const emailInput = document.getElementById("admin-login-email");
    const passInput = document.getElementById("admin-login-password");
    const email = emailInput ? emailInput.value.trim() : "";
    const pass = passInput ? passInput.value : "";
    const btn = document.getElementById("btn-admin-login");
    const errorAlert = document.getElementById("admin-login-error");

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Authenticating...';
    }
    if (errorAlert) errorAlert.classList.add("d-none");

    try {
      const resp = await API.login(email, pass);
      API.setToken(resp.token);
      API.setUser(resp.user);

      // Close modal cleanly and strip backdrops immediately
      const modalEl = document.getElementById("modal-admin-login");
      if (modalEl) {
        const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
        if (modalInstance) modalInstance.hide();
      }
      document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
      document.body.classList.remove("modal-open");
      document.body.style.removeProperty("overflow");
      document.body.style.removeProperty("padding-right");

      // Switch to Admin Panel instantly
      await this.showAdminPanel();
    } catch (err) {
      if (errorAlert) {
        errorAlert.innerText = err.message || "Invalid email or password.";
        errorAlert.classList.remove("d-none");
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="log-in" style="width: 16px;" class="me-1"></i> Sign In to Admin Portal';
        if (window.lucide) lucide.createIcons();
      }
    }
  },

  handleAdminLogout() {
    API.clearToken();
    this.updateSignInButtonState();
    this.showKioskPanel();
  },

  /* ========================================================= */
  /* ADMIN MODULE NAVIGATION                                   */
  /* ========================================================= */
  navigateTo(viewId) {
    this.currentAdminView = viewId;

    // Update sidebar active link
    document.querySelectorAll(".sidebar-nav .nav-link").forEach(link => {
      if (link.getAttribute("data-view") === viewId) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Hide all admin views, show target view
    document.querySelectorAll(".app-view").forEach(v => {
      v.classList.remove("active");
      v.style.display = "none";
    });
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
      target.classList.add("active");
      target.style.display = "block";
    }

    // Stop camera if navigating away from camera / enrollment views to save resources
    if (viewId !== "camera" && viewId !== "enrollment") {
      CameraController.stopWebcam();
      if (window.EnrollmentController && EnrollmentController.stream) {
        EnrollmentController.stopWebcam();
      }
    }

    // View-specific hooks
    if (viewId === "dashboard") {
      this.loadDashboardData();
    } else if (viewId === "students" || viewId === "student-registration" || viewId === "faculty-registration") {
      StudentsController.loadStudents();
    } else if (viewId === "camera") {
      CameraController.startWebcam();
    } else if (viewId === "enrollment") {
      EnrollmentController.startWebcam();
      StudentsController.loadStudents();
    } else if (viewId === "entries") {
      EntriesController.loadEntries();
    } else if (viewId === "unknowns") {
      UnknownsController.loadUnknowns();
    } else if (viewId === "evaluation") {
      EvaluationController.loadLatestResults();
    } else if (viewId === "settings") {
      SettingsController.loadSettings();
    }

    if (window.lucide) lucide.createIcons();
    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  async loadDashboardData() {
    try {
      const resp = await API.getDashboardAnalytics();
      const k = resp.kpis;

      document.getElementById("kpi-registered-students").innerText = k.total_registered_students;
      document.getElementById("kpi-enrolled-biometrics").innerText = k.total_enrolled_biometrics;
      document.getElementById("kpi-entries-today").innerText = k.total_entries_today;
      document.getElementById("kpi-unknowns-today").innerText = k.total_unknowns_today;
      document.getElementById("kpi-avg-rec-time").innerText = `${k.avg_recognition_time_ms} ms`;
      document.getElementById("kpi-db-latency").innerText = `${k.db_latency_ms} ms`;

      this.renderDashboardDailyChart(resp.daily_trends);
      this.renderDashboardDeptChart(resp.department_distribution);
    } catch (err) {
      console.warn("Error fetching dashboard metrics:", err);
    }
  },

  renderDashboardDailyChart(data) {
    const ctx = document.getElementById("chart-dashboard-daily")?.getContext("2d");
    if (!ctx) return;
    if (this.charts.daily) this.charts.daily.destroy();

    this.charts.daily = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Identified Students",
            data: data.identified,
            backgroundColor: "#10b981",
            borderRadius: 6
          },
          {
            label: "Unknown Detections",
            data: data.unknowns,
            backgroundColor: "#ef4444",
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          x: { stacked: true, grid: { color: "rgba(100, 116, 139, 0.15)" } },
          y: { stacked: true, grid: { color: "rgba(100, 116, 139, 0.15)" } }
        }
      }
    });
  },

  renderDashboardDeptChart(data) {
    const ctx = document.getElementById("chart-dashboard-depts")?.getContext("2d");
    if (!ctx) return;
    if (this.charts.depts) this.charts.depts.destroy();

    const colors = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"];

    this.charts.depts = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          backgroundColor: colors.slice(0, data.labels.length)
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "bottom", labels: { color: "#64748b" } }
        }
      }
    });
  },

  startTelemetryPoller() {
    setInterval(async () => {
      try {
        const resp = await API.getSystemMetrics();
        const m = resp.metrics;
        const badges = [document.getElementById("kiosk-db-ping"), document.getElementById("navbar-db-ping")];
        badges.forEach(b => {
          if (b) b.innerHTML = `<span class="badge-pulse"></span> Atlas DB: <strong>${m.db_query_latency_ms} ms</strong>`;
        });
      } catch (e) {
        // quiet fallback
      }
    }, 15000);
  }
};

// Initialize application on DOM loaded
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
