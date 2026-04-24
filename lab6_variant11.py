from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from PIL import Image, ImageDraw, ImageFont

VARIANT = 11
ALPHABET_NAME = "Угаритский алфавит"
# Основные 30 букв угаритского письма: U+10380..U+1039D
SYMBOLS = [chr(code) for code in range(0x10380, 0x1039E)]

FONT_SIZE = 92
# Романтическая фраза из символов выбранного алфавита.
# Для сегментации символы отделены пробелами, как это обычно делают для учебных образцов.
PHRASE = "𐎀𐎁𐎂 𐎍𐎎𐎏 𐎛𐎚𐎗"
CANVAS_PAD = 30
BIN_THRESHOLD = 120
TRIM_PADDING = 2

PROFILE_MIN_FG_RUN = 2
PROFILE_MAX_BG_GAP = 0

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

        Path("/Library/Fonts/NotoSansUgaritic-Regular.ttf"),
        Path.home() / "Library/Fonts/NotoSansUgaritic-Regular.ttf",

        Path("/System/Library/Fonts/Supplemental/NotoSansUgaritic-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansUgaritic-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansUgaritic-Regular.ttf"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Не найден шрифт NotoSansUgaritic-Regular.ttf. "
        "Положи его рядом с lab6_variant11.py."
    )


