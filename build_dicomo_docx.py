"""Generate a full DICOMO paper .docx (A4, 2-column body, multi-page allowed)."""
from docx import Document
from docx.shared import Pt, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = "/Users/rn-lab/WebXR/public/fujii/dicomo2026_abstract.docx"

JP_TITLE = "VR教室観察システムにおける学習者納得度の多モーダル自動推定：客観指標と主観指標の統合に向けて"
JP_AUTHORS = "藤井優羽¹　中村亮太¹"
EN_TITLE = "Toward Multimodal Estimation of Learner Conviction in a VR Classroom Observation System: Integrating Objective and Subjective Indicators"
EN_AUTHORS = "YU FUJII¹　　RYOTA NAKAMURA¹"
AFFIL = "1 武蔵野大学 データサイエンス学部 / Faculty of Data Science, Musashino University"

ABSTRACT_JP = (
    "教室における学習効果は、教師の発話を学習者がどれだけ理解・同意・受容し、行動意図に至ったかという多次元の心理状態に支えられる。"
    "我々はこれらを総称して「納得度（conviction）」と呼び、その計測に向けてWebXRで構築したVR教室上に観察室と分析モジュールを実装した。"
    "本稿では、頭部運動（うなずき・首振り）、表情（AU4/6/7/12）、言語・対話（同意・不同意・聞き返し・hedge・行動意図）、音声（F0・音量・発話速度・ポーズ長）の4モーダルを自動測定する仕組みと、"
    "retrospective法による7件法×4次元の主観リッカート尺度の取得設計を述べる。"
    "客観時系列と主観評定を同一セグメントで対応付け、Spearman相関およびRidge/GBDT回帰で各次元の予測可能性を評価する分析計画を示す。"
    "生理指標（EDA・HRV・瞳孔径）は将来拡張とし、最終的には観察室ビューにリアルタイム納得度ヒートマップを提示するアシスト機能として運用することを目指す。"
)

ABSTRACT_EN = (
    "Effective classroom learning depends on multi-dimensional psychological states — comprehension, agreement, acceptance, and behavioral commitment — that arise as listeners process a teacher's speech. "
    "We term this composite \"conviction\" and present a multimodal sensing infrastructure embedded in a WebXR-based VR classroom. "
    "The system automatically measures (a) head motion (nods and shakes), (b) facial action units (AU4/6/7/12), (c) language and dialogue acts via local and cloud LLMs, and (d) prosodic features (F0, RMS, speaking rate, pause length). "
    "On the subjective side, we administer a 4-dimension × 7-point Likert questionnaire under a retrospective protocol over 30–60 second video segments. "
    "Objective time series and subjective ratings are aligned per segment and analyzed by Spearman correlation and Ridge/GBDT regression. "
    "We describe the implementation, planned pilot (N≈20), and the road map toward a real-time conviction heatmap that assists the lecturer."
)

