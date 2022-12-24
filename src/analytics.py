import numpy
import pandas as pd
import src.statink as s
import src.constants as c


def load_details(details_path: str, use_deny: bool = False) -> pd.DataFrame:
    """
    csv からバトル詳細をロードする

    details_path: バトル詳細の csv ファイルのパス
    use_deny: 統計情報利用不可のバトルを含める
    """
    details = pd.read_csv(details_path)
    return details if use_deny else details[details["Stats"] == "allow"]


def _extract_columns_for_player_info(details: pd.DataFrame) -> pd.DataFrame:
    """
    プレイヤー情報のためのカラムを抽出する

    details: バトル詳細の DataFrame
    """
    use_columns = ["Username", "Url", "Datetime", "Rule", "Stage", "Win", "Time"]
    player_list = ["A2", "A3", "A4", "B1", "B2", "B3", "B4"]
    for p in player_list:
        use_columns.extend(
            [
                f"{p} Main Weapon",
                f"{p} Sub Weapon",
                f"{p} Special Weapon",
                f"{p} Inked",
                f"{p} Kill & Assist",
                f"{p} Kill",
                f"{p} Assist",
                f"{p} Death",
                f"{p} Specials",
            ]
        )
    return details[use_columns]


def _concat_player_info(details: pd.DataFrame) -> pd.DataFrame:
    """
    投稿者以外のプレイヤーの情報をまとめてプレイヤーごとに1つのカラムに変形する

    details: バトル詳細の DataFrame
    """
    player_list = ["A2", "A3", "A4", "B1", "B2", "B3", "B4"]
    for p in player_list:
        details[p] = (
            details[f"{p} Main Weapon"]
            + ","
            + details[f"{p} Sub Weapon"]
            + ","
            + details[f"{p} Special Weapon"]
            + ","
            + details[f"{p} Inked"].astype(str)
            + ","
            + details[f"{p} Kill & Assist"].astype(str)
            + ","
            + details[f"{p} Kill"].astype(str)
            + ","
            + details[f"{p} Assist"].astype(str)
            + ","
            + details[f"{p} Death"].astype(str)
            + ","
            + details[f"{p} Specials"].astype(str)
        )
    drop_columns = []
    for p in player_list:
        drop_columns.extend(
            [
                f"{p} Main Weapon",
                f"{p} Sub Weapon",
                f"{p} Special Weapon",
                f"{p} Inked",
                f"{p} Kill & Assist",
                f"{p} Kill",
                f"{p} Assist",
                f"{p} Death",
                f"{p} Specials",
            ]
        )
    return details.drop(columns=drop_columns)


def _melt_to_players(details: pd.DataFrame) -> pd.DataFrame:
    """
    バトル詳細を wide format に変形し
    投稿者以外のプレイヤーの情報の DataFrame を返す

    details: バトル詳細の DataFrame
    """
    players = details.melt(
        id_vars=["Username", "Url", "Datetime", "Rule", "Stage", "Win", "Time"],
        value_name="Player",
    )
    player_to_team_dict = {
        "A2": "alpha",
        "A3": "alpha",
        "A4": "alpha",
        "B1": "bravo",
        "B2": "bravo",
        "B3": "bravo",
        "B4": "bravo",
    }
    players["Team"] = players["variable"].map(player_to_team_dict)
    players["Win"] = players["Win"] == players["Team"]
    return players.drop(columns="variable")


def _split_player_info(players: pd.DataFrame) -> pd.DataFrame:
    """
    結合したプレイヤー情報を再度分解する

    players: プレイヤーの DataFrame
    """
    split = (
        players["Player"]
        .str.split(",", expand=True)
        .astype(
            {
                3: "int64",
                4: "int64",
                5: "int64",
                6: "int64",
                7: "int64",
                8: "int64",
            }
        )
    )
    players["Main Weapon"] = split[0]
    players["Sub Weapon"] = split[1]
    players["Special Weapon"] = split[2]
    players["Inked"] = split[3]
    players["Kill & Assist"] = split[4]
    players["Kill"] = split[5]
    players["Assist"] = split[6]
    players["Death"] = split[7]
    players["Specials"] = split[8]
    return players.drop(columns="Player")


def get_unique_user_num(details: pd.DataFrame):
    """
    ユニークユーザー数を取得する

    details: バトル詳細の DataFrame
    """
    return len(details["Username"].unique())


