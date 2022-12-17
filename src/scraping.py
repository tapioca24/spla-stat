import os
import json
import time
import re
import datetime as dt
from typing import Union

import requests
import pandas as pd
from bs4 import BeautifulSoup

import src.utils as u
import src.statink as s
import src.constants as c


TZ_JST = dt.timezone(dt.timedelta(hours=9))


def update_source_weapons():
    """
    ブキデータを取得して更新する
    """
    os.makedirs(c.SOURCE_PATH, exist_ok=True)

    r = requests.get(s.API_WEAPON_URL)
    weapon_json = json.loads(r.content)

    def weapon_to_wobj(weapon: object) -> object:
        return {
            "Key": weapon["key"],
            "Name": weapon["name"]["ja_JP"],
            "Type": weapon["type"]["key"],
            "Type Name": weapon["type"]["name"]["ja_JP"],
            "Sub": weapon["sub"]["key"],
            "Sub Name": weapon["sub"]["name"]["ja_JP"],
            "Special": weapon["special"]["key"],
            "Special Name": weapon["special"]["name"]["ja_JP"],
        }

    weapon_obj_list = list(map(weapon_to_wobj, weapon_json))
    main = pd.DataFrame(weapon_obj_list)
    main.to_csv(c.SOURCE_MAIN_PATH, index=False)

    sub = (
        main[["Sub", "Sub Name"]]
        .rename(columns={"Sub": "Key", "Sub Name": "Name"})
        .drop_duplicates()
    )
    sub.to_csv(c.SOURCE_SUB_PATH, index=False)

    special = (
        main[["Special", "Special Name"]]
        .rename(columns={"Special": "Key", "Special Name": "Name"})
        .drop_duplicates()
    )
    special.to_csv(c.SOURCE_SPECIAL_PATH, index=False)

    weapon_type = (
        main[["Type", "Type Name"]]
        .rename(columns={"Type": "Key", "Type Name": "Name"})
        .drop_duplicates()
    )
    weapon_type.to_csv(c.SOURCE_TYPE_PATH, index=False)


def update_source_rules():
    """
    ルールデータを取得して更新する
    """
    os.makedirs(c.SOURCE_PATH, exist_ok=True)
    r = requests.get(s.API_RULE_URL)
    rule_json = json.loads(r.content)

    def rule_to_robj(rule: object) -> object:
        return {"Key": rule["key"], "Name": rule["short_name"]["ja_JP"]}

    rule_obj_list = list(map(rule_to_robj, rule_json))
    rule = pd.DataFrame(rule_obj_list)
    rule.to_csv(c.SOURCE_RULE_PATH, index=False)


def update_source_stages():
    """
    ステージデータを取得して更新する
    """
    os.makedirs(c.SOURCE_PATH, exist_ok=True)
    r = requests.get(s.API_STAGE_URL)
    stage_json = json.loads(r.content)

    def stage_to_sobj(stage: object) -> object:
        return {"Key": stage["key"], "Name": stage["name"]["ja_JP"]}

    stage_obj_list = list(map(stage_to_sobj, stage_json))
    stage = pd.DataFrame(stage_obj_list)
    stage.to_csv(c.SOURCE_STAGE_PATH, index=False)


def _download_image_from_statink(asset_type: str, key: str, dst_dir: str):
    url = f"{s.BASE_URL}{s.ASSETS_PATH}/{asset_type}/{key}.png"
    print(url)
    u.download_file_to_dir(url, dst_dir)


def update_source_images(delay: int):
    """
    stat.ink から画像を取得する
    すでにファイルがある場合はスキップ

    delay: 取得間隔（秒）
    """
    os.makedirs(c.IMAGES_DIR, exist_ok=True)
    source_list = [
        ("main", c.SOURCE_MAIN_PATH),
        ("sub", c.SOURCE_SUB_PATH),
        ("special", c.SOURCE_SPECIAL_PATH),
    ]
    for i, (asset_type, source_path) in enumerate(source_list):
        df = pd.read_csv(source_path)
        for j, row in df.iterrows():
            key = row["Key"]
            path = f"{c.IMAGES_DIR}/{key}.png"
            if os.path.exists(path):
                continue
            if not (i == 0 and j == 0):
                time.sleep(delay)
            _download_image_from_statink(asset_type, key, c.IMAGES_DIR)


