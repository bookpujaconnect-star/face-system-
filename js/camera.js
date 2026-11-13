/**
 * Campus AI - Live Camera Monitoring Controller
 * Powers both the Main Entrance Kiosk and the Admin Surveillance View
 */

const CameraController = {
  videoElem: null,
  canvasElem: null,
  ctx: null,
  stream: null,
  isProcessing: false,
  timerId: null,
  activeCameraId: "cam_gate_north",
  activeCameraName: "North Main Entrance - Lane 1",
  soundEnabled: true,
  nightVisionEnabled: false,
  lastDetections: [],

  init() {
    // Select elements based on active panel (Kiosk vs Admin)
    const isKiosk = !document.getElementById("kiosk-panel")?.classList.contains("d-none");
    if (isKiosk) {
      this.videoElem = document.getElementById("kiosk-webcam-video");
      this.canvasElem = document.getElementById("kiosk-camera-canvas");
    } else {
      this.videoElem = document.getElementById("webcam-video") || document.getElementById("kiosk-webcam-video");
      this.canvasElem = document.getElementById("camera-canvas") || document.getElementById("kiosk-camera-canvas");
    }

    if (this.canvasElem) {
      this.ctx = this.canvasElem.getContext("2d");
    }
  },

  async startWebcam() {
    this.init();
    if (!this.videoElem || !this.canvasElem) return;

    try {
      if (this.stream) {
        this.stopWebcam();
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Webcam access requires localhost or HTTPS security context.");
      }

      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });

      // Hide MJPEG image and show canvas
      const mjpegElems = [document.getElementById("kiosk-mjpeg-stream-img"), document.getElementById("mjpeg-stream-img")];
      mjpegElems.forEach(img => {
        if (img) {
          img.src = "";
          img.classList.add("d-none");
        }
      });
      if (this.canvasElem) this.canvasElem.classList.remove("d-none");

      this.videoElem.srcObject = this.stream;
      await this.videoElem.play();

      this.updateStatusPill(`<span class="badge-pulse"></span> LIVE WEBCAM SCANNING`, true);
      this.toggleButtons(true);

      // Start continuous detection loop at ~8-10 FPS
      this.timerId = setInterval(() => this.captureAndProcess(), 120);
    } catch (err) {
      console.warn("Could not access user webcam:", err);
      this.startSimulatedFeed();
    }
  },

  stopWebcam() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElem) {
      this.videoElem.srcObject = null;
    }

    const mjpegElems = [document.getElementById("kiosk-mjpeg-stream-img"), document.getElementById("mjpeg-stream-img")];
    mjpegElems.forEach(img => {
      if (img) {
        img.src = "";
        img.classList.add("d-none");
      }
    });

    this.updateStatusPill("SCANNER PAUSED", false);
    this.toggleButtons(false);

    if (this.ctx && this.canvasElem) {
      this.ctx.clearRect(0, 0, this.canvasElem.width, this.canvasElem.height);
    }
  },

  startSimulatedFeed() {
    this.updateStatusPill(`<span class="badge-pulse"></span> LIVE ENTRANCE GATE STREAM`, true);
    const nv = this.nightVisionEnabled ? "1" : "0";
    const mjpegElems = [document.getElementById("kiosk-mjpeg-stream-img"), document.getElementById("mjpeg-stream-img")];
    mjpegElems.forEach(img => {
      if (img) {
        img.onerror = () => {
          setTimeout(() => {
            if (!img.classList.contains("d-none")) {
              img.src = `/api/camera/current-frame?night_vision=${nv}&t=${Date.now()}`;
            }
          }, 1500);
        };
        img.src = `/api/camera/stream?night_vision=${nv}&t=${Date.now()}`;
        img.classList.remove("d-none");
      }
    });
    if (this.canvasElem) this.canvasElem.classList.add("d-none");
    if (this.videoElem) this.videoElem.classList.add("d-none");
    this.toggleButtons(true);
  },

  updateStatusPill(html, isLive) {
    const pills = [document.getElementById("kiosk-status-pill"), document.getElementById("camera-status-pill")];
    pills.forEach(p => {
      if (p) {
        p.innerHTML = html;
        if (isLive) p.classList.add("live");
        else p.classList.remove("live");
      }
    });
  },

  toggleButtons(isRunning) {
    const startBtns = [document.getElementById("kiosk-btn-start"), document.getElementById("btn-start-camera")];
    const stopBtns = [document.getElementById("kiosk-btn-stop"), document.getElementById("btn-stop-camera")];

    startBtns.forEach(b => {
      if (b) {
        if (isRunning) b.classList.add("d-none");
        else b.classList.remove("d-none");
      }
    });

    stopBtns.forEach(b => {
      if (b) {
        if (isRunning) b.classList.remove("d-none");
        else b.classList.add("d-none");
      }
    });
  },

  toggleNightVision() {
    this.nightVisionEnabled = !this.nightVisionEnabled;
    const btns = [document.getElementById("kiosk-btn-night"), document.getElementById("btn-night-camera")];
    btns.forEach(b => {
      if (b) {
        if (this.nightVisionEnabled) {
          b.classList.remove("btn-outline-warning");
          b.classList.add("btn-warning", "active");
          b.innerHTML = '<i data-lucide="sun" style="width: 14px;"></i> Night Vision ON';
        } else {
          b.classList.remove("btn-warning", "active");
          b.classList.add("btn-outline-warning");
          b.innerHTML = '<i data-lucide="moon" style="width: 14px;"></i> Night Vision';
        }
      }
    });

    const pills = [document.getElementById("kiosk-night-pill"), document.getElementById("camera-night-pill")];
    pills.forEach(p => {
      if (p) {
        if (this.nightVisionEnabled) p.classList.remove("d-none");
        else p.classList.add("d-none");
      }
    });

    // If currently viewing simulated live stream, refresh stream URL with night_vision parameter
    const mjpegElems = [document.getElementById("kiosk-mjpeg-stream-img"), document.getElementById("mjpeg-stream-img")];
    const nv = this.nightVisionEnabled ? "1" : "0";
    let isStreamActive = false;
    mjpegElems.forEach(img => {
      if (img && !img.classList.contains("d-none")) {
        isStreamActive = true;
        img.src = `/api/camera/stream?night_vision=${nv}&t=${Date.now()}`;
      }
    });

    // If stream is not active and physical webcam is not active, auto-start the live stream with the chosen night vision state
    if (!isStreamActive && !this.stream) {
      this.startSimulatedFeed();
    }

    if (window.lucide) lucide.createIcons();
  },

  async captureAndProcess() {
    if (this.isProcessing || !this.videoElem || this.videoElem.readyState < 2) return;
    this.isProcessing = true;

    try {
      const vw = this.videoElem.videoWidth || 640;
      const vh = this.videoElem.videoHeight || 480;

      this.canvasElem.width = vw;
      this.canvasElem.height = vh;

      // Draw current video frame to canvas
      this.ctx.drawImage(this.videoElem, 0, 0, vw, vh);

      // Export base64 jpeg
      const b64 = this.canvasElem.toDataURL("image/jpeg", 0.75);

      const resp = await API.processFrame(b64, this.activeCameraId, this.activeCameraName, this.nightVisionEnabled);
      if (resp && resp.results) {
        this.renderDetections(
          resp.results,
          vw,
          vh,
          resp.total_frame_latency_ms,
          resp.fps_estimate,
          resp.night_vision_active,
          resp.ambient_brightness
        );
      }
    } catch (err) {
      console.error("Frame processing error:", err);
    } finally {
      this.isProcessing = false;
    }
  },

  renderDetections(results, vw, vh, totalLatency, fps, nightActive, ambientLux) {
    // Redraw frame
    this.ctx.drawImage(this.videoElem, 0, 0, vw, vh);

    const isNightActive = nightActive || this.nightVisionEnabled;

    // Optional night vision phosphorescence effect on canvas
    if (isNightActive) {
      this.ctx.fillStyle = "rgba(16, 185, 129, 0.08)";
      this.ctx.fillRect(0, 0, vw, vh);
      this.ctx.fillStyle = "#10b981";
      this.ctx.font = "bold 11px monospace";
      this.ctx.fillText(`⚡ NIGHT VISION ACTIVE | AMBIENT: ${ambientLux ? ambientLux.toFixed(0) : 40} LUX`, 16, vh - 16);
    }

    // Update HUD metrics on both panels
    const fpsBadges = [document.getElementById("kiosk-fps-pill"), document.getElementById("camera-fps-pill")];
    fpsBadges.forEach(b => { if (b) b.innerText = `${fps || 12} FPS`; });

    const latBadges = [document.getElementById("kiosk-lat-pill"), document.getElementById("camera-lat-pill")];
    latBadges.forEach(b => { if (b) b.innerText = `${totalLatency || 60} ms`; });

    const nightPills = [document.getElementById("kiosk-night-pill"), document.getElementById("camera-night-pill")];
    nightPills.forEach(p => {
      if (p) {
        if (isNightActive) {
          p.classList.remove("d-none");
          p.innerHTML = `<i data-lucide="moon" style="width: 12px; height: 12px;"></i> NIGHT VISION ON`;
        } else if (!this.nightVisionEnabled) {
          p.classList.add("d-none");
        }
      }
    });

    results.forEach(res => {
      const [x, y, w, h] = res.bbox;
      const isIdentified = (res.status === "Identified" && res.student);

      // Color scheme: Emerald green for identified, Crimson red for unknown
      const strokeColor = isIdentified ? "#10b981" : "#ef4444";
      const bgColor = isIdentified ? "rgba(16, 185, 129, 0.90)" : "rgba(239, 68, 68, 0.90)";

      // Draw bounding box
      this.ctx.strokeStyle = strokeColor;
      this.ctx.lineWidth = 4;
      this.ctx.strokeRect(x, y, w, h);

      // Corner accent markers
      const cLen = Math.min(20, Math.floor(w * 0.2));
      this.ctx.lineWidth = 6;
      this.ctx.beginPath();
      // Top-left
      this.ctx.moveTo(x, y + cLen); this.ctx.lineTo(x, y); this.ctx.lineTo(x + cLen, y);
      // Top-right
      this.ctx.moveTo(x + w - cLen, y); this.ctx.lineTo(x + w, y); this.ctx.lineTo(x + w, y + cLen);
      // Bottom-left
      this.ctx.moveTo(x, y + h - cLen); this.ctx.lineTo(x, y + h); this.ctx.lineTo(x + cLen, y + h);
      // Bottom-right
      this.ctx.moveTo(x + w - cLen, y + h); this.ctx.lineTo(x + w, y + h); this.ctx.lineTo(x + w, y + h - cLen);
      this.ctx.stroke();

      // Label text
      let label = "";
      if (isIdentified) {
        label = `✓ SIGNED IN: ${res.student.name} • ${res.student.reg_no} (${(res.similarity_score * 100).toFixed(0)}%)`;
      } else {
        label = `⚠ Unknown Person (${(res.similarity_score * 100).toFixed(0)}%)`;
      }

      this.ctx.font = "bold 14px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto";
      const textWidth = this.ctx.measureText(label).width;

      // Draw label background pill
      this.ctx.fillStyle = bgColor;
      this.ctx.fillRect(x, Math.max(0, y - 28), textWidth + 18, 26);

      // Draw text
      this.ctx.fillStyle = "#ffffff";
      this.ctx.fillText(label, x + 8, Math.max(18, y - 10));

      // Push detection to live feeds only if newly logged or throttled (prevents spamming 10x/sec)
      if (this.shouldPushFeed(res)) {
        this.pushRecentDetection(res);
      }
    });
  },

  recentPushedTimes: {},

  shouldPushFeed(res) {
    if (res.event_logged) return true;
    const now = Date.now();
    if (res.status === "Identified" && res.student) {
      const sid = res.student.student_id;
      const last = this.recentPushedTimes[sid] || 0;
      if (now - last > 10000) {
        this.recentPushedTimes[sid] = now;
        return true;
      }
      return false;
    } else {
      const lastUnk = this.recentPushedTimes["_unknown_"] || 0;
      if (now - lastUnk > 8000) {
        this.recentPushedTimes["_unknown_"] = now;
        return true;
      }
      return false;
    }
  },

  pushRecentDetection(res) {
    const lists = [document.getElementById("kiosk-detections-list"), document.getElementById("live-detections-list")];
    const isId = (res.status === "Identified" && res.student);
    const nowStr = new Date().toLocaleTimeString();

    lists.forEach(list => {
      if (!list) return;

      const item = document.createElement("div");
      item.className = `recognition-alert-card ${isId ? 'identified' : 'unknown'}`;

      if (isId) {
        item.innerHTML = `
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge badge-custom badge-success">✓ SIGNED IN</span>
                <span class="fw-bold">${res.student.name}</span>
              </div>
              <div class="small text-muted mt-1">
                <span><strong>Reg:</strong> ${res.student.reg_no}</span> • 
                <span>${res.student.department}</span>
              </div>
              <div class="small text-muted mt-1">
                <span>Confidence: <strong>${(res.similarity_score * 100).toFixed(1)}%</strong></span> • 
                <span>Speed: ${res.total_face_latency_ms} ms</span>
              </div>
              ${res.event_logged ? '<div class="text-success small mt-1 fw-bold">✓ Campus Entry Signed In & Logged</div>' : '<div class="text-success small mt-1">✓ Student Verified & Entry Granted</div>'}
            </div>
            <span class="text-muted small">${nowStr}</span>
          </div>
        `;
      } else {
        item.innerHTML = `
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge badge-custom badge-danger">UNKNOWN</span>
                <span class="fw-bold">Unmatched Face</span>
              </div>
              <div class="small text-muted mt-1">
                Best match similarity: <strong>${(res.similarity_score * 100).toFixed(1)}%</strong>
              </div>
              <div class="small text-muted mt-1">
                Logged for manual officer review.
              </div>
            </div>
            <span class="text-muted small">${nowStr}</span>
          </div>
        `;
      }

      list.insertBefore(item, list.firstChild);
      while (list.children.length > 8) {
        list.removeChild(list.lastChild);
      }
    });
  },

  handleTestFileUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    this.stopWebcam();
    this.init();

    const mjpegElems = [document.getElementById("kiosk-mjpeg-stream-img"), document.getElementById("mjpeg-stream-img")];
    mjpegElems.forEach(img => {
      if (img) {
        img.src = "";
        img.classList.add("d-none");
      }
    });
    if (this.canvasElem) this.canvasElem.classList.remove("d-none");

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = async () => {
        const vw = img.width || 640;
        const vh = img.height || 480;
        this.canvasElem.width = vw;
        this.canvasElem.height = vh;
        this.ctx.drawImage(img, 0, 0, vw, vh);

        this.updateStatusPill(`<span class="badge-pulse"></span> PROCESSING TEST IMAGE`, true);

        try {
          const resp = await API.processFrame(
            e.target.result,
            this.activeCameraId,
            this.activeCameraName,
            this.nightVisionEnabled
          );
          if (resp && resp.results) {
            this.renderDetections(
              resp.results,
              vw,
              vh,
              resp.total_frame_latency_ms,
              resp.fps_estimate,
              resp.night_vision_active,
              resp.ambient_brightness
            );
            this.updateStatusPill(`SCANNED: ${resp.faces_count} FACE(S)`, true);
          }
        } catch (err) {
          console.error("Test image scan error:", err);
          this.updateStatusPill("SCAN FAILED", false);
        }
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }
};
