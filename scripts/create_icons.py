from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def create_icon() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (70, 70, size - 70, size - 70),
        radius=210,
        fill=(12, 16, 26, 255),
        outline=(60, 71, 91, 255),
        width=18,
    )
    draw.rounded_rectangle(
        (340, 230, 665, 790),
        radius=145,
        fill=(201, 255, 87, 255),
    )
    draw.ellipse((390, 285, 615, 510), fill=(238, 255, 202, 255))
    draw.polygon(
        [(470, 458), (650, 505), (520, 650), (350, 600)],
        fill=(126, 141, 255, 255),
    )

    image.save(ASSETS / "Yingcun.png")
    image.save(
        ASSETS / "Yingcun.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    image.save(ASSETS / "Yingcun.icns")


if __name__ == "__main__":
    create_icon()
