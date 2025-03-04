FROM python:3.11

# 作業ディレクトリを設定
WORKDIR /bot

# .dockerignore を活用して不要なファイルを除外
COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクト全体をコンテナにコピー
COPY . /bot/

# ポート指定（FastAPI用）
EXPOSE 8080

# アプリケーション実行コマンド
CMD ["python", "apps/main.py"]