def update_user_list():
    """
    stat.ink の最新のバトルからユーザー名を抽出して USER_DATA_PATH へ保存する
    csv ファイルがすでに存在する場合は重複がないようにマージする
    """
    # ファイルがなければ作成する
    os.makedirs(c.DATA_DIR, exist_ok=True)
    if not os.path.exists(c.USER_DATA_PATH):
        f = open(c.USER_DATA_PATH, "w")
        f.write("Username")
        f.close()

    df = pd.read_csv(c.USER_DATA_PATH)

    # 最新のバトルデータを stat.ink から取得する
    url = f"{s.BASE_URL}/api/internal/latest-battles"
    r = requests.get(url)

    # バトルデータをパースしてリストに変換する
    battles_dict = json.loads(r.content)
    battles = battles_dict["battles"]

    # バトルデータから投稿者の username を抽出する関数を定義する
    def extract_username(battle):
        user_url = battle["user"]["url"]
        username = re.search(r"https://stat.ink/@(.*)", user_url)
        return username.group(1)

    # バトルのリストを username のリストに変換する
    usernames = list(map(extract_username, battles))
    # username の重複を排除する
    unique_usernames = list(set(usernames))

    # username のリストから DataFrame を作成する
    latest_df = pd.DataFrame({"Username": unique_usernames})

    # 既存の DataFrame と今回取得した DataFrame をマージした新しい DataFrame を作成する
    merged_df = pd.concat([df, latest_df], ignore_index=True)
    # username の重複を排除する
    merged_df = merged_df.drop_duplicates()

    # csv ファイルを上書きする
    merged_df.to_csv(c.USER_DATA_PATH, index=False)


def _create_user_battle_list_item(battle_row):
    # Datetime
    time_tag = battle_row.select_one(".cell-datetime time")
    battle_dt_str = time_tag.get("datetime")
    battle_dt = dt.datetime.fromisoformat(battle_dt_str).astimezone(TZ_JST)

    # Url
    battle_path = battle_row.find("a", text="Detail").get("href")
    battle_url = f"{s.BASE_URL}{battle_path}"

    # Username
    username = re.search(r"/@(.+)/spl3", battle_url).group(1)

    # Rule
    image = battle_row.select_one(".cell-rule-icon img")
    src = image.get("src")
    rule = re.search(r"/spl3/(.+).png", src).group(1)

    # Disconnected
    disconnected = "disconnected" in battle_row["class"]

    return {
        "Datetime": battle_dt,
        "Username": username,
        "Url": battle_url,
        "Rule": rule,
        "Disconnected": disconnected,
    }


def _get_user_battles_in_page(page_url: str) -> tuple[pd.DataFrame, Union[str, None]]:
    # user battle list ページをリクエストする
    print(f"request to {page_url}")
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, "html.parser")

    # ページ内の user_battle_list を取得する
    battle_rows = soup.find_all("tr", class_="battle-row")
    user_battle_list_in_page = list(map(_create_user_battle_list_item, battle_rows))
    user_battles_df = pd.DataFrame(user_battle_list_in_page)

    # 次ページの ancher タグを取得する
    next_link_tag = soup.select_one("ul.pagination > li.next > a")

    if next_link_tag is None:
        return user_battles_df, None

    next_link_path = next_link_tag.get("href")
    next_link = f"{s.BASE_URL}{next_link_path}"

    return user_battles_df, next_link


def _check_duplication(
    battles_old: pd.DataFrame, battles_new: pd.DataFrame
) -> tuple[bool, pd.DataFrame]:
    if battles_old.empty or battles_new.empty:
        return False, battles_new

    battles_merged = pd.concat([battles_new, battles_old], ignore_index=True)
    dup = battles_merged.duplicated(subset=["Url"])
    has_duplication = dup.sum() > 0

    battles_dup = battles_merged[dup]
    battles_up_to_date = battles_new[~battles_new["Url"].isin(battles_dup["Url"])]

    return has_duplication, battles_up_to_date


