FROM continuumio/anaconda3:latest

# pip をアップグレードし必要なパッケージをインストール
# RUN pip install --upgrade pip && \
#   pip install autopep8 && \
#   pip install Keras && \
#   pip install tensorflow

# コンテナ側のルート直下に workdir/ という名前の作業ディレクトリを作り移動する
WORKDIR /workdir

# コンテナ側のリッスンポート番号
# 明示しているだけでなくても動く
EXPOSE 8888

# ENTRYPOINT 命令はコンテナ起動時に実行するコマンドを指定 （基本 docker run の時に上書きしないもの）
# "jupyter-lab" => jupyter-lab 立ち上げコマンド
# "--ip=0.0.0.0" => ip 制限なし
# "--port=8888" => EXPOSE 命令で書いたポート番号と合わせる
# ”--no-browser” => ブラウザを立ち上げない
# "--allow-root" => root ユーザーの許可。 セキュリティ的には良くないので自分で使うときだけ。
# "--NotebookApp.token=''" => トークンなしで起動許可。 これもセキュリティ的には良くない。
ENTRYPOINT ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]

# CMD 命令はコンテナ起動時に実行するコマンドを指定 （docker run の時に上書きする可能性のあるもの）
# "--notebook-dir=/workdir" => Jupyter Lab のルートとなるディレクトリを指定
CMD ["--notebook-dir=/workdir"]
