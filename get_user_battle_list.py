import time
import re
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import statink

tz_jst = timezone(timedelta(hours=9))

# battle row の HTML から user battle item の辞書を抽出して返却する
def extract_user_battle_item_from_html(battle_row):
    # バトルの URL を取得する
    battle_path = battle_row.find("a", text="Detail").get("href")
    battle_url = f"{statink.BASE_URL}{battle_path}"

    # URL からユーザー名を抽出する
    username = re.search(r"https://stat.ink/@(.*)/spl3", battle_url).group(1)

    # バトルの日時を取得する
    battle_dt_str = battle_row.find("time").get("datetime")
    battle_dt = datetime.fromisoformat(battle_dt_str).astimezone(tz_jst)

    return {"Datetime": battle_dt, "Username": username, "Url": battle_url}


# user battle list ページを再帰的に fetch し、マージしたリストを返却する
def get_user_battle_list_from_url(user_battle_list_url: str, interval: int):
    # user battle list ページをリクエストする
    print(f"request to {user_battle_list_url}")
    r = requests.get(user_battle_list_url)
    soup = BeautifulSoup(r.text, "html.parser")

    # ページ内のすべての battle row を検索する
    battle_rows = soup.find_all("tr", class_="battle-row")
    user_battle_list_in_page = list(
        map(extract_user_battle_item_from_html, battle_rows)
    )

    # 次のページが存在するか確認し、なければ終了する
    next_link_tag = soup.select_one("ul.pagination > li.next > a")
    if next_link_tag is None:
        return user_battle_list_in_page

    time.sleep(interval)

    # 次のページがあれば続けて探索する
    next_user_battle_list_page_path = next_link_tag.get("href")
    next_user_battle_list_page_url = (
        f"{statink.BASE_URL}{next_user_battle_list_page_path}"
    )
    next_user_battle_list_in_page = get_user_battle_list_from_url(
        next_user_battle_list_page_url, interval
    )

    # このページの結果と次のページの結果を結合する
    user_battle_list_in_page.extend(next_user_battle_list_in_page)

    return user_battle_list_in_page


# username の user battle list を返す
def get_user_battle_list(username: str, interval: int = 5):
    first_user_battle_list_url = (
        f"{statink.BASE_URL}/@{username}/spl3?f%5Blobby%5D=bankara_challenge"
    )
    return get_user_battle_list_from_url(first_user_battle_list_url, interval)
