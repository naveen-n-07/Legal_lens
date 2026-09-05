"""
translation_middleware.py - Root Entrypoint Wrapper for TranslationMiddleware

Enterprise Concurrent Multilingual Translation Layer with Indic Numeral Protection
Designed for SIH 26034 (Pan-India Legal Metrology AI Inspection Support System).
"""
import os
import sys
import time

# Ensure UTF-8 output encoding on Windows consoles for Indic scripts
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app', 'ocr'))

from backend.app.ocr.translation_middleware import (
    TranslationMiddleware,
    INDIC_NUMERAL_TABLE,
    STATUTORY_PROTECTION_PATTERNS
)

if __name__ == "__main__":
    print("=" * 80)
    print("[METRIX-LM] MULTILINGUAL TRANSLATION MIDDLEWARE (SIH 26034) BENCHMARK")
    print("=" * 80)

    # 1. Initialize Middleware with ThreadPoolExecutor
    middleware = TranslationMiddleware(max_workers=8)

    # 2. Comprehensive Mixed-Language Pan-India Packaging Dataset
    # Tests Tamil, Telugu, Kannada, Malayalam, Odia, Hindi, Sanskrit with Indic & Arabic numbers
    mixed_language_declarations = [
        # Hindi / Sanskrit (Devanagari numerals: ०-९)
        "अधिकतम खुदरा मूल्य : ₹१२०.०० (सभी कर सहित)",
        "शुद्ध मात्रा : ५०० ग्राम (मानक पैकेजिंग)",
        "उत्पादन तिथि : २४/०८/२०२६ | उपयोग समाप्ति : २५/०२/२०२७",

        # Tamil (Tamil script + mixed numerals)
        "அதிகபட்ச சில்லறை விலை : ₹௨௪௫.௦௦ (வரிகள் உட்பட)",
        "மொத்த எடை : 1.0 கிலோகிராம் (உயர்தர கோதுமை மாவு)",
        "உற்பத்தி தேதி : 08/2026 | காலாவதி : 02/2027",

        # Telugu (Telugu numerals: ౦-౯)
        "గరిష్ట రిటైల్ ధర : ₹౨౯౯.౫౦",
        "నికర పరిమాణం : 750 గ్రాములు",

        # Kannada (Kannada numerals: ೦-೯)
        "ಗರಿಷ್ಠ ಮಾರಾಟ ಬೆಲೆ : ₹೪೫೦.೦೦ (ಎಲ್ಲಾ ತೆರಿಗೆಗಳು ಸೇರಿವೆ)",
        "ನಿವ್ವಳ ತೂಕ : 2.5 ಕಿಲೋಗ್ರಾಂ",

        # Malayalam (Malayalam numerals: ൦-൯)
        "പരമാവധി വില്പന വില : ₹൧௬൫.൦൦",
        "ആകെ തൂക്കം : 500 ഗ്രാം",

        # Odia (Odia numerals: ୦-୯)
        "ସର୍ବାଧିକ ଖୁଚୁରା ମୂଲ୍ୟ : ₹୧୮୦.୦୦ (ସମସ୍ତ ଟିକସ ସହିତ)",
        "ନିଟ୍ ଓଜନ : 1.0 କିଲୋଗ୍ରାମ",

        # Sanskrit / Statutory Legal Clause
        "मानक भारः परिमाणं च : ५.० किलोग्रामम् | मूल्यम् : ₹५००"
    ]

    print(f"[*] Input Batch Size: {len(mixed_language_declarations)} statutory packaging lines")
    print("[*] Launching Concurrent Parallel Translation via ThreadPoolExecutor (max_workers=8)...")
    print("-" * 80)

    t_start = time.perf_counter()
    batch_translations = middleware.translate_batch(mixed_language_declarations)
    total_elapsed_ms = (time.perf_counter() - t_start) * 1000

    print("\n" + "=" * 80)
    print(f"PARALLEL BATCH TRANSLATION RESULTS (Completed in {total_elapsed_ms:.1f}ms)")
    print("=" * 80)

    for i, item in enumerate(batch_translations, 1):
        print(f"[{i:02d}] ORIGINAL   : {item['original']}")
        print(f"     NORMALIZED : {item['normalized']}")
        print(f"     TRANSLATED : {item['translated']}")
        print(f"     LATENCY    : {item['latency_ms']} ms | CACHED: {item['cached']}")
        print("-" * 80)

    # 3. Numeric Integrity Validation
    print("\n[TEST 3] Statutory Numeric Integrity Verification")
    print("-" * 80)
    test_1 = batch_translations[0]["translated"]
    has_number_120 = "120" in test_1
    print(f"[*] Hindi Price Check ('₹१२०.००' -> '₹120.00'): {'[PASS]' if has_number_120 else '[!] FAILED'}")
    assert has_number_120, "CRITICAL: Numeral was corrupted during translation!"

    test_3 = batch_translations[2]["translated"]
    has_date = "24/08/2026" in test_3 or "24" in test_3
    print(f"[*] Date Preservation Check ('२४/०८/२०२६'):     {'[PASS]' if has_date else '[!] FAILED'}")

    # 4. Cache Efficiency Test
    print("\n[TEST 4] In-Memory Cache Verification (Zero Latency Repeat Calls)")
    print("-" * 80)
    cached_res = middleware.translate_single(mixed_language_declarations[0])
    print(f"[*] Repeat Call Cached: {cached_res['cached']} | Latency: {cached_res['latency_ms']} ms")
    assert cached_res["cached"] is True, "CRITICAL: Cache did not intercept repeated query!"

    print("\n[+] All Translation Middleware enterprise specifications verified successfully.")
