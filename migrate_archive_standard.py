# -*- coding: utf-8 -*-
"""
档案国标字段迁移脚本
为 archive_files 表增加符合以下标准的新字段：
  DA/T 18-1999  《档案著录规则》
  DA/T 22-2015  《归档文件整理规则》
  DA/T 31-2005  《纸质档案数字化技术规范》
  DA/T 47-2009  《纸质档案数字化扫描工作规范》

用法：
  python migrate_archive_standard.py
  # 或指定数据库路径
  python migrate_archive_standard.py path/to/ooa.db
"""
import os
import sys
import sqlite3

# ── 强制 UTF-8 输出 ──────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── 定位数据库 ───────────────────────────────────────
def find_db():
    if len(sys.argv) > 1 and sys.argv[1].endswith('.db'):
        return sys.argv[1]
    candidates = [
        os.path.join(os.path.dirname(__file__), 'instance', 'ooa.db'),
        os.path.join(os.path.dirname(__file__), 'ooa.db'),
        os.path.join(os.path.dirname(__file__), 'oa.db'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 搜索同目录
    for root, dirs, files in os.walk(os.path.dirname(__file__) or '.'):
        dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__', '.git')]
        for f in files:
            if f.endswith('.db'):
                return os.path.join(root, f)
    return None

DB_PATH = find_db()
if not DB_PATH:
    print("错误：找不到数据库文件！")
    sys.exit(1)

print(f"数据库路径：{DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── 获取 archive_files 表的已有字段 ───────────────────
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archive_files'")
if not cur.fetchone():
    print("[提示] archive_files 表不存在，将跳过迁移。")
    print("       请先启动 Flask 应用（python app.py）或运行 init_archive_data.py 完成建表后再执行本脚本。")
    conn.close()
    sys.exit(0)

cur.execute("PRAGMA table_info(archive_files)")
existing_cols = {row[1] for row in cur.fetchall()}
print(f"现有字段数量：{len(existing_cols)}")

# ── 需要新增的字段 ────────────────────────────────────
# 格式：(列名, SQLite类型, 注释说明)
NEW_COLUMNS = [
    # ── 完整档号 ─────────────────────────────────────
    ("full_archive_code",   "VARCHAR(100)",    "完整档号（全宗-目录-案卷-件号）"),

    # ── DA/T 18 著录扩展项 ────────────────────────────
    ("abstract",            "TEXT",            "摘要（DA/T18 § 5.8）"),
    ("subject_headings",    "VARCHAR(500)",    "主题词（DA/T18 § 5.7，分号分隔）"),
    ("language",            "VARCHAR(20)",     "语种（DA/T18 § 5.6）"),
    ("related_archives",    "VARCHAR(500)",    "相关档案号"),

    # ── 开放/利用信息 ────────────────────────────────
    ("open_status",         "VARCHAR(20)",     "开放状态（开放/控制使用/不开放）"),
    ("open_date",           "DATE",            "开放日期"),
    ("use_restriction",     "VARCHAR(200)",    "利用限制说明"),

    # ── 物理状况 ─────────────────────────────────────
    ("physical_condition",  "VARCHAR(50)",     "实物状况（良好/一般/破损）"),

    # ── 扫描详细信息（DA/T 47）─────────────────────
    ("scan_device",         "VARCHAR(200)",    "扫描设备型号"),
    ("scan_operator",       "VARCHAR(100)",    "扫描操作员"),
    ("scan_date",           "DATE",            "扫描日期"),

    # ── 多格式文件路径（DA/T 31）──────────────────
    ("tiff_path",           "VARCHAR(500)",    "TIFF归档路径"),
    ("jpeg_path",           "VARCHAR(500)",    "JPEG查阅副本路径"),
    ("pdf_path",            "VARCHAR(500)",    "PDF/A路径"),

    # ── 技术元数据（DA/T 31 § 6）─────────────────
    ("actual_dpi",          "INTEGER",         "实测DPI值"),
    ("compression_type",    "VARCHAR(50)",     "压缩方式"),
    ("image_width",         "INTEGER",         "图像宽度（像素）"),
    ("image_height",        "INTEGER",         "图像高度（像素）"),

    # ── 图像处理（DA/T 47）─────────────────────────
    ("deskew_angle",        "REAL DEFAULT 0.0","纠偏角度（度）"),
    ("border_removed",      "BOOLEAN DEFAULT 0","是否已去黑边"),
    ("enhanced",            "BOOLEAN DEFAULT 0","是否已图像增强"),

    # ── OCR（DA/T 31 § 4.5）───────────────────────
    ("has_ocr_layer",       "BOOLEAN DEFAULT 0","PDF是否含OCR文字层"),
    ("ocr_engine",          "VARCHAR(50)",     "OCR引擎"),
    ("ocr_language",        "VARCHAR(50)",     "OCR识别语言"),
    ("ocr_confidence",      "REAL",            "OCR平均置信度（0-100）"),

    # ── 质检（DA/T 47 § 5）────────────────────────
    ("quality_score",       "INTEGER",         "质量评分（0-100）"),
    ("quality_checked",     "BOOLEAN DEFAULT 0","是否已通过质检"),
    ("quality_checked_at",  "DATETIME",        "质检时间"),
    ("quality_checked_by",  "INTEGER",         "质检人员ID"),
    ("quality_report",      "TEXT",            "质检报告（JSON）"),
    ("dpi_compliant",       "BOOLEAN",         "DPI是否达标（>=300）"),
    ("format_compliant",    "BOOLEAN",         "格式是否合规"),

    # ── 文件完整性（DA/T 31 § 4.6）────────────────
    ("file_checksum",       "VARCHAR(64)",     "文件MD5/SHA256校验值"),
    ("checksum_type",       "VARCHAR(10) DEFAULT 'MD5'", "校验类型"),

    # ── 状态标志 ─────────────────────────────────
    ("is_active",           "BOOLEAN DEFAULT 1","是否有效"),
]

# ── 执行迁移 ─────────────────────────────────────────
added   = []
skipped = []
failed  = []

for col_name, col_type, comment in NEW_COLUMNS:
    if col_name in existing_cols:
        skipped.append(col_name)
        continue
    try:
        cur.execute(f"ALTER TABLE archive_files ADD COLUMN {col_name} {col_type}")
        added.append(col_name)
        print(f"  ✅ 新增：archive_files.{col_name}  [{comment}]")
    except Exception as e:
        failed.append((col_name, str(e)))
        print(f"  ❌ 失败：archive_files.{col_name} — {e}")

# ── 创建索引 ─────────────────────────────────────────
INDEXES = [
    ("idx_af_full_code",    "archive_files(full_archive_code)"),
    ("idx_af_quality",      "archive_files(quality_checked, quality_score)"),
    ("idx_af_dpi",          "archive_files(dpi_compliant)"),
    ("idx_af_retention",    "archive_files(retention_period)"),
    ("idx_af_security",     "archive_files(security_level)"),
    ("idx_af_open_status",  "archive_files(open_status)"),
    ("idx_af_ref",          "archive_files(reference_number)"),
]

print("\n── 创建索引 ──────────────────────────────────")
for idx_name, idx_def in INDEXES:
    try:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
        print(f"  ✅ 索引：{idx_name}")
    except Exception as e:
        print(f"  ❌ 索引失败：{idx_name} — {e}")

conn.commit()
conn.close()

# ── 迁移摘要 ─────────────────────────────────────────
print("\n" + "=" * 50)
print(f"迁移完成！")
print(f"  新增字段：{len(added)} 个")
print(f"  已存在跳过：{len(skipped)} 个")
print(f"  失败：{len(failed)} 个")
if failed:
    for col, err in failed:
        print(f"    ✗ {col}: {err}")
print("=" * 50)
print("\n✔ 数据库已准备好，可以正常运行档案数字化系统。")
