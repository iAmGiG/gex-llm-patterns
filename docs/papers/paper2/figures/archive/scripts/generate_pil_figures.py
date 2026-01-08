#!/usr/bin/env python3
"""
Generate publication-quality figures for Paper #2 using PIL.

Creates PNG figures at 300 DPI for:
- Figure 5: Obfuscation process
- Figure 6: Regime window structure
- Figure 7: Selectivity grid
- Figure 8: Validation funnel
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DPI = 300
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Colors (IEEE compatible)
COLORS = {
    "red": (214, 39, 40),  # Persistent negative
    "green": (44, 160, 44),  # Persistent positive
    "gray": (127, 127, 127),  # Transitional
    "blue": (31, 119, 180),  # Accepted
    "orange": (255, 127, 14),  # Rejected
    "light_blue": (232, 244, 248),  # Background
    "light_green": (232, 248, 232),  # Background
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def create_simple_figure_5():
    """Figure 5: Obfuscation process (simple box-and-arrow diagram)."""
    # Create image: 1050 x 600 pixels (3.5" x 2" at 300 DPI)
    img = Image.new("RGB", (1050, 600), color=COLORS["white"])
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Title
    draw.text((525, 30), "Temporal Obfuscation Process", fill=COLORS["black"], font=title_font, anchor="mm")

    # Left box: Original Data
    draw.rectangle([80, 150, 320, 350], outline=COLORS["black"], fill=COLORS["light_blue"], width=2)
    draw.text((200, 210), "Original Data", fill=COLORS["black"], font=text_font, anchor="mm")
    draw.text((200, 270), "2024-01-15, SPY", fill=COLORS["black"], font=small_font, anchor="mm")
    draw.text((200, 310), "-$12.3B GEX", fill=COLORS["black"], font=small_font, anchor="mm")

    # Arrow
    draw.line([(340, 250), (480, 250)], fill=COLORS["black"], width=3)
    draw.polygon([(480, 250), (450, 230), (450, 270)], fill=COLORS["black"])
    draw.text((410, 200), "Strip temporal", fill=COLORS["black"], font=small_font, anchor="mm")
    draw.text((410, 225), "context", fill=COLORS["black"], font=small_font, anchor="mm")

    # Right box: Obfuscated Data
    draw.rectangle([500, 150, 740, 350], outline=COLORS["black"], fill=COLORS["light_green"], width=2)
    draw.text((620, 210), "Obfuscated Data", fill=COLORS["black"], font=text_font, anchor="mm")
    draw.text((620, 270), "Day T-10, INDEX_1", fill=COLORS["black"], font=small_font, anchor="mm")
    draw.text((620, 310), "-$12.3B GEX", fill=COLORS["black"], font=small_font, anchor="mm")

    # Annotations
    draw.text((525, 390), "✓ Structural patterns preserved", fill=COLORS["black"], font=small_font, anchor="mm")
    draw.text((525, 425), "✓ Calendar context removed", fill=COLORS["black"], font=small_font, anchor="mm")
    draw.text((525, 460), "✓ Prevents memorization", fill=COLORS["black"], font=small_font, anchor="mm")

    img.save(OUTPUT_DIR / "figure5_obfuscation_flow.png", "PNG", dpi=(DPI, DPI))
    print("✓ Figure 5: Obfuscation process")


def create_simple_figure_6():
    """Figure 6: 30-day regime window (bar chart)."""
    img = Image.new("RGB", (2100, 600), color=COLORS["white"])
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Title
    draw.text((1050, 30), "30-Day Persistent Regime Example", fill=COLORS["black"], font=title_font, anchor="mm")

    # Draw bars for 30 days (mostly red for negative GEX, a few green for positive)
    bar_width = 60
    start_x = 100
    start_y = 500
    height_scale = 2

    for day in range(30):
        x = start_x + day * bar_width
        if day in [8, 22]:  # A couple positive flips
            color = COLORS["green"]
            height = 4 * height_scale
        else:
            color = COLORS["red"]
            height = 13 * height_scale

        # Draw bar
        draw.rectangle([x, start_y - height, x + 50, start_y], outline=COLORS["black"], fill=color, width=1)
        # Draw day label
        draw.text((x + 25, start_y + 30), str(day + 1), fill=COLORS["black"], font=small_font, anchor="mm")

    # Y-axis line
    draw.line([(80, 50), (80, 500)], fill=COLORS["black"], width=2)
    draw.text((30, 250), "GEX (B$)", fill=COLORS["black"], font=small_font, anchor="mm")

    # Criteria box
    criteria_text = [
        "✓ Persistence: 28/30 negative (93.3%)",
        "✓ Magnitude: Avg $13.5B (> $5B)",
        "✓ Stability: 2 sign flips (≤ 5)",
        "→ PERSISTENT REGIME DETECTED",
    ]

    box_x, box_y = 1600, 150
    box_w, box_h = 450, 200

    draw.rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h], outline=COLORS["black"], fill=COLORS["light_green"], width=2
    )

    for i, line in enumerate(criteria_text):
        draw.text((box_x + 10, box_y + 20 + i * 40), line, fill=COLORS["black"], font=small_font)

    img.save(OUTPUT_DIR / "figure6_regime_window.png", "PNG", dpi=(DPI, DPI))
    print("✓ Figure 6: Regime window structure")


def create_simple_figure_7():
    """Figure 7: Selectivity grid (2x2)."""
    img = Image.new("RGB", (1400, 800), color=COLORS["white"])
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((700, 30), "Framework Selectivity (2x2 Grid)", fill=COLORS["black"], font=title_font, anchor="mm")

    examples = [
        ("2024 Persistent", ["Persist: 96%", "Mag: $14B", "Flips: 1"], True, "2x2 Detected"),
        ("2020 Fragmented", ["Persist: 83%", "Mag: $2.9B", "Flips: 2"], False, "Mag too low"),
        ("2024 Transitional", ["Persist: 90%", "Mag: $31B", "Flips: 8"], False, "Too many flips"),
        ("Synthetic Low-Mag", ["Persist: 100%", "Mag: $3.2B", "Flips: 0"], False, "Mag too low"),
    ]

    positions = [(200, 150), (900, 150), (200, 500), (900, 500)]

    for pos, (title, metrics, detected, reason) in zip(positions, examples):
        x, y = pos
        box_size = 350

        # Draw box
        color = COLORS["light_green"] if detected else (255, 245, 245)
        draw.rectangle(
            [x - box_size // 2, y - 100, x + box_size // 2, y + 200], outline=COLORS["black"], fill=color, width=2
        )

        # Title
        draw.text((x, y - 80), title, fill=COLORS["black"], font=label_font, anchor="mm")

        # Metrics
        for i, metric in enumerate(metrics):
            draw.text((x - 100, y - 20 + i * 35), metric, fill=COLORS["black"], font=text_font, anchor="lm")

        # Badge
        badge_char = "✓" if detected else "✗"
        badge_color = COLORS["green"] if detected else COLORS["red"]
        draw.text((x, y + 120), badge_char, fill=badge_color, font=title_font, anchor="mm")

        # Status text
        status = "DETECTED" if detected else "NOT DETECTED"
        draw.text((x, y + 160), status, fill=badge_color, font=text_font, anchor="mm")

    img.save(OUTPUT_DIR / "figure7_selectivity.png", "PNG", dpi=(DPI, DPI))
    print("✓ Figure 7: Framework selectivity")


def create_simple_figure_8():
    """Figure 8: Validation funnel."""
    img = Image.new("RGB", (1050, 700), color=COLORS["white"])
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((525, 30), "Validation Progression", fill=COLORS["black"], font=title_font, anchor="mm")

    # NOTE: Phase 4A (multi-year 2021-2023, 2025) was planned but NOT executed.
    # Only Phases 1-4 have validated data (446 windows: 2020 + 2024).
    phases = [
        ("Phase 1\n(Q1 2024)", "52 win\n71.2%"),
        ("Phase 2\n(Negatives)", "809 win\n6.3%"),
        ("Phase 3\n(Full 2024)", "223 win\n81.2%"),
        ("Phase 4\n(2020)", "223 win\n12.1%"),
    ]

    y_positions = [150, 270, 390, 510]
    widths = [400, 450, 400, 400]

    for i, ((phase, metrics), y, width) in enumerate(zip(phases, y_positions, widths)):
        x = 525
        h = 70

        # Draw trapezoid (approximated as rounded rectangle)
        draw.rectangle(
            [x - width // 2, y, x + width // 2, y + h], outline=COLORS["blue"], fill=(173, 216, 230), width=2
        )

        # Text
        draw.text((x - width // 4, y + h // 2), phase, fill=COLORS["black"], font=label_font, anchor="mm")
        draw.text((x + width // 4, y + h // 2), metrics, fill=COLORS["black"], font=text_font, anchor="mm")

        # Checkmark
        draw.text((x + width // 2 + 50, y + h // 2), "✓", fill=COLORS["green"], font=title_font, anchor="mm")

    img.save(OUTPUT_DIR / "figure8_validation_funnel.png", "PNG", dpi=(DPI, DPI))
    print("✓ Figure 8: Validation funnel")


def main():
    """Generate all figures."""
    print("Generating publication-quality figures...")
    create_simple_figure_5()
    create_simple_figure_6()
    create_simple_figure_7()
    create_simple_figure_8()
    print(f"\n✅ All figures generated successfully!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob("*.png")):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
