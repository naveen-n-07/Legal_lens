import React, { useRef, useState, useEffect, useCallback } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from 'lucide-react';

export default function ImageOverlay({ imgSrc, alt, showAnnotations = true, annotations = [] }) {
  const containerRef = useRef(null);
  const imgRef = useRef(null);
  
  // Zoom & Pan state for mobile touch & desktop inspection
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [touchStartDist, setTouchStartDist] = useState(null);
  const [touchStartPos, setTouchStartPos] = useState({ x: 0, y: 0 });

  // Bounding box scale mapping
  const [scale, setScale] = useState({ x: 1, y: 1 });

  const updateScale = useCallback(() => {
    if (imgRef.current) {
      const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imgRef.current;
      if (naturalWidth && naturalHeight) {
        setScale({
          x: clientWidth / naturalWidth,
          y: clientHeight / naturalHeight,
        });
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, [updateScale]);

  // Touch Gesture Handlers (Pinch-to-zoom and touch pan)
  const getTouchDistance = (e) => {
    if (e.touches.length < 2) return null;
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    return Math.hypot(dx, dy);
  };

  const handleTouchStart = (e) => {
    if (e.touches.length === 2) {
      const dist = getTouchDistance(e);
      setTouchStartDist(dist);
    } else if (e.touches.length === 1 && zoomLevel > 1) {
      setIsPanning(true);
      setTouchStartPos({
        x: e.touches[0].clientX - panOffset.x,
        y: e.touches[0].clientY - panOffset.y
      });
    }
  };

  const handleTouchMove = (e) => {
    if (e.touches.length === 2 && touchStartDist) {
      e.preventDefault();
      const currentDist = getTouchDistance(e);
      if (currentDist) {
        const factor = currentDist / touchStartDist;
        setZoomLevel(prev => Math.min(4, Math.max(1, prev * (factor > 1 ? 1.05 : 0.95))));
        setTouchStartDist(currentDist);
      }
    } else if (e.touches.length === 1 && isPanning && zoomLevel > 1) {
      e.preventDefault();
      setPanOffset({
        x: e.touches[0].clientX - touchStartPos.x,
        y: e.touches[0].clientY - touchStartPos.y
      });
    }
  };

  const handleTouchEnd = () => {
    setTouchStartDist(null);
    setIsPanning(false);
  };

  const handleZoomIn = () => setZoomLevel(prev => Math.min(4, prev + 0.5));
  const handleZoomOut = () => {
    setZoomLevel(prev => {
      const next = Math.max(1, prev - 0.5);
      if (next === 1) setPanOffset({ x: 0, y: 0 });
      return next;
    });
  };
  const handleResetZoom = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-full min-h-[300px] flex items-center justify-center overflow-hidden rounded-2xl bg-slate-950/90 select-none touch-none"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Zoom / Pan Action Bar Overlay (Mobile touch optimized min 44px) */}
      <div className="absolute top-3 right-3 z-30 flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md p-1 rounded-xl border border-slate-700/60 shadow-lg">
        <button
          type="button"
          onClick={handleZoomIn}
          className="w-9 h-9 sm:w-10 sm:h-10 flex items-center justify-center text-slate-200 hover:text-white hover:bg-slate-800/80 active:bg-slate-700 rounded-lg transition touch-manipulation cursor-pointer"
          title="Zoom in (Pinch to zoom)"
        >
          <ZoomIn className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          disabled={zoomLevel <= 1}
          className="w-9 h-9 sm:w-10 sm:h-10 flex items-center justify-center text-slate-200 hover:text-white hover:bg-slate-800/80 active:bg-slate-700 disabled:opacity-40 rounded-lg transition touch-manipulation cursor-pointer"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>
        {zoomLevel > 1 && (
          <button
            type="button"
            onClick={handleResetZoom}
            className="px-2.5 h-9 sm:h-10 flex items-center justify-center gap-1 text-2xs font-mono font-bold text-amber-400 hover:bg-slate-800/80 active:bg-slate-700 rounded-lg transition touch-manipulation cursor-pointer"
            title="Reset Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{Math.round(zoomLevel * 100)}%</span>
          </button>
        )}
      </div>

      {/* Helper Pill on Mobile */}
      <div className="absolute bottom-3 left-3 z-30 px-2.5 py-1 bg-slate-900/80 backdrop-blur-md rounded-lg border border-slate-700/50 text-[11px] font-mono text-slate-300 pointer-events-none">
        {zoomLevel > 1 ? `Zoom: ${Math.round(zoomLevel * 100)}% • Drag to Pan` : 'Pinch or tap + to zoom label'}
      </div>

      {/* Main Image & Bounding Box Spatial Transform Canvas */}
      <div 
        className="relative inline-block transition-transform duration-75 will-change-transform"
        style={{
          transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
          transformOrigin: 'center center'
        }}
      >
        <img
          ref={imgRef}
          src={imgSrc}
          alt={alt}
          className="w-full h-auto max-h-[480px] object-contain block mx-auto pointer-events-none"
          onLoad={updateScale}
        />
        
        {showAnnotations && annotations && annotations.length > 0 && (
          <svg
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            style={{ zIndex: 10 }}
          >
            {annotations.map((ann, idx) => {
              if (!ann.bbox || ann.bbox.length !== 4) return null;
              const [x1, y1, x2, y2] = ann.bbox;
              
              let renderedWidth = imgRef.current?.clientWidth || 0;
              let renderedHeight = imgRef.current?.clientHeight || 0;
              let offsetX = 0;
              let offsetY = 0;
              
              if (imgRef.current) {
                const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imgRef.current;
                if (!naturalWidth || !naturalHeight) return null;

                const imgRatio = naturalWidth / naturalHeight;
                const containerRatio = clientWidth / clientHeight;

                if (imgRatio > containerRatio) {
                  renderedWidth = clientWidth;
                  renderedHeight = clientWidth / imgRatio;
                  offsetY = (clientHeight - renderedHeight) / 2;
                } else {
                  renderedHeight = clientHeight;
                  renderedWidth = clientHeight * imgRatio;
                  offsetX = (clientWidth - renderedWidth) / 2;
                }
                
                const currentScaleX = renderedWidth / naturalWidth;
                const currentScaleY = renderedHeight / naturalHeight;
                
                const boxWidth = (x2 - x1) * currentScaleX;
                const boxHeight = (y2 - y1) * currentScaleY;
                const boxX = x1 * currentScaleX + offsetX;
                const boxY = y1 * currentScaleY + offsetY;

                let strokeColor = "#3b82f6";
                let bgColor = "rgba(59, 130, 246, 0.18)";
                if (ann.status === "PASS") {
                  strokeColor = "#22c55e";
                  bgColor = "rgba(34, 197, 94, 0.2)";
                } else if (ann.status === "FAIL") {
                  strokeColor = "#ef4444";
                  bgColor = "rgba(239, 68, 68, 0.25)";
                } else if (ann.status === "NEEDS_REVIEW" || ann.status === "REVIEW") {
                  strokeColor = "#f59e0b";
                  bgColor = "rgba(245, 158, 11, 0.22)";
                }

                return (
                  <g key={idx}>
                    <rect
                      x={boxX}
                      y={boxY}
                      width={boxWidth}
                      height={boxHeight}
                      stroke={strokeColor}
                      strokeWidth="2.5"
                      fill={bgColor}
                      rx="4"
                    />
                    {ann.rule_name && (
                      <text
                        x={boxX + 3}
                        y={boxY > 18 ? boxY - 5 : boxY + 14}
                        fill={strokeColor}
                        fontSize="11"
                        fontWeight="bold"
                        fontFamily="monospace"
                        style={{ textShadow: "0 0 4px #000000, 0 0 2px #000000" }}
                      >
                        {ann.rule_name.substring(0, 22)}
                      </text>
                    )}
                  </g>
                );
              }
              return null;
            })}
          </svg>
        )}
      </div>
    </div>
  );
}
