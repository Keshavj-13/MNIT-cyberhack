# Data Portfolio & Social Engineering Evaluation

## 1. Dataset Risk Provider Mapping

| Dataset | Primary Risk Provider Improved | Secondary Providers Improved |
| :--- | :--- | :--- |
| **IEEE-CIS Fraud** | Transaction Risk | Device Trust, Context Risk |
| **ULB Credit Card** | Transaction Risk | N/A |
| **CERT Insider Threat** | Context Risk | Network Risk |
| **LANL Cyber Security** | Network Risk | Context Risk |
| **UMDAA-02 (Biometrics)**| Behavioral Risk | Device Trust |

---

## 2. Dataset Scoring (0-10)

| Dataset | Fraud Value | ATO Value | SE Value | Device Intel | Explainability | Hackathon Demo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **IEEE-CIS Fraud** | 10 | 6 | 2 | 10 | 8 | 9 |
| **ULB Credit Card** | 9 | 1 | 0 | 0 | 6 | 7 |
| **CERT Insider Threat** | 3 | 9 | 4 | 5 | 5 | 5 |
| **LANL Cyber Security** | 2 | 8 | 0 | 2 | 4 | 4 |
| **UMDAA-02** | 5 | 8 | 8 | 9 | 2 | 10 |

*Note: UMDAA-02 scores high in SE value because hesitation, irregular typing cadence, or holding the phone differently are physical indicators of Authorized Push Payment (APP) scams (the victim is on the phone with a scammer).*

---

## 3. Feature Coverage Matrix

| Feature | IEEE CIS | ULB Fraud | CERT | LANL | UMDAA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Transaction amount** | ✓ | ✓ | ❌ | ❌ | ❌ |
| **Beneficiary info** | ✓ | ❌ | ❌ | ❌ | ❌ |
| **Device fingerprint** | ✓ | ❌ | ✓ | ❌ | ✓ |
| **Login history** | ❌ | ❌ | ✓ | ✓ | ❌ |
| **Session info** | ❌ | ❌ | ✓ | ❌ | ✓ |
| **Browser info** | ✓ | ❌ | ❌ | ❌ | ❌ |
| **Geographic info** | ✓ (Masked)| ❌ | ❌ | ❌ | ❌ |
| **User behavior** | ❌ | ❌ | ✓ | ✓ | ✓ |
| **Time patterns** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Network traffic** | ❌ | ❌ | ✓ | ✓ | ❌ |
| **Auth events** | ❌ | ❌ | ✓ | ✓ | ❌ |
| **Account age** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Velocity features** | ✓ (Derived)| ❌ | ✓ (Derived)| ✓ | ❌ |
| **Risk labels** | ✓ | ✓ | ✓ | ✓ | N/A |

---

## 4. The Weakest Risk Provider
**The Context Risk Provider.**
While CERT and LANL provide excellent network and internal login history, they are enterprise IT datasets, not consumer banking datasets. They lack the specific contextual telemetry of a retail banking session (e.g., recipient account age, time since payee added, concurrent active phone call).

---

## 5. Missing Data for Social Engineering Detection
The portfolio fails to directly detect **Authorized Push Payment (APP) Fraud** (where the user is tricked into sending money). Missing data types include:
1.  **Communication Telemetry**: Is the user currently on an active voice call? Have they recently received an SMS with a link?
2.  **Screen Sharing Status**: Is TeamViewer, AnyDesk, or Zoom active during the banking session?
3.  **UI Interaction Anomalies**: Hesitation (dwell time) before hitting "Send," which implies the user is reading instructions or being coached.
4.  **Beneficiary Risk**: Was the destination account created yesterday? (Mule accounts).

---

## 6. Recommended Dataset for Social Engineering
**Dataset**: **SMS Spam Collection Dataset (UCI / Kaggle)** + **Phishing URLs**
*   **Why**: Since real bank-level APP fraud databases are strictly proprietary, the best hackathon approach is to detect the *attack vector* that precipitates the transaction.
*   **Application**: Build a lightweight NLP classification endpoint. If a transaction occurs within 15 minutes of the user's device receiving an SMS matching the "Urgent Bank Alert" profile in this dataset, the Context Risk score spikes to maximum. This is visually stunning for a demo.

---

## 7. Revised Roadmap: The Hackathon-Winning Prototype

**Goal**: Abandon massive, slow academic models. Build a visually impressive, cohesive, and easily explainable prototype that solves a compelling narrative (e.g., Grandma getting scammed).

### Week 1: Core Engine (IEEE-CIS)
1.  **Drop ULB, CERT, and LANL.** They require too much engineering for a demo.
2.  **Focus entirely on IEEE-CIS Fraud.** It merges Transaction and Device data natively.
3.  Train a fast LightGBM model on IEEE-CIS. This instantly powers the **Transaction Risk** and **Device Trust** endpoints with real, explainable data.

### Week 2: The Social Engineering "Hook"
1.  Train a simple NLP model (e.g., TF-IDF + Naive Bayes or a lightweight HuggingFace transformer) on the **SMS Spam Collection Dataset**.
2.  Create a `ContextRiskProvider` that takes in an SMS payload. If it's a scam text, the SE risk score hits `0.95`.

### Week 3: The Ensemble & API
1.  Wire the IEEE-CIS Transaction/Device model and the NLP SMS model into the `EnsembleEngine`.
2.  Final Formula: `0.4*Tx + 0.3*Device + 0.3*SE_Context`.
3.  Finalize the FastAPI endpoints to return SHAP factors (e.g., "High Risk: Transaction initiated 2 minutes after receiving suspected Smishing link").

### Week 4: The UI/Demo
1.  Build a simple frontend (Streamlit, React, or terminal UI).
2.  **The Demo Script**:
    *   *Step 1*: Normal transaction -> ALLOW.
    *   *Step 2*: Scammer sends SMS.
    *   *Step 3*: Victim initiates identical transaction -> BLOCK (Explainability flags the SMS and new device fingerprint).
3.  This narrative-driven approach wins hackathons, whereas showing ROC AUC tables does not.
