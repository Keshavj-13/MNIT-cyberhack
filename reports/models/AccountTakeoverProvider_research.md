# Account Takeover Provider Research

**Datasets Used**: Africa Social Media Account Takeover

**Feature Engineering**: Engineered Isolation Forest anomaly scores to represent behavioral deviations. (Mocked session features where data lacked true session telemetry).

### Model: RandomForest
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 1.0000
- **Test F1**: 0.9980 (Prec: 1.0000, Rec: 0.9960)
- **Train Time**: 0.18s

### Model: XGBoost
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 1.0000
- **Test F1**: 1.0000 (Prec: 1.0000, Rec: 1.0000)
- **Train Time**: 0.26s

### Model: CatBoost
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 1.0000
- **Test F1**: 1.0000 (Prec: 1.0000, Rec: 1.0000)
- **Train Time**: 1.10s

**Winner**: XGBoost (F1: 1.0000)
**Observed Weaknesses**: Dataset lacks true high-frequency sequential session data.
