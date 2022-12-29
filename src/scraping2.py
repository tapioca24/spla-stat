import os
import re
import time
import requests
from bs4 import BeautifulSoup
import src.statink as s
import src.constants as c
import src.utils as u


def _get_csv_file_paths(current_path: str, delay: int) -> list[str]:
    url = f"{s.CSV_BASE_URL}{current_path}"
    print(f"request to {current_path}")
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    anchors = soup.find_all("a")
    paths = list(map(lambda x: x.get("href"), anchors))
    csv_paths = list(filter(lambda x: re.match(rf"{current_path}.+\.csv", x), paths))
    dir_paths = list(filter(lambda x: re.match(rf"{current_path}.+/", x), paths))

    for dir_path in dir_paths:
        time.sleep(delay)
        nested_csv_paths = _get_csv_file_paths(dir_path, delay)
        csv_paths.extend(nested_csv_paths)

    return csv_paths


def _check_csv_exist(file_url: str) -> bool:
    filename = os.path.basename(file_url)
    filepath = f"{c.STATINK_CSV_DIR}/{filename}"
    return os.path.exists(filepath) and os.path.getsize(filepath) > 0


def update_csv_files(delay: int):
    csv_paths = _get_csv_file_paths(s.RESULTS_CSV_ROOT_PATH, delay)
    non_existing_files = list(filter(lambda x: not _check_csv_exist(x), csv_paths))

    file_num = len(non_existing_files)

    for i, path in enumerate(non_existing_files):
        time.sleep(delay)
        url = s.CSV_BASE_URL + path
        print(f"({i+1}/{file_num}) download {url}")
        u.download_file_to_dir(url, c.STATINK_CSV_DIR)
