# -*- coding: utf-8 -*-
"""
档案质量自动检验模块
符合以下标准：
  DA/T 47-2009 《纸质档案数字化扫描工作规范》§ 5 质量控制
  DA/T 31-2005 《纸质档案数字化技术规范》§ 5.3 质量检验
  DA/T 62-2017 《电子档案管理系统基本功能规定》

质检维度：
  1. 图像技术指标（DPI / 色彩 / 格式）
  2. 文件完整性（校验和 / 文件存在性）
  3. OCR文字层（是否嵌入 / 置信度）
  4. 元数据完整性（国标必填项）
  5. 档号合规性（命名格式）
  6. 命名规范符合度
"""
import os
import io
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ── 国标阈值配置 ──────────────────────────────
STANDARD = {
    'MIN_DPI': 300,              # DA/T 47 最低分辨率
    'RECOMMENDED_DPI': 400,      # 推荐分辨率
    'MAX_SKEW_ANGLE': 2.0,       # 最大允许倾斜角（度）
    'MIN_QUALITY_SCORE': 80,     # 最低质量分（满分100）
    'MIN_OCR_CONFIDENCE': 60.0,  # 最低OCR置信度
    'REQUIRED_FORMATS': ['tiff', 'tif', 'pdf'],  # 必须有其中一种
    'METADATA_REQUIRED': [       # 必填元数据项
        'title', 'responsibility', 'file_date',
        'retention_period', 'archive_type',
    ],
}

# 质检结果等级
GRADE_MAP = {
    range(90, 101): 'A',   # 优
    range(75, 90):  'B',   # 良
    range(60, 75):  'C',   # 合格
    range(0, 60):   'D',   # 不合格
}


class QualityCheckResult:
    """单项质检结果"""

    def __init__(self, item: str, passed: bool, score: int,
                 detail: str = '', suggestion: str = ''):
        self.item = item          # 检测项名称
        self.passed = passed      # 是否通过
        self.score = score        # 得分（0-100）
        self.detail = detail      # 详细说明
        self.suggestion = suggestion  # 整改建议
        self.checked_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            'item': self.item,
            'passed': self.passed,
            'score': self.score,
            'detail': self.detail,
            'suggestion': self.suggestion,
            'checked_at': self.checked_at.isoformat(),
        }


