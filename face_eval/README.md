# 頭部（頷き）・表情 精度評価パイプライン

face-api.js による頷き検出と表情分類の精度評価。

## 構成

```
face_eval/
  recorder.html         … 録画 + face-api.js でリアルタイム検出ログ
  annotate.html         … 動画にTP/FP/FN + 表情区間ラベルを付ける
  server.py             … 録画/アノテーションのアップロード受け
  evaluate_nod.py       … 頷き検出 (P/R/F1)
  evaluate_expression.py… 表情分類 (Acc/F1/κ/Confusion)
  models/               … face-api.js モデル
  data/                 … 録画・検出ログ・アノテーション
```

## 起動

```bash
cd /Users/fujiiyuu/my_research/face_eval
python3 server.py        # http://localhost:8001
```

## ワークフロー

### 1. 録画 + 検出ログ収集
ブラウザで http://localhost:8001/recorder.html

- セッションID入力（例: `subject01_face1`）
- 「録画開始」→ 1〜2分間、頷きや表情を変えながら話す
- 「録画停止」で `data/<id>.webm` と `data/<id>.json`（検出ログ）が自動保存

検出ログJSONには:
- `frames`: 100ms 毎の `{t, nose_y, expressions: {neutral, happy, ...}}`
- `nod_events`: しきい値超過した頷き候補 `{t, diff}`

### 2. アノテーション
ブラウザで http://localhost:8001/annotate.html

- 上部入力欄に `/data/<id>.json` を入力 → 「読み込み」
- 動画と検出ログが読み込まれる

**頷き判定:**
- 各検出イベント横の「TP / FP / ?」を押す
- 「▶」で該当時刻にジャンプして動画確認
- 見逃しを発見したら動画を停止 → 「現在時刻で追加」（FN候補）

**表情アノテーション:**
- 動画を再生して表情が安定している区間を見つける
- 「start=現在」「end=現在」で時刻入力 → ラベル選択 → 「追加」
- 全体の30〜50%程度をカバーできれば十分

「アノテーションを保存」で `data/<id>.annotation.json` に保存。

### 3. 評価実行

```bash
# 頷き (イベントレベル)
python evaluate_nod.py data/ --tolerance 0.5

# 表情 (フレームレベル)
python evaluate_expression.py data/
```

## 出力例

```
[頷き]
session                    TP   FP   FN       P       R      F1
----------------------------------------------------------------------
subject01_face1             8    2    1   0.800   0.889   0.842
----------------------------------------------------------------------
micro avg                   8    2    1   0.800   0.889   0.842

[表情]
=== Aggregate (n=520 frames) ===
Accuracy:    0.6731
Macro F1:    0.5842
Cohen's κ:   0.5210
```

## 評価のコツ

- **頷きしきい値のチューニング**: recorder.html の入力欄を 5〜15 で変えて録画 → 評価
- **PR曲線を書きたい場合**: しきい値別の複数録画 → P/R をプロット
- **複数被験者**: 同一スクリプトで複数 session_id を録画して micro avg を見る
- **照明・距離の影響**: 検出器の弱点として注目しておく

## 既存検出器の限界（評価で見えてくる想定）

- **頷き**: 単純な nose Y 差分のため、笑い・あくびで FP が出やすい
- **表情**: face-api.js は欧米顔データで学習されており、日本人で精度が落ちる傾向。
  特に sad/disgusted/angry の区別が弱い。論文では「ベースライン」と位置付け、
  独自モデルや MediaPipe + 学習済み感情分類器との比較を提案する余地あり。
