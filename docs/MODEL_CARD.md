# DermaSense Model Card

**Project:** DermaSense (Smart India Hackathon 2025, Team Healthnautix, PS 25049)  
**Standard Compliance:** Non-Negotiable Rules 3 & 4 (Empirical numbers from actual runs, preliminary screening disclaimer).  
**Evaluation Scope:** Strictly evaluated on unseen **TEST split** only (123 samples).

---

## 1. Model Summary & Architecture

- **Model Type:** Deep Convolutional Neural Network
- **Backbone Architecture:** `efficientnet_b0` (via `timm`)
- **Pretraining:** ImageNet-1k
- **Input Resolution:** 224 x 224 (RGB 3-channel)
- **Active Output Classes:** 3 classes
- **Training Protocol:** Two-stage optimization (Classifier head warmup, followed by full backbone unfreezing with Cosine Annealing learning rate schedule)
- **Imbalance Mitigation:** Weighted Random Sampler & Multiclass Focal Loss ($\gamma = 2.0$)
- **Probability Calibration:** Temperature Scaling calibrated on validation set

---

## 2. Test Split Evaluation Metrics

| Metric | Score | Clinical Significance |
|---|---|---|
| **Overall Accuracy** | **80.49%** | Overall fraction of correct predictions across test split |
| **Macro-Averaged F1** | **0.6905** | Unweighted mean F1 ensuring under-represented classes are equally evaluated |
| **Weighted F1** | **0.8076** | Class-frequency weighted harmonic mean of precision and recall |
| **One-vs-Rest ROC-AUC** | **0.9079** | Diagnostic discriminative ability across multi-class thresholds |
| **Melanoma Sensitivity** | **0.5000** | Critical screening metric: percentage of malignant melanoma detected |

---

## 3. Per-Class Performance Breakdown

| Condition Label | Precision | Recall (Sensitivity) | F1-Score | Support (Test Samples) |
|:---|---:|---:|---:|---:|
| **melanocytic_nevus** | 0.5357 | 0.6250 | 0.5769 | 24 |
| **melanoma** | 0.5455 | 0.5000 | 0.5217 | 24 |
| **not_skin** | 0.9863 | 0.9600 | 0.9730 | 75 |


---

## 4. Test Split Confusion Matrix

| True \ Pred | melanocytic_nevus | melanoma | not_skin |
|:---| ---: | ---: | ---: |
| **melanocytic_nevus** | 15 | 8 | 1 |
| **melanoma** | 12 | 12 | 0 |
| **not_skin** | 1 | 2 | 72 |


A visual heatmap is saved at: [`docs/confusion_matrix.png`](confusion_matrix.png)

---

## 5. Out-of-Distribution (OOD) & Low-Confidence Triage

To prevent hazardous overconfident misclassifications on blurred, non-skin, or unrecognized conditions:
- **Maximum Softmax Threshold:** Rejects inputs where top calibrated softmax probability is below the validation percentile threshold.
- **Energy Score Threshold:** Computes $-T \cdot \log \sum_i e^{logits_i / T}$; low energy scores flag anomalous or out-of-distribution inputs.
- **System Action:** If an input falls below either threshold, DermaSense refuses definitive categorization and outputs:  
  `"Unable to assess clearly. The photograph may be out-of-focus, non-skin, or unidentifiable. Please consult a clinician directly."`

---

## 6. Clinical & Ethical Disclaimers

> **IMPORTANT MEDICAL NOTICE:**  
> DermaSense is strictly an educational public health screening tool and **DOES NOT** provide medical diagnosis. Photographic screening cannot replace in-person dermatoscopy, full-body skin examinations, or tissue histopathology biopsies.