def _get_new_user_battles_from_url(
    page_url: str, battles_old: pd.DataFrame, delay: int
) -> pd.DataFrame:
    battles_new, next_link = _get_user_battles_in_page(page_url)
    has_duplication, battles_up_to_date = _check_duplication(battles_old, battles_new)

    # 重複した or 次ページリンクがない => 終了
    if has_duplication or (next_link is None):
        return battles_up_to_date

    time.sleep(delay)

    battles_up_to_date_on_next = _get_new_user_battles_from_url(
        next_link, battles_old, delay
    )
    battles_up_to_date = pd.concat(
        [battles_up_to_date, battles_up_to_date_on_next], ignore_index=True
    )
    return battles_up_to_date


def _get_new_user_battles(
    username: str, battles_old: pd.DataFrame, lobby: str, delay: int
) -> pd.DataFrame:
    page_url = f"{s.BASE_URL}/@{username}/spl3?f%5Blobby%5D={lobby}"
    battles_up_to_date = _get_new_user_battles_from_url(page_url, battles_old, delay)
    return battles_up_to_date


def _update_user_battle_list(
    username: str, battle_list_path: str, lobby: str, delay: int
):
    """
    指定したユーザー名についてバトル一覧を取得し csv を更新する
    """
    if not os.path.exists(battle_list_path):
        f = open(battle_list_path, "w")
        f.write("Datetime,Username,Url,Rule,Disconnected")
        f.close()

    battles = pd.read_csv(battle_list_path)
    battles["Datetime"] = pd.to_datetime(battles["Datetime"])
    user_battles = battles[battles["Username"] == username]
    new_user_battles = _get_new_user_battles(username, user_battles, lobby, delay)

    if new_user_battles.empty:
        return

    battles_merged = pd.concat([new_user_battles, battles], ignore_index=True)
    battles_dedup = battles_merged.drop_duplicates()
    battles_sorted = battles_dedup.sort_values("Datetime", ascending=False)

    battles_sorted.to_csv(battle_list_path, index=False)


def update_battle_list(battle_list_path: str, lobby: str, delay: int):
    """
    USER_DATA_PATH のすべてのユーザー名について
    指定されたバトルの一覧を取得し指定したパスへ csv として保存する

    battle_list_path: バトル一覧の csv のファイルパス
    lobby: ロビー文字列
        xmatch: Xマッチ
        bankara_challenge: バンカラマッチ（チャレンジ）
        splatfest_challenge: フェスマッチ（チャレンジ）
    delay: 取得間隔（秒）
    """
    users = pd.read_csv(c.USER_DATA_PATH)
    user_num = len(users.index)
    print(f"update battle list for {user_num} users")

    for i, user in users.iterrows():
        username = user["Username"]
        if i != 0:
            time.sleep(delay)
        print(f"({i+1}/{user_num}): @{username}")
        _update_user_battle_list(username, battle_list_path, lobby, delay)


def _get_result(texts: list[str]) -> str:
    if any("Victory" in t for t in texts):
        return "victory"
    if any("Defeat" in t for t in texts):
        return "defeat"
    if any("Draw" in t for t in texts):
        return "draw"
    return "unknown"


def _get_win(result: str) -> str:
    if result == "victory":
        return "alpha"
    if result == "defeat":
        return "bravo"
    if result == "draw":
        return "draw"
    return "unknown"


def _get_stats_info(text: str) -> str:
    if "Used in global stats: Yes" in text:
        return "allow"
    if "Used in global stats: No" in text:
        return "deny"
    if "Defeat (Exempted)" in text:
        return "exempted"
    if "Disconnected" in text:
        return "disconnected"
    return "unknown"


