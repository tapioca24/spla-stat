import os
import datetime as dt
import requests

TZ_JST = dt.timezone(dt.timedelta(hours=9))


def date_range(start, stop, step=dt.timedelta(days=1)):
    current = start
    while current < stop:
        yield current
        current += step


def download_file(url: str, dst_path: str):
    """
    url が指すファイルを指定したパスにダウンロードする
    """
    try:
        r = requests.get(url)
        with open(dst_path, mode="wb") as f:
            f.write(r.content)
    except Exception as e:
        print(e)


def download_file_to_dir(url, dst_dir):
    """
    url が指すファイルを指定したディレクトリにダウンロードする
    ファイル名は url のベースネームを使用する
    """
    os.makedirs(dst_dir, exist_ok=True)
    download_file(url, os.path.join(dst_dir, os.path.basename(url)))


def color_code_to_rgb(code: str) -> tuple[int, int, int]:
    """
    カラーコードを RGB に変換する
    RGB の各値の範囲は (255, 255, 255)
    e.g. "#df6624" => (223, 102, 36)
    """
    r = int(code[1:3], 16)
    g = int(code[3:5], 16)
    b = int(code[5:7], 16)
    return r, g, b


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    """
    RGB を HSL に変換する
    HSL の各値の範囲は (360, 100, 100)
    e.g. (223, 102, 36) => (21, 74, 50)
    """
    min_value = min(r, g, b)
    max_value = max(r, g, b)

    if min_value == max_value:
        h_dash = 0
    if min_value == b:
        h_dash = 60 * (g - r) / (max_value - min_value) + 60
    elif min_value == r:
        h_dash = 60 * (b - g) / (max_value - min_value) + 180
    else:
        h_dash = 60 * (r - b) / (max_value - min_value) + 300
    h = int(h_dash)

    l_dash = (max_value + min_value) / 2
    l = int(l_dash * 100 / 255)

    s_dash = (
        (max_value - min_value) / (max_value + min_value)
        if l_dash <= 127
        else (max_value - min_value) / (510 - max_value - min_value)
    )
    s = int(100 * s_dash)

    return h, s, l


def color_code_to_hsl(code: str) -> tuple[int, int, int]:
    """
    カラーコードを HSL に変換する
    HSL の各値の範囲は (360, 100, 100)
    e.g. "#df6624" => (21, 74, 50)
    """
    r, g, b = color_code_to_rgb(code)
    return rgb_to_hsl(r, g, b)
