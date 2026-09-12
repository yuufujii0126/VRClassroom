"""
Whisperで音声ファイルを文字起こしし、JSON結果を保存する。

Usage:
    python transcribe.py data/subject01_session1.webm
    python transcribe.py data/*.webm --model large-v3

Output: 入力と同じディレクトリに <name>.transcript.json を保存
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from faster_whisper import WhisperModel
except ImportError:
    sys.exit("faster-whisper が必要です。`pip install faster-whisper` を実行してください")


def transcribe_one(model: WhisperModel, audio_path: Path, language: str) -> dict:
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=5,
    )
    seg_list = []
    full_text = []
    for s in segments:
        seg_list.append({"start": s.start, "end": s.end, "text": s.text.strip()})
        full_text.append(s.text.strip())

    return {
        "audio": str(audio_path.name),
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "text": " ".join(full_text),
        "segments": seg_list,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="音声ファイル (.webm/.wav/.mp3/.m4a)")
    parser.add_argument("--model", default="large-v3",
                        help="Whisperモデル名 (tiny/base/small/medium/large-v3 など)")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--compute-type", default="auto",
                        help="計算精度 (auto/int8/int8_float16/float16/float32)")
    parser.add_argument("--language", default="ja")
    args = parser.parse_args()

    print(f"[load] model={args.model} device={args.device} compute_type={args.compute_type}")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    for input_path in args.inputs:
        audio_path = Path(input_path)
        if not audio_path.exists():
            print(f"[skip] not found: {audio_path}")
            continue

        print(f"[transcribe] {audio_path.name}")
        result = transcribe_one(model, audio_path, args.language)

        out_path = audio_path.with_suffix(".transcript.json")
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"[done] {out_path.name}  ({len(result['segments'])} segments)")
        print(f"        text: {result['text'][:80]}...")


if __name__ == "__main__":
    main()
