import re
import sys
from pathlib import Path

from ultralytics import YOLO

VAL_ROOT = Path("brand_dataset/val")
COMPCARS_PATTERN = re.compile(r"^\d+_\d+_[0-9a-f]{8,}\.\w+$", re.IGNORECASE)


def main():
    if len(sys.argv) < 2:
        print("Usage: eval_brand_own_crops.py <path_to_best.pt>")
        sys.exit(1)
    model = YOLO(sys.argv[1])

    own_correct = own_total = 0
    compcars_correct = compcars_total = 0
    per_class = {}

    for class_dir in sorted(VAL_ROOT.iterdir()):
        if not class_dir.is_dir():
            continue
        true_label = class_dir.name
        own_c = own_t = comp_c = comp_t = 0
        for path in class_dir.iterdir():
            if path.name == ".gitkeep" or not path.is_file():
                continue
            is_own = not COMPCARS_PATTERN.match(path.name)
            result = model(str(path), verbose=False)[0]
            pred = model.names[int(result.probs.top1)]
            correct = int(pred == true_label)
            if is_own:
                own_t += 1
                own_c += correct
            else:
                comp_t += 1
                comp_c += correct
        own_correct += own_c
        own_total += own_t
        compcars_correct += comp_c
        compcars_total += comp_t
        per_class[true_label] = (own_c, own_t, comp_c, comp_t)

    print(f"{'class':<14} {'own acc':>12} {'compcars acc':>14}")
    for cls, (oc, ot, cc, ct) in per_class.items():
        own_str = f"{oc}/{ot}" if ot else "n/a"
        comp_str = f"{cc}/{ct}" if ct else "n/a"
        print(f"{cls:<14} {own_str:>12} {comp_str:>14}")

    print()
    if own_total:
        print(f"OWN CROPS overall: {own_correct}/{own_total} = {own_correct / own_total:.1%}")
    else:
        print("OWN CROPS overall: no own-crop val images at all")
    if compcars_total:
        print(f"COMPCARS overall:  {compcars_correct}/{compcars_total} = {compcars_correct / compcars_total:.1%}")


if __name__ == "__main__":
    main()
