import os
import json
import re
import requests
import pandas as pd

USERS_DATA_FILENAME = "data/users.csv"

# csv ファイルがなければ作成しておく
is_file = os.path.isfile(USERS_DATA_FILENAME)
if not is_file:
    f = open(USERS_DATA_FILENAME, "w")
    f.write("Username")
    f.close()

# csv ファイルから既存のユーザーを読み込む
df = pd.read_csv(USERS_DATA_FILENAME)

# 最新のバトルデータを stat.ink から取得する
r = requests.get("https://stat.ink/api/internal/latest-battles")

# バトルデータをパースしてリストに変換する
battles_dict = json.loads(r.text)
battles = battles_dict["battles"]

# バトルデータから投稿者の username を抽出する関数を定義する
def extract_username(battle):
    user_url = battle["user"]["url"]
    username = re.search(r"https://stat.ink/@(.*)", user_url)
    return username.group(1)


# バトルのリストを username のみのリストに変換する
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
merged_df.to_csv(USERS_DATA_FILENAME, index=False)