# (level, heading, body) tuples; level 1=section, 2=subsection, 0=plain paragraph (no heading), -1=bullet
SECTIONS = [
    (1, "1. はじめに", None),
    (0, None,
     "教室における学習は単純な情報伝達ではない。教師の発話に対し、学習者は内的に意味を構築し、解釈の妥当性を評価し、自身の信念体系と照合し、最終的に行動方針を更新する。この一連のプロセスを総合した心理状態を、本研究では「納得度（conviction）」と呼ぶ。納得度は自己効力や行動変容の前段階として教育心理学の中心的な構成概念であり、その動的計測は学習評価・学習支援の精緻化に直結する。"),
    (0, None,
     "しかしながら、納得度は内的状態であるがゆえに直接観測できない。これまでの実証研究の多くは授業後の自己報告質問紙に頼っており、(i) 時間粒度が粗い、(ii) 想起バイアスを免れない、(iii) リアルタイムフィードバックに使えない、という限界を抱えてきた。一方、近年の表情解析・頭部運動推定・LLMによる対話解析・音響特徴抽出の発展により、学習者の非言語・対話・音声・テキストからの納得度推定が現実的になりつつある。"),
    (0, None,
     "本研究は、WebXRベースのVR教室上に客観・主観両面の納得度計測基盤を構築し、両者を対応付けて分析することで、客観指標から納得度を予測する回帰モデルの妥当性を検証することを目的とする。本稿では、(1) 4次元による納得度の操作的定義、(2) 各次元に対応する客観指標の選定根拠と実装、(3) 主観評価プロトコル、(4) 客観×主観の照合と統計分析計画、(5) パイロット実験の手順を順に述べる。"),

    (1, "2. 関連研究", None),
    (2, "2.1 納得度の心理学的構成", None),
    (0, None,
     "説得論におけるYale Approach [13]、計画的行動理論 [1]、態度変容の二重過程モデル [17] のいずれにおいても、態度形成は「理解→評価→受容→行動意図」という多段階プロセスとして概念化されてきた。本研究はこの伝統に倣い、納得度を理解 (comprehension)、同意 (agreement)、受容 (acceptance)、コミットメント (commitment) の4次元で構成する。"),
    (2, "2.2 頭部運動と非言語フィードバック", None),
    (0, None,
     "うなずきは対話における理解・同意・関与のシグナルとして広く研究されている [2,16]。一方、首振りは否定・不同意の機能を持つ [14,15]。VR/HMD環境では頭部の6DoFポーズが連続的に取得できるため、零交差・振幅閾値による自動検出が比較的容易である。"),
    (2, "2.3 表情と認知的不均衡", None),
    (0, None,
     "Facial Action Coding System [7] は、各筋肉ユニットの動きとしてAU (Action Unit) を定義する。AU6 (cheek raiser) と AU12 (lip corner puller) の同時出現は Duchenne smile に相当し、ポジティブな情動と関連する [4]。AU4 (brow lowerer) は集中・困惑・否定を示し [5,7]、特に AU4+AU7 (lid tightener) の併発は学習文脈で「認知的不均衡」と関連する [6]。"),
    (2, "2.4 LLMによる対話・テキスト解析", None),
    (0, None,
     "近年、LLMの発展により、同意・不同意 [9,12]、理解確認 [3]、修復要求 [21]、不確実性表現 [19]、態度変化 [22]、行動意図 [23] といった対話的振る舞いを高い精度で分類できるようになった。本研究ではローカルLLM（qwen3:latest, gemma3:12b）と OpenAI gpt-5-nano を切り替え可能な構成で運用する。"),
    (2, "2.5 音声プロソディ", None),
    (0, None,
     "声の基本周波数 (F0)、音量、発話速度、ポーズ長は感情・覚醒・確信度の手掛かりとして広く利用される [8,20]。特にポーズ長と話速の変化は不確実性・認知負荷との関連が強い [10,11]。"),

    (1, "3. 4次元納得度モデル", None),
    (2, "3.1 操作的定義", None),
    (-1, None, "理解 (comprehension)：教師の発話の意味内容を、学習者が自身の言葉で再構成・他者へ説明できる状態"),
    (-1, None, "同意 (agreement)：発話内容の真偽・正当性を学習者が肯定する状態"),
    (-1, None, "受容 (acceptance)：発話内容と既存の信念・知識の整合が取れ、必要に応じて学習者の認知構造が更新された状態"),
    (-1, None, "コミットメント (commitment)：学習内容を将来の場面で活用する意図・準備が形成された状態"),
    (2, "3.2 リッカート尺度の設計", None),
    (0, None,
     "各次元につき 3〜5 項目、7件法 (1=強く同意しない 〜 7=強く同意する) で評定する。逆転項目を含めて応答バイアスを軽減する。代表的な項目を以下に示す。"),
    (-1, None, "理解：「いま教師が説明したことを、自分の言葉で他人に説明できる」(正) ／「いま示された内容で分からない部分があった」(逆)"),
    (-1, None, "同意：「いま教師が言ったことは正しいと思う」(正) ／「いま教師が言ったことに対して、反論したい点があった」(逆)"),
    (-1, None, "受容：「いまの説明で、自分の考えが少し変わった」(正) ／「いまの説明は、自分のこれまでの理解と矛盾しなかった」(正)"),
    (-1, None, "コミットメント：「いま学んだことを、今後使ってみたい」(正) ／「いま学んだことを、他の場面で応用できそうだ」(正)"),
    (2, "3.3 評定タイミング", None),
    (0, None,
     "retrospective法を採用する。被験者はVR教室で授業を受けた後、録画された自分の視点ビデオを30〜60秒のセグメント単位で視聴し、各セグメント直後に質問紙へ回答する。これにより、(a) 授業中のタスク負荷を増やさず、(b) 客観指標時系列とのセグメント単位対応付けが可能となる。個人差は z-score 標準化により補正する。"),

    (1, "4. システム実装", None),
    (2, "4.1 VR教室環境", None),
    (0, None,
     "VR教室は japanese_classroom.glb (1.9MB, GLTFバイナリ) を用い、Three.js + WebXR Device API で描画する。WebXR対応HMD（Meta Quest等）またはデスクトップブラウザから入室可能で、Socket.IOプラグイン multiplayer.js (/multiplayer-io/) により最大20名のアバター同期を実現する。各アバターは8色から自動割当され、60秒タイムアウトで離脱検出する。教師役・生徒役・観察者役の3ロールは observation-room.html にて切替可能で、観察者には学習者群の頭部姿勢・表情・音声指標がダッシュボード observation-analysis.html に集約表示される。"),
    (2, "4.2 頭部運動の検出", None),
    (0, None,
     "WebXR の XRReferenceSpace から取得される HMD の 6DoF ポーズ（位置・四元数）を、毎フレーム CSV logs/observation-room/ に書き出す。四元数を Tait-Bryan 角に変換し Pitch (うなずき軸) と Yaw (首振り軸) の時系列を得る。"),
    (0, None,
     "うなずき検出は (i) Pitch系列に 0.5–3.0 Hz のバンドパスを適用、(ii) ゼロ交差点を検出、(iii) ピーク間振幅 5°以上 かつ 200–1500ms の往復を「うなずき1回」とカウントする。首振りは Yaw系列に同等の処理を適用する。オフライン検証用に nod-fp-debug.html を実装し、nod_debug_2026-02-04T*.json の実走ログを再生して閾値調整を行う。誤検出の主因は (a) HMD調整動作、(b) 視線追従の急速な頭部回頭であり、振幅・周期の二重閾値で抑制する。"),
    (2, "4.3 表情解析", None),
    (0, None,
     "非HMDモード（デスクトップ参加者）ではフロントカメラ映像を MediaPipe Face Landmarker (Tasks API, JavaScript) で解析し、52種のブレンドシェイプ係数を 30Hz で取得する。これらを Ekman の AU 体系に近似写像し、特に AU4 (browDownLeft/Right の重み付き和)、AU6 (cheekSquintLeft/Right)、AU7 (eyeSquintLeft/Right)、AU12 (mouthSmileLeft/Right) の時系列を保存する。実装ファイル mediapipe/ 配下に Face Landmarker のローダと AU 写像テーブルを置き、観察室クライアントから WebSocket 経由で送信する。サーバ側 observation-room.js プラグインは AU 時系列を被験者単位で集約し、CSV および SQLite の face_au テーブルに記録する。"),
    (2, "4.4 言語・対話解析", None),
    (0, None,
     "生徒の発話は voice-chat.js (/voice-chat-io/) によって WebRTC P2P で交換される一方、観察者向けにはサーバへの混合ストリームも供給される。30 秒スライディングウィンドウごとに音声を切り出し、Whisper（ローカル）で文字起こしを得る。テキストは ollama-chat.js (/ollama-chat-io/) を介して、ローカル GPU サーバ (ssh rn-lab@202.240.109.53、Ollama: qwen3:latest または gemma3:12b)、または OpenAI API (gpt-5-nano) のいずれかに送られる。"),
    (0, None,
     "LLM への系統的プロンプトにより、各セグメントに対し以下のラベルを付与する：同意表現、不同意・反論、理解・確認応答、聞き返し・修復要求、不確実性 (hedge) の強度、スタンス変化、行動意図・コミットメント表明、質問・根拠要求。ラベルは JSON で返却され、CSV logs/llm-labels/ へ書き出される。LLM の応答品質はゴールドラベル付き 100 セグメントで定期検証する。"),
    (2, "4.5 音声プロソディ", None),
    (0, None,
     "WebRTC PCM ストリームから、独自モジュールで以下の特徴量を 100ms フレームで抽出する：基本周波数 F0 (YINアルゴリズム)、RMS エネルギー、ZCR、発話速度（mora/秒、Whisperトランスクリプトから推定）、ポーズ長分布 (>200ms の無音区間)。確信度プロソディの代理指標として、F0レンジの圧縮、ポーズ長の延伸、発話速度の低下を組み合わせた複合スコア [18] を算出する。"),
    (2, "4.6 ログ基盤", None),
    (0, None,
     "すべての客観指標は (a) 即時可読性のため CSV として logs/{plugin}/ に書き出され、(b) 統計解析用に SQLite データベース space/dimensio.db の以下のテーブルに格納される：sessions（被験者・日時・条件）、episodes（30〜60秒の評定セグメント）、trajectories（3D位置・回転）、head_motion（うなずき・首振りイベント）、face_au（AU 時系列）、prosody（F0・RMS・速度・ポーズ）、llm_labels（LLMによる対話ラベル）、subjective（4次元×7件法の評定結果）。API POST /api/space/log、/api/episode/start|end、/api/space/trajectory を経由して、クライアントから一貫してログを書き込む。"),

    (1, "5. 主観評価の取得", None),
    (2, "5.1 retrospective プロトコル", None),
    (0, None,
     "授業終了後、被験者は別室の PC で自分の視点ビデオを再生する。動画プレイヤは 30 秒経過ごとに自動で停止し、4次元計 12 項目の質問紙を画面に提示する。被験者は 7 件法スライダーで回答し、「次へ」を押すと次のセグメントへ進む。1セッション 15 分の授業に対し、評定は 30 セグメント程度・所要時間 約 25 分となる。"),
    (2, "5.2 個人差処理", None),
    (0, None,
     "被験者ごとに評定値全体の平均・標準偏差を算出し z-score 化する。これにより「常に高得点をつける学習者」「常に中央値に寄せる学習者」のスタイル差を補正する。"),
    (2, "5.3 信頼性検証", None),
    (0, None,
     "各次元の Cronbach's α を算出し、α≥0.7 を採用基準とする。α が低い項目は除外、または再設計する。"),

    (1, "6. 客観×主観の照合と分析計画", None),
    (2, "6.1 セグメント整列", None),
    (0, None,
     "主観評定は 30 秒セグメント単位、客観指標は 100ms〜30Hz のフレーム時系列で得られる。各セグメントごとに客観指標を集約統計量（平均・分散・最大・最小・スロープ）に変換し、4次元の z-score と対応付ける。"),
    (2, "6.2 仮説検定", None),
    (-1, None, "H1: うなずき頻度は同意次元と正相関する。"),
    (-1, None, "H2: 首振り頻度は同意次元と負相関する。"),
    (-1, None, "H3: AU4+AU7 共起時間は理解次元と負相関する（認知的不均衡仮説）。"),
    (-1, None, "H4: F0レンジ圧縮 × ポーズ長延伸の複合スコアは受容次元と負相関する。"),
    (-1, None, "H5: LLM 行動意図ラベルはコミットメント次元と正相関する。"),
    (0, None,
     "各仮説について Spearman 順位相関を算出し、Bonferroni 補正後 p<.05 を有意とする。"),
    (2, "6.3 予測モデル", None),
    (0, None,
     "客観指標を入力、4次元の主観評定を目的変数として、Ridge回帰および GBDT (LightGBM) で予測モデルを構築する。被験者交差検証 (Leave-One-Subject-Out) で汎化性能を評価する。評価指標は Spearman 相関と RMSE。"),
    (2, "6.4 特徴重要度分析", None),
    (0, None,
     "GBDT の SHAP 値により、各次元に対する各客観指標の寄与度を可視化する。これにより、4次元それぞれを最も予測する非言語・対話チャネルを特定する。"),

    (1, "7. パイロット実験計画", None),
    (2, "7.1 参加者", None),
    (0, None,
     "武蔵野大学 データサイエンス学部の学部生 N ≈ 20 を対象に、3 週間以内にパイロットを実施する。倫理審査は学部内 IRB に申請する。"),
    (2, "7.2 教材", None),
    (0, None,
     "データサイエンス領域からトピックを 3 つ選び、各 5 分の講義動画を VR 教師アバターが提示する形で提示する。トピックは難易度（初級・中級・上級）と一貫性（事実中心・主張中心）を変える。"),
    (2, "7.3 手続き", None),
    (0, None,
     "(1) インフォームドコンセント、(2) HMD・カメラ設置、(3) 練習セッション 5 分、(4) 本セッション 15 分、(5) retrospective 評定 25 分、(6) 事後インタビュー 10 分。所要時間 約 70 分。"),
    (2, "7.4 分析と達成目標", None),
    (0, None,
     "§6 の手順で客観×主観の対応を分析し、4次元それぞれの予測精度として Spearman ≥ 0.4 を目標とする。"),

    (1, "8. むすび", None),
    (0, None,
     "本稿では、WebXR ベースの VR 教室に学習者の納得度を多モーダルで自動測定する基盤を実装し、retrospective リッカート尺度との照合により妥当性を検証する研究計画を述べた。客観指標としては頭部運動・表情AU・LLMによる対話ラベル・音声プロソディの4チャネルを整備し、主観指標は理解・同意・受容・コミットメントの4次元で操作化した。今後はパイロット実験を通じて各仮説を検証し、生理指標 (EDA, HRV, 瞳孔径) を統合した拡張、観察室ビューにリアルタイム納得度ヒートマップを提示する教師向けアシスト機能 (assistPolicy) への展開を進める。"),
]