class ArchiveQualityChecker:
    """
    档案数字化质量自动检验器
    
    检验流程：
    ┌─────────────────────────────────────────┐
    │  1. 图像技术指标检查                      │
    │  2. 文件完整性校验                        │
    │  3. 格式合规检查                          │
    │  4. OCR文字层检查                         │
    │  5. 元数据完整性检查                      │
    │  6. 档号命名规范检查                      │
    │  7. 综合评分与报告生成                    │
    └─────────────────────────────────────────┘
    """

    def __init__(self):
        pass

    # ══════════════════════════════════════════
    # 主入口：全面质检
    # ══════════════════════════════════════════

    def check_archive(self, archive_file) -> dict:
        """
        对单份档案进行全面质量检验

        Args:
            archive_file: ArchiveFile模型实例

        Returns:
            完整质检报告 dict
        """
        report = {
            'archive_id': archive_file.id,
            'archive_code': archive_file.get_archive_code() if hasattr(archive_file, 'get_archive_code') else '',
            'title': archive_file.title,
            'checked_at': datetime.now().isoformat(),
            'checks': [],
            'total_score': 0,
            'grade': 'D',
            'passed': False,
            'summary': '',
            'critical_issues': [],
            'suggestions': [],
        }

        checks = []

        # 1. 图像技术指标
        checks.append(self._check_image_tech(archive_file))

        # 2. 文件完整性
        checks.append(self._check_file_integrity(archive_file))

        # 3. 格式合规性
        checks.append(self._check_format_compliance(archive_file))

        # 4. OCR文字层
        checks.append(self._check_ocr_layer(archive_file))

        # 5. 元数据完整性
        checks.append(self._check_metadata(archive_file))

        # 6. 档号命名规范
        checks.append(self._check_naming(archive_file))

        # 7. 图像质量（如有TIFF）
        if getattr(archive_file, 'tiff_path', None) or getattr(archive_file, 'file_path', None):
            checks.append(self._check_image_quality(archive_file))

        # 汇总
        report['checks'] = [c.to_dict() for c in checks]

        # 加权评分
        total = self._calculate_total_score(checks)
        report['total_score'] = total
        report['grade'] = self._get_grade(total)
        report['passed'] = total >= STANDARD['MIN_QUALITY_SCORE']

        # 问题汇总
        critical = [c.detail for c in checks if not c.passed and c.score == 0]
        suggestions = [c.suggestion for c in checks if c.suggestion and not c.passed]
        report['critical_issues'] = critical
        report['suggestions'] = list(set(suggestions))

        # 生成摘要
        report['summary'] = self._generate_summary(report)

        return report

    def check_batch(self, archive_files: list) -> dict:
        """
        批量质检

        Returns:
            {
                total, passed, failed, avg_score,
                grade_distribution: {A, B, C, D},
                files: [report],
                batch_summary: str
            }
        """
        reports = []
        grade_dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        scores = []

        for af in archive_files:
            try:
                r = self.check_archive(af)
                reports.append(r)
                scores.append(r['total_score'])
                grade = r.get('grade', 'D')
                grade_dist[grade] = grade_dist.get(grade, 0) + 1
            except Exception as e:
                logger.error(f"质检失败 {getattr(af, 'id', '?')}: {e}")
                reports.append({'archive_id': getattr(af, 'id', '?'), 'error': str(e)})

        passed_count = sum(1 for r in reports if r.get('passed', False))
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            'total': len(archive_files),
            'passed': passed_count,
            'failed': len(archive_files) - passed_count,
            'pass_rate': f"{passed_count / len(archive_files) * 100:.1f}%" if archive_files else '0%',
            'avg_score': round(avg_score, 1),
            'grade_distribution': grade_dist,
            'files': reports,
            'batch_summary': (
                f"共检验{len(archive_files)}份档案，"
                f"通过{passed_count}份，"
                f"不合格{len(archive_files) - passed_count}份，"
                f"平均得分{avg_score:.1f}分"
            ),
            'generated_at': datetime.now().isoformat(),
        }

    # ══════════════════════════════════════════
    # 各项检验
    # ══════════════════════════════════════════

    def _check_image_tech(self, af) -> QualityCheckResult:
        """检验图像技术指标（DPI / 色彩模式 / 倾斜角）"""
        issues = []
        score = 100

        # DPI检查（DA/T 47 § 4.1）
        dpi = getattr(af, 'actual_dpi', None) or int(getattr(af, 'scan_resolution', '0') or 0)
        if dpi == 0:
            issues.append("未记录实际DPI值")
            score -= 20
        elif dpi < STANDARD['MIN_DPI']:
            issues.append(f"DPI={dpi}，低于国标最低要求{STANDARD['MIN_DPI']}DPI")
            score -= 40
        elif dpi < STANDARD['RECOMMENDED_DPI']:
            issues.append(f"DPI={dpi}，建议提升至{STANDARD['RECOMMENDED_DPI']}DPI以上")
            score -= 10

        # 倾斜角检查
        angle = abs(getattr(af, 'deskew_angle', 0) or 0)
        if angle > STANDARD['MAX_SKEW_ANGLE']:
            issues.append(f"倾斜角{angle:.1f}°超过允许范围{STANDARD['MAX_SKEW_ANGLE']}°")
            score -= 20

        # 色彩模式
        color_mode = getattr(af, 'color_mode', '') or ''
        if not color_mode:
            issues.append("未记录色彩模式")
            score -= 5

        passed = score >= 60
        detail = '；'.join(issues) if issues else f"DPI={dpi}，达标"
        suggestion = "建议重新扫描，设置分辨率≥300DPI" if dpi < STANDARD['MIN_DPI'] else ''

        return QualityCheckResult(
            item='图像技术指标（DPI/色彩/倾斜）',
            passed=passed,
            score=max(0, score),
            detail=detail,
            suggestion=suggestion,
        )

    def _check_file_integrity(self, af) -> QualityCheckResult:
        """检验文件完整性（文件存在 + MD5校验）"""
        issues = []
        score = 100

        # 主文件是否存在
        main_path = getattr(af, 'tiff_path', None) or getattr(af, 'file_path', None)
        if not main_path:
            issues.append("无主文件路径记录")
            score -= 50
        elif not os.path.exists(main_path):
            issues.append(f"主文件不存在: {os.path.basename(main_path)}")
            score -= 50

        # PDF文件
        pdf_path = getattr(af, 'pdf_path', None)
        if pdf_path and not os.path.exists(pdf_path):
            issues.append(f"PDF文件不存在: {os.path.basename(pdf_path)}")
            score -= 20

        # 校验和验证
        checksum = getattr(af, 'file_checksum', None)
        if not checksum:
            issues.append("未生成文件校验和，无法验证完整性")
            score -= 10
        elif main_path and os.path.exists(main_path):
            actual_md5 = self._calculate_md5(main_path)
            if actual_md5 != checksum:
                issues.append(f"文件校验失败：预期{checksum[:8]}…，实际{actual_md5[:8]}…")
                score = 0  # 文件损坏，0分

        passed = score >= 60
        detail = '；'.join(issues) if issues else "文件完整，校验通过"
        suggestion = "请检查存储路径，重新生成校验和" if issues else ''

        return QualityCheckResult(
            item='文件完整性校验',
            passed=passed,
            score=max(0, score),
            detail=detail,
            suggestion=suggestion,
        )

    def _check_format_compliance(self, af) -> QualityCheckResult:
        """检验格式合规性（需有TIFF或PDF/A）"""
        issues = []
        score = 0

        has_tiff = bool(getattr(af, 'tiff_path', None))
        has_pdf = bool(getattr(af, 'pdf_path', None))
        file_format = (getattr(af, 'file_format', '') or '').lower()

        if has_tiff or file_format in ('tiff', 'tif'):
            score += 60  # TIFF是国标首选格式
        if has_pdf:
            score += 30  # PDF/A作为流通格式
        if has_tiff and has_pdf:
            score += 10  # 双格式加分

        if not has_tiff and file_format not in ('tiff', 'tif'):
            issues.append("未保存TIFF格式（DA/T 31规定首选格式）")
        if not has_pdf:
            issues.append("未生成PDF格式（不便于查阅利用）")

        # JPEG查阅副本
        has_jpeg = bool(getattr(af, 'jpeg_path', None))
        if not has_jpeg:
            issues.append("未生成JPEG查阅副本")

        passed = score >= 60
        detail = '；'.join(issues) if issues else "TIFF+PDF双格式齐全"
        suggestion = "请生成TIFF归档格式和PDF/A查阅格式" if not passed else ''

        return QualityCheckResult(
            item='格式合规性（TIFF/PDF/A）',
            passed=passed,
            score=min(100, score),
            detail=detail,
            suggestion=suggestion,
        )

    def _check_ocr_layer(self, af) -> QualityCheckResult:
        """检验OCR文字层（是否嵌入 + 置信度）"""
        issues = []
        score = 100

        # 判断是否数字化文件
        is_digitized = getattr(af, 'is_digitized', False)
        file_format = (getattr(af, 'file_format', '') or '').lower()
        is_image = file_format in ('tiff', 'tif', 'jpg', 'jpeg', 'png', 'bmp')
        pdf_path = getattr(af, 'pdf_path', None)

        # 如果是原生PDF文档（非扫描件），跳过此项
        if not is_digitized and file_format == 'pdf':
            return QualityCheckResult(
                item='OCR文字层（扫描图像）',
                passed=True,
                score=100,
                detail='原生PDF文档，无需OCR检测',
            )

        # 检查OCR层
        has_ocr = getattr(af, 'has_ocr_layer', False)
        ocr_conf = getattr(af, 'ocr_confidence', None)

        if not has_ocr:
            issues.append("PDF中未嵌入OCR文字层，文字不可检索")
            score -= 50

            # 实时检测（如果PDF存在）
            if pdf_path and os.path.exists(pdf_path) and PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(pdf_path)
                    has_text = any(page.get_text().strip() for page in doc)
                    doc.close()
                    if has_text:
                        has_ocr = True
                        issues = [i for i in issues if 'OCR文字层' not in i]
                        score += 40
                except Exception:
                    pass

        if ocr_conf is not None and ocr_conf < STANDARD['MIN_OCR_CONFIDENCE']:
            issues.append(f"OCR置信度{ocr_conf:.1f}%，低于要求{STANDARD['MIN_OCR_CONFIDENCE']}%")
            score -= 20

        passed = score >= 60
        detail = '；'.join(issues) if issues else f"OCR文字层已嵌入，置信度{ocr_conf or 'N/A'}"
        suggestion = "请使用Tesseract重新生成带OCR层的PDF" if not has_ocr else ''

        return QualityCheckResult(
            item='OCR文字层',
            passed=passed,
            score=max(0, score),
            detail=detail,
            suggestion=suggestion,
        )

    def _check_metadata(self, af) -> QualityCheckResult:
        """检验元数据完整性（DA/T 18必填项）"""
        REQUIRED_FIELDS = {
            'title': '题名',
            'responsibility': '责任者',
            'file_date': '文件日期',
            'retention_period': '保管期限',
            'archive_type': '档案类型',
            'full_archive_code': '完整档号',
        }

        RECOMMENDED_FIELDS = {
            'abstract': '摘要',
            'subject_headings': '主题词',
            'reference_number': '文号',
            'language': '语种',
            'security_level': '密级',
        }

        missing_required = []
        missing_recommended = []

        for field, label in REQUIRED_FIELDS.items():
            val = getattr(af, field, None)
            if not val or (isinstance(val, str) and not val.strip()):
                missing_required.append(label)

        for field, label in RECOMMENDED_FIELDS.items():
            val = getattr(af, field, None)
            if not val or (isinstance(val, str) and not val.strip()):
                missing_recommended.append(label)

        # 计算分数
        total_required = len(REQUIRED_FIELDS)
        filled_required = total_required - len(missing_required)
        score = int(filled_required / total_required * 80)  # 必填占80分

        total_recommended = len(RECOMMENDED_FIELDS)
        filled_recommended = total_recommended - len(missing_recommended)
        score += int(filled_recommended / total_recommended * 20)  # 推荐占20分

        passed = len(missing_required) == 0

        if missing_required:
            detail = f"缺少必填字段：{'、'.join(missing_required)}"
        elif missing_recommended:
            detail = f"可补充推荐字段：{'、'.join(missing_recommended)}"
        else:
            detail = "元数据完整，符合DA/T 18著录规则"

        suggestion = f"请补充以下必填字段：{'、'.join(missing_required)}" if missing_required else ''

        return QualityCheckResult(
            item='元数据完整性（DA/T 18）',
            passed=passed,
            score=min(100, score),
            detail=detail,
            suggestion=suggestion,
        )

    def _check_naming(self, af) -> QualityCheckResult:
        """检验档号命名规范性"""
        from archive_naming import archive_naming

        archive_code = getattr(af, 'full_archive_code', None) or \
                       (af.get_archive_code() if hasattr(af, 'get_archive_code') else '')

        if not archive_code:
            return QualityCheckResult(
                item='档号命名规范',
                passed=False,
                score=0,
                detail='无档号记录',
                suggestion='请按全宗号-目录号-案卷号-件号格式生成档号',
            )

        validation = archive_naming.validate_archive_code(archive_code)
        score = 100 if validation['valid'] else 40

        if validation['errors']:
            score -= 40 * len(validation['errors'])
        if validation['warnings']:
            score -= 10 * len(validation['warnings'])

        detail = '；'.join(validation['errors'] + validation['warnings']) \
                 if (validation['errors'] or validation['warnings']) \
                 else f"档号格式合规：{archive_code}"

        return QualityCheckResult(
            item='档号命名规范（DA/T 18）',
            passed=validation['valid'],
            score=max(0, min(100, score)),
            detail=detail,
            suggestion='请参照DA/T 18-1999规范调整档号格式' if not validation['valid'] else '',
        )

    def _check_image_quality(self, af) -> QualityCheckResult:
        """检验图像视觉质量（清晰度 / 完整性）"""
        if not PIL_AVAILABLE:
            return QualityCheckResult(
                item='图像视觉质量',
                passed=True,
                score=70,
                detail='Pillow未安装，跳过图像质量检测',
            )

        img_path = getattr(af, 'tiff_path', None) or getattr(af, 'file_path', None)
        if not img_path or not os.path.exists(img_path):
            return QualityCheckResult(
                item='图像视觉质量',
                passed=False,
                score=0,
                detail='图像文件不存在，无法检测质量',
                suggestion='请检查文件路径是否正确',
            )

        try:
            img = Image.open(img_path)
            issues = []
            score = 100

            # 尺寸检查（A4纸 300DPI = 2480×3508px）
            w, h = img.size
            if w < 800 or h < 800:
                issues.append(f"图像分辨率过低（{w}×{h}px）")
                score -= 30

            # 色彩深度
            if img.mode == '1':
                # 二值图质量检查：查看黑白比例
                pass  # 合理，不减分
            elif img.mode in ('RGB', 'L'):
                pass  # 正常

            # 文件大小异常（可能是空文件或截断）
            file_size = os.path.getsize(img_path)
            expected_min = w * h * 0.1  # 预期最小（有压缩）
            if file_size < 1024:
                issues.append("文件体积异常小，可能是空文件或损坏")
                score -= 50

            # 已有quality_score时直接采用
            stored_score = getattr(af, 'quality_score', None)
            if stored_score is not None:
                score = stored_score

            passed = score >= 70
            detail = '；'.join(issues) if issues else f"图像质量良好（{w}×{h}px）"

            return QualityCheckResult(
                item='图像视觉质量',
                passed=passed,
                score=max(0, score),
                detail=detail,
                suggestion='建议重新扫描或进行图像增强处理' if not passed else '',
            )

        except Exception as e:
            return QualityCheckResult(
                item='图像视觉质量',
                passed=False,
                score=0,
                detail=f"无法打开图像：{str(e)}",
                suggestion='文件可能已损坏，请重新扫描',
            )

    # ══════════════════════════════════════════
    # 评分 / 报告
    # ══════════════════════════════════════════

    def _calculate_total_score(self, checks: list) -> int:
        """
        加权计算总分

        权重：
          图像技术指标    20%
          文件完整性      20%
          格式合规性      20%
          OCR文字层       15%
          元数据完整性    15%
          档号命名        10%
        """
        WEIGHTS = {
            '图像技术指标（DPI/色彩/倾斜）': 0.20,
            '文件完整性校验': 0.20,
            '格式合规性（TIFF/PDF/A）': 0.20,
            'OCR文字层': 0.15,
            '元数据完整性（DA/T 18）': 0.15,
            '档号命名规范（DA/T 18）': 0.10,
        }
        EXTRA_WEIGHT = 0.10  # 图像视觉质量

        total = 0.0
        weight_used = 0.0

        for check in checks:
            item = check.item
            w = WEIGHTS.get(item, EXTRA_WEIGHT)
            total += check.score * w
            weight_used += w

        # 归一化到100分
        if weight_used > 0:
            total = total / weight_used

        return min(100, max(0, round(total)))

    def _get_grade(self, score: int) -> str:
        """根据分数获取等级"""
        for score_range, grade in GRADE_MAP.items():
            if score in score_range:
                return grade
        return 'D'

    def _generate_summary(self, report: dict) -> str:
        """生成质检摘要文本"""
        score = report['total_score']
        grade = report['grade']
        passed = report['passed']
        critical = report.get('critical_issues', [])

        grade_names = {'A': '优（A）', 'B': '良（B）', 'C': '合格（C）', 'D': '不合格（D）'}
        status = "通过质检" if passed else "未通过质检"

        summary = f"综合评分 {score} 分，等级 {grade_names.get(grade, grade)}，{status}。"

        if critical:
            summary += f" 严重问题：{'；'.join(critical[:3])}"

        return summary

    # ══════════════════════════════════════════
    # 工具函数
    # ══════════════════════════════════════════

    def _calculate_md5(self, file_path: str) -> str:
        """计算文件MD5"""
        h = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
        except Exception:
            return ''
        return h.hexdigest()

    def calculate_file_checksum(self, file_path: str, algorithm: str = 'MD5') -> str:
        """计算文件校验和（供外部调用）"""
        if algorithm == 'MD5':
            return self._calculate_md5(file_path)
        elif algorithm in ('SHA256', 'SHA-256'):
            h = hashlib.sha256()
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                return h.hexdigest()
            except Exception:
                return ''
        return ''

    def generate_quality_report_json(self, report: dict) -> str:
        """将质检报告序列化为JSON字符串（用于存入数据库）"""
        try:
            return json.dumps(report, ensure_ascii=False, default=str)
        except Exception:
            return '{}'

    def save_report_to_archive(self, af, db_session) -> bool:
        """
        执行质检并将结果保存到档案模型

        Args:
            af: ArchiveFile实例
            db_session: SQLAlchemy db.session
        """
        from datetime import datetime
        try:
            report = self.check_archive(af)

            af.quality_score = report['total_score']
            af.quality_checked = report['passed']
            af.quality_checked_at = datetime.now()
            af.quality_report = self.generate_quality_report_json(report)
            af.dpi_compliant = any(
                c['item'] == '图像技术指标（DPI/色彩/倾斜）' and c['passed']
                for c in report.get('checks', [])
            )
            af.format_compliant = any(
                c['item'] == '格式合规性（TIFF/PDF/A）' and c['passed']
                for c in report.get('checks', [])
            )

            # 计算校验和（如主文件存在）
            main_path = getattr(af, 'tiff_path', None) or getattr(af, 'file_path', None)
            if main_path and os.path.exists(main_path) and not af.file_checksum:
                af.file_checksum = self._calculate_md5(main_path)
                af.checksum_type = 'MD5'

            db_session.commit()
            return True

        except Exception as e:
            logger.error(f"保存质检结果失败: {e}", exc_info=True)
            db_session.rollback()
            return False


# 全局实例
archive_quality_checker = ArchiveQualityChecker()
