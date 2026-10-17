"""
DermaSense Multilingual RAG Chatbot Service.
Embeds clinical knowledge base guides using multilingual Sentence-Transformers + FAISS.
Answers strictly from retrieved clinical text with citations.
Enforces out-of-scope rejection: 'I don't know, please see a doctor.'
Supports conversational follow-ups with detected condition context.
Works 100% offline via local extractive grounding (Ollama optional).
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from backend.config import PROJECT_ROOT, KNOWLEDGE_BASE_DIR

TRANSLATIONS_DIR = PROJECT_ROOT / "data" / "translations"
KB_TRANSLATIONS_PATH = TRANSLATIONS_DIR / "kb_translations.json"
UI_TRANSLATIONS_PATH = TRANSLATIONS_DIR / "ui_translations.json"

OUT_OF_SCOPE_ANSWER = "I don't know, please see a doctor."

OUT_OF_SCOPE_TRANSLATIONS = {
    "en": "I don't know, please see a doctor.",
    "hi": "मुझे नहीं पता, कृपया डॉक्टर को दिखाएं।",
    "or": "ମୁଁ ଏହା ଜାଣିନାହିଁ, ଦୟାକରି ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
    "bn": "আমি এটি জানি না, দয়া করে একজন ডাক্তারের পরামর্শ নিন।",
    "ta": "எனக்கு தெரியவில்லை, தயவுசெய்து மருத்துவரை அணுகவும்.",
    "te": "నాకు తెలియదు, దయచేసి వైద్యుడిని సంప్రదించండి.",
    "mr": "मला माहिती नाही, कृपया डॉक्टरांचा सल्ला घ्या."
}

# Domain keyword check to rapidly filter non-medical queries
DERM_KEYWORDS = {
    "skin", "lesion", "mole", "spot", "rash", "melanoma", "nevus", "cancer", "bcc",
    "keratosis", "eczema", "psoriasis", "tinea", "ringworm", "fungal", "acne", "pimple",
    "itch", "bleed", "bleeding", "spread", "contagious", "doctor", "ointment", "cream",
    "sunscreen", "uv", "sunburn", "blister", "scab", "first aid", "avoid", "cure", "treat",
    "treatment", "symptom", "precaution", "danger", "urgent", "red flag", "pus", "infection",
    "त्वचा", "तिल", "दाग", "कैंसर", "संक्रामक", "संक्रमण", "इलाज", "उपचार", "खुजली", "चर्म",
    "मेलानोमा", "फैलता", "फैल", "फैलने", "हानिकारक", "नुकसान", "मस्सा", "फफोले",
    "ଡାକ୍ତର", "ରୋଗ", "କଳାଜାଇ", "କୁଣ୍ଡାଇ", "ମେଲାନୋମା", "ଡିଆଁ", "ବ୍ୟାପେ",
    "চর্ম", "আঁচিল", "মেলানোমা", "ছোঁয়াচে", "தோல்", "மருத்துவர்", "மெலனோமா", "தொற்று",
    "మచ్చ", "వైద్యుడు", "మెలనోమా", "सोके", "कॅन्सर", "संसर्ग", "संसर्गजन्य"
}


class ClinicalChunk:
    def __init__(
        self,
        chunk_id: int,
        condition_id: str,
        condition_name: str,
        section: str,
        title: str,
        text: str,
        sources: List[Dict[str, str]],
        language: str = "en",
    ):
        self.chunk_id = chunk_id
        self.condition_id = condition_id
        self.condition_name = condition_name
        self.section = section
        self.title = title
        self.text = text
        self.sources = sources
        self.language = language

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "condition_id": self.condition_id,
            "condition_name": self.condition_name,
            "section": self.section,
            "title": self.title,
            "text": self.text,
            "sources": self.sources,
            "language": self.language,
        }


class RAGChatbotService:
    def __init__(
        self,
        kb_dir: Path = KNOWLEDGE_BASE_DIR,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.38,
    ):
        self.kb_dir = kb_dir
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold

        self.chunks: List[ClinicalChunk] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dim: int = 384
        self.is_ready: bool = False

        self.kb_translations: Dict[str, Any] = {}
        self._load_translations()
        self._build_index()

    def _load_translations(self):
        """Loads cached Indic translations."""
        if KB_TRANSLATIONS_PATH.exists():
            try:
                with open(KB_TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                    self.kb_translations = json.load(f).get("conditions", {})
            except Exception as e:
                print(f"[WARN] Failed to load kb_translations.json: {e}")

    def _extract_chunks_from_kb(self):
        """Extracts granular clinical passages from all verified condition guides."""
        self.chunks.clear()
        chunk_id = 0

        for json_file in sorted(self.kb_dir.glob("*.json")):
            if json_file.name == "conditions.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[WARN] Could not parse {json_file}: {e}")
                continue

            cid = data.get("condition_id", "")
            cname = data.get("name", cid.replace("_", " ").title())
            sources = data.get("sources", [])
            local_names = ", ".join(data.get("local_names", []))

            # 1. Description & Overview
            desc = data.get("description", "")
            if desc:
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="description",
                    title=f"{cname} Description and Overview",
                    text=f"{cname} ({local_names}): {desc}",
                    sources=sources,
                ))
                chunk_id += 1

            # 2. Symptoms
            symptoms = data.get("common_symptoms", [])
            if symptoms:
                sym_text = f"Common signs and symptoms of {cname} (symptoms signs लक्षण ଲକ୍ଷଣ লক্ষণ அறிகுறிகள் లక్షణాలు): " + "; ".join(symptoms) + "."
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="symptoms",
                    title=f"{cname} Symptoms",
                    text=sym_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 3. First Aid
            first_aid = data.get("first_aid", [])
            if first_aid:
                fa_text = f"Immediate first aid and safe initial steps for {cname} (first aid care प्राथमिक उपचार ପ୍ରାଥମିକ ଚିକିତ୍ସା প্রাথমিক চিকিৎসা முதலுதவி ప్రథమ చికిత్స): " + "; ".join(first_aid) + "."
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="first_aid",
                    title=f"{cname} First Aid",
                    text=fa_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 4. Precautions & Home Care
            precautions = data.get("precautions", [])
            home_care = data.get("home_care", [])
            if precautions or home_care:
                prec_text = f"Precautions and home care for {cname} (precautions home care सावधानियां ସତର୍କତା): " + "; ".join(precautions + home_care) + "."
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="precautions",
                    title=f"{cname} Precautions",
                    text=prec_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 5. Do NOT (Harmful practices to avoid)
            do_not = data.get("do_not", [])
            if do_not:
                dont_text = f"What to strictly avoid and harmful practices for {cname} (avoid do not strictly avoid harmful practices क्या न करें କଣ କରିବା ଉଚିତ ନୁହେଁ কি করবেন না செய்யக்கூடாதவை చేయకూడని పనులు काय करू नये): " + "; ".join(do_not) + "."
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="do_not",
                    title=f"Things to Avoid for {cname}",
                    text=dont_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 6. Red Flags
            red_flags = data.get("red_flags", [])
            if red_flags:
                rf_text = f"Red flag warning signs for {cname} (red flags danger emergency खतरे ବିପଦ धोका): " + "; ".join(red_flags) + "."
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="red_flags",
                    title=f"{cname} Red Flags",
                    text=rf_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 7. When to See a Doctor
            doctor = data.get("when_to_see_doctor", "")
            if doctor:
                doc_text = f"When to see a doctor or dermatologist for {cname} (doctor hospital clinic dermatologist डॉक्टर ଡାକ୍ତର மருத்துவர் వైద్యుడు): {doctor}"
                self.chunks.append(ClinicalChunk(
                    chunk_id=chunk_id,
                    condition_id=cid,
                    condition_name=cname,
                    section="when_to_see_doctor",
                    title=f"When to See a Doctor for {cname}",
                    text=doc_text,
                    sources=sources,
                ))
                chunk_id += 1

            # 8. Contagious Status
            is_contagious = data.get("contagious", False)
            cont_kw = "contagious spread संक्रामक संसर्गजन्य ସଂକ୍ରାମକ সংক্রামক தொற்று అంటు"
            contagious_text = (
                f"Is {cname} contagious? ({cont_kw}) Yes, {cname} is contagious and can spread through direct skin contact or sharing contaminated clothing, towels, or personal items."
                if is_contagious else
                f"Is {cname} contagious? ({cont_kw}) No, {cname} is NOT contagious. It cannot spread from person to person through touch, clothing, or air."
            )
            self.chunks.append(ClinicalChunk(
                chunk_id=chunk_id,
                condition_id=cid,
                condition_name=cname,
                section="contagious",
                title=f"Is {cname} Contagious?",
                text=contagious_text,
                sources=sources,
            ))
            chunk_id += 1

        print(f"[OK] Extracted {len(self.chunks)} clinical guidance chunks from knowledge base.")

    def _build_index(self):
        """Encodes all passages and builds FAISS inner product index."""
        self._extract_chunks_from_kb()
        if not self.chunks:
            print("[WARN] No chunks available to index.")
            return

        try:
            # Try offline load first, then online
            try:
                self.model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                self.model = SentenceTransformer(self.model_name)

            self.embedding_dim = self.model.get_embedding_dimension()
            texts = [c.text for c in self.chunks]
            embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)

            # L2 normalize embeddings for cosine similarity with IndexFlatIP
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            embeddings = (embeddings / norms).astype(np.float32)

            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.index.add(embeddings)
            self.is_ready = True
            print(f"[OK] RAGChatbotService: Built FAISS index with {self.index.ntotal} vectors (dim={self.embedding_dim}).")
        except Exception as e:
            print(f"[ERROR] Failed to build FAISS index with SentenceTransformer: {e}")
            self.is_ready = False

    def query(
        self,
        question: str,
        detected_condition: Optional[str] = None,
        language: str = "en",
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes grounded retrieval and answers strictly from verified clinical passages.
        If out of scope: returns "I don't know, please see a doctor."
        """
        clean_q = question.strip()
        if not clean_q:
            fallback = OUT_OF_SCOPE_TRANSLATIONS.get(language, OUT_OF_SCOPE_ANSWER)
            return {
                "answer": fallback,
                "sources": [],
                "grounded": False,
                "confidence": 0.0,
                "section": "none",
                "condition_id": detected_condition or "unknown"
            }

        # Rapid out-of-domain check
        q_lower = clean_q.lower()
        has_medical_term = any(k in q_lower for k in DERM_KEYWORDS)
        is_contextual_followup = bool(detected_condition and (has_medical_term or len(q_lower.split()) <= 20))

        if not has_medical_term and not is_contextual_followup:
            fallback = OUT_OF_SCOPE_TRANSLATIONS.get(language, OUT_OF_SCOPE_ANSWER)
            return {
                "answer": fallback,
                "sources": [],
                "grounded": False,
                "confidence": 0.0,
                "section": "out_of_scope",
                "condition_id": detected_condition or "unknown"
            }

        if not self.is_ready or self.index is None or self.model is None:
            fallback = OUT_OF_SCOPE_TRANSLATIONS.get(language, OUT_OF_SCOPE_ANSWER)
            return {
                "answer": fallback,
                "sources": [],
                "grounded": False,
                "confidence": 0.0,
                "section": "service_offline",
            }

        # Augment query if detected condition is supplied for follow-up context
        search_query = clean_q
        if detected_condition:
            cond_clean = detected_condition.replace("_", " ")
            if cond_clean.lower() not in search_query.lower():
                search_query = f"{cond_clean} {clean_q}"

        # Encode query
        q_emb = self.model.encode([search_query], convert_to_numpy=True)
        q_norm = np.linalg.norm(q_emb, axis=1, keepdims=True)
        q_norm[q_norm == 0] = 1.0
        q_emb = (q_emb / q_norm).astype(np.float32)

        # FAISS search
        scores, indices = self.index.search(q_emb, k=top_k)
        best_score = float(scores[0][0])
        best_idx = int(indices[0][0])

        # Strict relevance threshold check
        if best_score < self.similarity_threshold or best_idx < 0:
            fallback = OUT_OF_SCOPE_TRANSLATIONS.get(language, OUT_OF_SCOPE_ANSWER)
            return {
                "answer": fallback,
                "sources": [],
                "grounded": False,
                "confidence": round(best_score, 4),
                "section": "low_similarity",
                "condition_id": detected_condition or "unknown"
            }

        matched_chunk = self.chunks[best_idx]

        # Prioritize matching section among top candidates if intent is explicit
        is_contagious_q = any(w in q_lower for w in ["contagious", "spread", "catch", "pass", "फैलता", "फैल", "संक्रामक", "ସଂକ୍ରାମକ", "ଡିଆଁ", "ବ୍ୟାପେ", "সংক্রামକ", "ছোঁয়াচে", "தொற்று", "అంటు", "संसर्गजन्य"])
        is_donot_q = any(w in q_lower for w in ["avoid", "do not", "don't", "harmful", "न करें", "ଉଚିତ ନୁହେଁ", "করবেন না", "கூடாது", "కూడదు", "नये"])
        is_firstaid_q = any(w in q_lower for w in ["first aid", "care", "प्राथमिक उपचार", "ପ୍ରାଥମିକ", "முதலுதவி", "ప్రథమ", "प्रथमोपचार"])
        is_doctor_q = any(w in q_lower for w in ["doctor", "hospital", "clinic", "डॉक्टर", "ଡାକ୍ତର", "மருத்துவர்", "వైద్యుడు", "दाखवा"])
        is_symptoms_q = any(w in q_lower for w in ["symptom", "signs", "लक्षण", "ଲକ୍ଷଣ", "లక్షణాలు", "அறிகுறிகள்", "চিহ্ন"])

        target_condition = detected_condition or matched_chunk.condition_id
        for candidate_idx in indices[0][:5]:
            if candidate_idx < 0:
                continue
            cand_chunk = self.chunks[candidate_idx]
            if cand_chunk.condition_id == target_condition:
                if is_contagious_q and cand_chunk.section == "contagious":
                    matched_chunk = cand_chunk
                    break
                elif is_donot_q and cand_chunk.section == "do_not":
                    matched_chunk = cand_chunk
                    break
                elif is_firstaid_q and cand_chunk.section == "first_aid":
                    matched_chunk = cand_chunk
                    break
                elif is_doctor_q and cand_chunk.section == "when_to_see_doctor":
                    matched_chunk = cand_chunk
                    break
                elif is_symptoms_q and cand_chunk.section == "symptoms":
                    matched_chunk = cand_chunk
                    break

        cid = matched_chunk.condition_id
        sec = matched_chunk.section

        # Construct localized or extractive answer
        raw_answer = matched_chunk.text

        # If user asked in Indic language (hi, or, bn, ta, te, mr) and we have translations
        if language in ("hi", "or", "bn", "ta", "te", "mr") and cid in self.kb_translations:
            tr_data = self.kb_translations[cid].get(language, {})
            if sec == "contagious" and "contagious_answer" in tr_data:
                raw_answer = tr_data["contagious_answer"]
            elif sec == "description" and "description" in tr_data:
                raw_answer = tr_data["description"]
            elif sec == "when_to_see_doctor" and "when_to_see_doctor" in tr_data:
                raw_answer = tr_data["when_to_see_doctor"]
            elif sec == "first_aid" and "first_aid" in tr_data:
                raw_answer = f"प्राथमिक उपचार ({tr_data.get('name', cid)}): " + "; ".join(tr_data["first_aid"])
            elif sec == "do_not" and "do_not" in tr_data:
                raw_answer = f"क्या न करें ({tr_data.get('name', cid)}): " + "; ".join(tr_data["do_not"])

        # Format citations
        formatted_sources = [
            {"title": s.get("title", "Clinical Guideline"), "url": str(s.get("url", ""))}
            for s in matched_chunk.sources
        ]

        return {
            "answer": raw_answer,
            "sources": formatted_sources,
            "grounded": True,
            "confidence": round(best_score, 4),
            "matched_condition": matched_chunk.condition_name,
            "condition_id": matched_chunk.condition_id,
            "section": matched_chunk.section,
        }


# Singleton instance
rag_service = RAGChatbotService()
