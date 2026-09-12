# -*- coding: utf-8 -*-
"""DICOMO2026 発表スライドを編集可能な PowerPoint (.pptx) として生成する。

実行: python3 build_dicomo_pptx.py
出力: dicomo2026_slides.pptx
内容は dicomo2026_slides.md と対応。タイトル・本文・表・発表ノートすべて
PowerPoint 上で後から編集できる。
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ---- 配色・フォント ----
GREEN = RGBColor(0x22, 0x99, 0x66)
DARK = RGBColor(0x11, 0x77, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
HEAD_BG = RGBColor(0xF0, 0xF6, 0xF2)
HEAD_FG = RGBColor(0x11, 0xAA, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
JP_FONT = "Yu Gothic"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]

FOOTER = "DICOMO2026 / 藤井優羽・中村亮太"


def _set_font(run, size=None, bold=None, color=None, font=JP_FONT):
    run.font.name = font
    # 日本語グリフにもフォントを適用
    rPr = run._r.get_or_add_rPr()
    from pptx.oxml.ns import qn
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {})
        rPr.append(ea)
    ea.set('typeface', font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_slide():
    return prs.slides.add_slide(BLANK)


def add_footer(slide):
    tb = slide.shapes.add_textbox(Inches(8.3), Inches(7.05), Inches(4.9), Inches(0.35))
    tf = tb.text_frame
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = FOOTER
    _set_font(r, size=10, color=RGBColor(0xAA, 0xAA, 0xAA))


def add_title(slide, text, top=Inches(0.35)):
    tb = slide.shapes.add_textbox(Inches(0.6), top, Inches(12.1), Inches(0.95))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = text
    _set_font(r, size=30, bold=True, color=DARK)
    # 下線バー
    ln = slide.shapes.add_shape(1, Inches(0.62), top + Inches(0.92), Inches(3.2), Pt(3))
    ln.fill.solid()
    ln.fill.fore_color.rgb = GREEN
    ln.line.fill.background()
    return tb


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def add_body(slide, items, left=Inches(0.7), top=Inches(1.6),
             width=Inches(12.0), height=Inches(5.0), base_size=20):
    """items: list of (text, level, opts)。opts dict: bold,color,size,bullet(bool)"""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        text, level, opts = item
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = level
        p.space_after = Pt(6)
        bullet = opts.get('bullet', True)
        prefix = ('• ' if level == 0 else '– ') if bullet else ''
        r = p.add_run()
        r.text = prefix + text
        _set_font(r, size=opts.get('size', base_size),
                  bold=opts.get('bold', False),
                  color=opts.get('color', RGBColor(0x22, 0x22, 0x22)))
    return tb


def add_table(slide, headers, rows, left=Inches(0.7), top=Inches(1.7),
              width=Inches(12.0), col_widths=None, font_size=14):
    nrows = len(rows) + 1
    ncols = len(headers)
    height = Inches(0.4 * nrows)
    gtbl = slide.shapes.add_table(nrows, ncols, left, top, width, height)
    tbl = gtbl.table
    if col_widths:
        total = sum(col_widths)
        for i, w in enumerate(col_widths):
            tbl.columns[i].width = Emu(int(int(width) * w / total))
    # header
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = HEAD_BG
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = h
        _set_font(r, size=font_size, bold=True, color=HEAD_FG)
    # body
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = val
            _set_font(r, size=font_size, color=RGBColor(0x22, 0x22, 0x22))
    return gtbl


# ============================================================
# スライド1：タイトル
# ============================================================
s = add_slide()
# タグ
tag = s.shapes.add_shape(1, Inches(5.4), Inches(1.9), Inches(2.5), Inches(0.45))
tag.fill.solid(); tag.fill.fore_color.rgb = GREEN; tag.line.fill.background()
tp = tag.text_frame.paragraphs[0]; tp.alignment = PP_ALIGN.CENTER
tr = tp.add_run(); tr.text = "DICOMO2026"; _set_font(tr, size=14, bold=True, color=WHITE)

tb = s.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11.7), Inches(1.7))
tf = tb.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run(); r.text = "VR教室で「納得度」は自動で測れるか"
_set_font(r, size=40, bold=True, color=DARK)

tb2 = s.shapes.add_textbox(Inches(0.8), Inches(4.1), Inches(11.7), Inches(0.7))
p2 = tb2.text_frame.paragraphs[0]; p2.alignment = PP_ALIGN.CENTER
r2 = p2.add_run(); r2.text = "頭部・表情・音声・言語の多モーダル指標による学習者納得度の推定"
_set_font(r2, size=18, bold=True, color=GREEN)

tb3 = s.shapes.add_textbox(Inches(0.8), Inches(5.2), Inches(11.7), Inches(0.7))
p3 = tb3.text_frame.paragraphs[0]; p3.alignment = PP_ALIGN.CENTER
r3 = p3.add_run(); r3.text = "藤井優羽　中村亮太　武蔵野大学 データサイエンス学部"
_set_font(r3, size=20, color=RGBColor(0x22, 0x22, 0x22))
set_notes(s, "⏱0:30 — 武蔵野大学の中村です。本日は『VR教室観察システムにおける学習者の納得度推定に向けた多モーダル指標の自動測定』と題して発表します。学習者がどれだけ納得しているかを、自己申告に頼らず、頭部・表情・声・言葉から自動で測る試みです。よろしくお願いします。")

# ============================================================
# 目次
# ============================================================
s = add_slide(); add_title(s, "本日の発表の流れ")
items = [
    ("1. 研究背景と課題 — 学習における「納得度」と従来手法の限界", 0, {'bullet': False, 'size': 20}),
    ("2. 関連研究と研究目的 — 多モーダルと心理状態の対応、本研究の立ち位置", 0, {'bullet': False, 'size': 20}),
    ("3. 提案手法 — 主観指標（4次元尺度）／システム構成／客観指標（5モーダル）", 0, {'bullet': False, 'size': 20}),
    ("4. 客観×主観の照合方法 — 相関分析と予測モデル、主仮説", 0, {'bullet': False, 'size': 20}),
    ("5. 現状の進捗と実験計画 — パイロット実装から検証フェーズへ", 0, {'bullet': False, 'size': 20}),
    ("6. 将来像とまとめ — 教師支援への応用", 0, {'bullet': False, 'size': 20}),
]
add_body(s, items, top=Inches(1.9))
for p in items:
    pass
add_footer(s)
set_notes(s, "本日は、まず研究背景と課題、次に関連研究と目的、そして提案手法、客観と主観の照合方法、進捗と実験計画、最後に将来像とまとめ、という流れでお話しします。")

# ============================================================
# 2 研究背景
# ============================================================
s = add_slide(); add_title(s, "研究背景 — 学習効果は「納得度」に依存する")
add_body(s, [
    ("「分かった」だけでは学びは完成しない", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 22}),
    ("学習は多次元の心理状態を経て深まる：理解 → 同意 → 受容 → 行動意図（コミットメント）", 0, {'bullet': False, 'size': 18, 'color': GREEN, 'bold': True}),
    ("教師が説明を「伝えた」ことと、学習者が「納得した」ことは別物", 0, {}),
    ("納得度（agreement / acceptance）が低いまま進むと、知識は定着・応用されない", 0, {}),
    ("だが教師は「今この瞬間、伝わっているか」を客観的に知る手段を持たない", 0, {}),
], top=Inches(1.7))
add_footer(s)
set_notes(s, "まず背景です。学習効果は『納得度』という心理状態に支えられています。これは単なる理解だけでなく、同意し、受け入れ、行動に移そうと思う、という多段階の状態です。教師が説明したつもりでも、学習者が納得しているとは限りません。しかし教師には、その場で納得度を客観的に知る手段がありませんでした。")

# ============================================================
# 3 従来手法の限界
# ============================================================
s = add_slide(); add_title(s, "従来手法の限界")
add_body(s, [("従来の納得度測定 = 授業後アンケート（自己報告）頼み", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 20})], top=Inches(1.5), height=Inches(0.6))
add_table(s, ["課題", "内容"], [
    ["後出し", "授業が終わってからしか分からない"],
    ["主観的", "本人の自己申告に依存し、客観性に欠ける"],
    ["非リアルタイム", "「今この瞬間」の状態を捉えられない"],
    ["粒度が粗い", "どの説明で納得が下がったかを特定できない"],
], top=Inches(2.2), col_widths=[2, 6], font_size=16)
add_body(s, [("→ 授業中の振る舞いから、納得度をリアルタイム・客観的に自動推定したい", 0, {'bold': True, 'bullet': False, 'color': GREEN, 'size': 18})], top=Inches(5.6), height=Inches(0.6))
add_footer(s)
set_notes(s, "従来、納得度はもっぱら授業後アンケートで測られてきました。しかしこれは後出しで、主観的で、リアルタイム性がなく、どの場面で納得が下がったかも分かりません。そこで本研究は、授業中の学習者の振る舞いそのものから、納得度を自動推定することを目指します。")

# ============================================================
# 4 関連研究
# ============================================================
s = add_slide(); add_title(s, "関連研究と本研究の差分")
add_body(s, [("既存研究は「感情・関与」を測る ─ 本研究は「納得度（態度の多段階）」を測る", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19})], top=Inches(1.5), height=Inches(0.6))
add_table(s, ["手がかり", "意味", "代表的根拠"], [
    ["うなずき／首振り", "同意・フィードバック", "Allwood '92, Morency '07"],
    ["表情AU（笑顔／困惑）", "感情・認知的不均衡", "Ekman '78, D'Mello '12"],
    ["同意／不同意表現", "言語的態度", "Galley '04"],
    ["声の高さ・間（ポーズ）", "不確実性・関与", "Scherer '03"],
], top=Inches(2.1), col_widths=[3, 3, 4], font_size=15)
add_body(s, [
    ("モーダルと心理状態の対応は確立済み。多モーダル統合自体も先行例は多い", 0, {'size': 15}),
    ("既存研究が測るのは多くが emotion / engagement / confusion（\"状態\"）", 0, {'size': 15}),
    ("本研究が測るのは 納得度＝理解→同意→受容→行動意図（\"態度変容の多段階\"）", 0, {'size': 15, 'bold': True, 'color': GREEN}),
    ("→ 多モーダル統合は\"手段\"。測る対象（納得度の4次元化）と客観×主観の妥当性検証こそが新規性", 0, {'size': 15, 'bold': True, 'color': GREEN}),
], top=Inches(5.0))
add_footer(s)
set_notes(s, "関連研究です。うなずきが同意を、表情が認知的不均衡を、声や言葉が態度を反映することは各分野で確立され、多モーダル統合の研究も既にあります。ただ多くが測るのは感情・関与・困惑という\"状態\"です。本研究が測るのは、理解・同意・受容・行動意図という\"態度変容の多段階\"＝納得度。多モーダル統合は手段で、この\"測る対象\"の置き方と主観尺度での妥当性検証こそが新規性です。")

# ============================================================
# 5 研究目的
# ============================================================
s = add_slide(); add_title(s, "研究目的")
add_body(s, [
    ("目的：測る対象を「感情・関与」ではなく「納得度（態度の多段階）」に定め、多モーダル指標から自動推定し、主観評価と照合して妥当性を検証する", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 18}),
    ("1. 測る対象を 態度変容の多段階＝納得度（理解／同意／受容／コミットメント） に定める ← 概念的新規性", 0, {'bullet': False, 'size': 18}),
    ("2. WebXR の VR教室に観察室＋分析モジュールを実装し、5モーダルを自動測定（手段）", 0, {'bullet': False, 'size': 18}),
    ("3. 事後の 4次元リッカート尺度 を主観指標（ground truth）として取得", 0, {'bullet': False, 'size': 18}),
    ("4. 両者を照合し、どの客観指標がどの納得度次元を予測できるか を次元別に定量検証 ← 妥当性検証＝科学的貢献", 0, {'bullet': False, 'size': 18}),
], top=Inches(1.8))
add_footer(s)
set_notes(s, "研究目的です。本研究の核は\"何を測るか\"の置き方にあります。既存研究のように感情や関与という状態ではなく、理解・同意・受容・コミットメントという納得度の多段階を測る対象に定めます。その上で5モーダルから自動推定する基盤を作り、事後に取る4次元の主観尺度をground truthとして突き合わせ、どの客観指標がどの納得度次元を予測できるかを次元ごとに検証します。\"測る対象の再定義\"と\"客観×主観の照合\"が本研究の二本柱です。")

# ============================================================
# 6 主観指標
# ============================================================
s = add_slide(); add_title(s, "主観指標 — 4次元リッカート尺度")
add_body(s, [("納得度を4次元で操作的に定義（各3〜5項目・7件法）", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19})], top=Inches(1.45), height=Inches(0.5))
add_table(s, ["次元", "例文"], [
    ["理解 comprehension", "「いま説明されたことを、自分の言葉で他人に説明できる」"],
    ["同意 agreement", "「いま教師が言ったことは正しいと思う」"],
    ["受容 acceptance", "「いまの説明で、自分の考えが少し変わった」"],
    ["コミットメント commitment", "「いま学んだことを、今後使ってみたい／応用したい」"],
], top=Inches(2.05), col_widths=[3, 7], font_size=14)
add_body(s, [
    ("各次元に逆転項目（例「分からない部分があった」）を含め回答の偏りを抑制", 0, {'size': 16}),
    ("事後 retrospective 法：授業録画を 30〜60秒セグメント単位で視聴して回答", 0, {'size': 16}),
    ("個人差は z-score 標準化 で補正", 0, {'size': 16}),
], top=Inches(5.0))
add_footer(s)
set_notes(s, "主観指標として、納得度を理解・同意・受容・コミットメントの4次元で定義しました。それぞれ7件法で複数項目を用意し、逆転項目も入れています。回答は事後に、授業録画を30〜60秒のセグメントで見返しながら付けてもらう retrospective 法を採ります。個人差はz-score標準化で補正します。")

# ============================================================
# 7 システム全体構成
# ============================================================
s = add_slide(); add_title(s, "システム全体構成")
add_body(s, [("WebXR + Three.js でVR教室を構築、Socket.IO で多人数同期収集", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19})], top=Inches(1.45), height=Inches(0.5))
diagram = (
    "[ VR教室 japanese_classroom.glb ]  ← Three.js + WebXR Device API\n"
    "        │  学習者の頭部姿勢・音声・対話\n"
    "        ▼\n"
    "[ 観察室 observation-room.html ]   ← 複数学習者を同時観察\n"
    "        │  Socket.IO プラグイン\n"
    "        │  multiplayer.js / voice-chat.js / ollama-chat.js\n"
    "        ▼\n"
    "[ 分析ダッシュボード observation-analysis.html ]\n"
    "        ▼\n"
    "[ ログ ]  CSV(logs/) ＋ SQLite(space/dimensio.db)  ※エピソード／軌跡単位"
)
db = s.shapes.add_textbox(Inches(0.9), Inches(2.1), Inches(11.5), Inches(3.6))
dtf = db.text_frame; dtf.word_wrap = True
for i, line in enumerate(diagram.split("\n")):
    p = dtf.paragraphs[0] if i == 0 else dtf.add_paragraph()
    rr = p.add_run(); rr.text = line
    _set_font(rr, size=14, color=RGBColor(0x22, 0x22, 0x22), font="Consolas")
add_body(s, [("LLM推論は ローカルGPUサーバ（qwen3 / gemma3:12b）と OpenAI gpt-5-nano を切替可能", 0, {'size': 16})], top=Inches(6.0), height=Inches(0.6))
add_footer(s)
set_notes(s, "システム構成です。VR教室をThree.jsとWebXRで描画し、その上に観察室を置いて複数学習者を同時に観察します。頭部・音声・対話はSocket.IOプラグインで同期収集し、分析ダッシュボードに集約、すべてCSVとSQLiteにエピソード単位で記録します。言語処理のLLMは、ローカルGPUサーバとクラウドを切り替えられる設計です。")

# ============================================================
# 8 客観指標① 頭部・表情
# ============================================================
s = add_slide(); add_title(s, "客観指標① 頭部・表情")
add_body(s, [("非言語の手がかりを WebXR と MediaPipe で自動抽出", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19})], top=Inches(1.45), height=Inches(0.5))
add_table(s, ["モーダル", "指標", "方向", "実装手段"], [
    ["頭部", "うなずき", "＋", "WebXR 6DoF＋MediaPipe、Pitch系列の零交差検出"],
    ["頭部", "首振り", "−", "同上（Yaw系列）"],
    ["表情", "笑顔（AU6+AU12）", "＋", "Face Landmarker のブレンドシェイプ→AU写像"],
    ["表情", "困惑（AU4）", "−", "同上"],
    ["表情", "認知的不均衡（AU4+AU7）", "−", "同上（D'Mello モデル）"],
], top=Inches(2.05), col_widths=[1.3, 2.8, 0.9, 5.5], font_size=13)
add_body(s, [
    ("＋＝納得を高める方向、−＝下げる方向の手がかり", 0, {'size': 15}),
    ("うなずき検出は オフライン検証環境 nod-fp-debug.html で誤検出を調整", 0, {'size': 15}),
], top=Inches(5.6))
add_footer(s)
set_notes(s, "客観指標の前半、頭部と表情です。頭部はWebXRの6自由度姿勢とMediaPipeを併用し、ピッチ方向の零交差からうなずきを、ヨー方向から首振りを検出します。表情はFace LandmarkerのブレンドシェイプをFACSのアクションユニットに写像し、笑顔や困惑、さらにD'Melloの認知的不均衡に対応するAU4+AU7を取ります。うなずき検出は専用のデバッグ環境で誤検出を詰めています。")

# ============================================================
# 9 客観指標② 言語・対話・音声
# ============================================================
s = add_slide(); add_title(s, "客観指標② 言語・対話・音声（LLM活用）")
add_body(s, [("発話・対話は LLM、声の物理特徴は音響解析で抽出", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19})], top=Inches(1.4), height=Inches(0.5))
add_table(s, ["モーダル", "指標", "方向", "実装手段"], [
    ["言語", "同意／不同意表現", "±", "LLM推論（gpt-5-nano / qwen3 / gemma3:12b）"],
    ["言語", "理解確認・聞き返し", "±∓", "同上、30〜60秒セグメント単位でラベル付与"],
    ["言語", "hedge・確信度低下", "−", "同上"],
    ["対話", "行動意図の表明", "＋", "同上"],
    ["対話", "質問・根拠要求", "(−)", "同上"],
    ["音声", "F0・音量・発話速度・ポーズ長", "不確実性／関与", "WebRTC PCM の音響特徴 ＋ analyze_speech.py（librosa＋Whisper）"],
], top=Inches(1.95), col_widths=[1.2, 3.0, 1.3, 5.0], font_size=12)
add_footer(s)
set_notes(s, "後半は言語・対話・音声です。発話の同意／不同意、理解確認やhedge、行動意図といった言語的な手がかりは、LLMにセグメント単位でラベル付けさせます。一方、声の高さや間の長さといった物理的な特徴は、librosaとWhisperを組み合わせた音響解析パイプラインで抽出します。言語の意味と声の物理量、両面から捉えるのが狙いです。")

# ============================================================
# 9.8 納得度の算出方法
# ============================================================
s = add_slide(); add_title(s, "納得度の算出方法 — 特徴量から4次元、そして統合へ")
add_body(s, [
    ("特徴量 → 4観点スコア → 統合納得度 の3ステップで算出", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19}),
    ("① 特徴量 f：うなずき率・表情(AU4+AU7)・同意表現・声 …（30〜60秒ごと／z-score）", 0, {'bold': True, 'bullet': False, 'color': GREEN, 'size': 17}),
    ("⬇", 0, {'bullet': False, 'size': 16}),
    ("② 式1：4観点を 0–1 にスコア化", 0, {'bold': True, 'bullet': False, 'color': GREEN, 'size': 17}),
    ("Ĉ⁽ᵏ⁾ = σ( Σ wᵢ⁽ᵏ⁾·fᵢ + b )　　k ＝ 理解／同意／受容／コミット", 1, {'size': 18, 'bold': True}),
    ("⬇", 0, {'bullet': False, 'size': 16}),
    ("③ 式2：4観点を統合", 0, {'bold': True, 'bullet': False, 'color': GREEN, 'size': 17}),
    ("Ĉ_total = Σ γ_k·Ĉ⁽ᵏ⁾", 1, {'size': 18, 'bold': True}),
    ("→ 重み wᵢ・γ_k はスライド10のRidge回帰で主観から推定（＋/−は重みの符号制約）", 0, {'bullet': False, 'size': 15}),
], top=Inches(1.6))
add_footer(s)
set_notes(s, "では、特徴量をどう納得度の数値にするかです。まず30〜60秒のセグメントごとに、うなずき率や認知的不均衡の表情、同意表現、声の変動といった5モーダルの特徴量をベクトルfにまとめ、z-scoreで個人差を補正します。次に式1で、この特徴量の重み付き和をシグモイドに通し、理解・同意・受容・コミットの4観点それぞれを0から1のスコアにします。先ほどのスライドで示した＋/−の方向は、ここで重みの符号の制約になります。そして式2で、4観点を重みγで足し合わせて一つの統合納得度にします。重みは、現状はドメイン知識で符号を固定したルールベースで、すでにダッシュボードに実装済みです。本実験では、この重みを次に説明するRidge回帰の係数として主観評価から推定します。つまり重みの同定と妥当性検証を同時に行う設計です。")

# ============================================================
# 10 客観×主観の照合方法
# ============================================================
s = add_slide(); add_title(s, "客観 × 主観の照合方法")
add_body(s, [
    ("同一セグメント上で客観時系列と主観4次元を対応付け、予測可能性を評価", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 19}),
    ("30〜60秒の同一セグメントで、客観指標の時系列 ↔ 主観4次元スコアを対応", 0, {'size': 18}),
    ("Spearman 相関 で関連を確認 → Ridge / GBDT 回帰 で各次元を予測", 0, {'size': 18}),
    ("評価軸：どの客観指標が、どの主観次元を、どれだけ説明できるか", 0, {'size': 18}),
    ("主仮説（検証の焦点）", 0, {'bold': True, 'bullet': False, 'color': GREEN, 'size': 19}),
    ("🎯 AU4+AU7（認知的不均衡）と「理解」次元の負相関", 1, {'size': 18}),
    ("🎯 うなずき頻度と「同意」次元の正相関", 1, {'size': 18}),
], top=Inches(1.7))
add_footer(s)
set_notes(s, "客観と主観をどう突き合わせるかです。同じ30〜60秒のセグメント上で、客観指標の時系列と主観4次元のスコアを対応付けます。まずSpearman相関で関連を見て、次にRidgeやGBDTで各次元を予測し、どの指標がどの次元を説明できるかを評価します。とくに、認知的不均衡の表情と理解の負相関、うなずきと同意の正相関を主仮説として検証します。")

# ============================================================
# 11 現状の進捗
# ============================================================
s = add_slide(); add_title(s, "現状の進捗（4〜5月の実装）")
add_body(s, [
    ("基盤実装からパイロットデータ取得まで前進", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 20}),
    ("✅ 観察分析ダッシュボード observation-analysis.html を新規実装", 0, {'bullet': False, 'size': 18}),
    ("✅ うなずき検出のオフライン検証環境 nod-fp-debug.html ＋ 回帰テスト用 nod_debug_*.json を整備", 0, {'bullet': False, 'size': 18}),
    ("✅ 発話音響分析パイプライン analyze_speech.py（librosa＋Whisper＋LLM分類）", 0, {'bullet': False, 'size': 18}),
    ("✅ 観察室 observation-room.html を機能拡張", 0, {'bullet': False, 'size': 18}),
    ("✅ パイロットデータの取得を開始（複数セッションの観察ログを収集）", 0, {'bullet': False, 'size': 18}),
    ("［要差替］取得済みセッション数・人数・予備的に見えた傾向があれば一言追加", 0, {'bullet': False, 'size': 15, 'color': GRAY}),
], top=Inches(1.7))
add_footer(s)
set_notes(s, "現状の進捗です。この数か月で、分析ダッシュボード、うなずき検出の検証環境、発話の音響分析パイプラインを実装し、観察室も機能拡張しました。すでに複数セッションのパイロットデータを取り始めています。［ここで取得状況や見えてきた傾向を補足］")

# ============================================================
# 12 実験計画
# ============================================================
s = add_slide(); add_title(s, "実験計画")
add_body(s, [
    ("パイロット → 検出精度評価 → 生理指標拡張 の3段階", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 20}),
    ("1. データサイエンス学部の学生 N≈20 を対象に、1セッション 15分 のパイロット実験 → 各客観指標と主観4次元の 相関を確認", 0, {'bullet': False, 'size': 18}),
    ("2. D'Mello の 認知的不均衡モデル に基づき、納得度低下区間の検出精度 を評価", 0, {'bullet': False, 'size': 18}),
    ("3. 皮膚電気活動・心拍変動・瞳孔径などの 生理指標 をウェアラブル／アイトラッカ導入後に拡張", 0, {'bullet': False, 'size': 18}),
], top=Inches(1.8))
add_footer(s)
set_notes(s, "今後の実験計画です。まず学生およそ20名で15分のパイロット実験を行い、客観指標と主観4次元の相関を確認します。次にD'Melloのモデルに基づいて、納得度が下がる区間をどれだけ正確に検出できるかを評価します。さらに将来は、心拍や瞳孔径などの生理指標も加えて拡張していきます。")

# ============================================================
# 13 将来像
# ============================================================
s = add_slide(); add_title(s, "将来像 — 教師支援への応用")
add_body(s, [
    ("最終ゴール：観察室にリアルタイム納得度ヒートマップを提示", 0, {'bold': True, 'bullet': False, 'color': DARK, 'size': 20}),
    ("教師の観察室ビュー上に、学習者ごと・時系列の 納得度ヒートマップ を可視化", 0, {'size': 19}),
    ("納得度が下がった瞬間に教師へフィードバック → その場で説明し直すアシスト機能（assistPolicy）", 0, {'size': 19}),
    ("「測る」研究から「教育現場を支える」システムへ", 0, {'size': 19, 'bold': True, 'color': GREEN}),
], top=Inches(1.9))
add_footer(s)
set_notes(s, "最終的に目指すのは、教師支援です。観察室の画面上に、誰がいつ納得度を下げたかをヒートマップで可視化し、教師がその場で説明をやり直せるようにします。測るだけでなく、教育現場を実際に支えるところまで持っていきたいと考えています。")

# ============================================================
# 14 まとめ
# ============================================================
s = add_slide(); add_title(s, "まとめ")
add_body(s, [
    ("学習の 納得度 は理解・同意・受容・コミットメントの多次元状態だが、従来はリアルタイム・客観的に測れなかった", 0, {'size': 18}),
    ("WebXRのVR教室上に観察室と分析モジュールを実装し、頭部・表情・音声・対話・言語の 5モーダルを自動測定 する基盤を構築", 0, {'size': 18}),
    ("4次元リッカート尺度と照合し、どの指標がどの次元を予測するかを検証（主仮説：認知的不均衡↔理解、うなずき↔同意）", 0, {'size': 18}),
    ("基盤実装とパイロットデータ取得まで前進、これから 検証フェーズ へ", 0, {'size': 18, 'bold': True, 'color': GREEN}),
], top=Inches(1.9))
add_footer(s)
set_notes(s, "まとめます。納得度はリアルタイムに測りにくい多次元の状態でしたが、本研究ではVR教室上に5モーダルを自動計測する基盤を構築し、4次元の主観尺度と照合して妥当性を検証します。基盤とデータ取得は前進しており、これから本格的な検証に入ります。ご清聴ありがとうございました。")

out = "dicomo2026_slides.pptx"
prs.save(out)
print(f"saved: {out}  ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
