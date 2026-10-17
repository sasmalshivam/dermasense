"""
DermaSense Colab / Kaggle Translation Pipeline.
Translates all clinical knowledge base guides into 6 Indic languages
(Hindi, Odia, Bengali, Tamil, Telugu, Marathi) using AI4Bharat IndicTrans2 or NLLB-200.

Expected Output Format:
data/translations/kb_translations.json:
{
  "notice": "Translations are machine-generated and need human review.",
  "conditions": {
    "melanoma": {
      "hi": { "name": "...", "description": "...", "first_aid": [...], "do_not": [...], "when_to_see_doctor": "..." },
      "or": { "name": "...", "description": "...", "first_aid": [...], "do_not": [...], "when_to_see_doctor": "..." },
      ...
    }
  }
}

Run on Google Colab with GPU:
!pip install torch transformers sentencepiece sacremoses
"""

import json
from pathlib import Path

# Target Indic Languages with ISO and NLLB / IndicTrans2 language codes
INDIC_LANGUAGES = {
    "hi": {"name": "Hindi", "nllb_code": "hin_Deva", "indic_code": "hin_Deva"},
    "or": {"name": "Odia", "nllb_code": "ory_Orya", "indic_code": "ory_Orya"},
    "bn": {"name": "Bengali", "nllb_code": "ben_Beng", "indic_code": "ben_Beng"},
    "ta": {"name": "Tamil", "nllb_code": "tam_Taml", "indic_code": "tam_Taml"},
    "te": {"name": "Telugu", "nllb_code": "tel_Telu", "indic_code": "tel_Telu"},
    "mr": {"name": "Marathi", "nllb_code": "mar_Deva", "indic_code": "mar_Deva"},
}

def translate_with_nllb(text_list, target_lang_code, model, tokenizer, device="cuda"):
    """Translates a list of strings using Meta NLLB-200."""
    inputs = tokenizer(text_list, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[target_lang_code],
        max_length=512
    )
    return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)

def main():
    print("=" * 80)
    print("DermaSense Indic Translation Generator (Colab / Local GPU)")
    print("=" * 80)

    kb_dir = Path("data/knowledge_base")
    output_path = Path("data/translations/kb_translations.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[*] Loading NLLB-200-distilled model...")
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "facebook/nllb-200-distilled-600M"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)
        print(f"[OK] Model loaded on {device}.")
    except Exception as e:
        print(f"[WARN] Local GPU translation model not loaded: {e}")
        print("Please run this script on a Colab GPU instance.")
        return

    result = {
        "notice": "Translations are machine-generated and need human review.",
        "conditions": {}
    }

    for json_file in kb_dir.glob("*.json"):
        if json_file.name == "conditions.json":
            continue
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cid = data.get("condition_id")
        result["conditions"][cid] = {}

        for lang_key, lang_info in INDIC_LANGUAGES.items():
            print(f"Translating {cid} into {lang_info['name']} ({lang_key})...")
            target_code = lang_info["nllb_code"]

            # Translate text fields
            name_tr = translate_with_nllb([data["name"]], target_code, model, tokenizer, device)[0]
            desc_tr = translate_with_nllb([data["description"]], target_code, model, tokenizer, device)[0]
            doctor_tr = translate_with_nllb([data["when_to_see_doctor"]], target_code, model, tokenizer, device)[0]

            first_aid_tr = translate_with_nllb(data.get("first_aid", []), target_code, model, tokenizer, device)
            do_not_tr = translate_with_nllb(data.get("do_not", []), target_code, model, tokenizer, device)
            red_flags_tr = translate_with_nllb(data.get("red_flags", []), target_code, model, tokenizer, device)

            result["conditions"][cid][lang_key] = {
                "name": name_tr,
                "description": desc_tr,
                "first_aid": first_aid_tr,
                "do_not": do_not_tr,
                "red_flags": red_flags_tr,
                "when_to_see_doctor": doctor_tr
            }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved translation output to {output_path}")

if __name__ == "__main__":
    main()

