"""Fine-tune brand.pt to this station's actual makes, on this camera's view.

brand.pt is currently a whole-image classifier over 161 manufacturers -- far
more than this station will ever see, and (per its class list) apparently
trained on generic logo/badge photos rather than this camera's rear-view
angle.  This narrows it to the makes that actually show up here and adapts
it to real footage, continuing from the existing pretrained weights so the
backbone's general visual features are reused rather than retrained from
scratch.

Because the target class list (14) differs from brand.pt's current one
(161), Ultralytics rebuilds the final classification layer to match
brand_dataset's folder names -- the backbone still transfers, but this is a
fresh head, not a continuation of the original 161-way one. A brand with no
real prior exposure in the source dataset (Zeekr is a recent brand and does
not appear in brand.pt's current class list at all) leans entirely on that
transferred backbone plus whatever examples you label for it, so gathering
somewhat more data for it than the other classes is worth the effort.

Usage (from ai-module/, with the project venv active):
    .venv/Scripts/python.exe train_brand.py
"""

from ultralytics import YOLO


def main():
    # Start from the current production weights, not a generic pretrained
    # checkpoint, so the backbone's already-learned visual features carry
    # over even though the classification head itself is being resized.
    model = YOLO("brand.pt")

    model.train(
        # Classification tasks in Ultralytics take a dataset ROOT directory
        # (train/<class>/*.jpg, val/<class>/*.jpg) rather than a data.yaml.
        data="brand_dataset",
        epochs=50,
        imgsz=224,
        batch=16,
        patience=15,
        lr0=0.003,
        # Freeze fewer early layers than a same-class-set fine-tune would --
        # narrowing to 14 classes with a fresh head needs more of the
        # network to adapt than a small nudge on an already-matching one.
        freeze=5,
        device=0,
        project="runs/brand_finetune",
        name="station_makes",
    )


if __name__ == "__main__":
    main()
