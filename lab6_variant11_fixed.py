from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Лабораторная работа №6. Вариант 11 — Угаритский алфавит
# Сегментация текста по профилям
# ============================================================

VARIANT = 11
ALPHABET_NAME = "Угаритский алфавит"
SYMBOLS = [chr(code) for code in range(0x10380, 0x1039E)]  # U+10380..U+1039D

FONT_SIZE = 92

# Для устойчивой сегментации учебной строки каждый символ отделён пробелом.
PHRASE = "𐎀 𐎁 𐎂 𐎍 𐎎 𐎏 𐎛 𐎚 𐎗"
EXPECTED_SYMBOL_COUNT = len(PHRASE.replace(" ", ""))

CANVAS_PAD = 30
BIN_THRESHOLD = 120
TRIM_PADDING = 2

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
SRC_DIR = BASE_DIR / "src"
REPORT_PATH = BASE_DIR / "report.md"

INPUT_DIR = RESULTS_DIR / "input"
PROFILES_DIR = RESULTS_DIR / "profiles"
SEGMENTS_DIR = RESULTS_DIR / "segments"
ALPHABET_DIR = RESULTS_DIR / "alphabet"
ALPHABET_TEMPLATES_DIR = ALPHABET_DIR / "templates"
ALPHABET_PROFILES_DIR = ALPHABET_DIR / "profiles"

SRC_INPUT_DIR = SRC_DIR / "input"
SRC_PROFILES_DIR = SRC_DIR / "profiles"
SRC_SEGMENTS_DIR = SRC_DIR / "segments"
SRC_ALPHABET_DIR = SRC_DIR / "alphabet"
SRC_ALPHABET_TEMPLATES_DIR = SRC_ALPHABET_DIR / "templates"
SRC_ALPHABET_PROFILES_DIR = SRC_ALPHABET_DIR / "profiles"

BOXES_CSV = RESULTS_DIR / "segments_boxes.csv"


@dataclass
class SegmentBox:
    index: int
    x0: int
    y0: int
    x1: int
    y1: int
    width: int
    height: int
    file_name: str


def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def setup_dirs() -> None:
    for path in [
        RESULTS_DIR,
        SRC_DIR,
        INPUT_DIR,
        PROFILES_DIR,
        SEGMENTS_DIR,
        ALPHABET_DIR,
        ALPHABET_TEMPLATES_DIR,
        ALPHABET_PROFILES_DIR,
        SRC_INPUT_DIR,
        SRC_PROFILES_DIR,
        SRC_SEGMENTS_DIR,
        SRC_ALPHABET_DIR,
        SRC_ALPHABET_TEMPLATES_DIR,
        SRC_ALPHABET_PROFILES_DIR,
    ]:
        ensure_clean_dir(path)


