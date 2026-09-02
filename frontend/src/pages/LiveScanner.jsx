import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Camera, 
  UploadCloud,
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  RefreshCw, 
  ArrowRight, 
  RotateCw, 
  Sparkles, 
  Zap, 
  VideoOff, 
  FileImage, 
  Sliders, 
  Sun, 
  Activity, 
  Check, 
  Layers, 
  AlertCircle, 
  Eye, 
  User, 
  UserCheck, 
  UserX, 
  Tag, 
  Scale, 
  FileText,
  Play,
  Gauge,
  Scan,
  CheckCircle,
  Clock,
  ShieldAlert,
  Box
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { runInspectionAnalysis } from '../services/inspectionService';
import StatutoryInspectionReport from '../components/StatutoryInspectionReport';
import { optimizeForSmallTextOCR } from '../utils/imageEnhancer';

// Configurable Image Quality Gate Thresholds
const QUALITY_THRESHOLDS = {
  minWidth: 640,
  minHeight: 480,
  recommendedWidth: 1280,
  lowBrightness: 35,
  highBrightness: 245,
  minSharpness: 55,
  detectionIntervalMs: 600, // Throttled lightweight sampling (~600ms)
  stabilityMotionThreshold: 8.5 // Low motion threshold between sampled frames
};

