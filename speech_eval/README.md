# 発話音声 精度評価パイプライン

発話音声の2段階パイプライン（ASR + LLM分類）の精度評価ツール一式。

## 構成

```
speech_eval/
  recorder.html       … ブラウザ録音ページ
  transcribe.py       … Whisperで文字起こし
  evaluate_asr.py     … ASR精度 (CER/WER) を評価
  evaluate_llm.py     … LLM分類精度 (Accuracy/F1/κ) を評価
  prompts/
    classify_satisfaction.txt   … 納得度分類プロンプト
  data/               … 録音・文字起こし・正解を置く
```

## セットアップ

```bash
cd /Users/fujiiyuu/my_research/speech_eval
python3 -m venv .venv && source .venv/bin/activate
pip install faster-whisper jiwer openai anthropic
```

Apple Silicon の場合は `pip install faster-whisper` だけで CPU 推論が可能です（CoreML 利用なら `whisper.cpp` か `mlx-whisper` も選択肢）。

## 使い方

### 1. 録音

`recorder.html` をブラウザで開く（マイクアクセスのため `https://` または `localhost` が必要）:

```bash
cd /Users/fujiiyuu/my_research/speech_eval
python3 -m http.server 8000
# → http://localhost:8000/recorder.html
```

- セッションIDを入力（例: `subject01_s1`）
- 「録音開始」→ 発話 → 「録音停止」で `.webm` と `.json`（メタデータ＋マーカー）がDLされる
- ダウンロードしたファイルを `data/` に置く

### 2. 文字起こし

```bash
python transcribe.py data/subject01_s1.webm --model large-v3
# → data/subject01_s1.transcript.json が生成される
```

モデル選択の目安:
- `tiny` / `base`: 速いが精度低
- `small` / `medium`: バランス型
- `large-v3`: 最高精度（日本語実用ベース）

### 3. 正解書き起こしを用意

`data/subject01_s1.reference.txt` を人手で作る（録音内容を正確に文字化）。

### 4. 評価

```bash
python evaluate_asr.py data/
```

出力例:
```
name                                CER      WER    ref_len
------------------------------------------------------------
subject01_s1                     0.0231   0.0876        128
subject02_s1                     0.0312   0.1042         95
------------------------------------------------------------
mean                              0.0272   0.0959
```

- **CER (Character Error Rate)**: 文字単位の誤り率。日本語ではこちらが主指標
- **WER (Word Error Rate)**: 単語単位の誤り率。参考値として
- 目安: CER < 0.05 なら後段LLMが影響を受けにくい

## LLM分類の評価

### 1. 正解ラベルCSVを用意

`data/labels.csv` を以下の形式で作成:

```csv
session_id,gold_label,note
subject01_s1,納得,理解の言い直しあり
subject01_s2,不納得,質問発話
subject02_s1,中立,相槌のみ
```

ラベルは `納得 / 中立 / 不納得` の3クラス（`prompts/classify_satisfaction.txt` で変更可）。

理想は **2名以上で独立にラベル付け** → Cohen's κ で一致率確認（0.6以上）→ 不一致は合議。

### 2. APIキー設定

```bash
export OPENAI_API_KEY=sk-...
# または
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. 実行

```bash
# OpenAI (GPT-4o-mini)
python evaluate_llm.py data/ --provider openai --model gpt-4o-mini

# Anthropic (Claude Haiku)
python evaluate_llm.py data/ --provider anthropic --model claude-haiku-4-5-20251001

# 高精度モデルで再評価
python evaluate_llm.py data/ --provider openai --model gpt-4o
```

### 4. 出力例

```
=== 結果 (n=30) ===
Accuracy:    0.8333
Macro F1:    0.8201
Cohen's κ:   0.7456

[per-class]
  納得: P=0.857 R=0.857 F1=0.857 n=14
  中立: P=0.778 R=0.875 F1=0.824 n=8
  不納得: P=0.875 R=0.778 F1=0.824 n=9

[confusion matrix]  (rows=gold, cols=pred)
            納得    中立  不納得
    納得    12      2      0
    中立     1      7      0
   不納得     1      1      7
```

### 指標の解釈
- **Accuracy**: 全体一致率
- **Macro F1**: クラス不均衡に頑健な平均F1（論文での主指標）
- **Cohen's κ**: 偶然一致を除いた一致度。**0.4-0.6=中程度 / 0.6-0.8=良好 / 0.8+=優秀**
- **Confusion Matrix**: どのクラス間で誤りが多いかを可視化

### 比較実験のコツ
- **複数モデル比較**: gpt-4o vs gpt-4o-mini vs claude-haiku → コスト/精度トレードオフ
- **プロンプト戦略比較**: zero-shot / few-shot / CoT のablation
- **マルチモーダル統合**: 頷き・表情の検出結果をプロンプトに混ぜて精度向上を測る

## 評価サンプル数の目安

- パイロット（精度の見当をつける）: 1〜2サンプル × 1〜2分
- 論文用一次評価: 5〜10名 × 3〜5分
- 信頼区間付きで報告したい: 30サンプル以上
