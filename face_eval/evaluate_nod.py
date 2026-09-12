"""
頷き検出のイベントレベル評価。

入力:
    data/<id>.json             … 検出器ログ (recorder.html が出力)
    data/<id>.annotation.json  … アノテーション (annotate.html が出力)

評価:
    - 検出器の nod_events に対して TP/FP 判定（annotate.html のクリックに従う）
    - gold_nods_extra（人手追加された頷き）が ±tolerance 秒以内に検出されているか確認
      されていなければ FN
    - Precision, Recall, F1 を算出
"""
import argparse
import json
from pathlib import Path


def eval_one(detection_path: Path, annotation_path: Path, tolerance: float) -> dict:
    det = json.loads(detection_path.read_text(encoding="utf-8"))
    ann = json.loads(annotation_path.read_text(encoding="utf-8"))

    verdicts = ann.get("nod_verdicts", [])
    gold_extra = ann.get("gold_nods_extra", [])

    tp = sum(1 for v in verdicts if v["verdict"] == "tp")
    fp = sum(1 for v in verdicts if v["verdict"] == "fp")
    skipped = sum(1 for v in verdicts if v["verdict"] == "skip")

    # gold_extra のうち、検出器のどの TP/skip からも tolerance 外なら FN
    detected_t = [v["t"] for v in verdicts]
    fn = 0
    matched_extra = 0
    for g in gold_extra:
        nearby = any(abs(g - t) <= tolerance for t in detected_t)
        if nearby:
            matched_extra += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "session_id": det.get("sessionId"),
        "duration_sec": det.get("durationSec"),
        "threshold": det.get("nodThreshold"),
        "detected": len(verdicts),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "skipped_unjudged": skipped,
        "gold_extra_matched_existing": matched_extra,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="頷きイベントの許容窓 (秒)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    anns = sorted(data_dir.glob("*.annotation.json"))
    if not anns:
        print("[error] *.annotation.json が見つかりません")
        return

    rows = []
    for ann_path in anns:
        base = ann_path.name.replace(".annotation.json", "")
        det_path = data_dir / f"{base}.json"
        if not det_path.exists():
            print(f"[skip] 検出ログ無し: {det_path.name}")
            continue
        rows.append(eval_one(det_path, ann_path, args.tolerance))

    if not rows:
        return

    print(f"\n{'session':<24} {'TP':>4} {'FP':>4} {'FN':>4} {'P':>7} {'R':>7} {'F1':>7}")
    print("-" * 70)
    for r in rows:
        print(f"{(r['session_id'] or '?'):<24} "
              f"{r['tp']:>4} {r['fp']:>4} {r['fn']:>4} "
              f"{r['precision']:>7.3f} {r['recall']:>7.3f} {r['f1']:>7.3f}")
    print("-" * 70)

    total_tp = sum(r["tp"] for r in rows)
    total_fp = sum(r["fp"] for r in rows)
    total_fn = sum(r["fn"] for r in rows)
    P = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    R = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    print(f"{'micro avg':<24} {total_tp:>4} {total_fp:>4} {total_fn:>4} "
          f"{P:>7.3f} {R:>7.3f} {F1:>7.3f}")

    out = data_dir / "nod_eval_results.json"
    out.write_text(json.dumps({
        "tolerance_sec": args.tolerance,
        "per_session": rows,
        "micro_avg": {"tp": total_tp, "fp": total_fp, "fn": total_fn,
                      "precision": P, "recall": R, "f1": F1},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n詳細: {out}")


if __name__ == "__main__":
    main()