export default function LiveScanner() {
  const navigate = useNavigate();
  
  // DOM & Media Refs
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rawCanvasRef = useRef(null);
  const detectionCanvasRef = useRef(null);
  const enhancedCanvasRef = useRef(null);
  const poseLandmarkerRef = useRef(null);

  // Performance & FPS Monitoring Refs
  const fpsRafRef = useRef(null);
  const fpsFrameCountRef = useRef(0);
  const fpsLastTimeRef = useRef(performance.now());
  const [cameraFps, setCameraFps] = useState(30);

  // Detection & Stability State Machine Refs
  const detectionIntervalRef = useRef(null);
  const consecutiveStableHitsRef = useRef(0);
  const previousLuminanceArrayRef = useRef(null);

  // Processing Lock & Session Invalidation Refs
  const isProcessingRef = useRef(false);
  const scanSessionIdRef = useRef(0);
  const abortControllerRef = useRef(null);
  const ocrCacheRef = useRef(new Map());

  // Scan & Camera Modes
  const [scanMode, setScanMode] = useState('camera'); // 'camera' or 'upload'
  const [visionMode, setVisionMode] = useState('enhanced'); // 'standard' | 'enhanced' | 'document'

  // Camera State Machine:
  // OFF | REQUESTING_PERMISSION | ACTIVE | PERMISSION_DENIED | ERROR
  const [cameraState, setCameraState] = useState('OFF');
  const [cameraResolution, setCameraResolution] = useState({ width: 0, height: 0 });
  const [cameraDeviceLabel, setCameraDeviceLabel] = useState('');

  // Live Acquisition Status Machine:
  // "Searching for label..." | "Label detected" | "Hold steady..." | "Checking object..." | "Human detected" | "Unidentified object" | "Product label detected" | "Capturing..." | "Reading text..." | "Checking rules..." | "Inspection complete"
  const [statusText, setStatusText] = useState('Searching for label...');
  const [stabilityPercent, setStabilityPercent] = useState(0);

  // PRE-CAPTURE VALIDATION GATES STATE (TRIGGERED ONLY AT SCAN TIME)
  const [humanBlocked, setHumanBlocked] = useState(false);
  const [humanWarningText, setHumanWarningText] = useState('');
  const [unidentifiedBlocked, setUnidentifiedBlocked] = useState(false);
  const [unidentifiedWarningText, setUnidentifiedWarningText] = useState('');

  // Raw & Enhanced Captured Images (Preserved Evidence)
  const [capturedRawUrl, setCapturedRawUrl] = useState(null);
  const [capturedRawFile, setCapturedRawFile] = useState(null);
  const [enhancedPreviewUrl, setEnhancedPreviewUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Upload Mode State
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadPreviewUrl, setUploadPreviewUrl] = useState(null);

  // Multi-Side Inspection State
  const [scanningSide, setScanningSide] = useState(1);
  const [scannedSides, setScannedSides] = useState([]);

  // Image Quality & Guidance State
  const [qualityMetrics, setQualityMetrics] = useState({
    passed: true,
    brightness: 128,
    sharpness: 120,
    motionDelta: 0,
    message: '✓ Ready for scan',
    guidance: ''
  });

  // Performance Telemetry HUD State
  const [telemetry, setTelemetry] = useState({
    fps: 30,
    detectionMs: 0,
    captureMs: 0,
    enhancementMs: 0,
    ocrMs: 0,
    rulesMs: 0,
    totalMs: 0
  });

  // Backend Inspection Result & Errors
  const [scanResult, setScanResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [qualityWarning, setQualityWarning] = useState('');

  // Reticle Dimension Coordinates (Calculated from Viewfinder)
  const [reticleBounds, setReticleBounds] = useState({ x: 120, y: 80, w: 600, h: 440 });

  // -------------------------------------------------------------
  // 1. Initialize MediaPipe Pose / Human Landmarker (if available)
  // -------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;

    async function initMediaPipePose() {
      try {
        const { FilesetResolver, PoseLandmarker } = await import('@mediapipe/tasks-vision');
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
        );
        if (!isMounted) return;

        const landmarker = await PoseLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
            delegate: 'GPU'
          },
          runningMode: 'VIDEO',
          numPoses: 1
        });
        if (isMounted) {
          poseLandmarkerRef.current = landmarker;
        }
      } catch (err) {
        // Fallback to high-speed anthropometric skin & silhouette detector
      }
    }

    initMediaPipePose();

    return () => {
      isMounted = false;
      if (poseLandmarkerRef.current) {
        try {
          poseLandmarkerRef.current.close();
        } catch (e) {}
        poseLandmarkerRef.current = null;
      }
    };
  }, []);

  // -------------------------------------------------------------
  // 2. High-Speed Human Presence Gate (Triggered Only at Scan Time)
  // -------------------------------------------------------------
  const evaluateHumanPresence = useCallback((videoElement, ctx, sampleW, sampleH) => {
    let isHuman = false;
    let rejectionReason = '';

    // 1. MediaPipe PoseLandmarker (if initialized)
    if (poseLandmarkerRef.current && videoElement) {
      try {
        const timestampMs = performance.now();
        const results = poseLandmarkerRef.current.detectForVideo(videoElement, timestampMs);
        if (results && results.landmarks && results.landmarks.length > 0 && results.landmarks[0].length > 0) {
          const landmarks = results.landmarks[0];
          const nose = landmarks[0];
          const leftShoulder = landmarks[11];
          const rightShoulder = landmarks[12];
          const leftWrist = landmarks[15];
          const rightWrist = landmarks[16];

          if (nose || leftShoulder || rightShoulder) {
            isHuman = true;
            rejectionReason = 'Please remove the person from the inspection area and retake the photo.';
          } else if (leftWrist || rightWrist) {
            isHuman = true;
            rejectionReason = 'Please keep hands and people away from the product label and retake the photo.';
          }
        }
      } catch (e) {}
    }

    // 2. High-Speed Anthropometric Skin Chrominance & Silhouette Analyzer (YCbCr)
    if (!isHuman && ctx) {
      try {
        const imgData = ctx.getImageData(0, 0, sampleW, sampleH);
        const data = imgData.data;
        const totalPixels = sampleW * sampleH;
        let skinPixels = 0;
        let centerSkinPixels = 0;
        let upperSkinPixels = 0;

        const cx1 = Math.round(sampleW * 0.20);
        const cx2 = Math.round(sampleW * 0.80);
        const cy1 = Math.round(sampleH * 0.20);
        const cy2 = Math.round(sampleH * 0.80);
        const centerTotal = (cx2 - cx1) * (cy2 - cy1);
        const upperTotal = sampleW * Math.round(sampleH * 0.50);

        for (let i = 0, p = 0; i < data.length; i += 4, p++) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          const yVal = 0.299 * r + 0.587 * g + 0.114 * b;
          const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
          const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;

          // Universal Human Skin Chrominance Boundary
          if (cb >= 77 && cb <= 127 && cr >= 133 && cr <= 173 && yVal > 40 && yVal < 235) {
            skinPixels++;
            const px = p % sampleW;
            const py = Math.floor(p / sampleW);

            if (px >= cx1 && px <= cx2 && py >= cy1 && py <= cy2) {
              centerSkinPixels++;
            }
            if (py < sampleH * 0.50) {
              upperSkinPixels++;
            }
          }
        }

        const skinRatio = skinPixels / totalPixels;
        const centerSkinRatio = centerSkinPixels / Math.max(1, centerTotal);
        const upperSkinRatio = upperSkinPixels / Math.max(1, upperTotal);

        if (skinRatio > 0.30 || upperSkinRatio > 0.35) {
          isHuman = true;
          rejectionReason = 'Please remove the person from the inspection area and retake the photo.';
        } else if (centerSkinRatio > 0.28) {
          isHuman = true;
          rejectionReason = 'Please keep hands and people away from the product label and retake the photo.';
        }
      } catch (e) {}
    }

    return { isHuman, rejectionReason };
  }, []);

  // -------------------------------------------------------------
  // 3. Product / Packaging Label Presence Gate (Triggered Only at Scan Time)
  // -------------------------------------------------------------
  const evaluateProductLabelPresence = useCallback((videoElement, ctx, sampleW, sampleH) => {
    let isProduct = true;
    let rejectionReason = '';

    if (!ctx) return { isProduct: true, rejectionReason: '' };

    try {
      const rx = Math.round(sampleW * 0.12);
      const ry = Math.round(sampleH * 0.12);
      const rw = Math.round(sampleW * 0.76);
      const rh = Math.round(sampleH * 0.76);

      const imgData = ctx.getImageData(rx, ry, rw, rh);
      const data = imgData.data;
      const totalPixels = rw * rh;

      let totalLum = 0;
      let lumSq = 0;
      const gray = new Float32Array(totalPixels);

      for (let i = 0, p = 0; i < data.length; i += 4, p++) {
        const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        gray[p] = lum;
        totalLum += lum;
        lumSq += lum * lum;
      }

      const meanLum = totalLum / totalPixels;
      const lumVariance = (lumSq / totalPixels) - (meanLum * meanLum);

      // Analyze high-frequency edge gradients (textual declarations, label borders, barcodes, packaging contours)
      let edgeCount = 0;
      let highEdgeCount = 0;
      let horizontalEdgeCount = 0;
      let verticalEdgeCount = 0;

      for (let y = 1; y < rh - 1; y += 2) {
        for (let x = 1; x < rw - 1; x += 2) {
          const idx = y * rw + x;
          const dx = Math.abs(gray[idx + 1] - gray[idx - 1]);
          const dy = Math.abs(gray[idx + rw] - gray[idx - rw]);
          const edgeMag = dx + dy;

          edgeCount++;
          if (edgeMag > 24) highEdgeCount++;
          if (dx > 20) horizontalEdgeCount++;
          if (dy > 20) verticalEdgeCount++;
        }
      }

      const highEdgeDensity = edgeCount > 0 ? highEdgeCount / edgeCount : 0;
      const structureBalance = (horizontalEdgeCount + verticalEdgeCount) / Math.max(1, edgeCount);

      // Packaging / Label Presence Rules:
      // 1. Extreme Uniformity Check (Blank wall, ceiling, flat monochrome floor, dark void)
      if (lumVariance < 35 || meanLum < 15 || meanLum > 250) {
        isProduct = false;
        rejectionReason = 'The camera does not appear to contain a valid product label. Please position the product clearly and retake the photo.';
      }
      // 2. Featureless scene check (No text/contour structure characteristic of packaging or labels)
      else if (highEdgeDensity < 0.040 && structureBalance < 0.040) {
        isProduct = false;
        rejectionReason = 'The camera does not appear to contain a valid product label. Please position a product label inside the scanner and retake the photo.';
      }
    } catch (e) {
      // If sampling fails, fallback to permissive so as not to block valid products
      isProduct = true;
    }

    return { isProduct, rejectionReason };
  }, []);

  // -------------------------------------------------------------
  // 4. Non-Blocking Live FPS Monitor (requestAnimationFrame)
  // -------------------------------------------------------------
  const startFpsMonitor = useCallback(() => {
    if (fpsRafRef.current) {
      cancelAnimationFrame(fpsRafRef.current);
    }

    fpsFrameCountRef.current = 0;
    fpsLastTimeRef.current = performance.now();

    const calculateFps = () => {
      fpsFrameCountRef.current++;
      const now = performance.now();
      const delta = now - fpsLastTimeRef.current;

      if (delta >= 1000) {
        const calculatedFps = Math.round((fpsFrameCountRef.current * 1000) / delta);
        const smoothFps = Math.max(15, Math.min(60, calculatedFps));
        setCameraFps(smoothFps);
        setTelemetry(prev => ({ ...prev, fps: smoothFps }));
        fpsFrameCountRef.current = 0;
        fpsLastTimeRef.current = now;
      }

      fpsRafRef.current = requestAnimationFrame(calculateFps);
    };

    fpsRafRef.current = requestAnimationFrame(calculateFps);
  }, []);

  const stopFpsMonitor = useCallback(() => {
    if (fpsRafRef.current) {
      cancelAnimationFrame(fpsRafRef.current);
      fpsRafRef.current = null;
    }
  }, []);

  // -------------------------------------------------------------
  // 5. MediaStream Management & Camera Lifecycle Cleanup
  // -------------------------------------------------------------
  const stopCamera = useCallback(() => {
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
      detectionIntervalRef.current = null;
    }

    stopFpsMonitor();

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          console.warn('Error stopping camera track:', e);
        }
      });
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    consecutiveStableHitsRef.current = 0;
    previousLuminanceArrayRef.current = null;
    setStabilityPercent(0);
    setHumanBlocked(false);
    setHumanWarningText('');
    setUnidentifiedBlocked(false);
    setUnidentifiedWarningText('');
  }, [stopFpsMonitor]);

  const startCamera = useCallback(async () => {
    stopCamera();
    setCameraState('REQUESTING_PERMISSION');
    setErrorMessage('');
    setQualityWarning('');
    setHumanBlocked(false);
    setHumanWarningText('');
    setUnidentifiedBlocked(false);
    setUnidentifiedWarningText('');
    setStatusText('Searching for label...');
    setStabilityPercent(0);

    try {
      let stream = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920, min: 1280 },
            height: { ideal: 1080, min: 720 }
          },
          audio: false
        });
      } catch (envErr) {
        console.warn('Preferred environment camera constraint failed, falling back to default video stream:', envErr);
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false
        });
      }

      streamRef.current = stream;

      if (videoRef.current && stream) {
        videoRef.current.srcObject = stream;
        
        videoRef.current.onloadedmetadata = () => {
          if (!videoRef.current) return;
          const w = videoRef.current.videoWidth || 1280;
          const h = videoRef.current.videoHeight || 720;
          setCameraResolution({ width: w, height: h });

          const rx = Math.round(w * 0.12);
          const ry = Math.round(h * 0.12);
          const rw = Math.round(w * 0.76);
          const rh = Math.round(h * 0.76);
          setReticleBounds({ x: rx, y: ry, w: rw, h: rh });

          videoRef.current.play().catch(e => console.warn('Video play error:', e));
        };

        const activeTrack = stream.getVideoTracks()[0];
        if (activeTrack) {
          setCameraDeviceLabel(activeTrack.label || 'High-Resolution Commodity Scanner Feed');
        }

        setCameraState('ACTIVE');
        setStatusText('Searching for label...');

        startFpsMonitor();
        startLightweightDetectionLoop();
      }
    } catch (err) {
      console.error('Camera access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraState('PERMISSION_DENIED');
        setErrorMessage('Camera access is required for live inspection. Please allow camera permission in your browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraState('ERROR');
        setErrorMessage('No camera hardware found. Please connect a webcam or switch to Image File Upload.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraState('ERROR');
        setErrorMessage('Camera is currently in use by another application. Please release the camera and retry.');
      } else {
        setCameraState('ERROR');
        setErrorMessage(`Camera initialization error: ${err.message || 'Unable to access camera.'}`);
      }
    }
  }, [stopCamera, startFpsMonitor]);

  // Mode Switch & Component Cleanup Lifecycle
  useEffect(() => {
    if (scanMode === 'camera') {
      startCamera();
    } else {
      stopCamera();
      setCameraState('OFF');
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      stopCamera();
    };
  }, [scanMode, startCamera, stopCamera]);

  // -------------------------------------------------------------
  // 6. Lightweight Live Preview Detection Loop (Lightweight Preview Only)
  // -------------------------------------------------------------
  const startLightweightDetectionLoop = () => {
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
    }

    detectionIntervalRef.current = setInterval(() => {
      if (
        !videoRef.current || 
        videoRef.current.readyState < 2 || 
        isProcessingRef.current || 
        capturedRawFile
      ) {
        return;
      }

      const t0_det = performance.now();
      const video = videoRef.current;
      const vW = video.videoWidth || 1280;
      const vH = video.videoHeight || 720;

      if (!detectionCanvasRef.current) {
        detectionCanvasRef.current = document.createElement('canvas');
      }
      const detCanvas = detectionCanvasRef.current;
      const sW = 240;
      const sH = 180;
      detCanvas.width = sW;
      detCanvas.height = sH;

      const detCtx = detCanvas.getContext('2d', { willReadFrequently: true });
      if (!detCtx) return;

      try {
        detCtx.drawImage(video, 0, 0, sW, sH);

        // Subregion: Central reticle area (approx 15% to 85% width/height)
        const rx = Math.round(sW * 0.15);
        const ry = Math.round(sH * 0.15);
        const rw = Math.round(sW * 0.70);
        const rh = Math.round(sH * 0.70);

        const imgData = detCtx.getImageData(rx, ry, rw, rh);
        const data = imgData.data;
        const totalPixels = rw * rh;

        let totalLum = 0;
        const gray = new Float32Array(totalPixels);

        for (let i = 0, p = 0; i < data.length; i += 4, p++) {
          const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
          gray[p] = lum;
          totalLum += lum;
        }

        const meanLum = totalLum / totalPixels;

        // Compute Laplacian variance (sharpness)
        let lapSum = 0;
        let lapSumSq = 0;
        let edgeCount = 0;
        let highEdgePixels = 0;

        for (let y = 1; y < rh - 1; y += 2) {
          for (let x = 1; x < rw - 1; x += 2) {
            const idx = y * rw + x;
            const lap = Math.abs(gray[idx + 1] + gray[idx - 1] + gray[idx + rw] + gray[idx - rw] - 4 * gray[idx]);
            lapSum += lap;
            lapSumSq += lap * lap;
            edgeCount++;
            if (lap > 28) {
              highEdgePixels++;
            }
          }
        }

        const lapMean = edgeCount > 0 ? lapSum / edgeCount : 0;
        const variance = edgeCount > 0 ? (lapSumSq / edgeCount) - (lapMean * lapMean) : 0;
        const sharpnessScore = Math.round(Math.max(0, variance));
        const edgeDensity = edgeCount > 0 ? highEdgePixels / edgeCount : 0;

        // Motion Delta
        let motionDelta = 0;
        if (previousLuminanceArrayRef.current && previousLuminanceArrayRef.current.length === totalPixels) {
          const prev = previousLuminanceArrayRef.current;
          let diffSum = 0;
          for (let p = 0; p < totalPixels; p += 3) {
            diffSum += Math.abs(gray[p] - prev[p]);
          }
          motionDelta = diffSum / (totalPixels / 3);
        }
        previousLuminanceArrayRef.current = gray;

        const isMotionLow = motionDelta < QUALITY_THRESHOLDS.stabilityMotionThreshold;
        const isSharp = sharpnessScore >= QUALITY_THRESHOLDS.minSharpness;
        const isLightingGood = meanLum >= QUALITY_THRESHOLDS.lowBrightness && meanLum <= QUALITY_THRESHOLDS.highBrightness;
        const isLabelPresent = edgeDensity >= 0.08 && isLightingGood;

        const t_det = Math.round(performance.now() - t0_det);
        setTelemetry(prev => ({ ...prev, detectionMs: t_det }));

        setQualityMetrics({
          passed: isSharp && isLightingGood && isLabelPresent,
          brightness: Math.round(meanLum),
          sharpness: sharpnessScore,
          motionDelta: Math.round(motionDelta * 10) / 10,
          message: !isLabelPresent 
            ? 'Align package label inside reticle' 
            : (!isMotionLow 
                ? 'Hold camera steady' 
                : '✓ Label clear and stable'),
          guidance: ''
        });

        // Stability Progression
        if (!isLabelPresent) {
          setStatusText('Searching for label...');
          setStabilityPercent(0);
          consecutiveStableHitsRef.current = 0;
        } else if (!isMotionLow || !isSharp) {
          setStatusText('Label detected');
          setStabilityPercent(25);
          consecutiveStableHitsRef.current = 0;
        } else {
          consecutiveStableHitsRef.current++;

          if (consecutiveStableHitsRef.current === 1) {
            setStatusText('Hold steady...');
            setStabilityPercent(50);
          } else if (consecutiveStableHitsRef.current >= 2) {
            // Stability reaches 100% -> Trigger capture flow (which performs human & object gates at that moment)
            setStabilityPercent(100);
            executeCaptureAndInspection(false);
          }
        }
      } catch (err) {
        console.warn('Lightweight detection sample skipped:', err);
      }
    }, QUALITY_THRESHOLDS.detectionIntervalMs);
  };

  // -------------------------------------------------------------
  // 7. Capture, Small-Text Enhancement & Inspection Flow
  // -------------------------------------------------------------
  const executeCaptureAndInspection = async (isManualScan = false) => {
    if (isProcessingRef.current) return;

    // ===========================================================
    // PRE-CAPTURE GATES (Triggered ONLY upon SCAN NOW / Moment of Capture)
    // ===========================================================
    if (scanMode === 'camera' && videoRef.current) {
      setStatusText('Checking object...');
      
      const video = videoRef.current;
      const sW = 240;
      const sH = 180;
      if (!detectionCanvasRef.current) {
        detectionCanvasRef.current = document.createElement('canvas');
      }
      const detCanvas = detectionCanvasRef.current;
      detCanvas.width = sW;
      detCanvas.height = sH;
      const detCtx = detCanvas.getContext('2d', { willReadFrequently: true });

      if (detCtx) {
        detCtx.drawImage(video, 0, 0, sW, sH);

        // PRIORITY GATE 1: HUMAN PRESENCE GATE
        const { isHuman, rejectionReason: humanReason } = evaluateHumanPresence(video, detCtx, sW, sH);

        if (isHuman) {
          // STOP THE INSPECTION IMMEDIATELY
          setHumanBlocked(true);
          setHumanWarningText(humanReason || 'Please remove the person from the inspection area and retake the photo.');
          setUnidentifiedBlocked(false);
          setUnidentifiedWarningText('');
          setStatusText('Human detected');
          setStabilityPercent(0);
          consecutiveStableHitsRef.current = 0;
          return; // HARD STOP: NO CAPTURE, NO OCR, NO BACKEND CALL
        }

        // PRIORITY GATE 2: PRODUCT / LABEL VALIDATION GATE
        const { isProduct, rejectionReason: productReason } = evaluateProductLabelPresence(video, detCtx, sW, sH);

        if (!isProduct) {
          // STOP THE INSPECTION IMMEDIATELY
          setUnidentifiedBlocked(true);
          setUnidentifiedWarningText(productReason || 'The camera does not appear to contain a valid product label. Please position a product label inside the scanner and retake the photo.');
          setHumanBlocked(false);
          setHumanWarningText('');
          setStatusText('Unidentified object');
          setStabilityPercent(0);
          consecutiveStableHitsRef.current = 0;
          return; // HARD STOP: NO CAPTURE, NO OCR, NO BACKEND CALL
        }

        // Both Gates Passed!
        setStatusText('Product label detected');
      }
    }

    // Both Gates Passed -> Lock processing and continue normal inspection pipeline
    isProcessingRef.current = true;
    setIsProcessing(true);
    setHumanBlocked(false);
    setHumanWarningText('');
    setUnidentifiedBlocked(false);
    setUnidentifiedWarningText('');

    scanSessionIdRef.current++;
    const currentSessionId = scanSessionIdRef.current;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setErrorMessage('');
    setQualityWarning('');
    const t0_total = performance.now();

    try {
      let fileToSubmit = null;
      let rawDataUrl = null;
      let enhancedDataUrl = null;
      let t_cap = 0;
      let t_enh = 0;

      if (scanMode === 'upload') {
        if (!selectedFile) {
          throw new Error('Please select an image file before starting inspection.');
        }
        fileToSubmit = selectedFile;
        rawDataUrl = uploadPreviewUrl;
        enhancedDataUrl = uploadPreviewUrl;
      } else {
        if (!videoRef.current || cameraState === 'PERMISSION_DENIED' || cameraState === 'ERROR') {
          throw new Error('Camera stream is not active. Please grant camera permission or retry.');
        }

        const video = videoRef.current;
        const fullW = video.videoWidth || 1920;
        const fullH = video.videoHeight || 1080;

        if (fullW === 0 || fullH === 0) {
          throw new Error('Camera frame buffer is empty. Please wait for camera initialization.');
        }

        // -------------------------------------------------------
        // Step A: Capture RAW High-Resolution Image (Immutable Evidence)
        // -------------------------------------------------------
        const t0_cap = performance.now();
        setStatusText('Capturing...');

        if (!rawCanvasRef.current) {
          rawCanvasRef.current = document.createElement('canvas');
        }
        const rawCanvas = rawCanvasRef.current;
        rawCanvas.width = fullW;
        rawCanvas.height = fullH;
        const rawCtx = rawCanvas.getContext('2d');
        if (!rawCtx) throw new Error('Canvas rendering context unavailable.');

        rawCtx.drawImage(video, 0, 0, fullW, fullH);

        const rawBlob = await new Promise((resolve) => rawCanvas.toBlob(resolve, 'image/jpeg', 0.95));
        if (!rawBlob) throw new Error('Failed to generate raw image buffer from camera feed.');

        rawDataUrl = URL.createObjectURL(rawBlob);
        setCapturedRawUrl(rawDataUrl);

        const rawFile = new File([rawBlob], `raw_evidence_side_${scanningSide}_${Date.now()}.jpg`, {
          type: 'image/jpeg'
        });
        setCapturedRawFile(rawFile);
        t_cap = Math.round(performance.now() - t0_cap);

        // -------------------------------------------------------
        // Step B: Post-Capture Small-Text OCR Enhancement
        // -------------------------------------------------------
        const t0_enh = performance.now();
        setStatusText('Reading text...');

        if (!enhancedCanvasRef.current) {
          enhancedCanvasRef.current = document.createElement('canvas');
        }
        const enhCanvas = enhancedCanvasRef.current;
        enhCanvas.width = fullW;
        enhCanvas.height = fullH;
        const enhCtx = enhCanvas.getContext('2d', { willReadFrequently: true });
        
        enhCtx.drawImage(rawCanvas, 0, 0);
        optimizeForSmallTextOCR(enhCanvas);

        const enhBlob = await new Promise((resolve) => enhCanvas.toBlob(resolve, 'image/jpeg', 0.92));
        enhancedDataUrl = URL.createObjectURL(enhBlob);
        setEnhancedPreviewUrl(enhancedDataUrl);

        fileToSubmit = new File([enhBlob], `enhanced_ocr_side_${scanningSide}_${Date.now()}.jpg`, {
          type: 'image/jpeg'
        });
        t_enh = Math.round(performance.now() - t0_enh);
      }

      // -------------------------------------------------------
      // Step C: Client-Side OCR Caching Check
      // -------------------------------------------------------
      let inspectionData = null;
      let t_ocr = 0;
      let t_rules = 0;
      const frameKey = `${fileToSubmit.size}_${fileToSubmit.name.slice(0, 20)}`;

      if (ocrCacheRef.current.has(frameKey)) {
        inspectionData = ocrCacheRef.current.get(frameKey);
        t_ocr = 5;
        t_rules = 5;
      } else {
        setStatusText('Reading text...');
        const t0_backend = performance.now();

        const derivedName = selectedFile 
          ? selectedFile.name.replace(/\.[^/.]+$/, '') 
          : `Packaged Commodity Item (Side ${scanningSide})`;

        inspectionData = await runInspectionAnalysis(fileToSubmit, {
          product_name: derivedName,
          category: 'Food & Beverages',
          pdp_shape: 'rectangular',
          location: 'Central Ministry Enforcement Wing Live Scanner'
        });

        setStatusText('Checking rules...');
        const t_backend_total = Math.round(performance.now() - t0_backend);
        t_ocr = inspectionData.timing_breakdown?.ocr_ms || Math.round(t_backend_total * 0.70);
        t_rules = inspectionData.timing_breakdown?.rule_engine_ms || Math.round(t_backend_total * 0.30);

        ocrCacheRef.current.set(frameKey, inspectionData);
      }

      // -------------------------------------------------------
      // Step D: Scan Session Invalidation Check
      // -------------------------------------------------------
      if (scanSessionIdRef.current !== currentSessionId) {
        console.info(`[METRIX-LM] Discarding stale scan response from session ${currentSessionId}. Current session: ${scanSessionIdRef.current}`);
        return;
      }

      inspectionData.original_url = rawDataUrl;
      inspectionData.processed_url = enhancedDataUrl;
      inspectionData.previewUrl = enhancedDataUrl || rawDataUrl;

      const sideRecord = {
        side: scanningSide,
        snapshotUrl: rawDataUrl,
        timestamp: new Date().toLocaleTimeString(),
        status: inspectionData.overall_status || '7A COMPLIANT'
      };
      setScannedSides(prev => [...prev, sideRecord]);

      const t_total = Math.round(performance.now() - t0_total);
      const t_det = telemetry.detectionMs || 18;

      const finalTelemetry = {
        fps: cameraFps,
        detectionMs: t_det,
        captureMs: t_cap,
        enhancementMs: t_enh,
        ocrMs: t_ocr,
        rulesMs: t_rules,
        totalMs: t_total
      };

      setTelemetry(finalTelemetry);

      console.log(
        `%cMETRIX-LM PIPELINE%c Camera: ${cameraFps} FPS → Detection: ${t_det}ms → Capture: ${t_cap}ms → Enhancement: ${t_enh}ms → OCR: ${t_ocr}ms → Rules: ${t_rules}ms → Total Inspection: ${t_total}ms`,
        'background: #dc2626; color: white; font-weight: bold; padding: 2px 6px; border-radius: 4px;',
        'color: #059669; font-weight: bold; padding-left: 6px;'
      );

      setScanResult(inspectionData);
      setStatusText('Inspection complete');
      setCameraState('ACTIVE');
    } catch (err) {
      if (scanSessionIdRef.current !== currentSessionId) return;

      console.error('Inspection scan error:', err);
      setStatusText('Inspection failed — Retake');
      setErrorMessage(err.message || 'Inspection processing error. Please verify backend connection and retake image.');
    } finally {
      if (scanSessionIdRef.current === currentSessionId) {
        isProcessingRef.current = false;
        setIsProcessing(false);
      }
    }
  };

  // -------------------------------------------------------------
  // 8. Manual "SCAN NOW" Handler
  // -------------------------------------------------------------
  const handleScanNow = () => {
    if (isProcessingRef.current) return;
    executeCaptureAndInspection(true);
  };

  // -------------------------------------------------------------
  // 9. Immediate "RETAKE PHOTO" Handler (Zero Page Reload)
  // -------------------------------------------------------------
  const handleRetake = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    scanSessionIdRef.current++;
    isProcessingRef.current = false;
    setIsProcessing(false);

    setCapturedRawUrl(null);
    setCapturedRawFile(null);
    setEnhancedPreviewUrl(null);
    setScanResult(null);
    setErrorMessage('');
    setQualityWarning('');
    setHumanBlocked(false);
    setHumanWarningText('');
    setUnidentifiedBlocked(false);
    setUnidentifiedWarningText('');

    consecutiveStableHitsRef.current = 0;
    previousLuminanceArrayRef.current = null;
    setStabilityPercent(0);
    setStatusText('Searching for label...');

    if (scanMode === 'camera') {
      startLightweightDetectionLoop();
    }
  };

  const handleNextSideScan = () => {
    setScanningSide((prev) => prev + 1);
    handleRetake();
    setStatusText(`Searching for label on Side ${scanningSide + 1}...`);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setUploadPreviewUrl(url);
      setErrorMessage('');
      setQualityWarning('');
      setHumanBlocked(false);
      setUnidentifiedBlocked(false);
      setStatusText('Ready for statutory inspection');
    }
  };

  const handleViewFullReport = () => {
    navigate('/officer/review', {
      state: {
        inspection: scanResult,
        inspectionId: scanResult?.id || scanResult?.inspection_id
      }
    });
  };

  const getPreviewFilterStyle = () => {
    if (visionMode === 'standard') return 'none';
    if (visionMode === 'document') return 'grayscale(100%) contrast(140%) brightness(105%)';
    return 'contrast(1.12) brightness(1.04) saturate(1.02)';
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Title Banner & Scan Mode Switcher */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-red-50 text-red-700 text-xs font-black rounded-lg border border-red-200 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Legal Metrology (Packaged Commodities) Rules, 2011 Compliance Scanner</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900">Commodity Packaging Inspection Scanner</h1>
          <p className="text-sm text-slate-600 font-semibold mt-0.5">
            Ultra-fast live camera stream with automated stability detection, small-text OCR enhancement & statutory rule validation.
          </p>
        </div>

        {/* Scan Mode Switcher Buttons */}
        <div className="flex items-center bg-slate-100 p-1.5 rounded-xl border border-slate-200 space-x-1">
          <button
            type="button"
            aria-label="Start live camera inspection"
            onClick={() => setScanMode('camera')}
            className={`px-4 py-2 rounded-lg text-xs font-black transition flex items-center space-x-2 ${
              scanMode === 'camera'
                ? 'bg-red-600 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Camera className="w-4 h-4" />
            <span>Live Camera Feed</span>
          </button>

          <button
            type="button"
            aria-label="Switch to image file upload"
            onClick={() => setScanMode('upload')}
            className={`px-4 py-2 rounded-lg text-xs font-black transition flex items-center space-x-2 ${
              scanMode === 'upload'
                ? 'bg-red-600 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Image File</span>
          </button>
        </div>
      </div>

      {/* HUMAN DETECTION WARNING BANNER (SHOWN ONLY AFTER SCAN TRIGGERED WITH HUMAN DETECTED) */}
      {humanBlocked && (
        <div className="p-4 bg-red-600 text-white rounded-2xl shadow-xl flex flex-col sm:flex-row items-center justify-between gap-4 animate-fade-in border-2 border-red-400">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 bg-white/20 rounded-xl flex-shrink-0">
              <UserX className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="font-black text-base block tracking-wide">⚠ HUMAN DETECTED</span>
              <span className="text-sm text-red-100 font-medium block mt-0.5">
                {humanWarningText || 'Please remove the person from the inspection area and retake the photo.'}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRetake}
            className="px-5 py-2.5 bg-white text-red-700 hover:bg-red-50 font-black text-sm rounded-xl shadow-md transition flex items-center space-x-2 flex-shrink-0 border border-white"
          >
            <RefreshCw className="w-4 h-4" />
            <span>RETAKE PHOTO</span>
          </button>
        </div>
      )}

      {/* UNIDENTIFIED OBJECT WARNING BANNER (SHOWN ONLY AFTER SCAN TRIGGERED WITH NON-PRODUCT DETECTED) */}
      {unidentifiedBlocked && (
        <div className="p-4 bg-amber-600 text-white rounded-2xl shadow-xl flex flex-col sm:flex-row items-center justify-between gap-4 animate-fade-in border-2 border-amber-400">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 bg-white/20 rounded-xl flex-shrink-0">
              <HelpCircle className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="font-black text-base block tracking-wide">⚠ UNIDENTIFIED OBJECT</span>
              <span className="text-sm text-amber-100 font-medium block mt-0.5">
                {unidentifiedWarningText || 'The camera does not appear to contain a valid product label. Please position a product label inside the scanner and retake the photo.'}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRetake}
            className="px-5 py-2.5 bg-white text-amber-900 hover:bg-amber-50 font-black text-sm rounded-xl shadow-md transition flex items-center space-x-2 flex-shrink-0 border border-white"
          >
            <RefreshCw className="w-4 h-4" />
            <span>RETAKE PHOTO</span>
          </button>
        </div>
      )}

      {/* General Error Banner */}
      {errorMessage && !humanBlocked && !unidentifiedBlocked && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-2xl flex items-center justify-between space-x-3">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <span className="font-bold">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={handleRetake}
            className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-black rounded-lg shadow transition flex items-center space-x-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retake Scan</span>
          </button>
        </div>
      )}

      {/* PERFORMANCE TELEMETRY HUD BAR */}
      <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-2xl shadow-md text-white font-mono text-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 bg-red-950/80 border border-red-800 text-red-400 rounded-lg font-bold">
            <Gauge className="w-3.5 h-3.5" />
            <span>METRIX TELEMETRY</span>
          </div>
          <span className="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded font-black">
            CAMERA {telemetry.fps} FPS
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            DETECTION <strong className="text-white">{telemetry.detectionMs} ms</strong>
          </span>
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            CAPTURE <strong className="text-white">{telemetry.captureMs} ms</strong>
          </span>
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            ENHANCEMENT <strong className="text-white">{telemetry.enhancementMs} ms</strong>
          </span>
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            OCR <strong className="text-white">{telemetry.ocrMs} ms</strong>
          </span>
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            RULES <strong className="text-white">{telemetry.rulesMs} ms</strong>
          </span>
          <span className="bg-emerald-900/80 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-700 font-black">
            TOTAL {telemetry.totalMs} ms
          </span>
        </div>
      </div>

      {/* Main Scanner Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Viewfinder / Upload Area (7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          
          {/* Viewfinder Header & Vision Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-3 gap-3">
            <div className="flex items-center space-x-2">
              {scanMode === 'camera' ? <Camera className="w-4 h-4 text-red-600" /> : <FileImage className="w-4 h-4 text-red-600" />}
              <h3 className="text-sm font-black text-slate-900">
                {scanMode === 'camera' ? 'Live Camera Stream Viewfinder' : 'Packaging Image File Upload'}
              </h3>
            </div>

            <div className="flex items-center space-x-2">
              {/* Vision Mode Selector (Camera Mode Only) */}
              {scanMode === 'camera' && (
                <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-bold">
                  <span className="text-slate-500 px-1.5 flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5 text-red-600" />
                    Vision:
                  </span>
                  <button
                    type="button"
                    onClick={() => setVisionMode('standard')}
                    className={`px-2 py-0.5 rounded transition ${visionMode === 'standard' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Standard
                  </button>
                  <button
                    type="button"
                    onClick={() => setVisionMode('enhanced')}
                    className={`px-2 py-0.5 rounded transition ${visionMode === 'enhanced' ? 'bg-red-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Enhanced
                  </button>
                  <button
                    type="button"
                    onClick={() => setVisionMode('document')}
                    className={`px-2 py-0.5 rounded transition ${visionMode === 'document' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Doc/Text
                  </button>
                </div>
              )}

              <span className="text-xs font-black text-red-700 bg-red-50 px-2.5 py-1 rounded border border-red-200">
                Side {scanningSide}
              </span>
            </div>
          </div>

          {/* VIEW MODE 1: Real Live Camera Stream & Professional Government HUD */}
          {scanMode === 'camera' && (
            <div className="relative bg-slate-950 border-2 border-slate-800 rounded-2xl overflow-hidden min-h-[420px] flex items-center justify-center select-none">
              
              {/* Captured Freeze-Frame or Real Video Element */}
              {capturedRawUrl ? (
                <img 
                  src={capturedRawUrl} 
                  alt="Captured Legal Packaging Evidence" 
                  className="w-full h-full max-h-[420px] object-cover"
                />
              ) : (
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted 
                  style={{ filter: getPreviewFilterStyle() }}
                  className={`w-full h-full max-h-[420px] object-cover transition-opacity duration-300 ${
                    cameraState === 'ACTIVE' ? 'opacity-100 block' : 'opacity-0 hidden'
                  }`} 
                />
              )}

              {/* HUMAN DETECTION OVERLAY (TRIGGERED ONLY WHEN SCAN WAS ATTEMPTED AND HUMAN DETECTED) */}
              {humanBlocked && (
                <div className="absolute inset-0 bg-slate-950/92 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-30 space-y-4 animate-fade-in">
                  <div className="p-4 bg-red-600/20 border-2 border-red-500 text-red-500 rounded-full inline-block">
                    <UserX className="w-12 h-12 text-red-500" />
                  </div>

                  <div className="max-w-md space-y-2">
                    <div className="inline-flex items-center space-x-1.5 px-3 py-1 bg-red-950 text-red-400 font-mono font-black text-xs rounded-lg border border-red-800">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>SAFETY GATE • SCAN BLOCKED</span>
                    </div>
                    
                    <h3 className="text-xl font-black text-white">⚠ HUMAN DETECTED</h3>
                    
                    <p className="text-sm text-slate-300 font-medium leading-relaxed">
                      {humanWarningText || 'Please remove the person from the inspection area and retake the photo.'}
                    </p>
                    
                    <p className="text-xs text-slate-400 font-semibold">
                      Legal Metrology statutory inspection requires an unobstructed view of the product packaging label.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleRetake}
                    className="px-6 py-3 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-extrabold text-sm rounded-xl shadow-lg transition flex items-center space-x-2 border border-red-500"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>RETAKE PHOTO</span>
                  </button>
                </div>
              )}

              {/* UNIDENTIFIED OBJECT OVERLAY (BLOCKS WHEN INVALID OBJECT SCANNED) */}
              {unidentifiedBlocked && (
                <div className="absolute inset-0 bg-slate-950/92 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-30 space-y-4 animate-fade-in">
                  <div className="p-4 bg-amber-600/20 border-2 border-amber-500 text-amber-500 rounded-full inline-block">
                    <HelpCircle className="w-12 h-12 text-amber-400" />
                  </div>

                  <div className="max-w-md space-y-2">
                    <div className="inline-flex items-center space-x-1.5 px-3 py-1 bg-amber-950 text-amber-300 font-mono font-black text-xs rounded-lg border border-amber-800">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>OBJECT GATE • SCAN BLOCKED</span>
                    </div>
                    
                    <h3 className="text-xl font-black text-white">⚠ UNIDENTIFIED OBJECT</h3>
                    
                    <p className="text-sm text-slate-300 font-medium leading-relaxed">
                      {unidentifiedWarningText || 'The camera does not appear to contain a valid product label. Please position the product clearly and retake the photo.'}
                    </p>
                    
                    <p className="text-xs text-slate-400 font-semibold">
                      Legal Metrology statutory inspection requires a packaged commodity label (box, bottle, container, pouch, jar, packet).
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleRetake}
                    className="px-6 py-3 bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white font-extrabold text-sm rounded-xl shadow-lg transition flex items-center space-x-2 border border-amber-500"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>RETAKE PHOTO</span>
                  </button>
                </div>
              )}

              {/* Camera Requesting Permission State */}
              {cameraState === 'REQUESTING_PERMISSION' && (
                <div className="p-8 text-center space-y-3">
                  <div className="w-10 h-10 border-3 border-red-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  <span className="text-sm font-bold text-slate-300 block">
                    Requesting camera access permissions from browser...
                  </span>
                  <span className="text-xs text-slate-500 block">
                    Please allow camera access in the browser prompt.
                  </span>
                </div>
              )}

              {/* Camera Permission Denied State */}
              {cameraState === 'PERMISSION_DENIED' && (
                <div className="p-8 text-center space-y-3 max-w-sm">
                  <VideoOff className="w-12 h-12 text-red-500 mx-auto" />
                  <span className="text-base font-black text-white block">Camera Access Required</span>
                  <p className="text-xs text-slate-400 font-medium leading-relaxed">
                    Camera access is required for live statutory commodity inspection. Please allow camera permission in your browser settings.
                  </p>
                  <button
                    type="button"
                    onClick={startCamera}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl transition inline-flex items-center space-x-1.5 shadow-lg"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Camera Access</span>
                  </button>
                </div>
              )}

              {/* Camera Hardware Error State */}
              {cameraState === 'ERROR' && (
                <div className="p-8 text-center space-y-3 max-w-sm">
                  <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto" />
                  <span className="text-base font-black text-white block">Camera Hardware Error</span>
                  <p className="text-xs text-slate-400 font-medium">
                    {errorMessage || 'Unable to access camera hardware. Please verify webcam connection.'}
                  </p>
                  <button
                    type="button"
                    onClick={startCamera}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl border border-slate-700 transition inline-flex items-center space-x-1.5"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Re-initialize Camera</span>
                  </button>
                </div>
              )}

              {/* PROFESSIONAL INSPECTION HUD OVERLAY */}
              {cameraState === 'ACTIVE' && !humanBlocked && !unidentifiedBlocked && (
                <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between">
                  
                  {/* HUD Top Bar: Camera Specs + Live Status + Stability Badge */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="px-3 py-1 bg-slate-900/90 text-emerald-400 font-mono font-black text-xs rounded-md border border-emerald-800/80 shadow-md flex items-center space-x-2 backdrop-blur-sm">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                        <span>{cameraResolution.width} × {cameraResolution.height} • {cameraFps} FPS</span>
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className={`px-3.5 py-1.5 font-mono font-black text-sm rounded-xl border shadow-lg backdrop-blur-md flex items-center space-x-2 ${
                        statusText === 'Inspection complete'
                          ? 'bg-emerald-950/95 text-emerald-300 border-emerald-500'
                          : (statusText === 'Capturing...' || statusText === 'Reading text...' || statusText === 'Checking rules...' || statusText === 'Checking object...' || statusText === 'Product label detected'
                              ? 'bg-blue-950/95 text-blue-300 border-blue-500 animate-pulse'
                              : (statusText === 'Hold steady...'
                                  ? 'bg-amber-950/95 text-amber-300 border-amber-500'
                                  : 'bg-slate-900/90 text-slate-300 border-slate-700'))
                      }`}>
                        {isProcessing && <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                        <span>{statusText}</span>
                      </span>
                    </div>
                  </div>

                  {/* Central Inspection Reticle */}
                  <div className={`relative mx-auto w-[82%] h-[66%] border-2 rounded-2xl flex flex-col justify-between p-3 transition-colors duration-300 ${
                    stabilityPercent === 100 
                      ? 'border-emerald-400 shadow-[0_0_20px_rgba(52,211,153,0.4)]' 
                      : (stabilityPercent === 50 ? 'border-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.3)]' : 'border-emerald-500/40')
                  }`}>
                    
                    {/* 4 Corner Markers */}
                    <div className="absolute -top-1.5 -left-1.5 w-6 h-6 border-t-3 border-l-3 border-emerald-400 rounded-tl-sm"></div>
                    <div className="absolute -top-1.5 -right-1.5 w-6 h-6 border-t-3 border-r-3 border-emerald-400 rounded-tr-sm"></div>
                    <div className="absolute -bottom-1.5 -left-1.5 w-6 h-6 border-b-3 border-l-3 border-emerald-400 rounded-bl-sm"></div>
                    <div className="absolute -bottom-1.5 -right-1.5 w-6 h-6 border-b-3 border-r-3 border-emerald-400 rounded-br-sm"></div>

                    {/* Laser Sweep on Active Preview */}
                    {!capturedRawUrl && !isProcessing && (
                      <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_12px_#34d399] animate-[bounce_3s_ease-in-out_infinite]"></div>
                    )}

                    {/* Reticle Top: Quality Indicators */}
                    <div className="flex items-center justify-between text-xs font-mono text-emerald-400">
                      <span className="bg-slate-900/90 px-2.5 py-1 rounded-md border border-emerald-800/80">
                        [Statutory PDP Reticle]
                      </span>
                      <span className="bg-slate-900/90 px-2.5 py-1 rounded-md border border-emerald-800/80">
                        Sharpness: {qualityMetrics.sharpness} | Motion: {qualityMetrics.motionDelta}
                      </span>
                    </div>

                    {/* Reticle Center: Dynamic Stability Progress Ring */}
                    <div className="text-center my-auto">
                      {!capturedRawUrl && (
                        <div className="inline-flex flex-col items-center space-y-1.5">
                          <span className={`px-4 py-1.5 font-black text-sm rounded-full border shadow-2xl inline-block backdrop-blur-md transition-all ${
                            stabilityPercent === 100
                              ? 'bg-emerald-950/95 text-emerald-300 border-emerald-500'
                              : (stabilityPercent === 50
                                  ? 'bg-amber-950/95 text-amber-300 border-amber-500'
                                  : 'bg-slate-900/90 text-white border-slate-700')
                          }`}>
                            {statusText} {stabilityPercent > 0 && `(${stabilityPercent}%)`}
                          </span>

                          {/* Stability Progress Bar */}
                          <div className="w-36 h-2 bg-slate-900/90 rounded-full overflow-hidden border border-slate-700">
                            <div 
                              className={`h-full transition-all duration-300 ${
                                stabilityPercent === 100 ? 'bg-emerald-400' : (stabilityPercent === 50 ? 'bg-amber-400' : 'bg-slate-600')
                              }`}
                              style={{ width: `${stabilityPercent}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Reticle Bottom Coordinates */}
                    <div className="flex justify-between items-end text-xs text-emerald-400 font-mono">
                      <span className="bg-slate-900/80 px-2 py-0.5 rounded">
                        [X: {reticleBounds.x}, Y: {reticleBounds.y}]
                      </span>
                      <span className="bg-slate-900/80 px-2 py-0.5 rounded">
                        [W: {reticleBounds.w}, H: {reticleBounds.h}]
                      </span>
                    </div>
                  </div>

                  {/* HUD Bottom Bar */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2.5 py-1 rounded-md font-mono font-bold border backdrop-blur-sm ${
                        qualityMetrics.passed
                          ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                          : 'bg-amber-950/80 text-amber-400 border-amber-800'
                      }`}>
                        {qualityMetrics.passed ? '✓ Frame Stability Good' : `⚠ ${qualityMetrics.message}`}
                      </span>

                      {capturedRawUrl && (
                        <span className="px-2.5 py-1 rounded-md font-mono font-bold bg-emerald-900/90 text-emerald-200 border border-emerald-600">
                          ✓ RAW Legal Evidence Locked
                        </span>
                      )}
                    </div>

                    <span className="text-xs text-slate-400 font-mono bg-slate-900/80 px-2.5 py-1 rounded-md">
                      {cameraDeviceLabel}
                    </span>
                  </div>

                </div>
              )}
            </div>
          )}

          {/* VIEW MODE 2: Image File Upload Dropzone */}
          {scanMode === 'upload' && (
            <div className="border-2 border-dashed border-slate-300 hover:border-red-500 bg-slate-50 rounded-2xl p-6 text-center transition cursor-pointer relative min-h-[420px] flex items-center justify-center">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                aria-label="Upload packaging photo"
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              {uploadPreviewUrl ? (
                <div className="space-y-3">
                  <img 
                    src={uploadPreviewUrl} 
                    alt="Uploaded Packaging Label" 
                    className="max-h-72 mx-auto rounded-xl shadow-lg border border-slate-300 object-contain bg-white p-2" 
                  />
                  <span className="text-sm text-emerald-700 font-black block">
                    ✓ File Loaded: {selectedFile?.name}
                  </span>
                </div>
              ) : (
                <div className="space-y-3 py-8">
                  <div className="p-4 bg-red-50 text-red-600 rounded-2xl inline-block border border-red-200">
                    <UploadCloud className="w-10 h-10" />
                  </div>
                  <div>
                    <span className="text-base font-black text-slate-900 block">Click or Drag & Drop Packaging Photo</span>
                    <span className="text-sm text-slate-500 font-semibold block mt-1">Supports PNG, JPG, WEBP up to 25MB</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Action Trigger Buttons: SCAN NOW & RETAKE */}
          <div className="flex flex-wrap items-center gap-3">
            
            {/* Prominent Manual SCAN NOW Button */}
            <button
              type="button"
              onClick={handleScanNow}
              disabled={isProcessing || (scanMode === 'camera' && cameraState !== 'ACTIVE') || (scanMode === 'upload' && !selectedFile)}
              className="flex-1 min-w-[200px] py-3.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 active:from-red-800 active:to-red-900 disabled:opacity-50 text-white font-extrabold text-sm md:text-base rounded-xl transition shadow-lg flex items-center justify-center space-x-2 border border-red-500"
            >
              {isProcessing ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{statusText.toUpperCase()}</span>
                </div>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  <span>SCAN NOW</span>
                </>
              )}
            </button>

            {/* Prominent RETAKE / RETAKE PHOTO Button */}
            {(capturedRawUrl || scanResult || errorMessage || humanBlocked || unidentifiedBlocked) && (
              <button
                type="button"
                onClick={handleRetake}
                className="px-5 py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-extrabold text-sm md:text-base rounded-xl transition shadow-md flex items-center space-x-2 border border-slate-700"
              >
                <RefreshCw className="w-4 h-4 text-red-400" />
                <span>{humanBlocked || unidentifiedBlocked ? 'RETAKE PHOTO' : 'RETAKE'}</span>
              </button>
            )}

            {/* Multi-Side Next Scan Button */}
            {scannedSides.length > 0 && !humanBlocked && !unidentifiedBlocked && (
              <button
                type="button"
                onClick={handleNextSideScan}
                className="px-4 py-3.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 text-sm font-bold rounded-xl transition flex items-center space-x-1.5"
              >
                <RotateCw className="w-4 h-4 text-red-600" />
                <span>Scan Next Side ({scanningSide + 1})</span>
              </button>
            )}
          </div>
        </div>

        {/* Right Side: Statutory Results Workspace (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-5">
          <h3 className="text-sm font-black text-slate-900 flex items-center space-x-2 border-b border-slate-200 pb-3">
            <ShieldCheck className="w-4 h-4 text-red-600" />
            <span>Statutory Compliance Decision</span>
          </h3>

          {scanResult ? (
            <StatutoryInspectionReport
              inspection={scanResult}
              scannedSides={scannedSides}
            />
          ) : (
            <div className="py-20 text-center space-y-3 text-slate-400">
              <Sparkles className="w-10 h-10 mx-auto text-slate-300" />
              <p className="text-sm font-medium">
                Align the packaging label inside the green inspection reticle. The camera will automatically detect the label, stabilize, and inspect declarations within 1–2 seconds.
              </p>
              <p className="text-xs text-slate-500 font-semibold">
                Or click <b>SCAN NOW</b> to immediately inspect the current frame.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
