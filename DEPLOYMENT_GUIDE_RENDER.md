# Complete Step-by-Step Guide: Deploying to Render (Render.com)

This guide walks you through deploying the **AI-Based Student Identification and Campus Entry Monitoring System** to [Render](https://render.com).

---

## 1. Prerequisites Checklist

Before deploying, ensure you have:
1. A **GitHub** account (https://github.com).
2. A **Render** account (https://render.com) — free sign up using your GitHub account.
3. Your **MongoDB Atlas Connection URI**:
   ```
   mongodb+srv://arnnavpanda_db_user:motupanda@cluster0.ncj9dnd.mongodb.net/?appName=Cluster0
   ```
4. **MongoDB Atlas IP Access**:
   - Go to [MongoDB Atlas](https://cloud.mongodb.com/) > **Network Access**.
   - Ensure `0.0.0.0/0` (Allow Access from Anywhere) is active so Render's cloud servers can connect to your database.

---

## 2. Push Your Code to GitHub

Open your terminal in this project folder (`/Users/arnnavpanda/Desktop/Research`):

```bash
# 1. Initialize git repository (if not already initialized)
git init

# 2. Add all files (the created .gitignore will automatically exclude venv, .env, static/uploads/ photos, and caches)
git add .

# 3. Create initial commit
git commit -m "Production release: AI-Based Student Identification & Campus Entry Monitoring System"

# 4. Link to your GitHub repository
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>.git

# 5. Push code to GitHub
git push -u origin main
```

---

## 3. Deploying on Render (Two Easy Methods)

### Method A: Automatic Deployment using Render Blueprint (`render.yaml`) (Recommended)

1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** at the top right and select **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically detect [`render.yaml`](./render.yaml).
5. Enter your `MONGO_URI`:
   ```
   mongodb+srv://arnnavpanda_db_user:motupanda@cluster0.ncj9dnd.mongodb.net/?appName=Cluster0
   ```
6. Click **Apply**. Render will automatically build the environment, install dependencies, and launch the service!

---

### Method B: Manual Web Service Setup (Step-by-Step)

If you prefer to configure it manually in the Render dashboard:

1. In Render Dashboard, click **New +** > **Web Service**.
2. Select **Build and deploy from a Git repository** and pick your repository.
3. Configure the following fields:

| Field | Value to Enter |
| :--- | :--- |
| **Name** | `campus-facial-id-system` (or any name you prefer) |
| **Region** | `Oregon (US West)` or closest to your location |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |
| **Instance Type** | `Free` (or Starter for 24/7 dedicated RAM) |

4. Scroll down to **Environment Variables** and add the following keys:

| Environment Variable Key | Value |
| :--- | :--- |
| `PYTHON_VERSION` | `3.10.12` |
| `MONGO_URI` | `mongodb+srv://arnnavpanda_db_user:motupanda@cluster0.ncj9dnd.mongodb.net/?appName=Cluster0` |
| `DB_NAME` | `campus_facial_id_db` |
| `SECRET_KEY` | `campus_ai_super_secret_jwt_key_2026_x89q2` (or click Generate) |
| `DEBUG` | `False` |
| `DEFAULT_INSTITUTION_NAME` | `Institute` |
| `DEFAULT_CAMPUS_LOCATION` | `Main Campus, North Gate` |
| `DEFAULT_ADMIN_EMAIL` | `admin@institution.edu` |
| `DEFAULT_ADMIN_PASSWORD` | `AdminSecure2026!` |
| `SIMILARITY_THRESHOLD` | `0.68` |
| `COOLDOWN_PERIOD_SECONDS` | `30` |
| `ANTI_SPOOFING_ENABLED` | `True` |

5. Under **Advanced Settings**:
   - **Health Check Path**: `/api/health`
6. Click **Create Web Service**.

---

## 4. Why `--workers 1 --threads 4` is Crucial on Render Free Tier

- Render's Free tier provides **512 MB of RAM**.
- Deep learning architectures (YOLOv8 + FaceNet Inception-ResNet-V1) require ~320 MB to reside in memory.
- Running multiple Gunicorn workers (e.g. `workers 4`) would duplicate the neural network into 4 separate processes, consuming $4 \times 320\text{ MB} = 1.28\text{ GB}$ and causing a **Linux Out-Of-Memory (OOM) / Process Killed** crash.
- With `--workers 1 --threads 4`, **only ONE instance of the AI model is loaded into RAM**, and all 4 threads share the weights and embedding cache concurrently. This ensures 100% stability well within Render's free tier limits!

---

## 5. Post-Deployment Verification

Once Render displays **"Live"** with a green checkmark:

1. Click your Render app URL (e.g., `https://campus-facial-id-system.onrender.com`).
2. **Kiosk Panel Verification**:
   - The Public Entrance Camera Feed will load immediately.
   - Click **"Live Stream"** to confirm simulated gate streaming.
   - Click **"Night Vision"** to verify tactical low-light contrast enhancement.
3. **Admin Sign In**:
   - Click **"Admin Sign In"** at the top right.
   - Click **"Auto-Fill Default Credentials"** (`admin@institution.edu` / `AdminSecure2026!`).
   - Sign in to verify full access to:
     - Main Surveillance Dashboard
     - Student & Faculty Directory
     - Faculty Registration
     - Unknown Person Monitoring (with **Delete All** button)
     - Empirical Benchmark Suite
     - Institutional System Settings

---

## 6. Keeping the Free Tier Active (Optional)

Render's free tier spins down after 15 minutes of inactivity (taking ~30 seconds to wake up on the next request). To keep it awake 24/7 for live presentations or research defense:
- Set up a free HTTP ping on [Cron-Job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) to ping your `/api/health` endpoint every 10 minutes.