def find_font_path() -> Path:
    candidates = [
        Path("NotoSansUgaritic-Regular.ttf"),
        BASE_DIR / "NotoSansUgaritic-Regular.ttf",

        # macOS
        Path("/Library/Fonts/NotoSansUgaritic-Regular.ttf"),
        Path.home() / "Library/Fonts/NotoSansUgaritic-Regular.ttf",
        Path("/System/Library/Fonts/Supplemental/NotoSansUgaritic-Regular.ttf"),

        # Linux
        Path("/usr/share/fonts/truetype/noto/NotoSansUgaritic-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansUgaritic-Regular.ttf"),

        # Windows
        Path(r"C:\Windows\Fonts\NotoSansUgaritic-Regular.ttf"),
        Path(r"C:\Windows\Fonts\seguihis.ttf"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Не найден шрифт NotoSansUgaritic-Regular.ttf. "
        "Положи его рядом с lab6_variant11_fixed.py или в папку проекта."
    )


def render_phrase_mono(phrase: str, font: ImageFont.FreeTypeFont) -> np.ndarray:
    canvas_w = 2400
    canvas_h = 320

    image = Image.new("L", (canvas_w, canvas_h), color=255)
    draw = ImageDraw.Draw(image)

    bbox = draw.textbbox((0, 0), phrase, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (canvas_w - text_w) // 2 - bbox[0]
    y = (canvas_h - text_h) // 2 - bbox[1]

    draw.text((x, y), phrase, fill=0, font=font)

    arr = np.asarray(image, dtype=np.uint8)
    mask = arr < BIN_THRESHOLD
    ys, xs = np.where(mask)

    if ys.size == 0:
        raise RuntimeError("Фраза не отрисована. Проверь шрифт с поддержкой угаритского письма.")

    y0 = max(0, int(ys.min()) - CANVAS_PAD // 3)
    y1 = min(arr.shape[0] - 1, int(ys.max()) + CANVAS_PAD // 3)
    x0 = max(0, int(xs.min()) - CANVAS_PAD)
    x1 = min(arr.shape[1] - 1, int(xs.max()) + CANVAS_PAD)

    cropped = arr[y0 : y1 + 1, x0 : x1 + 1]
    mono = np.where(cropped < BIN_THRESHOLD, 0, 255).astype(np.uint8)
    return mono


def save_gray(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array.astype(np.uint8), mode="L").save(path)


def save_profile_plot(profile: np.ndarray, axis_name: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 3), dpi=120)

    x = np.arange(profile.size)
    ax.bar(x, profile, width=0.85, color="black")
    ax.set_title(f"{axis_name}-профиль")
    ax.set_xlabel("Координата")
    ax.set_ylabel("Черные пиксели")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=16))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def extract_segments_fixed_count(mono: np.ndarray, expected_count: int) -> list[SegmentBox]:
    """
    Сегментация по вертикальному профилю с известным числом символов.
    Берём самые широкие вертикальные пробелы как границы между символами.

    Это нужно для угаритского письма, потому что некоторые знаки имеют внутренние
    разрывы и стандартная сегментация по профилю может давать лишние сегменты.
    """
    mask = (mono == 0).astype(np.uint8)
    h, _ = mask.shape

    v_profile = mask.sum(axis=0)
    cols = np.where(v_profile > 0)[0]

    if cols.size == 0:
        return []

    x_min = int(cols.min())
    x_max = int(cols.max())

    empty_cols = np.where(v_profile[x_min : x_max + 1] == 0)[0] + x_min

    gaps: list[tuple[int, int, int]] = []
    if empty_cols.size > 0:
        start = int(empty_cols[0])
        prev = int(empty_cols[0])

        for value in empty_cols[1:]:
            x = int(value)
            if x == prev + 1:
                prev = x
            else:
                gaps.append((start, prev, prev - start + 1))
                start = x
                prev = x

        gaps.append((start, prev, prev - start + 1))

    need_gaps = expected_count - 1

    if len(gaps) < need_gaps:
        raise RuntimeError(
            f"Недостаточно пробелов для сегментации: найдено {len(gaps)}, нужно {need_gaps}. "
            "Проверь, что в PHRASE символы разделены пробелами."
        )

    selected_gaps = sorted(gaps, key=lambda g: g[2], reverse=True)[:need_gaps]
    cuts = sorted([(g[0] + g[1]) // 2 for g in selected_gaps])

    bounds = [x_min] + cuts + [x_max + 1]

    boxes: list[SegmentBox] = []

    for i in range(len(bounds) - 1):
        x0 = bounds[i]
        x1 = bounds[i + 1] - 1

        part = mask[:, x0 : x1 + 1]
        ys, xs = np.where(part > 0)

        if ys.size == 0:
            continue

        real_x0 = x0 + int(xs.min())
        real_x1 = x0 + int(xs.max())
        y0 = int(ys.min())
        y1 = int(ys.max())

        # Небольшая рамка вокруг сегмента.
        x0p = max(0, real_x0 - 1)
        x1p = min(mask.shape[1] - 1, real_x1 + 1)
        y0p = max(0, y0 - 1)
        y1p = min(h - 1, y1 + 1)

        fname = f"segment_{i + 1:02d}.bmp"
        boxes.append(
            SegmentBox(
                index=i + 1,
                x0=x0p,
                y0=y0p,
                x1=x1p,
                y1=y1p,
                width=x1p - x0p + 1,
                height=y1p - y0p + 1,
                file_name=fname,
            )
        )

    return boxes


def draw_boxes_on_image(mono: np.ndarray, boxes: list[SegmentBox], path: Path) -> None:
    rgb = np.stack([mono, mono, mono], axis=-1)
    image = Image.fromarray(rgb.astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(image)

    for box in boxes:
        draw.rectangle((box.x0, box.y0, box.x1, box.y1), outline=(255, 0, 0), width=2)
        draw.text((box.x0, max(0, box.y0 - 14)), str(box.index), fill=(255, 0, 0))

    image.save(path)


def save_segments(mono: np.ndarray, boxes: list[SegmentBox]) -> None:
    for box in boxes:
        cropped = mono[box.y0 : box.y1 + 1, box.x0 : box.x1 + 1]
        save_gray(cropped, SEGMENTS_DIR / box.file_name)
        save_gray(cropped, SRC_SEGMENTS_DIR / box.file_name)


def save_boxes_csv(boxes: list[SegmentBox]) -> None:
    with BOXES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["index", "x0", "y0", "x1", "y1", "width", "height", "file"])

        for box in boxes:
            writer.writerow(
                [
                    box.index,
                    box.x0,
                    box.y0,
                    box.x1,
                    box.y1,
                    box.width,
                    box.height,
                    box.file_name,
                ]
            )


def render_symbol(symbol: str, font: ImageFont.FreeTypeFont) -> np.ndarray:
    canvas_w, canvas_h = 220, 220

    image = Image.new("L", (canvas_w, canvas_h), color=255)
    draw = ImageDraw.Draw(image)

    bbox = draw.textbbox((0, 0), symbol, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = (canvas_w - tw) // 2 - bbox[0]
    y = (canvas_h - th) // 2 - bbox[1]

    draw.text((x, y), symbol, fill=0, font=font)

    arr = np.asarray(image, dtype=np.uint8)
    mask = arr < BIN_THRESHOLD
    ys, xs = np.where(mask)

    if ys.size == 0:
        raise RuntimeError(
            f"Символ {symbol!r} не отрисован. Проверь шрифт с поддержкой угаритского письма."
        )

    y0 = max(0, int(ys.min()) - TRIM_PADDING)
    y1 = min(arr.shape[0] - 1, int(ys.max()) + TRIM_PADDING)
    x0 = max(0, int(xs.min()) - TRIM_PADDING)
    x1 = min(arr.shape[1] - 1, int(xs.max()) + TRIM_PADDING)

    cropped = arr[y0 : y1 + 1, x0 : x1 + 1]
    mono = np.where(cropped < BIN_THRESHOLD, 0, 255).astype(np.uint8)
    return mono


def build_alphabet_profiles(font: ImageFont.FreeTypeFont) -> None:
    for i, symbol in enumerate(SYMBOLS, start=1):
        code = f"U{ord(symbol):04X}"
        stem = f"sym_{i:02d}_{code}"

        symbol_img = render_symbol(symbol, font)
        mask = (symbol_img == 0).astype(np.uint8)

        profile_x = mask.sum(axis=0).astype(np.int32)
        profile_y = mask.sum(axis=1).astype(np.int32)

        template_name = f"{stem}.bmp"
        profile_x_name = f"{stem}_profile_x.png"
        profile_y_name = f"{stem}_profile_y.png"

        save_gray(symbol_img, ALPHABET_TEMPLATES_DIR / template_name)
        save_gray(symbol_img, SRC_ALPHABET_TEMPLATES_DIR / template_name)

        save_profile_plot(profile_x, "X", ALPHABET_PROFILES_DIR / profile_x_name)
        save_profile_plot(profile_y, "Y", ALPHABET_PROFILES_DIR / profile_y_name)

        shutil.copy2(ALPHABET_PROFILES_DIR / profile_x_name, SRC_ALPHABET_PROFILES_DIR / profile_x_name)
        shutil.copy2(ALPHABET_PROFILES_DIR / profile_y_name, SRC_ALPHABET_PROFILES_DIR / profile_y_name)


def write_report(
    phrase: str,
    image_shape: tuple[int, int],
    boxes: list[SegmentBox],
    font_path: Path,
) -> None:
    h, w = image_shape

    lines: list[str] = []

    lines.append("# Лабораторная работа №6")
    lines.append("## Сегментация текста")
    lines.append("")
    lines.append(f"### Вариант {VARIANT}: {ALPHABET_NAME}")
    lines.append("")
    lines.append("### Исходные данные")
    lines.append(f"- Фраза: `{phrase}`")
    lines.append(f"- Ожидаемое количество символов без пробелов: `{EXPECTED_SYMBOL_COUNT}`")
    lines.append(f"- Шрифт: `{font_path.name}`, размер `{FONT_SIZE}`")
    lines.append(f"- Размер монохромного изображения: `{w}x{h}`")
    lines.append(f"- Количество найденных символов: `{len(boxes)}`")
    lines.append("")
    lines.append("### Формулы профилей")
    lines.append("")
    lines.append("```text")
    lines.append("H(y) = sum_x I_b(x, y)")
    lines.append("V(x) = sum_y I_b(x, y)")
    lines.append("```")
    lines.append("")
    lines.append("Где `I_b(x,y)=1` для черного пикселя и `0` для белого.")
    lines.append("")
    lines.append("### 1. Подготовка строки")
    lines.append("")
    lines.append("#### 1.1 Монохромное изображение фразы")
    lines.append("![input](src/input/phrase_mono.bmp)")
    lines.append("")
    lines.append("### 2. Профили изображения")
    lines.append("")
    lines.append("| Горизонтальный профиль | Вертикальный профиль |")
    lines.append("|:----------------------:|:--------------------:|")
    lines.append("| ![h](src/profiles/horizontal_profile.png) | ![v](src/profiles/vertical_profile.png) |")
    lines.append("")
    lines.append("### 3. Сегментация символов")
    lines.append("")
    lines.append(
        "Из-за сложной структуры угаритских символов стандартная сегментация по нулевым "
        "провалам профиля может давать лишние разбиения. Поэтому использована сегментация "
        "по вертикальному профилю с априорно известным числом символов строки."
    )
    lines.append("")
    lines.append("#### 3.1 Обрамляющие прямоугольники")
    lines.append("![boxes](src/segments/segmentation_boxes.png)")
    lines.append("")
    lines.append("#### 3.2 Вырезанные сегменты")
    lines.append("")

    for box in boxes:
        lines.append(
            f"- Сегмент {box.index}: `[segment_{box.index:02d}]` -> "
            f"![s{box.index}](src/segments/{box.file_name})"
        )

    lines.append("")
    lines.append("#### 3.3 Массив координат прямоугольников")
    lines.append("")
    lines.append("| idx | x0 | y0 | x1 | y1 | w | h |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")

    for box in boxes:
        lines.append(
            f"| {box.index} | {box.x0} | {box.y0} | {box.x1} | {box.y1} | "
            f"{box.width} | {box.height} |"
        )

    lines.append("")
    lines.append(f"CSV с координатами (`;`-разделитель): `results/{BOXES_CSV.name}`")
    lines.append("")
    lines.append("### 4. Профили символов выбранного алфавита")
    lines.append("")
    lines.append("- Эталоны символов: `src/alphabet/templates/`")
    lines.append("- Профили X/Y: `src/alphabet/profiles/`")
    lines.append("- Построены для всех 30 символов угаритского алфавита варианта 11.")
    lines.append("")
    lines.append("Пример (первые 6 символов):")
    lines.append("")
    lines.append("| Символ | Эталон | Профиль X | Профиль Y |")
    lines.append("|:------:|:------:|:---------:|:---------:|")

    for i, symbol in enumerate(SYMBOLS[:6], start=1):
        code = f"U{ord(symbol):04X}"
        stem = f"sym_{i:02d}_{code}"
        lines.append(
            f"| {symbol} | ![t{i}](src/alphabet/templates/{stem}.bmp) | "
            f"![px{i}](src/alphabet/profiles/{stem}_profile_x.png) | "
            f"![py{i}](src/alphabet/profiles/{stem}_profile_y.png) |"
        )

    lines.append("")
    lines.append("### Вывод")
    lines.append(
        "Реализованы расчёты горизонтального и вертикального профилей, сегментация строки "
        "на символы и построение профилей символов алфавита варианта 11. Получен массив "
        "координат прямоугольников в порядке чтения слева направо."
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    setup_dirs()

    font_path = find_font_path()
    font = ImageFont.truetype(str(font_path), FONT_SIZE)

    mono = render_phrase_mono(PHRASE, font)

    save_gray(mono, INPUT_DIR / "phrase_mono.bmp")
    save_gray(mono, SRC_INPUT_DIR / "phrase_mono.bmp")

    mask = (mono == 0).astype(np.uint8)

    h_profile = mask.sum(axis=1).astype(np.int32)
    v_profile = mask.sum(axis=0).astype(np.int32)

    save_profile_plot(h_profile, "Горизонтальный", PROFILES_DIR / "horizontal_profile.png")
    save_profile_plot(v_profile, "Вертикальный", PROFILES_DIR / "vertical_profile.png")

    shutil.copy2(PROFILES_DIR / "horizontal_profile.png", SRC_PROFILES_DIR / "horizontal_profile.png")
    shutil.copy2(PROFILES_DIR / "vertical_profile.png", SRC_PROFILES_DIR / "vertical_profile.png")

    boxes = extract_segments_fixed_count(mono, expected_count=EXPECTED_SYMBOL_COUNT)

    draw_boxes_on_image(mono, boxes, SEGMENTS_DIR / "segmentation_boxes.png")
    shutil.copy2(SEGMENTS_DIR / "segmentation_boxes.png", SRC_SEGMENTS_DIR / "segmentation_boxes.png")

    save_segments(mono, boxes)
    save_boxes_csv(boxes)

    build_alphabet_profiles(font)

    write_report(PHRASE, mono.shape, boxes, font_path)

    print("Лабораторная работа №6 выполнена.")
    print(f"Вариант: {VARIANT} ({ALPHABET_NAME})")
    print(f"Фраза (Unicode): {PHRASE.encode('unicode_escape').decode('ascii')}")
    print(f"Ожидаемое количество символов: {EXPECTED_SYMBOL_COUNT}")
    print(f"Сегментов найдено: {len(boxes)}")
    print(f"CSV координат: {BOXES_CSV}")
    print(f"Отчет: {REPORT_PATH}")


if __name__ == "__main__":
    main()
