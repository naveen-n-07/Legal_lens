"""
package_detection module initialization
"""
from app.package_detection.yolo_detector import YoloRegionDetector
from app.package_detection.detector import PackageDetector

__all__ = ["YoloRegionDetector", "PackageDetector"]
