from typing import Optional

import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import seaborn as sns
import pandas as pd

import src.constants as c
import src.japanize as j


def get_translations():
    source_list = [
        c.SOURCE_MAIN_PATH,
        c.SOURCE_SUB_PATH,
        c.SOURCE_SPECIAL_PATH,
        c.SOURCE_TYPE_PATH,
        c.SOURCE_STAGE_PATH,
        c.SOURCE_RULE_PATH,
        c.SOURCE_LOBBY_PATH,
    ]
    dfs = list(map(lambda x: pd.read_csv(x)[["Key", "Name"]], source_list))
    translation = pd.concat(dfs, ignore_index=True).set_index("Key")
    return translation["Name"].to_dict()


def show_aggregated_heatmap(
    aggregated: pd.DataFrame,
    title: Optional[str] = None,
    figsize: tuple[float, float] = (6, 28),
    cmap=sns.cubehelix_palette(gamma=0.75, as_cmap=True),
    use_annotation_image: bool = False,
    annotation_image_zoom: float = 0.65,
    use_x_translation: bool = True,
    use_y_translation: bool = True,
):
    sns.set_theme()
    j.japanize()

    f, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        aggregated,
        annot=True,
        fmt=".1f",
        cbar=False,
        cmap=cmap,
        linewidths=2,
        ax=ax,
    )
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set(xlabel="", ylabel="")
    if title:
        ax.set(title=title)

    # translation ticklabels
    translation = {**get_translations(), "mean": "平均値", "median": "中央値"}
    xkeys = list(map(lambda x: x.get_text(), ax.xaxis.get_ticklabels()))
    ykeys = list(map(lambda x: x.get_text(), ax.yaxis.get_ticklabels()))
    if use_x_translation:
        # xaxis
        xlabels = list(map(lambda x: translation[x], xkeys))
        ax.xaxis.set_ticklabels(xlabels)
    if use_y_translation:
        # yaxis
        ylabels = list(map(lambda x: translation[x], ykeys))
        ylabels_x_offset = -0.09 if use_annotation_image else 0
        ax.yaxis.set_ticklabels(ylabels, x=ylabels_x_offset)

    if use_annotation_image:
        # annotate image
        for i, key in enumerate(ykeys):
            image_path = f"{c.IMAGES_DIR}/{key}.png"
            img = OffsetImage(plt.imread(image_path), zoom=annotation_image_zoom)
            img.image.axes = ax
            ab = AnnotationBbox(img, (0, 0), xybox=(-0.35, i + 0.5), frameon=False)
            ax.add_artist(ab)
    return plt, ax


def show_xpower_dist(details: pd.DataFrame):
    sns.set_theme()

    xpower_key = "x-power"
    ax = sns.displot(data=details, x=xpower_key)
    ax.set(xlabel="X Power")
    return plt, ax


def show_xpower_vs_weapon_usage(
    players: pd.DataFrame, mode: str, figsize: tuple[float, float] = (8, 6)
):
    mode_players = players[players["mode"] == mode].copy()
    weapon_order = mode_players["weapon"].value_counts().to_frame().index.to_list()
    # トップブキを抽出する
    top_weapons = weapon_order[:9]

    # トップブキ以外を other で置き換える
    mode_players["weapon-dummy"] = mode_players.apply(
        lambda x: x["weapon"] if x["weapon"] in top_weapons else "other", axis=1
    )

    top_weapons.append("other")

    translations = {**get_translations(), "other": "その他"}
    translated_top_weapons = list(map(lambda x: translations[x], top_weapons))

    sns.set_theme()
    j.japanize()

    g = sns.displot(
        data=mode_players,
        x="x-power",
        hue="weapon-dummy",
        hue_order=top_weapons,
        kind="kde",
        multiple="fill",
        bw_adjust=2,
    )
    g.ax.set(
        title=f"Xパワーvsブキ使用率（{translations[mode]}）",
        xlabel="Xパワー",
        ylabel="ブキ使用率 [%]",
        xlim=(1400, 2600),
    )

    # y軸のラベル表示を変更する
    yticks = g.ax.get_yticks()
    yticklabels = list(map(lambda x: f"{round(x * 100)}", yticks))
    g.ax.set(yticks=yticks, yticklabels=yticklabels)

    legend = g.fig.legends[0]
    legend.set_title("")
    for i, t in enumerate(legend.texts):
        t.set_text(translated_top_weapons[i])
    g.fig.set_size_inches(figsize)

    return plt, g.ax