REFERENCES = [
    "[1] Ajzen, I.: The theory of planned behavior, Organizational Behavior and Human Decision Processes, 50, pp.179–211 (1991).",
    "[2] Allwood, J., Nivre, J. & Ahlsén, E.: On the semantics and pragmatics of linguistic feedback, Journal of Semantics, 9, pp.1–26 (1992).",
    "[3] Clark, H. H. & Brennan, S. E.: Grounding in communication, Perspectives on Socially Shared Cognition, APA, pp.127–149 (1991).",
    "[4] Cohn, J. F. & Ekman, P.: Measuring facial action, in The New Handbook of Methods in Nonverbal Behavior Research, Oxford UP (2005).",
    "[5] Craig, S. D., D'Mello, S., Witherspoon, A. & Graesser, A.: Emote aloud during learning with AutoTutor, Cognition and Emotion, 22(5), pp.777–788 (2008).",
    "[6] D'Mello, S. & Graesser, A.: Dynamics of affective states during complex learning, Learning and Instruction, 22, pp.145–157 (2012).",
    "[7] Ekman, P. & Friesen, W. V.: Facial Action Coding System, Consulting Psychologists Press (1978).",
    "[8] Eyben, F., Scherer, K. R., Schuller, B. W. et al.: The Geneva Minimalistic Acoustic Parameter Set (GeMAPS), IEEE Trans. Affective Computing, 7(2), pp.190–202 (2016).",
    "[9] Galley, M., McKeown, K., Hirschberg, J. & Shriberg, E.: Identifying agreement and disagreement in conversational speech, Proc. ACL (2004).",
    "[10] Goldman-Eisler, F.: Psycholinguistics: Experiments in Spontaneous Speech, Academic Press (1968).",
    "[11] Heldner, M. & Edlund, J.: Pauses, gaps and overlaps in conversations, Journal of Phonetics, 38, pp.555–568 (2010).",
    "[12] Hillard, D., Ostendorf, M. & Shriberg, E.: Detection of agreement vs. disagreement in meetings, Proc. HLT-NAACL (2003).",
    "[13] Hovland, C. I., Janis, I. L. & Kelley, H. H.: Communication and Persuasion, Yale UP (1953).",
    "[14] Kendon, A.: Some uses of the head shake, Gesture, 2(2), pp.147–182 (2002).",
    "[15] McClave, E. Z.: Linguistic functions of head movements, Journal of Pragmatics, 32, pp.855–878 (2000).",
    "[16] Morency, L.-P., Sidner, C., Lee, C. & Darrell, T.: Head gestures for perceptual interfaces, Image and Vision Computing, 25(12), pp.1839–1851 (2007).",
    "[17] Petty, R. E. & Cacioppo, J. T.: The elaboration likelihood model of persuasion, Advances in Experimental Social Psychology, 19, pp.123–205 (1986).",
    "[18] Pon-Barry, H.: Prosodic manifestations of confidence and uncertainty in spoken language, Proc. Interspeech (2008).",
    "[19] Rubin, V. L., Liddy, E. D. & Kando, N.: Certainty identification in texts, JASIST, 57(4), pp.456–468 (2006).",
    "[20] Scherer, K. R.: Vocal communication of emotion, Speech Communication, 40, pp.227–256 (2003).",
    "[21] Schegloff, E. A., Jefferson, G. & Sacks, H.: The preference for self-correction in the organization of repair in conversation, Language, 53(2), pp.361–382 (1977).",
    "[22] Tan, C., Niculae, V., Danescu-Niculescu-Mizil, C. & Lee, L.: Winning arguments: interaction dynamics and persuasion strategies, Proc. WWW (2016).",
    "[23] Traum, D. R. & Allen, J. F.: Discourse obligations in dialogue processing, Proc. ACL (1994).",
    "[24] Walker, M. A., Anand, P., Abbott, R. & Tree, J. E. F.: A corpus for research on deliberation and debate, Proc. LREC (2012).",
]


