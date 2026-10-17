# DermaSense System Architecture

**Smart India Hackathon 2025**  
**Team Healthnautix | Problem Statement 25049: Public Health Chatbot**

---

## 1. System Overview

DermaSense is an open-source, local-first artificial intelligence platform designed to raise public health awareness for skin conditions. Users upload a photograph of a skin lesion or spot and receive:
1. **Model Confidence Scores** across possible dermatological conditions.
2. **Explainable AI (Grad-CAM Heatmap)** showing exact spatial regions the model analyzed.
3. **Source-Cited Public Health Guides** featuring symptoms, supportive first aid, precautions, harmful practices to avoid ("do-nots"), critical red flags, and triage advice.
4. **Interactive Public Health Assistant** offering conversational guidance grounded in official public health guidelines (WHO, MoHFW India, CDC, NHS, AAD, DermNet NZ).

---

## 2. Architectural Blueprint

```
+-----------------------------------------------------------------------------------+
|                                 USER BROWSER                                      |
|  [ React 19 + Vite 8 + Tailwind CSS + Lucide Icons ]                              |
|   - Image Uploader & Compression                                                  |
|   - Grad-CAM Interactive Comparison Slider / Overlay                              |
|   - Condition Probability Cards & Risk Indicators                                 |
|   - Structured Medical Guide Accordion (WHO / MoHFW / NHS / CDC / AAD Cited)      |
|   - Public Health Chatbot Drawer with Rule 4 Disclaimers                          |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST API (Port 8000)
                                           v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|   - /api/health                   : System status & device check (CPU / GPU)      |
|   - /api/predict                  : Image ingest, preprocessing, PyTorch inference|
|   - /api/gradcam                  : Target-layer activation map & heatmap overlay |
|   - /api/conditions               : Query source-cited condition knowledge base   |
|   - /api/chat                     : Clinical triage chatbot & guided Q&A          |
+-------------------+---------------------------------------+-----------------------+
                    |                                       |
                    v                                       v
+-------------------------------------+   +-----------------------------------------+
|             ML SUBSYSTEM            |   |         KNOWLEDGE SUBSYSTEM             |
|  [ PyTorch 2.14+ | timm 1.0+ ]      |   |  [ JSON / Pydantic V2 Schema ]          |
|   - Backbone: timm Vision Model     |   |   - conditions.json                     |
|   - Weights: Authentic Trained Model|   |   - Sources: WHO, MoHFW, NHS, CDC, AAD  |
|   - Grad-CAM: Layer-4 Activation Map|   |   - reviewed_by_clinician: false        |
|   - Metrics: Acc, Prec, Rec, F1     |   |   - Enforced disclaimer on every output |
+-------------------------------------+   +-----------------------------------------+
```

---

## 3. Directory Layout

```
dermasense/
├── ml/                       # Machine Learning Pipeline
│   ├── dataset.py            # Authentic dataset loading and augmentation
│   ├── model.py              # timm neural network backbone & classifier head
│   ├── gradcam.py            # Gradient-weighted Class Activation Mapping
│   ├── train.py              # Real training routine with validation loss/acc logging
│   ├── evaluate.py           # Evaluation script generating confusion matrix & metrics
│   └── weights/              # Saved model weights (.pt / .safetensors)
├── backend/                  # FastAPI Application
│   ├── main.py               # Application entrypoint & CORS middleware
│   ├── api/                  # API routers (predict, gradcam, conditions, chat)
│   ├── services/             # ML inference service, Grad-CAM service, triage engine
│   └── schemas/              # Pydantic request/response schemas
├── frontend/                 # React + Vite Single Page Application
│   ├── src/
│   │   ├── components/       # UI components (Upload, Results, GradCam, Guide, Chat)
│   │   ├── services/         # API client hooks
│   │   ├── App.jsx           # Main layout and state coordinator
│   │   └── main.jsx          # Root mount
│   ├── package.json          # Vite + React + Tailwind dependencies
│   └── vite.config.js        # Build configuration with backend proxy
├── data/
│   ├── knowledge_base/       # Source-cited medical guides & Pydantic schema
│   │   ├── conditions.json   # 11 conditions with WHO/MoHFW/NHS/CDC/AAD citations
│   │   └── schema.py         # Knowledge base validation schema
│   └── raw/                  # Real dermatological image samples & datasets
├── docs/                     # Specifications and compliance documentation
│   ├── architecture.md       # System design & component interaction
│   ├── medical_sources.md    # Source citation bibliography
│   └── disclaimers.md        # Rule 4 compliance & triage protocol
└── tests/                    # Automated Pytest suite
    ├── test_phase1_environment.py
    └── test_knowledge_base.py
```

---

## 4. Non-Negotiable Compliance Framework

1. **No Faked / Mocked Predictions:** Every prediction, weight, metric, or training run executes authentic PyTorch routines on real image tensors.
2. **Local & Free Stack:** Built completely with PyTorch, timm, FastAPI, and Vite without any proprietary or paywalled APIs.
3. **Empirical Reporting:** Every metric reported in documentation comes directly from executed CLI command outputs.
4. **Terminology Rigor:** System outputs label results as "possible conditions" with disclaimers displayed on all screens.
5. **Verified Medical Provenance:** Every medical text in the knowledge base links directly to WHO, MoHFW, NHS, CDC, AAD, or DermNet NZ and is flagged `reviewed_by_clinician: false`.

