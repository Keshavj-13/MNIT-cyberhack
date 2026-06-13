# Fraud Operations Simulation Report

**Model Selected**: CatBoost (Threshold: 0.6000)

### Scenario: Legitimate Customer
- **Risk Score**: 0.0001
- **Decision**: **ALLOW**
- **Top Risk Factors (SHAP)**:
  - `V1`: 0.9543
  - `V4`: 0.3226
  - `V12`: -0.2400

### Scenario: Stolen Card (High V4, V11)
- **Risk Score**: 0.9933
- **Decision**: **BLOCK**
- **Top Risk Factors (SHAP)**:
  - `V14`: 7.6271
  - `V4`: 3.4770
  - `V10`: 2.3596

### Scenario: Mule Account (Low V12, V14)
- **Risk Score**: 0.9997
- **Decision**: **BLOCK**
- **Top Risk Factors (SHAP)**:
  - `V14`: 6.1071
  - `V10`: 2.9739
  - `V4`: 2.2630

### Scenario: Rapid Transaction Burst
- **Risk Score**: 0.9998
- **Decision**: **BLOCK**
- **Top Risk Factors (SHAP)**:
  - `V14`: 6.6104
  - `V10`: 3.1810
  - `V4`: 2.9173

