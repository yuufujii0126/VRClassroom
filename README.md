# VRClassroom

**VR教室における学習者の納得度推定のための非言語行動分析システム**

WebXR 上に VR 教室と観察室を実装し、講師・学習者の頭部姿勢・音声・対話を同期収集して、学習者の「納得度」を推定するための研究リポジトリです。

- 藤井 優羽, 中村 亮太（武蔵野大学 データサイエンス学部）
- 発表：「VR教室における学習者の納得度推定のための非言語行動分析システムの設計と予備的検討」, DICOMO2026

## 概要

納得度を **理解・同意・受容・コミットメント** の4観点に分解し、21 の観測指標と対応づけます。各指標を重み付き和で統合した「統合納得度」を定義しています。

特徴は次の3系統から抽出し、共通の時刻軸で統合・可視化します。

| 系統 | 主な指標 |
|---|---|
| 言語 | 同意・理解確認・hedge など9指標（ModernBERT / LLM） |
| 音声 | F0・RMS・発話速度・ポーズ長 |
| 視覚 | 頷き・首振り検出、視線、表情 |

## 主な結果（予備評価）

| 検出器 | 結果 |
|---|---|
| 頷き検出 | micro F1 = 0.95（P 0.95 / R 0.95、許容誤差 0.5 秒） |
| 表情分類（face-api.js） | Accuracy 0.694 / macro F1 0.543 / κ 0.50（608 フレーム） |

表情分類では angry の Recall が 0.17 と低く、多くが neutral に誤判定されました。欧米顔で学習されたモデルの影響とみて、現状はベースラインとして扱っています。

## ディレクトリ構成

```
.
├── observation-room.html      # 観察室（講師 / 学習者 / 観察者の3ロール）
├── observation-analysis.html  # 分析ダッシュボード（時系列・指標の可視化）
├── vr-classroom.html          # VR教室（視線トラッキング付き）
├── classroom5.html            # VR教室の旧バージョン
├── voice-chat.html            # P2P 音声チャット
├── exp.html                   # 発話シグナル可視化の実験ページ
├── nod-fp-debug.html          # 頷き誤検出のデバッグ用
├── japanese_classroom.glb     # 教室の 3D モデル
├── mediapipe/                 # MediaPipe Face Mesh（ローカル配置）
├── analyze_speech.py          # マイク録音 → 音響分析 + Whisper + GPT で発話分類
├── face_eval/                 # 頷き・表情検出の精度評価
│   ├── recorder.html          #   録画 + 検出ログ出力
│   ├── annotate.html          #   正解アノテーション作成
│   ├── server.py              #   アップロード受付サーバ（:8001）
│   ├── evaluate_nod.py        #   頷き検出のイベント単位評価（P/R/F1）
│   └── evaluate_expression.py #   表情分類のフレーム単位評価（Acc/F1/κ）
├── speech_eval/               # 音声認識・発話分類の精度評価
│   ├── recorder.html          #   評価用の発話録音
│   ├── server.py              #   アップロード受付サーバ（:8000）
│   ├── transcribe.py          #   Whisper で文字起こし
│   ├── evaluate_asr.py        #   CER / WER 評価
│   ├── evaluate_llm.py        #   LLM による納得度ラベル分類の評価
│   └── prompts/               #   分類プロンプト
├── DICOMO2026_format_LaTeX/   # 論文（fujii.tex）
├── dicomo2026_slides.*        # 発表スライド（md / html / pptx）
├── dicomo2026_abstract.md     # 概要
├── build_dicomo_docx.py       # 概要 docx 生成
└── build_dicomo_pptx.py       # スライド pptx 生成
```

## 動かし方

### VR教室・観察室

このフォルダは 研究室の WebXR Content Server の `public/fujii/` に配置して使います。観察室の同期にはサーバ側の Socket.IO プラグイン `observation-room.js`（パス `/webxr/observation-room-io/`）が必要です。

```
https://<server>/fujii/observation-room.html      # 観察室
https://<server>/fujii/observation-analysis.html  # 分析ダッシュボード
```

A-Frame / Three.js / Socket.IO / Chart.js は CDN から読み込みます。

### 頷き・表情の精度評価（face_eval）

```bash
cd face_eval
python server.py --port 8001          # http://localhost:8001/ で recorder.html を開いて録画
# annotate.html で正解ラベルを付けてから評価
python evaluate_nod.py data/ --tolerance 0.5
python evaluate_expression.py data/
```

### 音声の精度評価（speech_eval）

```bash
cd speech_eval
python server.py --port 8000          # recorder.html で録音
python transcribe.py data/*.webm --model large-v3
python evaluate_asr.py data/          # 正解: data/<name>.reference.txt
python evaluate_llm.py data/ --provider openai --model gpt-4o-mini
```

LLM による分類には API キーが必要です。`.env`（git 管理外）か環境変数に設定してください。

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...   # --provider anthropic の場合
```

### 必要な Python パッケージ

```bash
# speech_eval / face_eval
pip install faster-whisper jiwer openai anthropic
# analyze_speech.py（Whisper は OpenAI API の whisper-1 を使用）
pip install librosa sounddevice soundfile numpy python-dotenv openai
```

## データの扱い

被験者の録画・録音・ログ（`Data/`, `face_eval/data/`, `speech_eval/data/`, `nod_debug_*.json`）は **git 管理しません**（`.gitignore` で除外）。フォーマット例として `speech_eval/data/labels.sample.csv` のみ含めています。

## 今後の予定

1. 音声パイプラインの精度評価（実データの投入）
2. 被験者20名規模の本実験：事後リッカート尺度（主観）と客観指標の相関を検証
3. 表情分類器の改善（MediaPipe ブレンドシェイプ、日本人顔データでの学習）
4. 主観指標を教師信号とした統合納得度モデルの重み推定
5. 観察室での納得度ヒートマップ表示と、講師へのリアルタイム通知
