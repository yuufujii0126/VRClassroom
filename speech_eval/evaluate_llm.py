"""
LLM分類の精度評価。
transcript.json と正解ラベルCSVを読み込み、LLMでラベル推定 → 評価指標を算出。

正解ファイル形式: data/labels.csv
    session_id,gold_label,note
    subject01_s1,納得,...

Usage:
    export OPENAI_API_KEY=...        # OpenAIを使う場合
    export ANTHROPIC_API_KEY=...     # Claudeを使う場合
    python evaluate_llm.py data/ --provider openai --model gpt-4o-mini
    python evaluate_llm.py data/ --provider anthropic --model claude-haiku-4-5-20251001
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

LABELS = ["納得", "中立", "不納得"]


def load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_labels(csv_path: Path) -> dict[str, str]:
    out = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["session_id"].strip()] = row["gold_label"].strip()
    return out


def load_transcript(transcript_path: Path) -> str:
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    return data.get("text", "").strip()


def call_openai(model: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def call_anthropic(model: str, prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def extract_json(text: str) -> Optional[dict]:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def classify(provider: str, model: str, prompt_template: str, utterance: str) -> dict:
    prompt = prompt_template.replace("{utterance}", utterance)
    if provider == "openai":
        raw = call_openai(model, prompt)
    elif provider == "anthropic":
        raw = call_anthropic(model, prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    parsed = extract_json(raw)
    if not parsed or parsed.get("label") not in LABELS:
        return {"label": None, "confidence": 0.0, "reason": "parse_error", "raw": raw}
    return parsed


def confusion_matrix(pairs: list[tuple[str, str]]) -> dict:
    """pairs: [(gold, pred), ...] -> {gold: {pred: count}}"""
    cm = {g: {p: 0 for p in LABELS} for g in LABELS}
    for g, p in pairs:
        if g in cm and p in cm[g]:
            cm[g][p] += 1
    return cm


def metrics(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    if n == 0:
        return {}
    correct = sum(1 for g, p in pairs if g == p)
    accuracy = correct / n

    per_class = {}
    f1_list = []
    for c in LABELS:
        tp = sum(1 for g, p in pairs if g == c and p == c)
        fp = sum(1 for g, p in pairs if g != c and p == c)
        fn = sum(1 for g, p in pairs if g == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[c] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list)

    # Cohen's kappa
    po = accuracy
    pe = 0.0
    for c in LABELS:
        p_gold = sum(1 for g, _ in pairs if g == c) / n
        p_pred = sum(1 for _, p in pairs if p == c) / n
        pe += p_gold * p_pred
    kappa = (po - pe) / (1 - pe) if pe < 1 else 0.0

    return {
        "n": n,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "cohen_kappa": kappa,
        "per_class": per_class,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", default=None,
                        help="provider のモデル名 (例: gpt-4o-mini, claude-haiku-4-5-20251001)")
    parser.add_argument("--prompt", default="prompts/classify_satisfaction.txt")
    parser.add_argument("--labels", default=None,
                        help="正解CSV (default: <data_dir>/labels.csv)")
    args = parser.parse_args()

    if args.model is None:
        args.model = "gpt-4o-mini" if args.provider == "openai" else "claude-haiku-4-5-20251001"

    data_dir = Path(args.data_dir)
    labels_path = Path(args.labels) if args.labels else data_dir / "labels.csv"
    prompt_path = Path(args.prompt)

    if not labels_path.exists():
        sys.exit(f"[error] 正解CSVが無い: {labels_path}")
    if not prompt_path.exists():
        sys.exit(f"[error] プロンプトが無い: {prompt_path}")

    prompt_template = load_prompt_template(prompt_path)
    gold = load_labels(labels_path)

    print(f"[config] provider={args.provider} model={args.model}")
    print(f"[load] {len(gold)} labeled sessions")

    results = []
    pairs = []
    for session_id, gold_label in gold.items():
        transcript_path = data_dir / f"{session_id}.transcript.json"
        if not transcript_path.exists():
            print(f"[skip] {transcript_path.name} が無い")
            continue
        utterance = load_transcript(transcript_path)
        if not utterance:
            print(f"[skip] {session_id}: 空のtranscript")
            continue

        try:
            pred = classify(args.provider, args.model, prompt_template, utterance)
        except Exception as e:
            print(f"[error] {session_id}: {e}")
            continue

        results.append({
            "session_id": session_id,
            "utterance": utterance,
            "gold": gold_label,
            "pred": pred.get("label"),
            "confidence": pred.get("confidence"),
            "reason": pred.get("reason"),
        })
        pairs.append((gold_label, pred.get("label")))
        mark = "✓" if gold_label == pred.get("label") else "✗"
        print(f"  {mark} {session_id}: gold={gold_label} pred={pred.get('label')} "
              f"conf={pred.get('confidence', 0):.2f}")

    if not pairs:
        sys.exit("[error] 有効なペアが0件")

    m = metrics(pairs)
    cm = confusion_matrix(pairs)

    print(f"\n=== 結果 (n={m['n']}) ===")
    print(f"Accuracy:    {m['accuracy']:.4f}")
    print(f"Macro F1:    {m['macro_f1']:.4f}")
    print(f"Cohen's κ:   {m['cohen_kappa']:.4f}")
    print(f"\n[per-class]")
    for c, v in m["per_class"].items():
        print(f"  {c}: P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f} n={v['support']}")
    print(f"\n[confusion matrix]  (rows=gold, cols=pred)")
    print(f"  {'':>6} " + " ".join(f"{c:>6}" for c in LABELS))
    for g in LABELS:
        print(f"  {g:>6} " + " ".join(f"{cm[g][p]:>6}" for p in LABELS))

    out = data_dir / "llm_eval_results.json"
    out.write_text(json.dumps({
        "config": {"provider": args.provider, "model": args.model},
        "metrics": m,
        "confusion_matrix": cm,
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n詳細結果: {out}")


if __name__ == "__main__":
    main()
