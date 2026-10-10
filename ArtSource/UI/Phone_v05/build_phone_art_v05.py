# Phone UI art v05 (TASK-000239): wallpaper from the picture Vadim chose last, used as delivered.
# Run: python build_phone_art_v05.py  (Pillow only). Same crop + soft extension as v04; v01-v04 stay untouched.
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v01"))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v04"))
import build_phone_art as v01  # noqa: E402
import build_phone_art_v04 as v04  # noqa: E402

v04.SOURCE = os.path.join(HERE, "Sources", "wallpaper_busik_vadim_v3.webp")
PREVIEW = os.path.join(HERE, "Previews")


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    results = []
    v01.save(v04.wallpaper(), "wallpaper", results)
    results[0][1].resize((300, 652), Image.LANCZOS).save(os.path.join(PREVIEW, "phone_art_v05.png"))
    print("wrote", [n for n, _ in results])


if __name__ == "__main__":
    main()
