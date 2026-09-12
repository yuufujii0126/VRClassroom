"""
表情分類のフレームレベル評価。

入力:
    data/<id>.json             … 検出器ログ (frames に各時刻の expression 確率)
    data/<id>.annotation.json  … expression_intervals: [{start, end, label}, ...]

評価:
    アノテーション区間内の各フレームで、検出器の top-1 表情と gold を比較。
    Accuracy, macro-F1, Cohen's kappa, Confusion Matrix を算出。
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

EXPR_LABELS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"]


def top1(expr_dict: dict) -> str:
    return max(expr_dict.items(), key=lambda kv: kv[1])[0]


def collect_pairs(detection_path: Path, annotation_path: Path) -> list[tuple[str, str]]:
    det = json.loads(detection_path.read_text(encoding="utf-8"))
    ann = json.loads(annotation_path.read_text(encoding="utf-8"))

    frames = det.get("frames", [])
    intervals = ann.get("expression_intervals", [])
    if not intervals:
        return []

    pairs = []
    for fr in frames:
        if not fr.get("face"):
            continue
        t = fr["t"]
        for iv in intervals:
            if iv["start"] <= t <= iv["end"]:
                gold = iv["label"]
                pred = top1(fr["expressions"])
                pairs.append((gold, pred))
                break
    return pairs


def metrics(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    if n == 0:
        return {}
    correct = sum(1 for g, p in pairs if g == p)
    accuracy = correct / n

    labels = sorted(set(g for g, _ in pairs) | set(p for _, p in pairs))
    per_class = {}
    f1_list = []
    for c in labels:
        tp = sum(1 for g, p in pairs if g == c and p == c)
        fp = sum(1 for g, p in pairs if g != c and p == c)
        fn = sum(1 for g, p in pairs if g == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[c] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0

    pe = 0.0
    for c in labels:
        p_gold = sum(1 for g, _ in pairs if g == c) / n
        p_pred = sum(1 for _, p in pairs if p == c) / n
        pe += p_gold * p_pred
    kappa = (accuracy - pe) / (1 - pe) if pe < 1 else 0.0

    return {
        "n": n, "accuracy": accuracy, "macro_f1": macro_f1, "cohen_kappa": kappa,
        "per_class": per_class, "labels": labels,
    }


def confusion(pairs: list[tuple[str, str]], labels: list[str]) -> dict:
    cm = {g: {p: 0 for p in labels} for g in labels}
    for g, p in pairs:
        if g in cm and p in cm[g]:
            cm[g][p] += 1
    return cm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    anns = sorted(data_dir.glob("*.annotation.json"))
    if not anns:
        print("[error] *.annotation.json が見つかりません")
        return

    all_pairs = []
    per_session = []
    for ann_path in anns:
        base = ann_path.name.replace(".annotation.json", "")
        det_path = data_dir / f"{base}.json"
        if not det_path.exists():
            print(f"[skip] 検出ログ無し: {det_path.name}")
            continue
        pairs = collect_pairs(det_path, ann_path)
        if not pairs:
            continue
        m = metrics(pairs)
        per_session.append({"session_id": base, "n_frames": len(pairs),
                            "accuracy": m["accuracy"], "macro_f1": m["macro_f1"]})
        all_pairs.extend(pairs)

    if not all_pairs:
        print("有効な比較ペアがありません（アノテーション区間なし？）")
        return

    print("\n[per-session]")
    print(f"{'session':<24} {'frames':>8} {'acc':>7} {'macroF1':>8}")
    print("-" * 55)
    for r in per_session:
        print(f"{r['session_id']:<24} {r['n_frames']:>8} "
              f"{r['accuracy']:>7.3f} {r['macro_f1']:>8.3f}")

    m = metrics(all_pairs)
    cm = confusion(all_pairs, m["labels"])

    print(f"\n=== Aggregate (n={m['n']} frames) ===")
    print(f"Accuracy:    {m['accuracy']:.4f}")
    print(f"Macro F1:    {m['macro_f1']:.4f}")
    print(f"Cohen's κ:   {m['cohen_kappa']:.4f}")
    print(f"\n[per-class]")
    for c, v in m["per_class"].items():
        print(f"  {c:<10} P={v['precision']:.3f} R={v['recall']:.3f} "
              f"F1={v['f1']:.3f} n={v['support']}")

    print(f"\n[confusion matrix]  (rows=gold, cols=pred)")
    header = "       " + " ".join(f"{c[:6]:>7}" for c in m["labels"])
    print(header)
    for g in m["labels"]:
        print(f"{g[:6]:>6} " + " ".join(f"{cm[g][p]:>7}" for p in m["labels"]))

    out = data_dir / "expression_eval_results.json"
    out.write_text(json.dumps({
        "metrics": m, "confusion_matrix": cm, "per_session": per_session,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n詳細: {out}")


if __name__ == "__main__":
    main()
