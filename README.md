# 💊 GenuineRx: Generic Medicine & Price Intelligence Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.2.0-646CFF.svg?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Robot Framework](https://img.shields.io/badge/Robot_Framework-7.0+-000000.svg?style=flat-square&logo=robot-framework&logoColor=white)](https://robotframework.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

> **GenuineRx** is an intelligent, privacy-first healthcare intelligence platform designed to tackle high out-of-pocket medicine expenses in India. It pairs an offline, deterministic pharmaceutical matching engine with computer vision (OCR + Barcode recognition), dynamic multi-channel price tracking (Jan Aushadhi, Apollo, 1mg, PharmEasy, Netmeds), and robotic process automation (RPA) test-and-scrape suites.

---

## 📑 Table of Contents

- [Key Highlights & Features](#-key-highlights--features)
- [System Architecture & Boundaries](#-system-architecture--boundaries)
- [Core Modules Breakdown](#-core-modules-breakdown)
  - [1. Deterministic Matching Engine](#1-deterministic-matching-engine)
  - [2. Computer Vision & OCR Resolver](#2-computer-vision--ocr-resolver)
  - [3. RPA & Price Intelligence Layer](#3-rpa--price-intelligence-layer)
  - [4. Safety & Caution Protocol](#4-safety--caution-protocol)
  - [5. Patient & Family Savings Dashboard](#5-patient--family-savings-dashboard)
- [Technology Stack](#-technology-stack)
- [Repository Structure](#-repository-structure)
- [Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Backend Setup & Migrations](#backend-setup--migrations)
  - [Database Seeding](#database-seeding)
  - [Frontend Setup](#frontend-setup)
- [Running Test Suites](#-running-test-suites)
  - [Unit & Integration Tests (Pytest)](#unit--integration-tests-pytest)
  - [Robot Framework RPA Suites](#robot-framework-rpa-suites)
- [API Reference](#-api-reference)
- [Safety & Medical Disclaimer](#-safety--medical-disclaimer)
- [License](#-license)

---

## 🌟 Key Highlights & Features

- 🎯 **Salt-Equivalence Resolution**: Order-independent, canonical salt-set equivalence matcher for single and multi-salt combination therapies (e.g., *Amoxicillin + Clavulanic acid*).
- 🏷️ **Jan Aushadhi Prioritization**: Ranks government-subsidized *Pradhan Mantri Bhartiya Janaushadhi Pariyojana* (PMBJP) alternatives first, yielding up to **85%+ savings**.
- 📸 **Edge Vision / Offline Prescription Resolver**: Offline image processing pipeline with CLAHE contrast enhancement, deskewing, and direct 1D/2D barcode detection before falling back to local Tesseract OCR + `rapidfuzz` scoring.
- 🤖 **Automated RPA Price Intelligence**: Headless browser automation and data integrity pipelines built with **Robot Framework** to track multi-pharmacy price variances, spot artificial price inflation ("fake discounts"), and maintain catalog freshness.
- 🛡️ **Built-in Narrow Therapeutic Index (NTI) Safeguards**: Auto-flags high-risk medications (e.g., Warfarin, Levothyroxine, Lithium, Digoxin) with mandatory medical advisories and pharmacist consultation warnings.
- 👨‍👩‍👧‍👦 **Family Profile & Spend Tracker**: Chronic medication tracking categorized by family members, computing recurring monthly expenditure savings in real time.

---

## 📐 System Architecture & Boundaries

The architecture enforces strict separation of concerns to guarantee determinism, low latency, and zero data leakage:

```mermaid
flowchart TD
    subgraph UI ["Client & Presentation Layer"]
        A[React 18 + Vite Web App]
        B[Prescription Upload / Barcode Scanner]
    end

    subgraph API ["Application / Gateway Layer (FastAPI)"]
        C[FastAPI Orchestrator]
        C --> D[Input Validation / Pydantic]
    end

    subgraph OFFLINE_CORE ["Deterministic Core (Zero Network Call)"]
        E[OCR & Barcode Pipeline<br/><i>OpenCV + Tesseract + RapidFuzz</i>]
        F[Matching Engine<br/><i>Salt Normalizer + Combination Ranker</i>]
    end

    subgraph RPA ["Automation / RPA Layer (Robot Framework)"]
        G[Scheduled Scraping Workflows]
        H[Data Sanity & Regression Suites]
        I[Jan Aushadhi PDF Parser]
    end

    subgraph DB ["Data Layer"]
        J[(PostgreSQL 16+<br/>Medicines, Salts, Price History, Profiles)]
        K[(Redis Hot-path Cache)]
    end

    A <-->|REST API| C
    B -->|Multipart / Form-Data| C
    C --> E
    C --> F
    F <--> J
    F <--> K
    G -->|Asynchronous Batch Upsert| J
    H -->|Synthetic Testing| C
```

### 🔒 Hard Architectural Invariants
1. **Zero Network Calls in Core Matching**: The `matching_engine` is composed of pure deterministic functions executing against PostgreSQL/Redis. It never invokes third-party LLMs or external network APIs on the hot path.
2. **Offline Vision Processing**: OCR and Barcode recognition run entirely on local binary pipelines (`pytesseract`, `cv2`), preventing health data from being exfiltrated to external cloud OCR APIs.
3. **Decoupled Automation Scraping**: Robot Framework test and scrape suites execute asynchronously on schedules. User search requests *never* trigger synchronous live web scraping.

---

## 🔬 Core Modules Breakdown

### 1. Deterministic Matching Engine
Located in [`matching_engine/`](matching_engine/):
- **Strength Normalization**: Standardizes dosage representations across varied naming conventions (`500 mg` $\to$ `500mg`, `0.5 g` $\to$ `500mg`, `10 mcg` $\to$ `0.01mg`).
- **Canonical Salt Normalization**: Normalizes chemical variant names (e.g., *Metformin Hydrochloride* $\to$ *Metformin*).
- **Set-Based Equivalence**: Treats multi-salt formulations as unordered sets to guarantee that `Salt A + Salt B` matches `Salt B + Salt A`.
- **Ranking Formula**: Sorts results with PMBJP generics first, followed by ascending cost per unit:
  $$\text{Order} = (\text{is\_jan\_aushadhi DESC}, \text{price\_per\_unit ASC})$$

### 2. Computer Vision & OCR Resolver
Located in [`ocr_resolver/`](ocr_resolver/):
- **Preprocessing Pipeline**: Auto-deskew via minimum area bounding rectangle and CLAHE (Contrast Limited Adaptive Histogram Equalization) for handwritten or wrinkled prescription strips.
- **Barcode Shortcut**: OpenCV Barcode Detector identifies EAN-13/UPC codes directly from medicine packaging, skipping OCR computation whenever feasible.
- **Fuzzy Token Matching**: Employs Levenshtein and token-set ratio scoring against pre-indexed brand names with confidence thresholding ($\ge 80\%$ auto-select, $50\text{--}79\%$ human-confirmation required).

### 3. RPA & Price Intelligence Layer
Located in [`rpa/`](rpa/):
- Built on **Robot Framework** using custom Python keyword extensions (`rpa/keywords/`).
- **Fake Discount Detector**: Implements SQL window functions over 14-day trailing price histories to flag synthetic discounts where baseline prices spiked $>20\%$ prior to a promotional mark-down.
- **TestSuite Automation**:
  - `smoke.robot`: API health and roundtrip validation.
  - `regression.robot`: Complex combination drug substitution verification.
  - `data_sanity.robot`: Database constraint, orphan key, and negative price checks.
  - `end_to_end.robot`: Full user journey execution from image ingestion to savings calculation.
  - `price_drop_alert.robot`: Email alert bot — detects price drops and Jan Aushadhi alternatives, emails users once per event (see below).

#### 📧 Price-Drop & Jan Aushadhi Email Alert Bot
Code: [`rpa/alerts/`](rpa/alerts/) · Suite: [`price_drop_alert.robot`](rpa/suites/price_drop_alert.robot)

Emails each user one digest when a tracked medicine's price drops, or a cheaper Jan Aushadhi medicine with the *identical salt + strength* exists. `alert_log` guarantees each alert is sent only once; high-risk (caution-list) salts get a "consult your doctor" warning. It also runs as step 5 of the nightly `scheduler_entry.py` pipeline.

```bash
alembic upgrade head                                   # adds users.email + alert_log (the bot also self-creates them)
python -m rpa.alerts.price_alert_bot --reset           # demo: forget sent alerts
python -m rpa.alerts.price_alert_bot --simulate-drop Crocin --pct 20   # fake a scraper finding a cheaper price
robot -d rpa/logs/alerts rpa/suites/price_drop_alert.robot
```
- **Zero-config demo mode:** with no SMTP settings, emails are saved as HTML in `rpa/outbox/` — open in a browser.
- **Real email (Gmail):** set `GENUINE_RX_SMTP_USER`, `GENUINE_RX_SMTP_PASSWORD` (a Google *App Password*) and `GENUINE_RX_ALERT_TO_EMAIL` (your inbox) in `.env`, then verify with `python -m rpa.alerts.price_alert_bot --test-email you@gmail.com`.
- Per-user addresses: `PUT /api/v1/users/{id}/email` or `--set-email USER_ID EMAIL`.

### 4. Safety & Caution Protocol
- Built-in clinical safety filter identifies medications with narrow therapeutic indices (e.g., *Warfarin*, *Levothyroxine*, *Carbamazepine*, *Digoxin*, *Theophylline*).
- Automatically sets `requires_exact_brand = true` and generates safety banners prohibiting brand switching without direct physician supervision.

### 5. Patient & Family Savings Dashboard
- Modern React SPA built with **Tailwind CSS**, featuring dark/light aesthetics, interactive search, file drag-and-drop OCR, interactive savings breakdown, and profile-based chronic medication monitoring.

---

## 🛠️ Technology Stack

| Domain | Technologies & Libraries |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| **Database & ORM** | PostgreSQL 16+, SQLAlchemy 2.0, Alembic |
| **Algorithm & Matching** | RapidFuzz, NumPy, Custom Salt Parsing Engine |
| **Computer Vision / OCR**| OpenCV (`cv2`), PyTesseract, Tesseract OCR Engine |
| **Automation / RPA** | Robot Framework 7+, Selenium / Requests, Custom Python Keywords |
| **Frontend SPA** | React 18, Vite, Tailwind CSS, Lucide React |
| **Testing & Quality** | Pytest, Pytest-Asyncio, HTTPX, Robot Framework Report Generator |

---

## 📂 Repository Structure

```tree
genuine-rx/
├── alembic/                 # Database schema migrations
│   └── versions/            # Version migration scripts
├── api/                     # FastAPI backend application
│   ├── database.py          # SQLAlchemy session & engine lifecycle
│   ├── main.py              # Application entrypoint & CORS configuration
│   ├── models.py            # Relational database models (ORM)
│   └── routes.py            # API route controllers & endpoints
├── docs/                    # Technical architecture & engineering specifications
│   ├── 01_ARCHITECTURE.md
│   ├── 03_DATA_MODEL.md
│   ├── 04_API_CONTRACT.md
│   └── 05_ROBOT_FRAMEWORK_SPEC.md
├── frontend/                # React + Vite + Tailwind CSS dashboard
│   ├── src/
│   │   ├── components/      # UI components (SearchBar, SubstituteList, TrackedMedicines)
│   │   ├── App.jsx          # Root application container
│   │   └── index.css        # Global CSS & Tailwind imports
│   ├── index.html
│   └── vite.config.js
├── matching_engine/         # Deterministic salt equivalence & ranking engine
│   ├── matcher.py           # Core matching algorithm
│   ├── normalizer.py        # Salt and dosage strength sanitization
│   ├── ranker.py            # Substitute ranking and savings calculation
│   └── types.py             # Domain dataclasses & schemas
├── ocr_resolver/            # Offline Computer Vision & OCR pipeline
│   ├── barcode.py           # OpenCV barcode scanning module
│   ├── image_prep.py        # CLAHE, grayscale, & deskew filters
│   ├── ocr.py               # Tesseract OCR invocation
│   └── pipeline.py          # End-to-end vision coordinator
├── rpa/                     # Robot Framework automation & test suites
│   ├── keywords/            # Custom Python keywords (scraping, delivery, validation)
│   ├── suites/              # Robot test suites (smoke, regression, data_sanity, end_to_end)
│   └── scheduler_entry.py   # Background job trigger
├── tests/                   # Automated unit & integration test suites
│   ├── test_api.py          # FastAPI endpoint integration tests
│   ├── test_matcher.py      # Substitution equivalence tests
│   ├── test_normalizer.py   # Salt & strength parsing tests
│   └── test_ocr_resolver.py # Vision pipeline unit tests
├── .env.example             # Template for environment variables
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # Python package metadata
├── requirements-core.txt    # Core backend requirements
├── requirements-rpa.txt     # Robot Framework requirements
└── seed.py                  # High-fidelity pharmaceutical dataset seeder
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **PostgreSQL 15+** running locally or via Docker
- *(Optional)* **Tesseract OCR**: Installed and added to system path (for OCR features)

### Backend Setup & Migrations

1. **Clone the repository**:
   ```bash
   git clone https://github.com/samarthrbhatt10/genuine-rx.git
   cd genuine-rx
   ```

2. **Set up Python Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements-core.txt -r requirements-rpa.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (refer to [`.env.example`](.env.example)):
   ```ini
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genuine_rx
   SECRET_KEY=your_secure_random_key_here
   DEBUG=True
   ```

5. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

### Database Seeding
Populate the database with representative branded medicines, Jan Aushadhi generic equivalents, salts, and realistic multi-pharmacy price histories:
```bash
python seed.py
```

6. **Start the FastAPI Server**:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Interactive Swagger documentation will be available at: `http://localhost:8000/docs`

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node modules**:
   ```bash
   npm install
   ```

3. **Launch Vite Development Server**:
   ```bash
   npm run dev
   ```
   Open your browser at: `http://localhost:5173`

---

## 🧪 Running Test Suites

### Unit & Integration Tests (Pytest)
Run all backend unit tests covering the matching engine, dosage normalizer, OCR pipeline, and API endpoints:
```bash
pytest -v
```

### Robot Framework RPA Suites
Run automated RPA suites to validate data sanity, regression capabilities, and end-to-end flows:

```bash
# Run all Robot Framework suites with HTML test reports generated in rpa/logs/
python -m robot --outputdir rpa/logs/regression rpa/suites/regression.robot
python -m robot --outputdir rpa/logs/smoke rpa/suites/smoke.robot
python -m robot --outputdir rpa/logs/sanity rpa/suites/data_sanity.robot
python -m robot --outputdir rpa/logs/e2e rpa/suites/end_to_end.robot
```

---

## 📡 API Reference

### 1. Medicine Search & Autocomplete
```http
GET /api/v1/medicines/search?q={query}&limit=10
```
**Sample Response**:
```json
[
  {
    "id": "med_aug625",
    "brand_name": "Augmentin 625 Duo Tablet",
    "manufacturer": "GlaxoSmithKline Pharmaceuticals Ltd",
    "mrp": 204.50,
    "dosage_form": "tablet",
    "is_jan_aushadhi": false,
    "salts": [
      { "name": "Amoxicillin", "strength": "500mg" },
      { "name": "Clavulanic Acid", "strength": "125mg" }
    ]
  }
]
```

### 2. Generic Substitutes & Savings
```http
GET /api/v1/medicines/{medicine_id}/substitutes
```
**Sample Response**:
```json
{
  "original_medicine": {
    "brand_name": "Augmentin 625 Duo Tablet",
    "mrp": 204.50
  },
  "caution_flag": null,
  "substitutes": [
    {
      "id": "med_ja_amox_clav_625",
      "brand_name": "Amoxycillin and Potassium Clavulanate Tablets IP 625mg",
      "manufacturer": "Jan Aushadhi (PMBJP)",
      "mrp": 38.00,
      "is_jan_aushadhi": true,
      "savings_percentage": 81.42,
      "savings_rupees": 166.50
    }
  ],
  "disclaimer": "Always consult a registered medical practitioner or pharmacist before substituting any medication."
}
```

### 3. OCR Prescription Ingestion
```http
POST /api/v1/ocr/resolve
Content-Type: multipart/form-data

file: [prescription_image.png / jpeg]
```

---

## ⚠️ Safety & Medical Disclaimer

> **IMPORTANT MEDICAL NOTICE**:
> GenuineRx is an educational and technological decision-support tool. It matches medicines based on chemical salt composition, form, and dosage equivalence according to published pharmacological databases.
>
> 1. **Do not alter prescriptions independently.** Always consult a licensed medical practitioner or registered pharmacist before switching from a prescribed brand to a generic alternative.
> 2. **Narrow Therapeutic Index (NTI) Drugs:** Patients prescribed critical-dose medications (e.g., antiepileptics, blood thinners, thyroid hormones, or immunosuppressants) should never substitute brands without direct medical oversight.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).