def _detail_to_team_stat(detail: pd.Series, team: str) -> dict:
    time = detail["Time"]
    result_keys = [
        "Inked",
        "Kill & Assist",
        "Kill",
        "Assist",
        "Death",
        "Specials",
    ]
    team_stat = {"Win": detail["Win"][0].upper() == team}
    for key in result_keys:
        result_list = list(map(lambda x: detail[f"{team}{x+1} {key}"], range(4)))
        team_stat[f"{key} / 5min"] = numpy.sum(result_list) / time * 300

    team_stat.update(
        {
            "Kill-Death / 5min": team_stat["Kill / 5min"] - team_stat["Death / 5min"],
            "Involved": team_stat["Kill & Assist / 5min"] / team_stat["Kill / 5min"]
            if team_stat["Kill / 5min"] > 0
            else None,
        }
    )
    return team_stat


def details_to_teams(details: pd.DataFrame) -> pd.DataFrame:
    """
    バトル詳細をチーム単位に整形する

    details: バトル詳細の DataFrame
    """

    def detail_to_teams(detail: pd.Series):
        team_names = ["A", "B"]
        return list(map(lambda x: _detail_to_team_stat(detail, x), team_names))

    teams = []
    common_cols = ["Username", "Url", "Datetime", "Rule", "Stage", "Time"]
    for i, row in details.iterrows():
        team_objs = detail_to_teams(row)
        common = row[common_cols].to_dict()
        team_objs = list(map(lambda x: {**common, **x}, team_objs))
        teams.extend(team_objs)
    df = pd.DataFrame(teams)
    return df


def details_to_players(
    details: pd.DataFrame, use_heroshooter: bool = False
) -> pd.DataFrame:
    """
    バトル詳細をプレイヤー単位に整形する

    details: バトル詳細の DataFrame
    use_heroshooter: ヒーローシューターレプリカを個別に取り扱う
    """

    d = details.copy()
    d = _extract_columns_for_player_info(d)
    d = _concat_player_info(d)
    p = _melt_to_players(d)
    p = _split_player_info(p)
    main = pd.read_csv(c.SOURCE_MAIN_PATH, index_col="Key")
    weapon_type = p["Main Weapon"].apply(lambda x: main.at[x, "Type"])
    p.insert(8, "Weapon Type", weapon_type)
    for key in ["Inked", "Kill & Assist", "Kill", "Assist", "Death", "Specials"]:
        p[f"{key}/m"] = p[key] / p["Time"] * 60
    if not use_heroshooter:
        p["Main Weapon"] = p["Main Weapon"].replace("heroshooter_replica", "sshooter")
    return p


def players_group_by_rule_and(groupby_key: str, players: pd.DataFrame) -> pd.DataFrame:
    """
    プレイヤーをルールとその他の key でグルーピングして
    勝率や使用率を計算する

    groupby_key: 集計したいカラム名
    players: プレイヤーの DataFrame
    """
    players_per_rule = players["Rule"].value_counts()
    group = players.groupby(["Rule", groupby_key])
    weapons = group.mean()
    count = group["Url"].count().to_frame()
    win_rate = weapons["Win"] * 100
    weapons.insert(0, "Count", count)
    weapons.insert(2, "Win Rate", win_rate)
    weapons = weapons.reset_index()
    total_count = weapons["Rule"].apply(lambda x: players_per_rule[x])
    weapons.insert(3, "Total Count", total_count)
    usage_rate = weapons["Count"] / weapons["Total Count"] * 100
    weapons.insert(4, "Usage Rate", usage_rate)
    return weapons


def aggregate_index_per_subject(
    players: pd.DataFrame, subject: str, target: str
) -> pd.DataFrame:
    """
    対象ごとに指標を集計する
    e.g. ブキごとの使用率を集計する

    players: プレイヤー情報の DataFrame
    subject: 対象 (e.g. "Main Weapon")
    target: 集計する指標 (e.g. "Usage Rate")
    """
    df = players_group_by_rule_and(subject, players)
    df_wide = df.pivot(subject, "Rule", target).reindex(
        columns=["area", "yagura", "hoko", "asari"]
    )
    mean = df_wide.mean(axis="columns")
    median = df_wide.median(axis="columns")
    df_wide["mean"] = mean
    df_wide["median"] = median
    return df_wide.sort_values("median", ascending=False)
