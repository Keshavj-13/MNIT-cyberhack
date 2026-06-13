# Device Trust Provider Research

**Datasets Used**: Banknote Authentication (Proxy for Device Verification)

**Feature Engineering**: Engineered Isolation Forest anomaly scores and KNN mean distance metrics to represent hardware identity deviation.

### Model: RandomForest
- **Train AUC**: 1.0000
- **Test AUC**: 1.0000
- **Test F1**: 1.0000 (Prec: 1.0000, Rec: 1.0000)
- **Train Time**: 0.14s

### Model: XGBoost
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9959 (Prec: 1.0000, Rec: 0.9918)
- **Train Time**: 0.11s

### Model: CatBoost
- **Train AUC**: 1.0000
- **Test AUC**: 1.0000
- **Test F1**: 1.0000 (Prec: 1.0000, Rec: 1.0000)
- **Train Time**: 0.48s

**Winner**: RandomForest (F1: 1.0000)
**Observed Weaknesses**: Proxy dataset is too simple, leading to perfect classification (F1=1.0). In a real environment, device spoofing introduces significantly more noise.