def _get_battle_data(battle_soup) -> dict:
    # Battle End
    td = battle_soup.find("th", text="Battle End").next_sibling
    battle_dt_str = td.find("time").get("datetime")
    battle_dt = dt.datetime.fromisoformat(battle_dt_str).astimezone(TZ_JST)

    td = battle_soup.find("th", text="Mode").next_sibling
    images = td.find_all("img")

    # Rule
    src = images[0].get("src")
    rule = re.search(r"/spl3/(.+).png", src).group(1)

    # Lobby
    src = images[1].get("src")
    lobby = re.search(r"/spl3/(.+).png", src).group(1)

    # Stage
    td = battle_soup.find("th", text="Stage").next_sibling
    stage_path = td.find("a").get("href")
    stage = re.search(r"map%5D=(.+)$", stage_path).group(1)

    # Result & Win
    td = battle_soup.find("th", text="Result").next_sibling
    labels = td.find_all("span", class_="label")
    texts = list(map(lambda label: label.text, labels))
    result = _get_result(texts)
    win = _get_win(result)

    # X Power
    if lobby == "xmatch":
        th = battle_soup.find("th", text="X Power")
        if th:
            td = th.next_sibling
            contents = td.contents
            if len(contents) > 0:
                if contents[0].name == "span":
                    xpower = None
                else:
                    xpower = float(contents[0].replace(",", ""))
            else:
                xpower = None
        else:
            xpower = None

    # Time
    td = battle_soup.find("th", text="Elapsed Time").next_sibling
    time = int(re.search(r"\((.+) seconds\)", td.text).group(1))

    # Game Version
    td = battle_soup.find("th", text="Game Version").next_sibling
    game_version = td.text

    # Stats
    td = battle_soup.find("th", text="Stats").next_sibling
    stats = _get_stats_info(td.text)

    if lobby == "xmatch":
        battle_data = {
            "Datetime": battle_dt,
            "Rule": rule,
            "Lobby": lobby,
            "Stage": stage,
            "Win": win,
            "X Power": xpower,
            "Time": time,
            "Game Version": game_version,
            "Stats": stats,
        }
    else:
        battle_data = {
            "Datetime": battle_dt,
            "Rule": rule,
            "Lobby": lobby,
            "Stage": stage,
            "Win": win,
            "Time": time,
            "Game Version": game_version,
            "Stats": stats,
        }

    return battle_data


def _get_player_data(
    player_soup,
    me_index,
    weapon_index,
    inked_index,
    kill_index,
    death_index,
    specials_index,
) -> dict:
    td_list = player_soup.find_all("td", recursive=False)

    # Me
    me = td_list[me_index].find("span") is not None

    # Weapons
    images = td_list[weapon_index].find_all("img")
    weapon_main = re.search(r"/main/(.+).png", images[0].get("src")).group(1)
    weapon_sub = re.search(r"/sub/(.+).png", images[1].get("src")).group(1)
    weapon_special = re.search(r"/special/(.+).png", images[2].get("src")).group(1)

    # Inked
    inked_str = td_list[inked_index].text
    if inked_str:
        inked = int(inked_str.replace(",", ""))
    else:
        inked = 0

    # Kill & Assist
    kill_and_assist_str = td_list[kill_index].text
    if kill_and_assist_str:
        match = re.search(r"(.+) \+ (.+)", kill_and_assist_str)
        kill = int(match.group(1))
        assist = int(match.group(2))
    else:
        kill = 0
        assist = 0

    kill_and_assist = kill + assist

    # Death
    death_str = td_list[death_index].text
    if death_str:
        death = int(death_str)
    else:
        death = 0

    # Specials
    specials_str = td_list[specials_index].text.replace(" ", "")
    if specials_str:
        specials = int(specials_str)
    else:
        specials = 0

    return {
        "Me": me,
        "Main Weapon": weapon_main,
        "Sub Weapon": weapon_sub,
        "Special Weapon": weapon_special,
        "Inked": inked,
        "Kill & Assist": kill_and_assist,
        "Kill": kill,
        "Assist": assist,
        "Death": death,
        "Specials": specials,
    }


def _get_team_data(
    team_soup,
    me_index,
    weapon_index,
    inked_index,
    kill_index,
    death_index,
    specials_index,
) -> list[dict]:
    players = []
    current_soup = team_soup
    for i in range(4):
        player_soup = current_soup.next_sibling.next_sibling
        current_soup = player_soup
        player_dict = _get_player_data(
            player_soup,
            me_index,
            weapon_index,
            inked_index,
            kill_index,
            death_index,
            specials_index,
        )
        players.append(player_dict)
    return sorted(players, key=lambda p: p["Me"], reverse=True)


