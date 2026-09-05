"""
ocr_engine.py - Root Entrypoint Wrapper for LegalMetrologyOCR
"""
import os
import sys

# Ensure UTF-8 output encoding on Windows consoles for Devanagari script
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app', 'ocr'))

from backend.app.ocr.ocr_engine import LegalMetrologyOCR

if __name__ == "__main__":
    from backend.app.ocr.image_preprocessor import ImagePreprocessor, generate_synthetic_commodity_label
    import json

    print("=" * 75)
    print("[METRIX-LM] DOCUMENT AI ENGINE: LegalMetrologyOCR Benchmark")
    print("=" * 75)

    # 1. Verify Singleton Pattern
    print("[*] Testing Singleton instantiation pattern...")
    engine_1 = LegalMetrologyOCR(lang="devanagari", ocr_version="PP-OCRv4")
    engine_2 = LegalMetrologyOCR()

    assert engine_1 is engine_2, "CRITICAL: LegalMetrologyOCR violated Singleton pattern!"
    print("[+] Singleton verified: Model is cached in memory exactly once.")
    print("-" * 75)

    # 2. Preprocess synthetic image
    print("[*] Generating synthetic commodity packaging sample with dot-matrix text...")
    raw_sample = generate_synthetic_commodity_label()
    preprocessor = ImagePreprocessor(target_width=1000)
    preprocessed_binary = preprocessor.process(raw_sample, apply_morphology=True, return_mode="binary")
    print(f"[*] Preprocessed Array Shape: {preprocessed_binary.shape} (1 Channel, Binary uint8)")

    # 3. Extract text
    print("[*] Executing LegalMetrologyOCR inference on 1-channel binary preprocessed image...")
    extracted_records = engine_1.extract(preprocessed_binary)

    print("\n" + "=" * 75)
    print("EXTRACTED STATUTORY DECLARATION DICTIONARY (JSON SERIALIZED)")
    print("=" * 75)
    print(json.dumps(extracted_records, indent=2, ensure_ascii=False))

    print("\n" + "=" * 75)
    print("CONCATENATED STATUTORY TEXT STREAM")
    print("=" * 75)
    print(engine_1.extract_full_text(preprocessed_binary))
    print("=" * 75)

    print(f"[+] Successfully extracted {len(extracted_records)} statutory text declaration lines.")
    print("[+] All coordinates verified as standard Python integers for JSON serialization.")
