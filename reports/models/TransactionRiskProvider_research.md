# Transaction Fraud Provider Research

**Datasets Used**: ULB Credit Card Fraud

**Feature Engineering**: Created Amount deviation, global rolling velocity, temporal (hour), and applied QuantileTransformer to Amount.

### Model: LightGBM
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 0.9749
- **Test PR AUC**: 0.9072
- **Test F1**: 0.9110 (Prec: 0.9355, Rec: 0.8878)
- **Train Time**: 0.14s

### Model: XGBoost
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 0.9809
- **Test PR AUC**: 0.9186
- **Test F1**: 0.9167 (Prec: 0.9362, Rec: 0.8980)
- **Train Time**: 0.25s

### Model: CatBoost
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 0.9797
- **Test PR AUC**: 0.9156
- **Test F1**: 0.9119 (Prec: 0.9263, Rec: 0.8980)
- **Train Time**: 1.37s

### Model: Fraud_Ensemble
- **Train ROC AUC**: 1.0000
- **Test ROC AUC**: 0.9756
- **Test PR AUC**: 0.9181
- **Test F1**: 0.9167 (Prec: 0.9362, Rec: 0.8980)
- **Train Time**: 5.00s

**Winner**: XGBoost (PR AUC: 0.9186)
**Observed Weaknesses**: Highly imbalanced. The ensemble performs well but lacks specific account context due to dataset anonymization.
