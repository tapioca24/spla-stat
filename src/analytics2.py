import datetime as dt
import numpy as np
import pandas as pd
import src.constants as c
import src.utils as u
import src.definitions as d


def read_details_on(date: dt.date, lobby: d.Lobby = d.Lobby.XMATCH) -> pd.DataFrame:
    """
    日付を指定して戦績データを取得する
    """
    filename = str(date) + ".csv"
    filepath = f"{c.STATINK_CSV_DIR}/{filename}"
    details = pd.read_csv(filepath)
    details = details[details["lobby"] == lobby.value]
    details.insert(2, "date", str(date))
    details["period"] = pd.to_datetime(details["period"])
    details["date"] = pd.to_datetime(details["date"])
    details["knockout"] = details["knockout"].astype("bool")
    return details


def read_details_from_to(
    date_from: dt.date, date_to: dt.date, lobby: d.Lobby = d.Lobby.XMATCH
) -> pd.DataFrame:
    """
    日付の期間を指定して戦績データを取得する
    """
    date_list = list(u.date_range(date_from, date_to))
    details_list = list(map(lambda x: read_details_on(x, lobby), date_list))
    return pd.concat(details_list, ignore_index=True)


def add_orchestration_columns(details: pd.DataFrame) -> pd.DataFrame:
    """
    戦績データにブキ編成のカラムを追加する
    - "A-orch"
    - "B-orch"
    - "weapon-match"
    - "pool-match"
    - "weapon-type-match"
    - "weapon-range-match"
    - "orch-diff"
    """
    pool = pd.read_csv(c.SOURCE_MAIN_POOL_PATH, index_col="Key")

    def create_team_cols(team: str) -> list[str]:
        return list(map(lambda x: f"{team}{x+1}-weapon", range(4)))

    def create_team_weapons(details: pd.DataFrame, team: str) -> pd.DataFrame:
        cols = create_team_cols(team)
        return details[cols].set_axis(range(4), axis=1)

    a_weapons = create_team_weapons(details, team="A")
    b_weapons = create_team_weapons(details, team="B")

    def create_orch(row: pd.Series) -> str:
        pools = list(map(lambda x: pool.at[row[x], "Pool"], range(4)))
        pools = sorted(pools)
        return "".join(pools)

    # ブキ編成を記号で表す
    details["A-orch"] = a_weapons.apply(create_orch, axis=1)
    details["B-orch"] = b_weapons.apply(create_orch, axis=1)

    # ブキ一致数を算出する
    def create_weapon_match(row: pd.Series) -> int:
        a_cols = create_team_cols("A")
        b_cols = create_team_cols("B")
        a_weapons = row[a_cols].to_list()
        b_weapons = row[b_cols].to_list()

        for i in a_weapons:
            if i in b_weapons:
                b_weapons.remove(i)

        return 4 - len(b_weapons)

    details["weapon-match"] = details.apply(create_weapon_match, axis=1)

    # プール一致数を算出する
    def calc_pool_match(a_orch: str, b_orch: str) -> int:
        count = 0
        b_diff = list(b_orch)
        for i in list(a_orch):
            if i in b_diff:
                b_diff.remove(i)
                count += 1
        return count

    details["pool-match"] = details.apply(
        lambda x: calc_pool_match(x["A-orch"], x["B-orch"]), axis=1
    )

    # ブキ種一致数を算出する
    def calc_weapon_type_match(a_orch: str, b_orch: str) -> int:
        return calc_pool_match(a_orch.lower(), b_orch.lower())

    details["weapon-type-match"] = details.apply(
        lambda x: calc_weapon_type_match(x["A-orch"], x["B-orch"]), axis=1
    )

    # 射程一致数を算出する
    def calc_weapon_range_match(a_orch: str, b_orch: str) -> int:
        def remove_weapon_type(orch: str) -> str:
            return "".join(list(map(lambda x: "x" if x.islower() else "X", orch)))

        return calc_pool_match(remove_weapon_type(a_orch), remove_weapon_type(b_orch))

    details["weapon-range-match"] = details.apply(
        lambda x: calc_weapon_range_match(x["A-orch"], x["B-orch"]), axis=1
    )

    # 不一致プールを算出する
    def calc_orchestration_diff(a: str, b: str) -> tuple[list[str], [list[str]]]:
        a_diff = []
        b_diff = list(b)
        for i in list(a):
            if i in b_diff:
                b_diff.remove(i)
            else:
                a_diff.append(i)
        return (a_diff, b_diff)

    details["orch-diff"] = details.apply(
        lambda x: calc_orchestration_diff(x["A-orch"], x["B-orch"]), axis=1
    )

    return details


