# Phishing Provider Research

**Datasets Used**: PhishingWebsites

**Feature Engineering**: Used existing structural and lexical features from the dataset. If raw URLs were present, entropy and keyword features would be extracted.

### Model: LightGBM
- **Train AUC**: 0.9986
- **Test AUC**: 0.9961
- **Test F1**: 0.9650 (Prec: 0.9730, Rec: 0.9571)
- **Train Time**: 0.09s

### Model: CatBoost
- **Train AUC**: 0.9990
- **Test AUC**: 0.9968
- **Test F1**: 0.9697 (Prec: 0.9772, Rec: 0.9622)
- **Train Time**: 0.86s

### Model: Lexical_Structural_Fusion
- **Train AUC**: 0.9990
- **Test AUC**: 0.9967
- **Test F1**: 0.9687 (Prec: 0.9742, Rec: 0.9633)
- **Train Time**: 5.42s

**Winner**: CatBoost (F1: 0.9697)
**Observed Weaknesses**: Relies heavily on pre-extracted features rather than raw URL inspection. Highly performant but susceptible to drift if attackers change URL structures.
