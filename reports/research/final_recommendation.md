# Final Recommendation Report

Based on the Dataset Intelligence, Literature Review, and Modeling Strategy phases, this report outlines the recommended approach for the next phase of the project: Intelligent Data Transformation and Model Building.

## 1. What Should Be Built

To achieve a state-of-the-art, hackathon-winning prototype that balances accuracy, explainability, and real-time performance, the following components should be built:

*   **Transaction Fraud Provider**: Implement the **HTGNN-Inspired Hybrid Ensemble** (CatBoost + LightGBM + Isolation Forest). The `CreditCardFraudDetection` dataset provides a clean baseline, but feature engineering (velocity, deviations) is critical. Isotonic regression should be used for calibration to manage the extreme class imbalance.
*   **Social Engineering Provider**: Implement the **Dual-Layer Contextual Ensemble**. Use the `SMS Spam Collection` (and related smishing datasets) to build a fast TF-IDF + XGBoost Layer 1, backed by a deep MLP on sentence embeddings for Layer 2.
*   **Phishing Provider**: Implement the **Lexical-Structural Fusion** model. Use the `PhishingWebsites` and related datasets to extract structural features for a LightGBM model, potentially fused with a character-level CNN.
*   **Network Risk Provider**: Implement the **FCNN-SE Proxy** (LightGBM + TabNet). The `SIMARGL2021` dataset is massive; aggressive sampling, deduplication, and Boruta feature selection are mandatory before training.
*   **Account Takeover Provider**: Implement a **Temporal Anomaly** approach. Use subset splits of the `electricsheepafrica` dataset, focusing on session velocity and device changes.

## 2. What Should NOT Be Built

*   **Vanilla / Untuned Models**: Avoid directly feeding raw datasets into algorithms without domain-specific transformations.
*   **Full Graph Neural Networks (GNNs)**: True GNNs require dedicated graph infrastructure (e.g., Neo4j) which is too complex for this prototype constraint. We will use HTGNN-*inspired* feature aggregation instead.
*   **Massive LLM Inference at the Edge**: Relying entirely on GPT-4/Llama for real-time smishing detection introduces unacceptable latency and cost. The dual-layer approach (fast ML first, semantic embeddings second) is required.
*   **Deep Learning on Trivial Tabular Data**: For simple numeric datasets (like the `banknote-authentication` proxy for Device Trust), complex DL models (like FT-Transformer) overfit and add unnecessary latency. Stick to calibrated Random Forests or LightGBM.

## 3. Estimated Complexity

*   **High Complexity**: Network Risk (due to dataset size and dimensionality reduction), Social Engineering (dual-layer text pipeline).
*   **Medium Complexity**: Transaction Fraud (feature engineering is complex, but modeling is straightforward), Phishing URLs (parsing features from raw URLs).
*   **Low Complexity**: Device Trust (using proxy datasets).

## 4. Expected Performance

Based on the literature review and dataset intelligence:
*   **Transaction Fraud**: Expected ROC AUC > 0.95, but optimized for **PR AUC** and **Recall > 0.80** on highly imbalanced data.
*   **Social Engineering**: Expected F1 > 0.95 due to distinct lexical cues in smishing datasets.
*   **Phishing URLs**: Expected Accuracy > 0.95 with structural features.
*   **Network Risk**: Expected high detection of known signatures, moderate detection of anomalies.
*   **Latency**: The ensemble architecture is designed to keep inference under 50ms per event.

## 5. Deployment Strategy

*   **Provider-Based Architecture**: Each trained pipeline (preprocessing + model + calibration) will be serialized (e.g., using `joblib` for scikit-learn/LightGBM pipelines, or `torch.save` for deep learning components).
*   **FastAPI Integration**: The `RiskEngine` will load these artifacts. When an event occurs, it will pass through the specific preprocessing pipeline of the corresponding provider before inference.
*   **Explainability**: SHAP (TreeExplainer or DeepExplainer) and LIME will be integrated directly into the inference loop to provide the `why_decision` context required for the UI Escalation Levels.

## Awaiting Approval
The dataset intelligence, literature review, and modeling strategy phases are complete. No models have been trained during this phase. The system is ready to proceed to Phase 21 (Intelligent Data Transformation and Model Building) upon user approval.
