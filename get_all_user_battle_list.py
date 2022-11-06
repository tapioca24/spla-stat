import time
import pandas as pd
from get_user_battle_list import get_user_battle_list

USER_DATA_SOURCE = "data/users.csv"
ALL_USER_BATTLE_LIST_PATH = "data/all_user_battle_list.csv"


def get_all_user_battle_list(interval: int = 5):
    all_user_battle_list = []

    user_list_df = pd.read_csv(USER_DATA_SOURCE)
    for index, user in user_list_df.iterrows():
        username = user["Username"]

        if index != 0:
            time.sleep(interval)

        user_battle_list = get_user_battle_list(username, interval)
        all_user_battle_list.extend(user_battle_list)

    return all_user_battle_list


all_user_battle_list = get_all_user_battle_list()
all_user_battle_df = pd.DataFrame(all_user_battle_list).drop_duplicates()
all_user_battle_df.to_csv(ALL_USER_BATTLE_LIST_PATH, index=False)
