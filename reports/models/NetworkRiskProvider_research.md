# Network Risk Provider Research

**Datasets Used**: SIMARGL2021

**Feature Engineering**: Removed IPs and Ports to prevent identity leakage. Applied RobustScaler for flow statistics normalization.

### Model: LightGBM
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9989 (Prec: 0.9990, Rec: 0.9988)
- **Train Time**: 0.39s

### Model: XGBoost
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9989 (Prec: 0.9988, Rec: 0.9990)
- **Train Time**: 0.53s

### Model: CatBoost
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9988 (Prec: 0.9985, Rec: 0.9990)
- **Train Time**: 1.53s

### Model: ExtraTrees
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9985 (Prec: 0.9987, Rec: 0.9982)
- **Train Time**: 0.35s

### Model: Hybrid_Intrusion_Ensemble
- **Train AUC**: 1.0000
- **Test AUC**: 0.9999
- **Test F1**: 0.9994 (Prec: 0.9993, Rec: 0.9995)
- **Train Time**: 3.76s

**Winner**: Hybrid_Intrusion_Ensemble (F1: 0.9994)
**Observed Weaknesses**: High dimensionality. The removal of ports prevents detection of known bad-port scans, but ensures generalization over memorization.
