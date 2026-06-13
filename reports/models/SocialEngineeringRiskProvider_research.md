# Social Engineering Provider Research

**Datasets Used**: SMS Spam Collection

**Feature Engineering**: Extracted TF-IDF, Ngrams (1-2), Urgency, Threat, Financial bait, and Account warning indicators.

### Model: LogisticRegression
- **Train AUC**: 0.9975
- **Test AUC**: 0.9823
- **Test F1**: 0.8764 (Prec: 0.9915, Rec: 0.7852)
- **Train Time**: 0.19s

### Model: LightGBM
- **Train AUC**: 0.9994
- **Test AUC**: 0.9742
- **Test F1**: 0.9066 (Prec: 0.9357, Rec: 0.8792)
- **Train Time**: 0.24s

### Model: XGBoost
- **Train AUC**: 0.9980
- **Test AUC**: 0.9669
- **Test F1**: 0.8643 (Prec: 0.9237, Rec: 0.8121)
- **Train Time**: 0.60s

**Winner**: LightGBM (F1: 0.9066)
**Observed Weaknesses**: Highly imbalanced dataset. While F1 is high, it relies on historical vocabulary which is prone to drift.
