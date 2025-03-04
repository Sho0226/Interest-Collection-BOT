FROM python:3.11

# 作業ディレクトリ設定
WORKDIR /bot

# 必要なファイルをコピー
COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /bot

# ポート指定（FastAPI用）
EXPOSE 8080

# アプリケーション実行コマンド
CMD ["python", "main.py"]
