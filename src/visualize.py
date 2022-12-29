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
    ]
    dfs = list(map(lambda x: pd.read_csv(x)[["Key", "Name"]], source_list))
    translation = pd.concat(dfs, ignore_index=True).set_index("Key")
    return translation["Name"].to_dict()


def show_aggregated_heatmap(
    aggregated: pd.DataFrame,
    title: Optional[str] = None,
    figsize: tuple[float, float] = (6, 28),
    use_annotation_image: bool = False,
    annotation_image_zoom: float = 0.65,
):
    sns.set_theme()
    j.japanize()

    f, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        aggregated,
        annot=True,
        fmt=".1f",
        cbar=False,
        cmap=sns.cubehelix_palette(gamma=0.75, as_cmap=True),
        linewidths=2,
        ax=ax,
    )
    ax.xaxis.tick_top()
    ax.set(xlabel="", ylabel="")
    if title:
        ax.set(title=title)

    # translation ticklabels
    # xaxis
    translation = {**get_translations(), "mean": "平均値", "median": "中央値"}
    xkeys = list(map(lambda x: x.get_text(), ax.xaxis.get_ticklabels()))
    xlabels = list(map(lambda x: translation[x], xkeys))
    ax.xaxis.set_ticklabels(xlabels)
    # yaxis
    ykeys = list(map(lambda x: x.get_text(), ax.yaxis.get_ticklabels()))
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
    plt.show()


def show_xpower_dist(details: pd.DataFrame):
    sns.set_theme()

    xpower_key = "X Power Before" if "X Power Before" in details else "X Power"
    ax = sns.displot(data=details, x=xpower_key)
    ax.set(xlabel="X Power")
    plt.show()
    return details[xpower_key].describe()
