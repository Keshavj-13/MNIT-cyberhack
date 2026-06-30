# AURA Platform: PlantUML High-Level Diagrams (HLD)

You can copy and paste these PlantUML codes into any PlantUML viewer (like PlantText.com or the VSCode PlantUML extension) to generate clean, professional diagrams for your technical documentation.

## 1. Component Diagram: Four-Surface Architecture
This High-Level Design (HLD) component diagram illustrates the strict isolation of the four Vite frontends and FastAPI backends, connecting to the shared centralized Risk Engine and Database.

```plantuml
@startuml
!theme plain
skinparam componentStyle uml2
skinparam BackgroundColor white

title AURA HLD: Four-Surface Architecture

package "Client Plane (Vite / React)" {
    [Customer UI\n(Port 3001)] as CUI
    [Admin SOC UI\n(Port 3002)] as ADUI
    [Attacker UI\n(Port 3003)] as ATUI
    [Showcase UI\n(Port 3004)] as SHUI
}

package "API Gateway Plane (FastAPI)" {
    [Customer API\n(Port 8001)] as CAPI
    [Admin API\n(Port 8002)] as ADAPI
    [Attacker API\n(Port 8003)] as ATAPI
    [Showcase API\n(Port 8004)] as SHAPI
}

package "Core Intelligence Plane" {
    [Evaluation Runner] as EvalRunner
    
    component "Risk Engine Ensemble" as RiskEngine {
        [Transaction Provider]
        [VarCNN Provider]
        [Phishing URL Provider]
    }
    
    component "ARIA Background Agent" as ARIA {
        [Clustering Logic]
        [SHAP Explainability]
        [Qwen3.5 VLM]
    }
}

database "SQLite Database" as DB {
    [users]
    [customer_sessions]
    [security_events]
}

' Connections
CUI -down-> CAPI : AES-GCM Encrypted
ADUI -down-> ADAPI : JWT Auth
ATUI -down-> ATAPI : JWT Auth (sim_ prefix)
SHUI -down-> SHAPI : Public Read-only

CAPI -down-> EvalRunner
ATAPI -down-> EvalRunner

EvalRunner -right-> RiskEngine : Extracts & Scores
RiskEngine -down-> DB : Persists Security Events
CAPI -down-> DB : Reads/Writes Session State
ADAPI -down-> DB : Fetches Events & ARIA

ARIA -up-> DB : Scans Events / Persists Assessments
ADAPI -left-> ARIA : Serves Assessment to SOC

@enduml
```

---

## 2. Flowchart: Risk Evaluation & Key Rotation Workflow
This flowchart illustrates the step-by-step logic when a user makes a high-risk request, how the engine scores it, and how the cryptographic key rotation is executed.

```plantuml
@startuml
!theme plain
skinparam BackgroundColor white

title AURA Workflow: Risk Evaluation & Key Rotation

start

:Customer clicks "Transfer Money";
:React UI encrypts payload with Session AES-Key v1;
:POST /customer/transfer;

partition "Customer API" {
    :Decrypt payload with AES-Key v1;
    :Fetch recent telemetry from DB;
}

partition "Evaluation Runner" {
    :Extract behavioral features (FeatureExtractor);
    :Append historical events for correlation;
}

partition "Risk Engine" {
    :Evaluate with VarCNN (Behavioral);
    :Evaluate with XGBoost/LightGBM (Contextual);
    :Calculate Weighted Risk Score;
    
    if (Risk Score >= 0.90) then (Yes)
        :Action = CONTAIN (Tier 4);
        :Deactivate Session;
    elseif (Risk Score >= 0.70) then (Yes)
        :Action = RESTRICT (Tier 3);
    elseif (Risk Score >= 0.40) then (Yes)
        :Action = CHALLENGE (Tier 2);
    else (No)
        :Action = ALLOW (Tier 1);
    endif
}

partition "API Response Phase" {
    if (Risk escalated?) then (Yes)
        :Generate new AES-Key v2;
        :Update key_version in DB;
        :Encrypt Response + new Key v2\nusing OLD Key v1;
    else (No)
        :Encrypt Response using Key v1;
    endif
}

:Return Encrypted Response to Client;

partition "Customer UI" {
    :Decrypt Response with Key v1;
    if (Response contains new Key v2?) then (Yes)
        :Rotate Local AES-Key to v2;
        :Show "Verification Required" / Lockout UI;
    else (No)
        :Show "Transfer Successful";
    endif
}

stop
@enduml
```
