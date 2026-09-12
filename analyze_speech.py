#!/usr/bin/env python3
"""
analyze_speech.py
マイク録音 → librosa音響分析 + Whisper文字起こし → GPT-4o-mini で発話分類

API key は .env から OPENAI_API_KEY を読み込みます (探索順: スクリプト同階層 → 親階層 → カレント)。

Usage:
  python3 analyze_speech.py                # Enterで録音開始/停止
  python3 analyze_speech.py --duration 5   # 5秒固定録音
  python3 analyze_speech.py --input file.wav  # 既存WAV解析
"""

import argparse
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
import sounddevice as sd
import librosa
from dotenv import load_dotenv
from openai import OpenAI


def load_env_file() -> Path | None:
    """スクリプト同階層 → 親階層 (WebXR ルートまで) → CWD の順で .env を探して読む。"""
    here = Path(__file__).resolve().parent
    candidates = [here, here.parent, here.parent.parent, Path.cwd()]
    seen = set()
    for d in candidates:
        if d in seen:
            continue
        seen.add(d)
        env_path = d / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            return env_path
    return None

SAMPLE_RATE = 16000
CHANNELS = 1
GPT_MODEL = "gpt-4o-mini"
WHISPER_MODEL = "whisper-1"

SIGNAL_DEFINITIONS = """
- lang-agree (同意表現): 「そうですね」「その通り」「賛成です」「確かに」など、相手の意見への賛意。
- lang-disagree (不同意・反論表現): 「いや」「違います」「でも」「反対」「それはちょっと」など、否定・反論。
- lang-understand (理解・確認応答): 「分かりました」「なるほど」「理解しました」「OKです」など、理解の表明。
- lang-repair (聞き返し・修復要求): 「もう一度」「え?」「どういう意味?」「すみません?」など、再説明要求。
- lang-hedge (不確実性・hedge): 「たぶん」「おそらく」「かもしれない」「~と思う」など、断定回避・不確実さ。
- lang-stance (スタンス・意見変化): 「やっぱり~に変える」「考え直すと」「前は思ったけど今は」など、立場の変化。
- lang-commit (行動意図・コミット): 「やります」「明日までに」「私が担当します」など、具体的行動の約束。
- dial-question (質問・根拠要求): 「なぜ?」「どうして?」「根拠は?」「具体的には?」「~ですか?」など、問い直し・情報要求。
"""


def record_with_enter() -> np.ndarray:
    """Enterで録音開始、もう一度Enterで停止。"""
    print("Enterキーで録音開始...", end="", flush=True)
    input()
    print("録音中... (Enterで停止)", flush=True)

    audio_q: "queue.Queue[np.ndarray]" = queue.Queue()
    stop_flag = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  [warn] {status}", file=sys.stderr)
        audio_q.put(indata.copy())

    def wait_for_enter():
        input()
        stop_flag.set()

    threading.Thread(target=wait_for_enter, daemon=True).start()

    chunks = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback, dtype="float32"):
        while not stop_flag.is_set():
            try:
                chunks.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                continue
        # drain remaining
        while not audio_q.empty():
            chunks.append(audio_q.get_nowait())

    if not chunks:
        return np.zeros((0,), dtype=np.float32)
    audio = np.concatenate(chunks, axis=0).flatten()
    print(f"録音完了: {len(audio) / SAMPLE_RATE:.2f} 秒")
    return audio


def record_fixed(duration: float) -> np.ndarray:
    """固定秒数録音。"""
    print(f"録音開始 ({duration}秒)...", flush=True)
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
    sd.wait()
    print("録音完了")
    return audio.flatten()


def analyze_audio(y: np.ndarray, sr: int) -> dict:
    """librosaで音響特徴量を抽出。"""
    if len(y) == 0:
        return {"error": "empty audio"}

    duration_sec = len(y) / sr

    # F0 (pitch) — pyinで信頼区間付き推定
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=float(librosa.note_to_hz("C2")), fmax=float(librosa.note_to_hz("C7")), sr=sr
        )
        f0_voiced = f0[~np.isnan(f0)]
        if len(f0_voiced) > 0:
            pitch = {
                "mean_hz": float(np.mean(f0_voiced)),
                "std_hz": float(np.std(f0_voiced)),
                "min_hz": float(np.min(f0_voiced)),
                "max_hz": float(np.max(f0_voiced)),
                "voiced_ratio": float(np.mean(voiced_flag)),
            }
        else:
            pitch = {"mean_hz": None, "note": "no voiced frames detected"}
    except Exception as e:
        pitch = {"error": str(e)}

    # RMS energy (loudness)
    rms = librosa.feature.rms(y=y)[0]
    energy = {
        "mean_rms": float(np.mean(rms)),
        "std_rms": float(np.std(rms)),
        "max_rms": float(np.max(rms)),
        "dynamic_range_db": float(20 * np.log10((np.max(rms) + 1e-9) / (np.mean(rms) + 1e-9))),
    }

    # Speech rate proxies
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    speech_rate = {
        "zcr_mean": float(np.mean(zcr)),
        "onset_count": int(len(onsets)),
        "onset_rate_per_sec": float(len(onsets) / duration_sec) if duration_sec > 0 else 0.0,
    }

    return {
        "duration_sec": float(duration_sec),
        "sample_rate": int(sr),
        "pitch": pitch,
        "energy": energy,
        "speech_rate": speech_rate,
    }


def transcribe(client: OpenAI, wav_path: Path) -> dict:
    """Whisper APIで文字起こし。"""
    with open(wav_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=f,
            language="ja",
            response_format="verbose_json",
        )
    return {
        "text": resp.text,
        "language": getattr(resp, "language", None),
        "duration": getattr(resp, "duration", None),
    }


