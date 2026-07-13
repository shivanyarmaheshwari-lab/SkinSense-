# SkinSense Colab Training Script
# Paste this into Google Colab OR upload this .py file and run it cell by cell.

# ============================================================
# 1. INSTALL / IMPORT
# ============================================================
import json
import os
import shutil
from pathlib import Path

import tensorflow as tf


# ============================================================
# 2. UPDATE YOUR DATASET LOCATION HERE
# ============================================================
# Put your unzipped image dataset folder in Colab and change this path.
# Example if you upload Dataset.zip and unzip it:
# RAW_DATASET_DIR = "/content/Dataset"
RAW_DATASET_DIR = "/content/Dataset"  # <<< CHANGE THIS IF YOUR DATASET FOLDER IS SOMEWHERE ELSE

CLEAN_DATASET_DIR = "/content/skinsense_clean_dataset"
MODEL_OUTPUT_PATH = "/content/skinsense_model.keras"
CLASS_NAMES_OUTPUT_PATH = "/content/class_names.json"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10
SEED = 42


# ============================================================
# 3. DISEASE LABEL MAPPING
# ============================================================
# This fixes your mixed dataset folders and turns them into clean classes.
TARGET_DISEASES = [
    "Irritant Contact Dermatitis",
    "Occupational Hand Eczema",
    "Athlete's Foot (Tinea pedis)",
    "Ringworm (Tinea corporis)",
    "Cutaneous Candidiasis",
    "Paronychia",
    "Folliculitis",
    "Cellulitis",
    "Impetigo",
    "Sunburn",
    "Actinic Keratosis",
]


def infer_label_from_path(path: Path) -> str | None:
    parts = [part.lower() for part in path.parts]
    parent = path.parent.name

    if parent == "Irritant Contact Dermatitis":
        return "Irritant Contact Dermatitis"
    if parent == "Occupational Hand Eczema":
        return "Occupational Hand Eczema"
    if parent in {"Tinea corporis", "Ringworm (Tinea corporis)", "FU-ringworm"}:
        return "Ringworm (Tinea corporis)"
    if parent == "FU-athlete-foot":
        return "Athlete's Foot (Tinea pedis)"
    if parent == "BA- cellulitis":
        return "Cellulitis"
    if parent == "BA-impetigo":
        return "Impetigo"
    if parent == "Actinic_Keratosis":
        return "Actinic Keratosis"
    if parent == "Sun_Sunlight_Damage":
        return "Sunburn"
    if "cutaneous candidiasis" in parts:
        return "Cutaneous Candidiasis"
    if "paronychia" in parts:
        return "Paronychia"
    if "folliculitis" in parts:
        return "Folliculitis"
    return None


# ============================================================
# 4. BUILD CLEAN DATASET
# ============================================================
def build_clean_dataset() -> None:
    raw_root = Path(RAW_DATASET_DIR)
    clean_root = Path(CLEAN_DATASET_DIR)
    if not raw_root.exists():
        raise FileNotFoundError(f"Dataset folder not found: {raw_root}")

    if clean_root.exists():
        shutil.rmtree(clean_root)
    clean_root.mkdir(parents=True, exist_ok=True)

    for disease in TARGET_DISEASES:
        (clean_root / disease).mkdir(parents=True, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    counts = {disease: 0 for disease in TARGET_DISEASES}
    skipped = 0

    for path in raw_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in image_exts:
            continue
        label = infer_label_from_path(path)
        if label is None:
            skipped += 1
            continue
        safe_name = f"{counts[label]:05d}_{path.name}"
        shutil.copy2(path, clean_root / label / safe_name)
        counts[label] += 1

    print("Clean dataset created:", clean_root)
    print("Counts:")
    for disease, count in counts.items():
        print(f"  {disease}: {count}")
    print("Skipped images:", skipped)

    empty_classes = [disease for disease, count in counts.items() if count == 0]
    if empty_classes:
        raise ValueError(f"These classes have 0 images: {empty_classes}")


build_clean_dataset()


# ============================================================
# 5. LOAD DATA FOR TRAINING
# ============================================================
train_ds = tf.keras.utils.image_dataset_from_directory(
    CLEAN_DATASET_DIR,
    validation_split=0.2,
    subset="training",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="categorical",
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    CLEAN_DATASET_DIR,
    validation_split=0.2,
    subset="validation",
    seed=SEED,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="categorical",
)

class_names = train_ds.class_names
print("Class order:", class_names)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.prefetch(AUTOTUNE)
val_ds = val_ds.prefetch(AUTOTUNE)


# ============================================================
# 6. TRAIN TRANSFER-LEARNING MODEL
# ============================================================
data_augmentation = tf.keras.Sequential(
    [
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.08),
        tf.keras.layers.RandomZoom(0.08),
        tf.keras.layers.RandomContrast(0.08),
    ],
    name="augmentation",
)

base_model = tf.keras.applications.MobileNetV2(
    input_shape=IMAGE_SIZE + (3,),
    include_top=False,
    weights="imagenet",
)
base_model.trainable = False

inputs = tf.keras.Input(shape=IMAGE_SIZE + (3,))
x = data_augmentation(inputs)
x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
x = base_model(x, training=False)
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dropout(0.25)(x)
outputs = tf.keras.layers.Dense(len(class_names), activation="softmax")(x)
model = tf.keras.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0004),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

callbacks = [
    tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
    tf.keras.callbacks.ModelCheckpoint(MODEL_OUTPUT_PATH, monitor="val_accuracy", save_best_only=True),
]

history = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)


# ============================================================
# 7. OPTIONAL FINE-TUNE
# ============================================================
base_model.trainable = True
for layer in base_model.layers[:-30]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.00005),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

model.fit(train_ds, validation_data=val_ds, epochs=3, callbacks=callbacks)


# ============================================================
# 8. SAVE FILES FOR STREAMLIT
# ============================================================
model = tf.keras.models.load_model(MODEL_OUTPUT_PATH)
with open(CLASS_NAMES_OUTPUT_PATH, "w", encoding="utf-8") as file:
    json.dump(class_names, file, indent=2)

print("Saved model:", MODEL_OUTPUT_PATH)
print("Saved class names:", CLASS_NAMES_OUTPUT_PATH)
print("Download these two files and put them beside app.py:")
print("  skinsense_model.keras")
print("  class_names.json")


# ============================================================
# 9. QUICK TEST ON ONE IMAGE
# ============================================================
sample_path = next(Path(CLEAN_DATASET_DIR).rglob("*.jpg"))
image = tf.keras.utils.load_img(sample_path, target_size=IMAGE_SIZE)
array = tf.keras.utils.img_to_array(image)
pred = model.predict(tf.expand_dims(array, axis=0), verbose=0)[0]
best = int(tf.argmax(pred).numpy())
print("Sample image:", sample_path)
print("Prediction:", class_names[best], float(pred[best]))