def set_jp_font(run, size_pt, bold=False, font="ＭＳ 明朝"):
    run.font.name = font
    run.font.size = Pt(size_pt)
    run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), font)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)


def add_centered(doc, text, size, bold=False, font="ＭＳ Ｐゴシック", space_after=2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    set_jp_font(run, size, bold=bold, font=font)
    return p


def add_paragraph(doc, text, size=9, bold=False, indent_mm=3.0, font="ＭＳ 明朝",
                  space_before=0, space_after=2, line_spacing=1.15):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing
    if indent_mm:
        pf.first_line_indent = Mm(indent_mm)
    run = p.add_run(text)
    set_jp_font(run, size, bold=bold, font=font)
    return p


def add_heading(doc, text, level=1):
    if level == 1:
        size, bold, before, after = 11, True, 6, 2
        font = "ＭＳ Ｐゴシック"
    else:
        size, bold, before, after = 10, True, 4, 1
        font = "ＭＳ Ｐゴシック"
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.15
    run = p.add_run(text)
    set_jp_font(run, size, bold=bold, font=font)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Mm(4)
    pf.first_line_indent = Mm(-3)
    pf.space_after = Pt(1)
    pf.line_spacing = 1.15
    run = p.add_run("・" + text)
    set_jp_font(run, 9, font="ＭＳ 明朝")


def add_continuous_section(doc, num_cols=2, space_twips=360):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    sectPr = OxmlElement("w:sectPr")
    sectType = OxmlElement("w:type")
    sectType.set(qn("w:val"), "continuous")
    sectPr.append(sectType)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num_cols))
    cols.set(qn("w:space"), str(space_twips))
    cols.set(qn("w:equalWidth"), "1")
    sectPr.append(cols)
    pPr.append(sectPr)


