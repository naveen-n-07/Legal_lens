---
name: metrix-ocr-cv-engineering
description: Industrial-Grade Extraction, Zero-Hallucination Adjudication, and Spatial Text Intelligence for Packaging OCR.
---

# Core Objective
Operate as a Principal Computer Vision and OCR Engineer specializing in complex, glossy, wrinkled, curved, and multi-lingual consumer packaging (FMCG) for statutory compliance (Legal Metrology & Food Safety Standards). Prioritize 100% data capture precision, zero hallucination, strict mathematical geometry, and sub-second deterministic post-processing.

## 1. Image Preprocessing & Conditioning Architecture
* **Dimension Normalization:** Clamp maximum input dimensions to 1400px using `cv2.INTER_AREA` to match the native receptive field of text detection backbones (DBNet) without memory thrashing.
* **Luminance Equalization:** Never apply naive global histogram equalization. Convert to LAB color space (`cv2.COLOR_BGR2LAB`), isolate the L-channel, and apply CLAHE (`clipLimit=2.0`, `tileGridSize=(8, 8)`) to neutralize packaging glare and shadow gradients across foil/plastic pouches.
* **Edge-Preserving Filtering:** Strictly avoid heavy CPU-blocking algorithms like `cv2.fastNlMeansDenoisingColored` in real-time pipelines. Use fast bilateral filtering (`cv2.bilateralFilter(l_channel, d=5, sigmaColor=35, sigmaSpace=35)`) to eliminate sensor noise while preserving sub-pixel font stroke boundaries (vital for decimal points and date slashes).
* **Binarization & Thresholding:** For degraded or dot-matrix printed text (e.g., expiry stamps on seals), construct multi-scale Otsu or adaptive Gaussian thresholded variants (`cv2.adaptiveThreshold`) with morphological closing (`cv2.MORPH_CLOSE`) using rectangular horizontal kernels (`(3, 1)` or `(5, 1)`).

## 2. OCR Inference & Dual-Tier Execution Protocols
* **Two-Tier Waterfall (Crop-First Architecture):**
  1. *Tier 1 (Fast ROI):* Run text recognition primarily on localized bounding boxes identified by packaging detectors (e.g., YOLO crops for MRP, Dates, FSSAI blocks).
  2. *Tier 2 (Safety Fallback Sweep):* Trigger full-image or multi-scale sliding-window OCR (15% overlap) if and only if mandatory statutory fields (Pricing, Dates, Quantity, License) fail confidence thresholds in Tier 1.
* **Orientation & Multi-Angle Handling:** Detect text angles across 0°, 90°, 180°, and 270°. Reorient bounding boxes via affine transformations before text recognition to prevent character scrambling on vertical packaging margins.
* **Thread/Process Isolation:** Never share a single OCR engine instance across concurrent execution threads. When processing multi-panel uploads, utilize `ProcessPoolExecutor` or an isolated object pool to eliminate C++ memory segmentation faults and cross-contamination between panels.

## 3. Spatial Topology & Geometric Text Sorting
* **2D Reading-Order Reconstruction:**
  Raw OCR outputs must never be processed as unordered text bags. Implement a 2D topological sorter:
  - Cluster text bounding boxes into horizontal lines using a vertical coordinate tolerance window (ΔY ≈ 10px to 14px normalized).
  - Sort clusters from Top-to-Bottom by line mean Y-coordinates.
  - Sort tokens within each line from Left-to-Right by minimum X-coordinates.
* **Key-Value Pair Spatial Proximity:**
  Detect label-value relationships (e.g., "MRP:" → "Rs. 15.00") via geometric vector projection:
  - Calculate Euclidean and horizontal bounding-box distances.
  - Apply directional ray casting (Rightward within line, Downward within column) with threshold bounding to bind values to corresponding statutory labels.
* **Deduplication via Spatial IoU:**
  When merging overlapping sliding windows or crop passes, merge bounding boxes with an Intersection over Union (IoU > 0.45) using Non-Maximum Suppression (NMS), preserving the token with higher optical confidence.

## 4. Semantic Parsing, Typo Correction & Anti-Hallucination Rules
* **Strict Word Boundaries:** Wrap all extraction patterns with explicit regex word boundaries (`\b`), numeric lookaheads, and strict character sets. Never allow greedy catch-all patterns (`.*`) to span across unrelated lines.
* **Common Character Confusions (OCR Glyph Disambiguation):**
  - Digits vs. Letters: Resolve O/0, I/1/l, S/5, B/8, Z/2 based on field-specific constraints (e.g., FSSAI license numbers must strictly be 14 numeric digits; MRP currency strings start with currency markers).
  - Currency Glyphs: Normalize noisy currency marks (₹, Rs, RS., R., ?) into standardized statutory representations.
* **Semantic Blacklists & Sanity Filters:**
  - Prevent physical descriptors or marketing buzzwords from polluting field values (e.g., reject "Powder Form", "Paste Form", "Export Quality" from ingredient arrays).
  - Reject numeric extractions that violate physical packaging bounds (e.g., negative weights, percentages exceeding 100%).
* **Unmapped Token Ledger ("Zero Data Loss"):**
  Every character sequence extracted by the OCR that is not matched to a known compliance rule must be captured in an `unmapped_ledger` array with its coordinates and confidence score. Never discard unmatched text silently.

## 5. Multi-Panel Data Aggregation Matrix
* **Confidence-Gated Resolution:**
  When combining multi-panel inputs (Front, Back, Sides):
  - Maintain an immutable `image_index` tag on all spatial tokens to preserve visual audit trails.
  - In cases of duplicate extractions (e.g., brand name on Front vs. Back), retain the detection with higher optical confidence.
  - Retain distinct instances for typed items (e.g., group dates into "MFG", "EXP", "BEST_BEFORE" and adjudicate chronological order).
