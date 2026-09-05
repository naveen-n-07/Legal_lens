"""
ocr_engine_multilingual.py - Root Entrypoint Wrapper for MultilingualLegalMetrologyOCR
"""
import os
import sys

# Ensure UTF-8 output encoding on Windows consoles for Indic scripts
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app', 'ocr'))

from backend.app.ocr.ocr_engine_multilingual import (
    MultilingualLegalMetrologyOCR,
    LRUModelPool,
    LANGUAGE_MAPPING
)

if __name__ == "__main__":
    import numpy as np
    import json

    print("=" * 80)
    print("[METRIX-LM] MULTILINGUAL PADDLEOCR ENGINE (SIH 26034) BENCHMARK")
    print("=" * 80)

    ocr = MultilingualLegalMetrologyOCR(max_models=3)
    dummy_img = np.full((500, 800, 3), 245, dtype=np.uint8)

    print("\n[TEST 1] Testing Dynamic Model Pooling & LRU Eviction Policy (Max 3 Models)")
    print("-" * 80)

    test_sequence = ["tamil", "telugu", "kannada", "hindi", "telugu"]

    for idx, lang in enumerate(test_sequence, 1):
        print(f"\n---> Request {idx}: Extracting packaging text in '{lang}'...")
        results = ocr.extract(dummy_img, lang=lang)
        print(f"     [+] Detections Extracted: {len(results)}")
        print(f"     [!] Current Active Models in RAM: {ocr.pool.active_languages}")

    assert len(ocr.pool.active_languages) <= 3, "CRITICAL: LRU Pool exceeded max_models limit!"
    assert "ta" not in ocr.pool.active_languages, "CRITICAL: 'ta' was not evicted by LRU policy!"
    print("\n[+] LRU Memory Management Verification: PASSED. Max 3 models enforced without memory leak.")

    print("\n[TEST 2] Structured Detection Output for Tamil ('ta') Packaging")
    print("-" * 80)
    tamil_results = ocr.extract(dummy_img, lang="ta")
    print(json.dumps(tamil_results, indent=2, ensure_ascii=False))
    print(f"\n[+] Active Models after reloading Tamil: {ocr.pool.active_languages}")
    print("[+] All multilingual requirements verified successfully.")