def details_to_players(
    details: pd.DataFrame,
    additional_columns: list[str] = [],
    use_uploader: bool = False,
    use_heroshooter: bool = False,
) -> pd.DataFrame:
    use_cols = [
        "# season",
        "period",
        "date",
        "game-ver",
        "lobby",
        "mode",
        "stage",
        "time",
        "win",
        "knockout",
        "x-power",
    ] + additional_columns
    player_names = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]
    items = [
        "weapon",
        "kill-assist",
        "kill",
        "assist",
        "death",
        "special",
        "inked",
        "abilities",
    ]
    player_cols = []
    for player_name in player_names:
        cols = list(map(lambda item: f"{player_name}-{item}", items))
        player_cols.extend(cols)

    # details を共通項とプレイヤー項に分離する
    common = details[use_cols].copy()
    player = details[player_cols].copy().fillna("nan")

    # 各プレイヤー情報を1つの列に結合する
    for player_name in player_names:
        player[player_name] = (
            player[f"{player_name}-weapon"]
            + "/"
            + player[f"{player_name}-kill-assist"].astype(str)
            + "/"
            + player[f"{player_name}-kill"].astype(str)
            + "/"
            + player[f"{player_name}-assist"].astype(str)
            + "/"
            + player[f"{player_name}-death"].astype(str)
            + "/"
            + player[f"{player_name}-special"].astype(str)
            + "/"
            + player[f"{player_name}-inked"].astype(str)
            + "/"
            + player[f"{player_name}-abilities"]
        )
    player = player.drop(columns=player_cols)

    # 共通項とプレイヤー項を結合し melt する
    df = pd.concat([common, player], axis=1)
    players = df.melt(id_vars=use_cols, value_name="player")

    # team 列を追加したり、win 列を boolean に置き換える
    player_name_to_team_map = {}
    for player_name in player_names:
        player_name_to_team_map[player_name] = (
            "alpha" if player_name[0] == "A" else "bravo"
        )
    team = players["variable"].map(player_name_to_team_map)
    players.insert(8, "team", team)

    uploader = players["variable"] == "A1"
    players.insert(12, "uploader", uploader)

    players["win"] = players["win"] == players["team"]
    players = players.drop(columns="variable")

    if not use_uploader:
        # 投稿者のデータを除外する
        players = players[~players["uploader"]]

    # 結合していたプレイヤー項を分離して元に戻す
    split = (
        players["player"]
        .str.split("/", expand=True)
        .replace("nan", np.nan)
        .rename(
            columns={
                0: "weapon",
                1: "kill-assist",
                2: "kill",
                3: "assist",
                4: "death",
                5: "special",
                6: "inked",
                7: "abilities",
            }
        )
        .astype(
            {
                "kill-assist": "int64",
                "kill": "int64",
                "assist": "int64",
                "death": "int64",
                "special": "int64",
                "inked": "int64",
            }
        )
    )

    # ヒーローシューターレプリカを合算する
    if not use_heroshooter:
        split["weapon"] = split["weapon"].replace("heroshooter_replica", "sshooter")

    # サブ・スペシャル・ブキ種を追加する
    main = pd.read_csv(c.SOURCE_MAIN_PATH, index_col="Key")
    weapon_sub = split["weapon"].apply(lambda x: main.at[x, "Sub"])
    weapon_special = split["weapon"].apply(lambda x: main.at[x, "Special"])
    weapon_type = split["weapon"].apply(lambda x: main.at[x, "Type"])
    split.insert(1, "weapon-sub", weapon_sub)
    split.insert(2, "weapon-special", weapon_special)
    split.insert(3, "weapon-type", weapon_type)

    players = pd.concat([players, split], axis=1)
    players = players.drop(columns="player")
    return players


def players_group_by_mode_and(groupby_key: str, players: pd.DataFrame) -> pd.DataFrame:
    """
    プレイヤーをモードとその他の key でグルーピングして
    勝率や使用率を計算する

    groupby_key: 集計したいカラム名
    players: プレイヤーの DataFrame
    """
    players_per_mode = players["mode"].value_counts()
    group = players.groupby(["mode", groupby_key])
    count = group["lobby"].count()
    subject = group.mean()
    win_rate = subject["win"] * 100
    subject.insert(0, "count", count)
    subject.insert(3, "win-rate", win_rate)
    subject = subject.reset_index()
    total_count = subject["mode"].apply(lambda x: players_per_mode[x])
    subject.insert(3, "total-count", total_count)
    usage_rate = subject["count"] / subject["total-count"] * 100
    subject.insert(4, "usage-rate", usage_rate)
    return subject


def aggregate_index_per_subject(
    players: pd.DataFrame, subject: str, target: str
) -> pd.DataFrame:
    """
    対象ごとに指標を集計する
    e.g. ブキごとの使用率を集計する

    players: プレイヤー情報の DataFrame
    subject: 対象 (e.g. "weapon")
    target: 集計する指標 (e.g. "usage-rate")
    """
    df = players_group_by_mode_and(subject, players)
    df_wide = df.pivot(subject, "mode", target).reindex(
        columns=["area", "yagura", "hoko", "asari"]
    )
    mean = df_wide.mean(axis="columns")
    median = df_wide.median(axis="columns")
    df_wide["mean"] = mean
    df_wide["median"] = median
    return df_wide.sort_values("median", ascending=False)