def set_cols_on_section(section, num_cols=2, space_twips=360):
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(num_cols))
    cols.set(qn("w:space"), str(space_twips))
    cols.set(qn("w:equalWidth"), "1")


def main():
    doc = Document()

    section = doc.sections[0]
    section.page_height = Mm(297)
    section.page_width = Mm(210)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(22)
    section.left_margin = Mm(18)
    section.right_margin = Mm(18)
    section.header_distance = Mm(10)
    section.footer_distance = Mm(10)

    # ---- Header (single column) ----
    add_centered(doc, JP_TITLE, size=14, bold=True)
    add_centered(doc, JP_AUTHORS, size=10, space_after=4)
    add_centered(doc, EN_TITLE, size=11, bold=True, space_after=2)
    add_centered(doc, EN_AUTHORS, size=9, space_after=8)

    # ---- Continuous break -> 2 columns ----
    add_continuous_section(doc, num_cols=2, space_twips=360)

    # ---- Abstracts ----
    add_heading(doc, "概要", level=1)
    add_paragraph(doc, ABSTRACT_JP, size=9)
    add_heading(doc, "Abstract", level=1)
    add_paragraph(doc, ABSTRACT_EN, size=9, font="Times New Roman")

    # ---- Body ----
    for level, heading, body in SECTIONS:
        if level == 1 and heading:
            add_heading(doc, heading, level=1)
        elif level == 2 and heading:
            add_heading(doc, heading, level=2)
        elif level == -1 and body:
            add_bullet(doc, body)
        elif body:
            add_paragraph(doc, body, size=9)

    # ---- References ----
    add_heading(doc, "参考文献", level=1)
    for ref in REFERENCES:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Mm(5)
        pf.first_line_indent = Mm(-5)
        pf.space_after = Pt(1)
        pf.line_spacing = 1.15
        run = p.add_run(ref)
        set_jp_font(run, 8, font="ＭＳ 明朝")

    # ---- Final section -> 2 columns ----
    set_cols_on_section(doc.sections[-1], num_cols=2, space_twips=360)

    # ---- Footer ----
    footer = doc.sections[-1].footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    frun = fp.add_run(AFFIL)
    set_jp_font(frun, 8, font="ＭＳ 明朝")

    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
