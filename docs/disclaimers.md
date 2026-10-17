# DermaSense Disclaimers & Public Health Protocol

**Team:** Healthnautix  
**Problem Statement:** PS 25049 (Public Health Chatbot, SIH 2025)  
**Strict Compliance:** Non-Negotiable Rule 4 ("The app never says 'diagnosis'. Use 'possible condition'. Disclaimer on every result screen.")

---

## Standard Medical Disclaimer (Mandatory Display)

> **IMPORTANT MEDICAL NOTICE:**  
> DermaSense is an assistive educational and public health awareness tool intended solely for preliminary risk screening and triage awareness. It **DOES NOT** provide medical diagnosis, clinical prognosis, or definitive treatment prescriptions.  
> 
> Automated image analysis and artificial intelligence models are subject to algorithmic limitations, photographic lighting variations, and skin tone biases. Any automated assessment reflects an estimated likelihood of a **possible condition** and MUST NOT be treated as a confirmed diagnosis.  
> 
> If you observe any lesion that is rapidly changing, bleeding, ulcerated, or satisfies the ABCDE criteria, consult a certified dermatologist, licensed physician, or seek immediate emergency care without delay.

---

## Terminology Policy

| Prohibited Term | Required Term | Reason |
|---|---|---|
| "Diagnosis" / "Diagnosed as" | "Possible condition" / "Observed pattern" | Prevents false certainty and legal/clinical overreach. |
| "Cure" / "Remedy" | "Supportive first aid" / "Preventive measures" | AI tools cannot prescribe clinical cures. |
| "Confirmed malignant" | "High priority screening - consult physician" | Histopathology / biopsy is the only gold standard. |
| "Doctor approved" | "reviewed_by_clinician: false" | Medical guidance is compiled from verified public portals, not individual clinical signoff. |

---

## Critical Red Flag Triage Matrix

When any of the following symptoms or signs are reported or flagged:
1. **Uncontrolled bleeding** from the skin lesion lasting > 15 minutes.
2. **Sudden, widespread rash accompanied by high fever or systemic toxicity**.
3. **Rapidly enlarging pigmented lesion with irregular variegated borders (ABCDE criteria)**.
4. **Painful, deep mucosal involvement (lips, eyes, genitals)**.

The application triggers an immediate, prominent **High Priority Clinical Warning** banner prompting the user to seek emergency medical attention or an immediate in-person dermatological consultation.

