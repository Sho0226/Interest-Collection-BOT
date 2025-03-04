FROM python:3.11

# 作業ディレクトリを設定
WORKDIR /bot

# 日本語ロケールとタイムゾーン設定
RUN apt-get update && apt-get install -y locales && \
    locale-gen ja_JP.UTF-8 && \
    ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "Asia/Tokyo" > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

# 必要なライブラリをインストール
COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクト全体をコンテナにコピー
COPY . /bot/

# ポート指定（FastAPI用）
EXPOSE 8080

# アプリケーション実行コマンド
CMD ["python", "apps/main.py"]
