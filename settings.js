/**
 * Campus AI - Institutional Settings Controller
 */

const SettingsController = {
  currentSettings: {},

  async loadSettings() {
    try {
      const resp = await API.getSettings();
      if (resp && resp.settings) {
        this.currentSettings = resp.settings;
        this.populateForm(resp.settings);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  },

  populateForm(s) {
    document.getElementById("setting-institution-name").value = s.institution_name || "";
    document.getElementById("setting-campus-location").value = s.campus_location || "";
    document.getElementById("setting-similarity-threshold").value = s.similarity_threshold || 0.68;
    document.getElementById("setting-threshold-val").innerText = s.similarity_threshold || 0.68;
    document.getElementById("setting-cooldown").value = s.cooldown_period_seconds || 30;
    document.getElementById("setting-blur-variance").value = s.min_blur_variance || 75.0;
    document.getElementById("setting-antispoofing").checked = bool(s.anti_spoofing_enabled);

    // Update branding in DOM
    App.updateInstitutionBranding(s.institution_name, s.campus_location);
  },

  async handleSaveSettings(event) {
    event.preventDefault();
    const updates = {
      institution_name: document.getElementById("setting-institution-name").value.trim(),
      campus_location: document.getElementById("setting-campus-location").value.trim(),
      similarity_threshold: parseFloat(document.getElementById("setting-similarity-threshold").value),
      cooldown_period_seconds: parseInt(document.getElementById("setting-cooldown").value),
      min_blur_variance: parseFloat(document.getElementById("setting-blur-variance").value),
      anti_spoofing_enabled: document.getElementById("setting-antispoofing").checked
    };

    try {
      const resp = await API.updateSettings(updates);
      alert("Institutional settings saved successfully!");
      App.updateInstitutionBranding(updates.institution_name, updates.campus_location);
    } catch (err) {
      alert(`Failed to save settings: ${err.message}`);
    }
  }
};

function bool(val) {
  return val === true || val === "true" || val === 1 || val === "1";
}
