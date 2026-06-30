# 7. Research & Training Pipelines

AURA's models are trained and validated offline using a suite of Python scripts before being deployed as `joblib` or `pth` artifacts. The showcase portal makes the results of these pipelines visible to reviewers.

---

## 7.1 Dataset Ecosystem

The platform relies on a variety of open-source datasets mapped to the banking threat context. Each dataset folder (`datasets/<name>/`) contains an `aura_metadata.json` file that describes its mapping.

| Dataset | Provider | Purpose |
|---------|----------|---------|
| **Feedzai BAF** | TransactionRisk | Binary classification of fraudulent transactions using 31 numeric/categorical features. |
| **Phishing Websites** | SocialEngineeringRisk | URL lexical analysis to detect phishing endpoints. |
| **CMU Keystroke** | AccountTakeover | Subject classification based on keystroke dwell and flight timings. |
| **BEACON** | BeaconBehavioral | VarCNN embedding of raw inter-event timing sequences. |

*(Note: Additional datasets like `simargl2021` and `sms_spam_collection` exist in the repository from previous prototype iterations but are not currently used in the active risk providers).*

---

## 7.2 Model Training (`src/train_official_models.py`)

This script trains the core tree-based models and exports them as `joblib` bundles to `models/artifacts/`.

### Behavioral Risk (CMU Keystroke)
1. Loads `DSL-StrongPasswordData.csv`.
2. Frames the problem as binary classification: "Is the current typist subject `s002`?".
3. Trains a `RandomForestClassifier` (100 estimators).
4. Exports `behavioral_risk.joblib`.

### Transaction Risk (Feedzai BAF)
1. Loads a 100k subset of `Base.csv` (for speed).
2. Performs basic label encoding on categorical features.
3. Trains an `XGBClassifier`.
4. Exports `transaction_risk.joblib` and `transaction_features.joblib`.

### URL Phishing Risk
1. Loads `phishing_websites.arff`.
2. Re-maps ARFF classes (`1` = legitimate, `-1` = phishing) to a binary target (`1` = phishing).
3. Trains an `XGBClassifier`.
4. Exports `phishing_url_risk.joblib`.

### Output
The training script also generates a JSON summary of evaluation metrics (Accuracy, F1, ROC-AUC) which is saved to `reports/models/training_summary.json` for the Showcase UI.

---

## 7.3 Model Validation (`src/validate_models.py`)

This script acts as an offline benchmark suite. It runs 5-fold cross-validation on candidate models (Logistic Regression, XGBoost, Random Forest, LightGBM) for a given dataset and outputs detailed performance reports.

### Pipeline
1. Loads data via `pd.read_parquet()`.
2. Initializes models (with fallback wrappers for LightGBM/RandomForest if DLLs fail).
3. Runs `StratifiedKFold` (n=5) cross-validation.
4. Generates a validation report with:
   - `roc_auc_cv`, `f1_cv`, `pr_auc`, `accuracy`, `precision`, `recall`
5. Flags a model as `UNUSABLE` if `roc_auc < 0.60`, else `PASS`.

### Explainability Extraction
During validation, the script also extracts SHAP-like feature importance arrays from the best-performing models and saves them, ensuring that the frontend explainability charts have grounded data to present.

---

## 7.4 BEACON Neural Network

The BEACON model (`models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth`) is handled differently:
- It is a PyTorch deep learning model.
- It was pre-trained using a separate high-compute pipeline (outside this repo).
- The checkpoint contains a `state_dict` representing the VarCNN architecture.
- It is loaded directly by `BeaconBehavioralProvider` in inference mode only.
