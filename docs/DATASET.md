# DermaSense Dataset Curation, Unified Taxonomy & Leakage Prevention Protocol

**Smart India Hackathon 2025**  
**Team Healthnautix | Problem Statement 25049: Public Health Chatbot**

---

## 1. Datasets Included & Sources

| Dataset Name | Source / Benchmark | Content & Clinical Scope | Access Mechanism | Status |
|---|---|---|---|---|
| **HAM10000** | Kaggle `kmader/skin-cancer-mnist-ham10000` (ViDIR Group, MedUni Vienna) | 10,015 dermatoscopic images across 7 diagnostic categories | Kaggle CLI / API (`~/.kaggle/kaggle.json`) | Automated via `ml/data/download.py` (requires credentials) |
| **DermNet** | Kaggle `shubhamgoel27/dermnet` (DermNet NZ archive) | 19,500+ clinical photography images covering 23 everyday conditions | Kaggle CLI / API (`~/.kaggle/kaggle.json`) | Automated via `ml/data/download.py` (requires credentials) |
| **Not-Skin** | Public benchmark non-skin images (clothing, accessories, everyday objects) | 500+ non-skin RGB images (224x224) | Direct automated download | **[Active & Populated]** |
| **ISIC 2019** | `isic-archive.com` / Challenge 2019 | 25,331 dermoscopic images for skin lesion analysis | Manual download | Optional |
| **PAD-UFES-20** | Mendeley Data (UFES Brazil) | 2,298 smartphone clinical photographs | Manual download | Optional (smartphone test) |
| **Fitzpatrick17k** | GitHub `nickjong/fitzpatrick17k` | 16,577 clinical images labeled by Fitzpatrick scale (I-VI) | Manual download | Optional (fairness audit) |

---

## 2. Unified Label Map & Taxonomy

To ensure seamless integration between dermatoscopic cancer datasets (HAM10000) and general public health clinical photography (DermNet), we map all source classes into a standardized, unified clinical taxonomy:

### A. HAM10000 Mapping
| HAM10000 Code | Raw Class Name | Unified Condition ID | Clinical Category |
|---|---|---|---|
| `mel` | Melanoma | `melanoma` | Malignant Melanocytic Neoplasm |
| `nv` | Melanocytic Nevus | `melanocytic_nevus` | Benign Melanocytic Lesion |
| `bcc` | Basal Cell Carcinoma | `basal_cell_carcinoma` | Non-Melanoma Skin Cancer |
| `akiec` | Actinic Keratosis / Bowen's Disease | `actinic_keratosis` | Precancerous Keratinocytic Lesion |
| `bkl` | Benign Keratosis (Solar Lentigo / Seborrheic Keratosis) | `benign_keratosis` | Benign Epidermal Growth |
| `df` | Dermatofibroma | `dermatofibroma` | Benign Fibrous Histiocytoma |
| `vasc` | Vascular Lesions (Pyogenic Granuloma / Angioma) | `vascular_lesion` | Benign Vascular Proliferation |

### B. DermNet Mapping
| DermNet Category Folder | Unified Condition ID | Clinical Category |
|---|---|---|
| `Acne and Rosacea Photos` | `acne` | Inflammatory Pilosebaceous Disorder |
| `Eczema Photos` / `Atopic Dermatitis Photos` | `eczema` | Chronic Inflammatory Dermatosis |
| `Psoriasis pictures Lichen Planus...` | `psoriasis` | Chronic Immune-Mediated Skin Disease |
| `Tinea Ringworm Candidiasis...` | `tinea_fungal` | Superficial Fungal Infection |
| `Warts Molluscum...` / `Herpes HPV...` | `viral_infections` | Cutaneous Viral Infections |
| `Cellulitis Impetigo...` | `bacterial_infections` | Bacterial Skin Infections |
| `Seborrheic Keratoses...` | `benign_keratosis` | Benign Epidermal Growth |
| `Vascular Tumors` | `vascular_lesion` | Benign Vascular Proliferation |
| `Melanoma Skin Cancer Nevi...` | `melanocytic_lesions` | Melanocytic Proliferations |

### C. Non-Skin Class
| Source | Unified Condition ID | Clinical Category |
|---|---|---|
| Public Benchmark Non-Skin (Clothing, accessories, objects) | `not_skin` | Non-Skin / Background Artifact |

---

## 3. Curation Rules & Decisions (< ~150 Images Threshold)

1. **Threshold Rule:** To avoid extreme class imbalance and unreliable validation metrics, any individual class or sub-category with fewer than ~150 verified images is:
   - Merged into its primary clinical parent category if clinically sound (e.g., combining contact dermatitis with eczema, or merging pyogenic granulomas with vascular lesions).
   - If no valid clinical parent category exists and image count remains < 150, the class is dropped and logged.
2. **Documented Merging Decisions:**
   - *Contact Dermatitis* (`Poison Ivy Photos...`) merged into `eczema`.
   - *Atopic Dermatitis* merged into `eczema`.
   - *Seborrheic Keratoses and Benign Tumors* merged with `benign_keratosis`.
   - *Nail Fungus* merged with `tinea_fungal`.
   - *Herpes and Warts* merged under `viral_infections`.

---

## 4. Stratified 70/15/15 Splitting & Leakage Prevention Protocol

### The Patient / Lesion Leakage Problem
In dermatological datasets such as HAM10000, multiple images frequently correspond to the same physical lesion on a single patient taken from different angles or lighting conditions (e.g. `HAM_0000118` has both `ISIC_0027419.jpg` and `ISIC_0025030.jpg`). Standard random splitting causes images of the same patient to appear in both training and testing sets, resulting in **data leakage** and artificially inflated, deceptive accuracy scores.

### Prevention Mechanism: GroupStratifiedSplit
1. **Lesion-Level Grouping:** All images sharing the same `lesion_id` are strictly locked into the same split (train, validation, or test).
2. **Stratification:** Stratification is performed over unique `lesion_id` units based on their ground-truth diagnosis, ensuring the 70/15/15 ratio is preserved for every disease class without separating lesion duplicates.
3. **Reproducibility:** Seed fixed to `42`.
4. **Cryptographic Deduplication:** SHA-256 hashes are calculated for every image file across all datasets to guarantee zero file duplication across splits.

### Verification Assertions
`ml/data/prepare.py` automatically asserts:
```python
assert len(train_lesion_ids.intersection(val_lesion_ids)) == 0
assert len(train_lesion_ids.intersection(test_lesion_ids)) == 0
assert len(val_lesion_ids.intersection(test_lesion_ids)) == 0
assert len(train_hashes.intersection(val_hashes)) == 0
assert len(train_hashes.intersection(test_hashes)) == 0
assert len(val_hashes.intersection(test_hashes)) == 0
```
Any overlap immediately halts pipeline execution with an `AssertionError`.