def render_phrase_mono(phrase: str, font: ImageFont.FreeTypeFont) -> np.ndarray:
    canvas_w = 2000
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
        raise RuntimeError("Фраза не отрисована.")

    y0 = max(0, int(ys.min()) - CANVAS_PAD // 3)
    y1 = min(arr.shape[0] - 1, int(ys.max()) + CANVAS_PAD // 3)
    x0 = max(0, int(xs.min()) - CANVAS_PAD)
    x1 = min(arr.shape[1] - 1, int(xs.max()) + CANVAS_PAD)
    cropped = arr[y0 : y1 + 1, x0 : x1 + 1]
    mono = np.where(cropped < BIN_THRESHOLD, 0, 255).astype(np.uint8)
    return mono


def save_gray(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array, mode="L").save(path)


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


def profile_to_binary_runs(profile: np.ndarray) -> np.ndarray:
    return (profile > 0).astype(np.uint8)


def _runs(binary: np.ndarray) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    start = None
    current = 0
    for i, v in enumerate(binary):
        if start is None and v == 1:
            start = i
            current = 1
        elif start is not None and v != current:
            runs.append((start, i - 1, current))
            start = i
            current = int(v)
        elif start is None and v == 0:
            start = i
            current = 0
    if start is not None:
        runs.append((start, len(binary) - 1, current))
    return runs


def thin_binary_profile(binary: np.ndarray, min_fg_run: int, max_bg_gap: int) -> np.ndarray:
    out = binary.copy()
    runs = _runs(out)

    # Заполняем короткие фоновые разрывы между символами.
    for i in range(1, len(runs) - 1):
        s, e, val = runs[i]
        if val == 0 and (e - s + 1) <= max_bg_gap:
            if runs[i - 1][2] == 1 and runs[i + 1][2] == 1:
                out[s : e + 1] = 1

    # Удаляем очень короткие передние пробеги (шум).
    runs = _runs(out)
    for s, e, val in runs:
        if val == 1 and (e - s + 1) < min_fg_run:
            out[s : e + 1] = 0

    return out


def extract_segments(mono: np.ndarray) -> list[SegmentBox]:
    mask = (mono == 0).astype(np.uint8)
    v_profile = mask.sum(axis=0)

    binary = profile_to_binary_runs(v_profile)
    thinned = thin_binary_profile(binary, min_fg_run=PROFILE_MIN_FG_RUN, max_bg_gap=PROFILE_MAX_BG_GAP)
    runs = [r for r in _runs(thinned) if r[2] == 1]

    boxes: list[SegmentBox] = []
    for idx, (x0, x1, _) in enumerate(runs, start=1):
        col_slice = mask[:, x0 : x1 + 1]
        y_indices = np.where(col_slice.sum(axis=1) > 0)[0]
        if y_indices.size == 0:
            continue
        y0 = int(y_indices.min())
        y1 = int(y_indices.max())
        w = int(x1 - x0 + 1)
        h = int(y1 - y0 + 1)
        fname = f"segment_{idx:02d}.bmp"
        boxes.append(SegmentBox(idx, int(x0), y0, int(x1), y1, w, h, fname))
    return boxes


def draw_boxes_on_image(mono: np.ndarray, boxes: list[SegmentBox], path: Path) -> None:
    rgb = np.stack([mono, mono, mono], axis=-1)
    image = Image.fromarray(rgb.astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(image)
    for b in boxes:
        draw.rectangle((b.x0, b.y0, b.x1, b.y1), outline=(255, 0, 0), width=2)
        draw.text((b.x0, max(0, b.y0 - 14)), str(b.index), fill=(255, 0, 0))
    image.save(path)


def save_segments(mono: np.ndarray, boxes: list[SegmentBox]) -> None:
    for b in boxes:
        cropped = mono[b.y0 : b.y1 + 1, b.x0 : b.x1 + 1]
        save_gray(cropped, SEGMENTS_DIR / b.file_name)
        save_gray(cropped, SRC_SEGMENTS_DIR / b.file_name)


def save_boxes_csv(boxes: list[SegmentBox]) -> None:
    with BOXES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["index", "x0", "y0", "x1", "y1", "width", "height", "file"])
        for b in boxes:
            writer.writerow([b.index, b.x0, b.y0, b.x1, b.y1, b.width, b.height, b.file_name])


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
        raise RuntimeError(f"Символ {symbol!r} не отрисован. Проверьте шрифт с поддержкой угаритского письма.")
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

        t_name = f"{stem}.bmp"
        px_name = f"{stem}_profile_x.png"
        py_name = f"{stem}_profile_y.png"

        save_gray(symbol_img, ALPHABET_TEMPLATES_DIR / t_name)
        save_gray(symbol_img, SRC_ALPHABET_TEMPLATES_DIR / t_name)

        save_profile_plot(profile_x, "X", ALPHABET_PROFILES_DIR / px_name)
        save_profile_plot(profile_y, "Y", ALPHABET_PROFILES_DIR / py_name)
        shutil.copy2(ALPHABET_PROFILES_DIR / px_name, SRC_ALPHABET_PROFILES_DIR / px_name)
        shutil.copy2(ALPHABET_PROFILES_DIR / py_name, SRC_ALPHABET_PROFILES_DIR / py_name)


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
    lines.append("### 3. Сегментация символов (по вертикальному профилю с прореживанием)")
    lines.append("")
    lines.append("#### 3.1 Обрамляющие прямоугольники")
    lines.append("![boxes](src/segments/segmentation_boxes.png)")
    lines.append("")
    lines.append("#### 3.2 Вырезанные сегменты")
    lines.append("")
    for b in boxes:
        lines.append(f"- Сегмент {b.index}: `[segment_{b.index:02d}]` -> ![s{b.index}](src/segments/{b.file_name})")
    lines.append("")
    lines.append("#### 3.3 Массив координат прямоугольников")
    lines.append("")
    lines.append("| idx | x0 | y0 | x1 | y1 | w | h |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for b in boxes:
        lines.append(f"| {b.index} | {b.x0} | {b.y0} | {b.x1} | {b.y1} | {b.width} | {b.height} |")
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
    for i, sym in enumerate(SYMBOLS[:6], start=1):
        code = f"U{ord(sym):04X}"
        stem = f"sym_{i:02d}_{code}"
        lines.append(
            f"| {sym} | ![t{i}](src/alphabet/templates/{stem}.bmp) | ![px{i}](src/alphabet/profiles/{stem}_profile_x.png) | ![py{i}](src/alphabet/profiles/{stem}_profile_y.png) |"
        )
    lines.append("")
    lines.append("### Вывод")
    lines.append("Реализованы расчеты горизонтального и вертикального профилей, сегментация символов по профилю с прореживанием и построение профилей символов алфавита варианта 11. Получен массив координат прямоугольников в порядке чтения слева направо.")

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

    boxes = extract_segments(mono)
    draw_boxes_on_image(mono, boxes, SEGMENTS_DIR / "segmentation_boxes.png")
    shutil.copy2(SEGMENTS_DIR / "segmentation_boxes.png", SRC_SEGMENTS_DIR / "segmentation_boxes.png")
    save_segments(mono, boxes)
    save_boxes_csv(boxes)

    build_alphabet_profiles(font)

    write_report(PHRASE, mono.shape, boxes, font_path)

    print("Лабораторная работа №6 выполнена.")
    print(f"Вариант: {VARIANT} ({ALPHABET_NAME})")
    print(f"Фраза (Unicode): {PHRASE.encode('unicode_escape').decode('ascii')}")
    print(f"Сегментов найдено: {len(boxes)}")
    print(f"CSV координат: {BOXES_CSV}")
    print(f"Отчет: {REPORT_PATH}")


if __name__ == "__main__":
    main()
