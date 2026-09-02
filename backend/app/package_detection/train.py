"""
train.py - Ultralytics YOLO Package Detection Model Training Script
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_ROOT = os.path.dirname(BASE_DIR)
DEFAULT_YAML_PATH = os.path.join(WORKSPACE_ROOT, "dataset", "data.yaml")
DEFAULT_PROJECT_PATH = os.path.join(BASE_DIR, "models_trained")

def train_yolo_package_model(
    data_yaml_path: str = DEFAULT_YAML_PATH,
    epochs: int = 50,
    img_size: int = 640,
    batch_size: int = 16
):
    """
    Trains Ultralytics YOLOv8 object detection model on the packaged commodity dataset.
    """
    try:
        from ultralytics import YOLO  # type: ignore
        print(f"Initializing YOLOv8 model training with data: {data_yaml_path}")
        model = YOLO("yolov8n.pt")
        results = model.train(
            data=data_yaml_path,
            epochs=epochs,
            imgsz=img_size,
            batch=batch_size,
            name="package_detector",
            project=DEFAULT_PROJECT_PATH
        )
        print("YOLO Training complete. Trained weights saved to:", results.save_dir)
        return results
    except Exception as e:
        print(f"YOLO Training failed: {e}")
        return None

if __name__ == "__main__":
    train_yolo_package_model()