def classify_signals(client: OpenAI, transcript_text: str, audio_features: dict) -> dict:
    """GPTで7シグナル判定 + 音響特徴量を踏まえた解釈。"""
    user_payload = {
        "transcript": transcript_text,
        "audio_features": audio_features,
    }

    system_prompt = f"""あなたは対話分析の専門家です。発話のテキストと音響特徴量を受け取り、以下の7つのシグナルそれぞれについて該当するかを判定してください。

{SIGNAL_DEFINITIONS}

出力は厳密にJSONのみ。以下の構造を守ってください:
{{
  "signals": {{
    "lang-agree":      {{"present": true/false, "confidence": 0-1, "evidence": "該当箇所の引用または説明"}},
    "lang-disagree":   {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "lang-understand": {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "lang-repair":     {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "lang-hedge":      {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "lang-stance":     {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "lang-commit":     {{"present": true/false, "confidence": 0-1, "evidence": "..."}},
    "dial-question":   {{"present": true/false, "confidence": 0-1, "evidence": "..."}}
  }},
  "prosody_interpretation": "ピッチ・エネルギー・発話速度から読み取れる話者の状態(短く)",
  "overall_summary": "発話の全体的な意図・態度の要約(1-2文)"
}}"""

    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "JSON parse failed", "raw": raw}


def main():
    parser = argparse.ArgumentParser(description="Mic → librosa + Whisper + GPT-4o-mini")
    parser.add_argument("--duration", type=float, default=None, help="固定秒数録音 (省略時はEnterで開始/停止)")
    parser.add_argument("--input", type=str, default=None, help="既存WAVファイルを解析 (録音スキップ)")
    parser.add_argument("--output", type=str, default=None, help="結果JSON出力先 (省略時は自動生成)")
    parser.add_argument("--keep-wav", action="store_true", help="録音WAVを残す")
    args = parser.parse_args()

    env_path = load_env_file()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY が見つかりません。", file=sys.stderr)
        print("  .env ファイルに OPENAI_API_KEY=sk-... を記述するか、環境変数として export してください。", file=sys.stderr)
        sys.exit(1)
    if env_path:
        print(f"  .env 読み込み: {env_path}")
    client = OpenAI(api_key=api_key)

    # 1. 音声取得
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "speech_analysis_out"
    out_dir.mkdir(exist_ok=True)

    if args.input:
        wav_path = Path(args.input)
        if not wav_path.exists():
            print(f"ERROR: {wav_path} が見つかりません", file=sys.stderr)
            sys.exit(1)
        y, sr = librosa.load(str(wav_path), sr=SAMPLE_RATE, mono=True)
    else:
        if args.duration:
            y = record_fixed(args.duration)
        else:
            y = record_with_enter()
        if len(y) < SAMPLE_RATE * 0.3:
            print("ERROR: 録音が短すぎます (0.3秒未満)", file=sys.stderr)
            sys.exit(1)
        sr = SAMPLE_RATE
        wav_path = out_dir / f"rec_{timestamp}.wav"
        sf.write(str(wav_path), y, sr, subtype="PCM_16")
        print(f"  WAV保存: {wav_path}")

    # 2. librosa解析
    print("librosa解析中...", flush=True)
    t0 = time.time()
    audio_features = analyze_audio(y, sr)
    print(f"  完了 ({time.time() - t0:.2f}秒)")

    # 3. Whisper文字起こし
    print("Whisper文字起こし中...", flush=True)
    t0 = time.time()
    asr = transcribe(client, wav_path)
    print(f"  完了 ({time.time() - t0:.2f}秒)")
    print(f"  発話: 「{asr['text']}」")

    # 4. GPT分類
    print(f"{GPT_MODEL}で分類中...", flush=True)
    t0 = time.time()
    classification = classify_signals(client, asr["text"], audio_features)
    print(f"  完了 ({time.time() - t0:.2f}秒)")

    # 5. 結果まとめ
    result = {
        "timestamp": timestamp,
        "wav_path": str(wav_path),
        "transcript": asr,
        "audio_features": audio_features,
        "classification": classification,
    }

    out_path = Path(args.output) if args.output else out_dir / f"result_{timestamp}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n結果保存: {out_path}\n")

    # コンソール表示
    print("=" * 60)
    print(f"発話: {asr['text']}")
    print("-" * 60)
    pitch = audio_features.get("pitch", {})
    if pitch.get("mean_hz"):
        print(f"ピッチ: 平均 {pitch['mean_hz']:.1f} Hz / SD {pitch['std_hz']:.1f} Hz")
    rate = audio_features.get("speech_rate", {})
    print(f"発話速度: オンセット {rate.get('onset_rate_per_sec', 0):.2f}/秒")
    print("-" * 60)
    sigs = classification.get("signals", {})
    for sid, info in sigs.items():
        mark = "✓" if info.get("present") else " "
        conf = info.get("confidence", 0)
        ev = info.get("evidence", "")
        print(f"  [{mark}] {sid:18s} (conf={conf:.2f}) {ev[:50]}")
    print("-" * 60)
    print(f"韻律解釈: {classification.get('prosody_interpretation', '')}")
    print(f"要約: {classification.get('overall_summary', '')}")
    print("=" * 60)

    if not args.keep_wav and not args.input:
        # 録音WAVを残すかどうか — デフォルトは残す方が安全なので残す
        pass


if __name__ == "__main__":
    main()
