# VR教室観察システムにおける学習者の納得度推定に向けた多モーダル指標の自動測定

中村亮太¹

A Multimodal Implementation toward Learner Conviction Estimation in a VR Classroom

RYOTA NAKAMURA¹

---

## 1. はじめに

教室における学習効果は、学習者が教師の発話を「理解」し「同意」し「受容」してさらに「行動意図」へ至るという、多次元の心理状態に依存する。従来、これらの納得度（agreement / acceptance）は授業後の自己報告に頼ってきたが、リアルタイムかつ客観的な計測手段は限定的である。本研究では、WebXR で構築した VR 教室上に観察室と分析モジュールを実装し、学習者の頭部運動・表情・音声・対話・言語の各モーダルから納得度を自動推定する基盤を構築する。同時に retrospective リッカート尺度を主観指標として取得し、両者を照合することで指標の妥当性を検証することを目的とする。

## 2. 主観指標：4次元リッカート尺度

納得度を以下の4次元で操作的に定義し、各次元 3〜5 項目・7件法で評定する。事後 retrospective 法により、被験者は授業録画を 30〜60 秒セグメント単位で視聴して回答する。個人差は z-score 標準化で補正する。

- **理解 (comprehension)**：例「いま教師が説明したことを、自分の言葉で他人に説明できる」
- **同意 (agreement)**：例「いま教師が言ったことは正しいと思う」
- **受容 (acceptance)**：例「いまの説明で、自分の考えが少し変わった」
- **コミットメント (commitment)**：例「いま学んだことを、今後使ってみたい／応用できそうだ」

各次元には逆転項目（例「分からない部分があった」）を含める。

## 3. 客観指標と自動測定の実装

VR教室 `japanese_classroom.glb` を Three.js + WebXR Device API で描画し、観察室 `observation-room.html` と分析ダッシュボード `observation-analysis.html` を実装した。Socket.IO プラグイン `multiplayer.js` / `voice-chat.js` / `ollama-chat.js` により、複数学習者の頭部姿勢・音声・対話を同期収集する。

| モーダル | 指標 | 方向 | 実装手段 | 文献 |
|---|---|---|---|---|
| 頭部 | うなずき | + | WebXR 6DoF + MediaPipe Pitch 系列の零交差検出 | [1][2] |
| 頭部 | 首振り | − | 同上 (Yaw 系列) | [3][4] |
| 表情 | AU6+AU12（笑顔） | + | MediaPipe Face Landmarker のブレンドシェイプを AU に写像 | [5] |
| 表情 | AU4（困惑） | − | 同上 | [5] |
| 表情 | AU4+AU7（認知的不均衡） | − | 同上 | [6] |
| 言語 | 同意／不同意表現 | ± | LLM 推論（gpt-5-nano／qwen3:latest／gemma3:12b） | [7][8] |
| 言語 | 理解確認・聞き返し | ±∓ | 同上、30〜60秒セグメント単位でラベル付与 | [9][10] |
| 言語 | hedge・確信度低下 | − | 同上 | [11] |
| 対話 | 行動意図表明 | + | 同上 | [12] |
| 対話 | 質問・根拠要求 | (−) | 同上 | [13] |
| 音声 | F0・音量・発話速度・ポーズ長 | 不確実性／関与 | WebRTC PCM からの音響特徴抽出（実装中） | [14][15] |

LLM 推論はローカル GPU サーバ（`ssh 202.240.109.53`、qwen3:latest／gemma3:12b）と OpenAI gpt-5-nano を切替可能にし、`/ollama-chat-io/` プラグイン経由でストリーミング応答する。すべての指標は CSV（`logs/`）および SQLite（`space/dimensio.db`）にエピソード／軌跡単位で記録する。`nod-fp-debug.html` で頭部運動のオフライン検証を行い、`nod_debug_*.json` を回帰テストに利用する。

## 4. 客観 × 主観の照合

同一セグメント上で客観指標時系列と主観 4 次元を対応付け、Spearman 相関および Ridge／GBDT 回帰により、各次元の予測可能性を評価する。とくに AU4+AU7 と「理解」次元の負相関、うなずき頻度と「同意」次元の正相関を主仮説とする。

## 5. 今後の実験計画

(1) 武蔵野大学データサイエンス学部の学生 N≈20 を対象に、VR 教室を用いた 1 セッション 15 分のパイロット実験を行い、各客観指標と主観 4 次元の相関を確認する。(2) D'Mello らの認知的不均衡モデル [6] に基づき、納得度低下区間の検出精度を評価する。(3) 皮膚電気活動・心拍変動・瞳孔径などの生理指標 [16] はウェアラブル／アイトラッカ導入後に拡張する。最終的には、教師に対して観察室ビュー上にリアルタイム納得度ヒートマップを提示するアシスト機能（`assistPolicy`）として運用する。

## 参考文献

[1] Allwood, J. et al.: On the semantics and pragmatics of linguistic feedback, J. Semantics, 9, pp.1–26 (1992). [2] Morency, L.-P. et al.: Head gestures for perceptual interfaces, IVC, 25(12), pp.1839–1851 (2007). [3] Kendon, A.: Some uses of the head shake, Gesture, 2(2) (2002). [4] McClave, E. Z.: Linguistic functions of head movements, J. Pragmatics, 32 (2000). [5] Ekman, P. & Friesen, W. V.: Facial Action Coding System (1978). [6] D'Mello, S. & Graesser, A.: Dynamics of affective states during complex learning, Learning and Instruction, 22 (2012). [7] Galley, M. et al.: Identifying agreement and disagreement, ACL (2004). [8] Hillard, D. et al.: Detection of agreement vs. disagreement in meetings, HLT-NAACL (2003). [9] Clark, H. H. & Brennan, S. E.: Grounding in communication (1991). [10] Schegloff, E. A. et al.: The preference for self-correction, Language, 53 (1977). [11] Rubin, V. L. et al.: Certainty identification in texts, JASIST, 57 (2006). [12] Ajzen, I.: The theory of planned behavior, OBHDP, 50 (1991). [13] Graesser, A. C. & Person, N. K.: Question asking during tutoring, AERJ, 31 (1994). [14] Scherer, K. R.: Vocal communication of emotion, Speech Communication, 40 (2003). [15] Heldner, M. & Edlund, J.: Pauses, gaps and overlaps in conversations, J. Phonetics, 38 (2010). [16] Picard, R. W.: Affective Computing (1997).

---

¹ 武蔵野大学 データサイエンス学部 / Faculty of Data Science, Musashino University
