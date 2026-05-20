"""
Zoom録音ファイル → 文字起こしツール
m4aファイルを分割してWhisper APIで文字起こしします
"""

import os
import sys
import math
import openai
from pathlib import Path

# =============================
# 設定
# =============================
OPENAI_API_KEY = "ここにAPIキーを入れてください"  # ← 変更してね
CHUNK_MINUTES = 10       # 何分ごとに分割するか（10分推奨）
LANGUAGE = "ja"          # 言語（日本語）
OUTPUT_DIR = "output"    # 出力フォルダ

# =============================
# メイン処理
# =============================

def split_audio(input_file: str, chunk_minutes: int = 10) -> list[str]:
    """音声ファイルを分割する（ffmpegを使用）"""
    import subprocess
    
    input_path = Path(input_file)
    chunk_dir = Path(OUTPUT_DIR) / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # 音声の長さを取得
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    chunk_seconds = chunk_minutes * 60
    num_chunks = math.ceil(duration / chunk_seconds)
    
    print(f"音声の長さ: {duration/60:.1f}分 → {num_chunks}個に分割します")
    
    chunk_files = []
    for i in range(num_chunks):
        start = i * chunk_seconds
        chunk_file = chunk_dir / f"chunk_{i:03d}.m4a"
        
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-ss", str(start),
            "-t", str(chunk_seconds),
            "-c", "copy",
            str(chunk_file)
        ], capture_output=True)
        
        chunk_files.append(str(chunk_file))
        print(f"  分割完了: {chunk_file.name} ({start/60:.1f}分〜)")
    
    return chunk_files


def transcribe_chunk(client: openai.OpenAI, chunk_file: str, chunk_index: int) -> str:
    """1つのチャンクを文字起こし"""
    print(f"  文字起こし中: chunk_{chunk_index:03d}...")
    
    with open(chunk_file, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=LANGUAGE,
            response_format="text"
        )
    
    return response


def transcribe_all(input_file: str) -> str:
    """全チャンクを文字起こしして結合"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # 分割
    print("\n【STEP 1】音声ファイルを分割中...")
    chunk_files = split_audio(input_file, CHUNK_MINUTES)
    
    # 文字起こし
    print("\n【STEP 2】文字起こし中...")
    transcripts = []
    for i, chunk_file in enumerate(chunk_files):
        text = transcribe_chunk(client, chunk_file, i)
        transcripts.append(text)
    
    # 結合
    full_transcript = "\n".join(transcripts)
    
    # 保存
    output_path = Path(OUTPUT_DIR) / "transcript.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_transcript, encoding="utf-8")
    
    print(f"\n【完了】文字起こしを保存しました: {output_path}")
    print(f"文字数: {len(full_transcript)}文字")
    
    return full_transcript


def check_dependencies():
    """必要なものが揃ってるか確認"""
    import subprocess
    
    # ffmpegチェック
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        print("❌ ffmpegがインストールされていません")
        print("   インストール: https://ffmpeg.org/download.html")
        return False
    
    # openaiチェック
    try:
        import openai
    except ImportError:
        print("❌ openaiライブラリがありません")
        print("   インストール: pip install openai")
        return False
    
    print("✅ 依存関係OK")
    return True


# =============================
# 実行
# =============================
if __name__ == "__main__":
    print("=" * 50)
    print("  Zoom録音 文字起こしツール")
    print("=" * 50)
    
    # 依存関係チェック
    if not check_dependencies():
        sys.exit(1)
    
    # ファイル指定
    if len(sys.argv) < 2:
        print("\n使い方: python zoom_transcriber.py 録音ファイル.m4a")
        print("例:     python zoom_transcriber.py meeting_2026-05-20.m4a")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        sys.exit(1)
    
    # APIキーチェック
    if OPENAI_API_KEY == "ここにAPIキーを入れてください":
        print("❌ APIキーを設定してください（スクリプト上部のOPENAI_API_KEY）")
        sys.exit(1)
    
    # 実行
    transcript = transcribe_all(input_file)
    
    print("\n" + "=" * 50)
    print("文字起こし完了！")
    print("output/transcript.txt をGeminiに貼り付けて議事録を作成してください")
    print("=" * 50)