def _get_players_data(players_soup) -> dict:
    headers = players_soup.select("thead th")
    header_texts = list(map(lambda h: h.text, headers))
    me_index = header_texts.index("")
    weapon_index = header_texts.index("Weapon")
    inked_index = header_texts.index("Inked")
    kill_index = header_texts.index("k")
    death_index = header_texts.index("d")
    specials_index = header_texts.index("Sp")

    alpha = players_soup.find("th", text="Good Guys").parent
    bravo = players_soup.find("th", text="Bad Guys").parent

    alpha_players = _get_team_data(
        alpha,
        me_index,
        weapon_index,
        inked_index,
        kill_index,
        death_index,
        specials_index,
    )
    bravo_players = _get_team_data(
        bravo,
        me_index,
        weapon_index,
        inked_index,
        kill_index,
        death_index,
        specials_index,
    )

    return {"Alpha": alpha_players, "Bravo": bravo_players}


def _get_battle_detail(page_url: str):
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, "html.parser")

    username = re.search(r"/@(.+)/spl3", page_url).group(1)

    battle_soup = soup.find(id="battle")
    battle_data = _get_battle_data(battle_soup)

    players_soup = soup.find(id="players")
    players_data = _get_players_data(players_soup)

    battle_detail = {
        "Username": username,
        "Url": page_url,
        **battle_data,
    }
    for index, player in enumerate(players_data["Alpha"]):
        player_name = f"A{index + 1}"
        battle_detail.update(
            {
                f"{player_name} Main Weapon": player["Main Weapon"],
                f"{player_name} Sub Weapon": player["Sub Weapon"],
                f"{player_name} Special Weapon": player["Special Weapon"],
                f"{player_name} Inked": player["Inked"],
                f"{player_name} Kill & Assist": player["Kill & Assist"],
                f"{player_name} Kill": player["Kill"],
                f"{player_name} Assist": player["Assist"],
                f"{player_name} Death": player["Death"],
                f"{player_name} Specials": player["Specials"],
            }
        )
    for index, player in enumerate(players_data["Bravo"]):
        player_name = f"B{index + 1}"
        battle_detail.update(
            {
                f"{player_name} Main Weapon": player["Main Weapon"],
                f"{player_name} Sub Weapon": player["Sub Weapon"],
                f"{player_name} Special Weapon": player["Special Weapon"],
                f"{player_name} Inked": player["Inked"],
                f"{player_name} Kill & Assist": player["Kill & Assist"],
                f"{player_name} Kill": player["Kill"],
                f"{player_name} Assist": player["Assist"],
                f"{player_name} Death": player["Death"],
                f"{player_name} Specials": player["Specials"],
            }
        )

    return battle_detail


def _append_new_details(
    details: pd.DataFrame, detail_list: list[dict], details_filepath: str
) -> pd.DataFrame:
    if len(detail_list) == 0:
        return details

    new_details = pd.DataFrame(detail_list)

    if details.empty:
        details = new_details
    else:
        details = pd.concat([details, new_details], ignore_index=True)

    details = details.sort_values("Datetime", ascending=False)
    details.to_csv(details_filepath, index=False)
    return details


def update_battle_details(battles: pd.DataFrame, details_filepath: str, delay: int):
    """
    バトル詳細を取得して csv ファイルに保存する

    battles: バトル一覧から読み込んだ DataFrame
    details_filepath: csv ファイルを保存するファイルパス
    delay: 取得間隔（秒）
    """
    if os.path.exists(details_filepath):
        details = pd.read_csv(details_filepath)
        details["Datetime"] = pd.to_datetime(details["Datetime"])
        # 未取得の battle を抽出する
        battles_unfetched = battles[~battles["Url"].isin(details["Url"])]
    else:
        details = pd.DataFrame()
        battles_unfetched = battles

    battle_num = len(battles_unfetched.index)
    print(f"get battle details for {battle_num} battles")

    detail_list = []
    for index, battle in battles_unfetched.reset_index().iterrows():
        if index != 0:
            time.sleep(delay)

        if index % 50 == 0:
            details = _append_new_details(details, detail_list, details_filepath)
            detail_list = []

        page_url = battle["Url"]

        print(f"({index+1}/{battle_num}) request to {page_url}")
        detail_list_item = _get_battle_detail(page_url)
        detail_list.append(detail_list_item)

    _append_new_details(details, detail_list, details_filepath)
