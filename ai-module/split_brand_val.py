"""Split brand_dataset's sorted train/ images into a train/val split.

Sort your labeled crops into brand_dataset/train/<Brand>/ only -- this
script then carves out a held-out val/ slice for you afterward.

Each class folder is a mix of two very different sources, identified by
filename: CompCars uses its own rigid native format (`<id>_<id>_<hex>.jpg`,
left unrenamed), while everything else is one of your own camera crops
(renamed by hand). Both pools are split independently at VAL_FRACTION so
val gets a fair share of your own real crops specifically -- not just
whatever CompCars happens to contribute by chance -- since your crops are
the ones that actually match this camera's deployment domain and matter
most for a meaningful val signal.

This is a plain per-image split within each pool, NOT grouped by vehicle.
That's a deliberate step back: an attempt at grouping your own crops by
vehicle (first via grayscale perceptual hash, then via colour-thumbnail
similarity, since neither the original track_id nor capture timestamp
survived your renaming) was tested against the actual dataset and both
approaches produced real false merges -- a silver sedan grouped with a
yellow-and-green taxi, then separately a silver Camry grouped with a beige
Vios, purely because they share this camera's rear-3/4 framing and a common
body colour. Rather than ship a "smart" grouping that can confidently merge
unrelated vehicles (worse than the leakage risk it was meant to prevent),
this accepts the smaller, bounded risk of a plain random split: a few
near-identical frames of the same vehicle might land on both sides of
train/val. If your own crops mostly aren't rapid-fire bursts of the same
car, this risk is minor; if they are, val accuracy for classes with heavy
bursts should be read with that caveat in mind.

This defaults to a DRY RUN: it prints the plan without moving anything.
Pass --apply to actually move files.

Re-running this after an earlier split re-splits the WHOLE train/ pool,
including images val already got its share of last time -- each run pulls
another VAL_FRACTION out of whatever is left in train, so val keeps growing
disproportionately every time you add a new batch and re-run this. Pass
--only-new instead: it leaves every file already sitting in train/ alone and
only splits images newer than the newest file currently in val/ (i.e. the
ones added since the last split). With an empty val/, --only-new has nothing
to compare against and falls back to the normal full split.

Usage (from ai-module/, with the project venv active):
    .venv/Scripts/python.exe split_brand_val.py                     # preview, whole pool
    .venv/Scripts/python.exe split_brand_val.py --only-new          # preview, new images only
    .venv/Scripts/python.exe split_brand_val.py --only-new --apply  # actually move them
"""

import random
import re
import shutil
import sys
from pathlib import Path

DATASET_ROOT = Path("brand_dataset")
VAL_FRACTION = 0.2
# A pool (your own crops, or CompCars images) with fewer images than this
# stays entirely in train -- a 1-2 image val slice is statistically
# meaningless and just wastes scarce data.
MIN_IMAGES_FOR_VAL = 5
SEED = 42

# CompCars' own native naming, e.g. "39_2008_4e8737e1d5ca2e.jpg" -- left
# untouched since only your own crops were renamed by hand.
COMPCARS_PATTERN = re.compile(r"^\d+_\d+_[0-9a-f]{8,}\.\w+$", re.IGNORECASE)


def _pick_val(paths, rng):
    """Return which images go to val, or none if the pool is too thin."""
    if len(paths) < MIN_IMAGES_FOR_VAL:
        return []
    shuffled = paths[:]
    rng.shuffle(shuffled)
    val_count = max(1, round(len(shuffled) * VAL_FRACTION))
    return shuffled[:val_count]


def _new_files_cutoff(val_root):
    """The newest mtime among current val/ images, or None if val/ is empty.

    Everything in train/ at or before this moment already had its chance to
    be picked for val by an earlier run (or was deliberately left out of a
    too-thin pool); only what's newer is unseen by any previous split."""
    mtimes = [
        p.stat().st_mtime
        for p in val_root.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    ]
    return max(mtimes) if mtimes else None


def main():
    apply_changes = "--apply" in sys.argv
    only_new = "--only-new" in sys.argv
    rng = random.Random(SEED)
    train_root = DATASET_ROOT / "train"
    val_root = DATASET_ROOT / "val"

    if not apply_changes:
        print("DRY RUN -- no files will be moved. Re-run with --apply to actually move them.\n")

    cutoff = _new_files_cutoff(val_root) if only_new else None
    if only_new and cutoff is None:
        print("--only-new: val/ is empty, nothing to compare against -- splitting the whole pool.\n")
    elif only_new:
        print(f"--only-new: only considering train/ images added since the last split.\n")

    for class_dir in sorted(train_root.iterdir()):
        if not class_dir.is_dir():
            continue
        images = [p for p in class_dir.iterdir() if p.is_file() and p.name != ".gitkeep"]
        if not images:
            continue

        skipped = 0
        if cutoff is not None:
            skipped = sum(1 for p in images if p.stat().st_mtime <= cutoff)
            images = [p for p in images if p.stat().st_mtime > cutoff]

        own_paths = [p for p in images if not COMPCARS_PATTERN.match(p.name)]
        compcars_paths = [p for p in images if COMPCARS_PATTERN.match(p.name)]

        val_own = _pick_val(own_paths, rng)
        val_compcars = _pick_val(compcars_paths, rng)

        already_split_note = f", {skipped} already split before (left alone)" if cutoff is not None else ""
        print(
            f"{class_dir.name}: {len(images)} new images "
            f"(own={len(own_paths)}, compcars={len(compcars_paths)}){already_split_note} -- "
            f"val: {len(val_own)} own images, {len(val_compcars)} compcars images"
        )

        if apply_changes:
            val_class_dir = val_root / class_dir.name
            val_class_dir.mkdir(parents=True, exist_ok=True)
            for path in val_own + val_compcars:
                shutil.move(str(path), str(val_class_dir / path.name))


if __name__ == "__main__":
    main()
