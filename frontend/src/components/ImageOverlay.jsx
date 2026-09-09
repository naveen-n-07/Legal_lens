import React, { useRef, useState, useEffect } from 'react';

export default function ImageOverlay({ imgSrc, alt, showAnnotations, annotations }) {
  const imgRef = useRef(null);
  const [scale, setScale] = useState({ x: 1, y: 1 });

  // Recalculate scaling whenever window resizes or image loads
  const updateScale = () => {
    if (imgRef.current) {
      const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imgRef.current;
      if (naturalWidth && naturalHeight) {
        setScale({
          x: clientWidth / naturalWidth,
          y: clientHeight / naturalHeight,
        });
      }
    }
  };

  useEffect(() => {
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, []);

  return (
    <div className="relative inline-block w-full flex justify-center h-full">
      <img
        ref={imgRef}
        src={imgSrc}
        alt={alt}
        className="w-full h-auto max-h-[500px] object-contain"
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
            
            // Adjust to center image offset (since object-contain might add padding)
            let renderedWidth = imgRef.current?.clientWidth || 0;
            let renderedHeight = imgRef.current?.clientHeight || 0;
            let offsetX = 0;
            let offsetY = 0;
            
            if (imgRef.current) {
              const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imgRef.current;
              const imgRatio = naturalWidth / naturalHeight;
              const containerRatio = clientWidth / clientHeight;

              if (imgRatio > containerRatio) {
                // Image is limited by width
                renderedWidth = clientWidth;
                renderedHeight = clientWidth / imgRatio;
                offsetY = (clientHeight - renderedHeight) / 2;
              } else {
                // Image is limited by height
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

              // Color based on status
              let strokeColor = "#3b82f6"; // default blue
              let bgColor = "rgba(59, 130, 246, 0.1)";
              if (ann.status === "PASS") {
                strokeColor = "#22c55e"; // green-500
                bgColor = "rgba(34, 197, 94, 0.15)";
              } else if (ann.status === "FAIL") {
                strokeColor = "#ef4444"; // red-500
                bgColor = "rgba(239, 68, 68, 0.15)";
              } else if (ann.status === "NEEDS_REVIEW" || ann.status === "REVIEW") {
                strokeColor = "#f59e0b"; // amber-500
                bgColor = "rgba(245, 158, 11, 0.15)";
              }

              return (
                <g key={idx}>
                  <rect
                    x={boxX}
                    y={boxY}
                    width={boxWidth}
                    height={boxHeight}
                    stroke={strokeColor}
                    strokeWidth="2"
                    fill={bgColor}
                    rx="4"
                  />
                  {ann.rule_name && (
                    <text
                      x={boxX}
                      y={boxY > 15 ? boxY - 5 : boxY + boxHeight + 15}
                      fill={strokeColor}
                      fontSize="10"
                      fontWeight="bold"
                      fontFamily="monospace"
                      style={{ textShadow: "1px 1px 2px rgba(0,0,0,0.8)" }}
                    >
                      {ann.rule_name.substring(0, 20)}
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
  );
}
