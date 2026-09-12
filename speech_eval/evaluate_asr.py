"""
ASR (Whisper) の精度評価。
正解 reference テキストと Whisper の出力を比較し、CER/WER を算出する。

正解ファイル形式: data/<name>.reference.txt （人手で書き起こした正解）
Whisper結果:    data/<name>.transcript.json （transcribe.py の出力）

Usage:
    python evaluate_asr.py data/
"""
import argparse
import json
import re
from pathlib import Path

try:
    from jiwer import cer, wer
except ImportError:
    import sys
    sys.exit("jiwer が必要です。`pip install jiwer` を実行してください")


def normalize_ja(text: str) -> str:
    """日本語向けの簡易正規化: 句読点・空白除去、全角→半角の必要に応じて。"""
    text = re.sub(r"[、。．,．\.\s「」『』（）()！？!?]", "", text)
    return text.strip()


def evaluate_pair(ref_path: Path, hyp_path: Path) -> dict:
    reference = ref_path.read_text(encoding="utf-8").strip()
    hypothesis_data = json.loads(hyp_path.read_text(encoding="utf-8"))
    hypothesis = hypothesis_data.get("text", "").strip()

    ref_norm = normalize_ja(reference)
    hyp_norm = normalize_ja(hypothesis)

    return {
        "name": ref_path.stem.replace(".reference", ""),
        "reference_len": len(ref_norm),
        "hypothesis_len": len(hyp_norm),
        "cer": cer(ref_norm, hyp_norm),
        "wer": wer(reference, hypothesis),
        "reference": reference,
        "hypothesis": hypothesis,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", help="正解と推定が入ったディレクトリ")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    references = sorted(data_dir.glob("*.reference.txt"))
    if not references:
        print(f"[error] {data_dir} に *.reference.txt が見つかりません")
        return

    results = []
    for ref_path in references:
        base = ref_path.name.replace(".reference.txt", "")
        hyp_path = data_dir / f"{base}.transcript.json"
        if not hyp_path.exists():
            print(f"[skip] {hyp_path.name} が無い")
            continue
        results.append(evaluate_pair(ref_path, hyp_path))

    if not results:
        return

    print(f"\n{'name':<30} {'CER':>8} {'WER':>8} {'ref_len':>8}")
    print("-" * 60)
    for r in results:
        print(f"{r['name']:<30} {r['cer']:>8.4f} {r['wer']:>8.4f} {r['reference_len']:>8}")
    print("-" * 60)
    mean_cer = sum(r["cer"] for r in results) / len(results)
    mean_wer = sum(r["wer"] for r in results) / len(results)
    print(f"{'mean':<30} {mean_cer:>8.4f} {mean_wer:>8.4f}")

    out = data_dir / "asr_eval_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n詳細結果: {out}")


if __name__ == "__main__":
    main()
