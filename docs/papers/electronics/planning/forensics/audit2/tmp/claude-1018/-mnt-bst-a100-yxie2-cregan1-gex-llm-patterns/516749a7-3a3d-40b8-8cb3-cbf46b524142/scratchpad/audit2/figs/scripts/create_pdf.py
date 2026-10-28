#!/usr/bin/env python3
"""
Create combined PDF from all generated figures.

Output: docs/papers/paper2/figures/output/paper2_figures.pdf
"""

from pathlib import Path

from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def create_pdf():
    """Combine all figures into a single PDF."""

    # Get all PNG files in order
    figures = sorted(OUTPUT_DIR.glob("fig*.png"))

    if not figures:
        print("No figures found in output directory")
        return

    print(f"Found {len(figures)} figures")

    # Load images and convert to RGB
    images = []
    for fig_path in figures:
        print(f"  Loading: {fig_path.name}")
        img = Image.open(fig_path)
        if img.mode == "RGBA":
            # Convert RGBA to RGB with white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)

    # Save as PDF
    pdf_path = OUTPUT_DIR / "paper2_figures.pdf"
    images[0].save(
        pdf_path,
        "PDF",
        resolution=300,
        save_all=True,
        append_images=images[1:],
    )

    print(f"\nPDF created: {pdf_path}")
    print(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    create_pdf()
