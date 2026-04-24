# Лабораторная работа №6
## Сегментация текста

### Вариант 11: Угаритский алфавит

### Исходные данные
- Фраза: `𐎀𐎁𐎂 𐎍𐎎𐎏 𐎛𐎚𐎗`
- Шрифт: `NotoSansUgaritic-Regular.ttf`, размер `92`
- Размер монохромного изображения: `892x123`
- Количество найденных символов: `11`

### Формулы профилей

```text
H(y) = sum_x I_b(x, y)
V(x) = sum_y I_b(x, y)
```

Где `I_b(x,y)=1` для черного пикселя и `0` для белого.

### 1. Подготовка строки

#### 1.1 Монохромное изображение фразы
![input](src/input/phrase_mono.bmp)

### 2. Профили изображения

| Горизонтальный профиль | Вертикальный профиль |
|:----------------------:|:--------------------:|
| ![h](src/profiles/horizontal_profile.png) | ![v](src/profiles/vertical_profile.png) |

### 3. Сегментация символов (по вертикальному профилю с прореживанием)

#### 3.1 Обрамляющие прямоугольники
![boxes](src/segments/segmentation_boxes.png)

#### 3.2 Вырезанные сегменты

- Сегмент 1: `[segment_01]` -> ![s1](src/segments/segment_01.bmp)
- Сегмент 2: `[segment_02]` -> ![s2](src/segments/segment_02.bmp)
- Сегмент 3: `[segment_03]` -> ![s3](src/segments/segment_03.bmp)
- Сегмент 4: `[segment_04]` -> ![s4](src/segments/segment_04.bmp)
- Сегмент 5: `[segment_05]` -> ![s5](src/segments/segment_05.bmp)
- Сегмент 6: `[segment_06]` -> ![s6](src/segments/segment_06.bmp)
- Сегмент 7: `[segment_07]` -> ![s7](src/segments/segment_07.bmp)
- Сегмент 8: `[segment_08]` -> ![s8](src/segments/segment_08.bmp)
- Сегмент 9: `[segment_09]` -> ![s9](src/segments/segment_09.bmp)
- Сегмент 10: `[segment_10]` -> ![s10](src/segments/segment_10.bmp)
- Сегмент 11: `[segment_11]` -> ![s11](src/segments/segment_11.bmp)

#### 3.3 Массив координат прямоугольников

| idx | x0 | y0 | x1 | y1 | w | h |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 48 | 101 | 67 | 72 | 20 |
| 2 | 120 | 11 | 191 | 67 | 72 | 57 |
| 3 | 210 | 10 | 229 | 87 | 20 | 78 |
| 4 | 272 | 10 | 291 | 87 | 20 | 78 |
| 5 | 296 | 10 | 315 | 87 | 20 | 78 |
| 6 | 320 | 10 | 339 | 87 | 20 | 78 |
| 7 | 358 | 10 | 418 | 87 | 61 | 78 |
| 8 | 455 | 10 | 518 | 88 | 64 | 79 |
| 9 | 562 | 16 | 639 | 112 | 78 | 97 |
| 10 | 658 | 40 | 735 | 58 | 78 | 19 |
| 11 | 754 | 18 | 861 | 60 | 108 | 43 |

CSV с координатами (`;`-разделитель): `results/segments_boxes.csv`

### 4. Профили символов выбранного алфавита

- Эталоны символов: `src/alphabet/templates/`
- Профили X/Y: `src/alphabet/profiles/`
- Построены для всех 30 символов угаритского алфавита варианта 11.

Пример (первые 6 символов):

| Символ | Эталон | Профиль X | Профиль Y |
|:------:|:------:|:---------:|:---------:|
| 𐎀 | ![t1](src/alphabet/templates/sym_01_U10380.bmp) | ![px1](src/alphabet/profiles/sym_01_U10380_profile_x.png) | ![py1](src/alphabet/profiles/sym_01_U10380_profile_y.png) |
| 𐎁 | ![t2](src/alphabet/templates/sym_02_U10381.bmp) | ![px2](src/alphabet/profiles/sym_02_U10381_profile_x.png) | ![py2](src/alphabet/profiles/sym_02_U10381_profile_y.png) |
| 𐎂 | ![t3](src/alphabet/templates/sym_03_U10382.bmp) | ![px3](src/alphabet/profiles/sym_03_U10382_profile_x.png) | ![py3](src/alphabet/profiles/sym_03_U10382_profile_y.png) |
| 𐎃 | ![t4](src/alphabet/templates/sym_04_U10383.bmp) | ![px4](src/alphabet/profiles/sym_04_U10383_profile_x.png) | ![py4](src/alphabet/profiles/sym_04_U10383_profile_y.png) |
| 𐎄 | ![t5](src/alphabet/templates/sym_05_U10384.bmp) | ![px5](src/alphabet/profiles/sym_05_U10384_profile_x.png) | ![py5](src/alphabet/profiles/sym_05_U10384_profile_y.png) |
| 𐎅 | ![t6](src/alphabet/templates/sym_06_U10385.bmp) | ![px6](src/alphabet/profiles/sym_06_U10385_profile_x.png) | ![py6](src/alphabet/profiles/sym_06_U10385_profile_y.png) |

### Вывод
Реализованы расчеты горизонтального и вертикального профилей, сегментация символов по профилю с прореживанием и построение профилей символов алфавита варианта 11. Получен массив координат прямоугольников в порядке чтения слева направо.
