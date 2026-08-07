from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "mouse_gesture.ico"


def point_on_circle(
    center: tuple[float, float], radius: float, degrees: float
) -> tuple[float, float]:
    radians = math.radians(degrees)
    return (
        center[0] + radius * math.cos(radians),
        center[1] + radius * math.sin(radians),
    )


def create_icon() -> None:
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (8, 8, 248, 248),
        radius=52,
        fill="#111827",
    )
    draw.rounded_rectangle(
        (22, 22, 234, 234),
        radius=42,
        fill="#18233A",
        outline="#26344F",
        width=4,
    )

    arc_box = (55, 48, 201, 194)
    draw.arc(arc_box, start=30, end=320, fill="#5B79FF", width=23)
    arrow_tip = point_on_circle((128, 121), 73, 320)
    arrow_left = (arrow_tip[0] - 7, arrow_tip[1] - 26)
    arrow_right = (arrow_tip[0] + 23, arrow_tip[1] - 12)
    draw.polygon(
        (arrow_tip, arrow_left, arrow_right),
        fill="#5B79FF",
    )

    draw.line(
        ((70, 139), (105, 174), (182, 88)),
        fill="#35D39A",
        width=22,
        joint="curve",
    )
    for point in ((70, 139), (182, 88)):
        draw.ellipse(
            (point[0] - 11, point[1] - 11, point[0] + 11, point[1] + 11),
            fill="#35D39A",
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        OUTPUT,
        format="ICO",
        sizes=((16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)),
    )
    print(OUTPUT)


if __name__ == "__main__":
    create_icon()
