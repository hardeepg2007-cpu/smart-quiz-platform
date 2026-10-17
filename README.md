# Smart Quiz Platform – PDF-Based Question & Answer System

A complete, production-ready, interactive web-based quiz platform built with **Python (Flask)** and **Bootstrap 5**, powered by questions extracted from a 12-page NPTEL course assignment PDF (*Introduction to Industry 4.0 and Industrial Internet of Things*).

---

## 1. Project Overview & Features

- **Actual Questions Extracted**: **180 verified questions** across **12 pages / course weeks** (exactly 15 questions per page).
- **Zero Mock / Hardcoded Data**: All question prompts, multiple-choice options, answers, and diagrams come directly from the source document.
- **Server-Side Answer Key Security**: Correct answers and scoring logic live strictly on the server in `answer_key.json`. The frontend never receives correct answers prior to quiz submission, making DevTools answer inspection impossible.
- **Practice Mode vs. Test Mode**:
  - **Full Test Mode**: Simulated examination with countdown timer, 5-min and 1-min warnings, live question palette, auto-submission on expiry, and post-exam score evaluation.
  - **Practice Mode**: Instant question-by-question feedback, answer evaluation, and solution explanations.
- **Custom Quiz Configurations**:
  - Question count: 15, 30, 50, 100, or All 180 questions.
  - Time limits: No Limit, 15m, 30m, 60m, or 90m.
  - Scope: All 12 pages or individual weeks / custom ranges (e.g. Weeks 1-4, 5-8, 9-12).
  - Randomization: Original order vs. randomized questions, and original options vs. option shuffling (server accurately maps shuffled options to the correct answer).
- **Interactive Question Palette**:
  - Live status indicators: Current, Answered (Green), Unanswered (Gray), and Marked for Review (Yellow/Orange).
  - Direct jumping to any question.
  - Filter palette by Answered, Unanswered, or Marked.
- **Keyboard Shortcuts**:
  - `<Left Arrow>` / `<Right Arrow>`: Navigate Previous / Next.
  - `1`, `2`, `3`, `4`: Select Options A, B, C, D.
  - `M`: Toggle Mark for Review.
  - `C`: Clear current answer.
- **Result & Performance Analytics**:
  - Real calculated statistics: Total attempted, Correct, Incorrect, Unanswered, Score, Percentage, Accuracy, and Time taken.
  - Pass/Fail evaluation based on customizable threshold (default 50%).
  - Interactive charts (Accuracy doughnut chart and Week-by-Week performance bar chart).
  - Weak area identification highlighting questions that need further review.
- **Comprehensive Answer Review**:
  - Question-by-question breakdown showing your selected answer, correct answer, status, and explanations.
  - Live search bar and filter pills (All, Correct, Incorrect, Unanswered, Marked).
- **Export & Print**:
  - One-click CSV export of results.
  - Print-ready stylesheet for generating PDF reports directly through browser print (`Ctrl + P`).

---

## 2. PDF Extraction Summary

| Page / Week | Topic Area | Extracted Questions | Verified Answers |
|---|---|:---:|:---:|
| **Page 01** | IoT Fundamentals, Protocols & Sensors | 15 | 15 |
| **Page 02** | Industry 4.0, Steam Engine, ICT & Cyber Systems | 15 | 15 |
| **Page 03** | Cyber-Physical Systems (CPS), Augmented Reality & AI | 15 | 15 |
| **Page 04** | IIoT Security, Malware, Phishing & Architectures | 15 | 15 |
| **Page 05** | Industrial Business Models, Air-as-a-Service & Logistics | 15 | 15 |
| **Page 06** | Sensor Types, Magnetostrictive & Gas Sensing | 15 | 15 |
| **Page 07** | LPWAN, LoRaWAN, CSS, XCTU & Big Data Smart Warehousing | 15 | 15 |
| **Page 08** | Industrial Analytics, Prognostics, FCM, RL & Cloud Platforms | 15 | 15 |
| **Page 09** | Fog Computing, Edge Filtration, Julia, BCube & SDN | 15 | 15 |
| **Page 10** | Software-Defined 6TiSCH, STRIDE Threat Model & OT Security | 15 | 15 |
| **Page 11** | Healthcare IoT, AMI, RFID Tags & Software Security | 15 | 15 |
| **Page 12** | Predictive Maintenance, Chemical Logistics & UAV Applications | 15 | 15 |
| **TOTAL** | **12 Pages Processed** | **180 Questions** | **180 Verified** |

### Special Cases & Integrity Notes:
- **Preserved Diagram**: Page 1 Question 11 includes a block diagram (*Input Signal -> Sensor -> ? -> Actuator -> Output Signal*). The diagram was cropped directly from the source PDF and preserved in `static/images/p01_q11_diagram.png`.
- **True / False Questions**: Page 2 Q7, Page 2 Q8, and Page 4 Q15 are True/False format with 2 options (A. True, B. False).
- **Source Anomaly Documented**: On Page 1 Question 15 (*Which of the following IoT protocols is based on the session layer...*), the printed PDF shows accepted answer text `D. Topics` (a visual carryover from Q14) while the actual question options are `A. MQTT`, `B. CoAP`, `C. AMQP`, `D. DTLS`. The platform faithfully retains option D as printed and flags it with a review note.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, Flask 3.x
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Data Storage**: JSON (`questions.json`, `answer_key.json`, `data/attempts.json`)

---

## 4. Installation and Running on Windows

### Step 1: Open PowerShell or Command Prompt
Navigate to the project root directory:

```powershell
cd smart_quiz_platform
```

### Step 2: Create and Activate Virtual Environment (Recommended)

```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 4: Run the Application

```powershell
python app.py
```

### Step 5: Open in Your Browser
Once running, open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Automated Tests

Run the complete automated test suite (14 test cases covering data integrity, answer key privacy, option shuffling, scoring accuracy, autosave, idempotency, and CSV export):

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

All 14 tests run synchronously in under 1 second.
