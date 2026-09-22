# Fine-tuning brand.pt: narrowed to this station's actual makes

`brand.pt` is currently a whole-image *classifier* (not a detector) over 161
manufacturers -- most of which will never appear at this station -- and its
161-class list suggests it was trained on generic logo/badge photos rather
than this camera's rear-view angle. This narrows it down to the makes you
actually expect here and adapts it to real footage from this camera.

Target classes (14), one folder per make:

```
BMW  BYD  Chevrolet  Ford  Honda  Isuzu  MG  Mazda
MercedesBenz  Mitsubishi  Nissan  Suzuki  Toyota  Zeekr
```

**Zeekr does not appear anywhere in brand.pt's current 161-class list** --
it's a newer brand the model has no prior exposure to at all, unlike the
other 13 which the model already sort of recognizes (some under slightly
different names/spellings, e.g. "Chevy", "MAZDA", "BWM", "Benz"). Try to
gather noticeably more Zeekr examples than the others, since there's no
existing knowledge for training to build on for that one.

## 1. Collect raw images

Run the live pipeline with `ENABLE_MAKE_MODEL=1` and
`DEBUG_MAKE_MODEL_SAVE_INPUTS=1` for a while, across as many real vehicles as
you can. Every attempt saves the exact crop the model sees to
`./debug_crops/make_input_<track_id>_<timestamp>.jpg`.

## 2. Label them

This is a *classifier*, not a detector, so labeling is just sorting -- no
bounding boxes to draw. For each saved crop:

- If the vehicle is one of the 14 target makes and the badge/wordmark is
  legible, copy the whole image into that make's folder under `train/`
  (most of the images) or `val/` (a held-out ~20%, used only to check
  progress, never trained on).
- If the vehicle is a make outside the 14, or the badge isn't legible, skip
  the image entirely -- don't force it into the closest folder.

Aim for at least ~20-40 images per class as a starting point (more for
Zeekr, per above); fewer is fine for a first pass since this fine-tunes an
existing model rather than training from zero, but more real examples will
always help, especially for makes whose original-dataset images looked
different from what this camera actually sees.

## 3. Fine-tune

From `ai-module/`, with the project venv active:

```
.venv/Scripts/python.exe train_brand.py
```

This continues from the current `brand.pt` weights and rebuilds the final
classification layer for these 14 classes (see `train_brand.py` for why, and
for the epoch/learning-rate/freeze settings -- tune them if you have very
little data for some classes, or a lot for all of them).

## 4. Swap in the result

The best checkpoint lands at
`runs/brand_finetune/station_makes/weights/best.pt`. Back up the current
model, then replace it:

```
cp brand.pt brand.pt.bak
cp runs/brand_finetune/station_makes/weights/best.pt brand.pt
```

Re-run with `DEBUG_MAKE_MODEL=1` to confirm `[MAKE] top5=...` now reports
sensible results on real footage before relying on it in production. Since
the class list changed, `model.names` will now only ever return these 14
makes -- a vehicle from any other manufacturer will get the closest-looking
wrong answer rather than "unknown", so keep `MAKE_MODEL_MIN_CONF` in mind
when deciding how much to trust a low-confidence result.
