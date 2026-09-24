import random
import re
import shutil
import sys
from pathlib import Path

DATASET_ROOT = Path("brand_dataset")
VAL_FRACTION = 0.2

MIN_IMAGES_FOR_VAL = 5
SEED = 42


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
    """Return the most recent modification time of any file in val_root, or None if empty."""
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
