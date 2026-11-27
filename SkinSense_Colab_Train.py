# SkinSense YOLO26 classification training script
# Run in Google Colab after uploading or mounting the eight-class dataset.

import json
import shutil
from pathlib import Path

from ultralytics import YOLO


# Change this to the folder containing the class subfolders. Ultralytics
# classification datasets should contain train/ and val/ directories.
DATASET_DIR = "/content/drive/MyDrive/finalclasses/SkinSense8/images"
BASE_MODEL = "yolo26n-cls.pt"
OUTPUT_DIR = "/content/runs/classify"
RUN_NAME = "skinsense_yolo26"
BEST_MODEL_OUTPUT = "/content/best.pt"
CLASS_NAMES_OUTPUT = "/content/class_names.json"

CLASS_NAMES = [
    "Actinic Keratosis",
    "Cutaneous Candidiasis",
    "Folliculitis / Furunculosis",
    "Impetigo",
    "Irritant Contact Dermatitis",
    "Occupational Hand Eczema",
    "Sunburn / Photodermatitis",
    "Tinea (Ringworm / Athlete's Foot)",
]


def validate_dataset(dataset_dir: str) -> None:
    root = Path(dataset_dir)
    if not root.exists():
        raise FileNotFoundError(f"Dataset folder not found: {root}")
    missing = [split for split in ("train", "val") if not (root / split).is_dir()]
    if missing:
        raise ValueError(
            "YOLO classification data must contain train/ and val/ folders; "
            f"missing: {', '.join(missing)}"
        )
    for split in ("train", "val"):
        class_dirs = {path.name for path in (root / split).iterdir() if path.is_dir()}
        if not class_dirs:
            raise ValueError(f"No class folders found in {root / split}")
        print(f"{split} classes: {sorted(class_dirs)}")


def main() -> None:
    validate_dataset(DATASET_DIR)
    model = YOLO(BASE_MODEL)
    results = model.train(
        data=DATASET_DIR,
        epochs=10,
        imgsz=224,
        batch=16,
        project=OUTPUT_DIR,
        name=RUN_NAME,
        pretrained=True,
        seed=0,
    )
    print(results)

    trained_best = Path(OUTPUT_DIR) / RUN_NAME / "weights" / "best.pt"
    if not trained_best.exists():
        raise FileNotFoundError(f"Training completed but no best.pt was found at {trained_best}")
    shutil.copy2(trained_best, BEST_MODEL_OUTPUT)
    Path(CLASS_NAMES_OUTPUT).write_text(json.dumps(CLASS_NAMES, indent=2) + "\n", encoding="utf-8")
    print(f"Saved model to {BEST_MODEL_OUTPUT}")
    print(f"Saved class order to {CLASS_NAMES_OUTPUT}")


if __name__ == "__main__":
    main()
