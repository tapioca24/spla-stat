import os
import urllib.error
import urllib.request


def download_file(url, dst_path):
    """
    url が指すファイルを指定したパスにダウンロードする
    """
    try:
        with urllib.request.urlopen(url) as web_file, open(
            dst_path, "wb"
        ) as local_file:
            local_file.write(web_file.read())
    except urllib.error.URLError as e:
        print(e)


def download_file_to_dir(url, dst_dir):
    """
    url が指すファイルを指定したディレクトリにダウンロードする
    ファイル名は url のベースネームを使用する
    """
    os.makedirs(dst_dir, exist_ok=True)
    download_file(url, os.path.join(dst_dir, os.path.basename(url)))
