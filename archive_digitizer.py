# -*- coding: utf-8 -*-
"""
档案数字化处理模块 - 国标合规增强版
复用知识库的智能处理功能，并集成图像处理/OCR/质检/命名规范模块
符合档案国家标准：DA/T 18 / DA/T 22 / DA/T 31 / DA/T 47
"""
import os
import re
import shutil
import hashlib
import logging
from datetime import datetime
from flask import current_app
from models import db
from archive_models import ArchiveFile, ArchiveVolume, ArchiveFonds, ArchiveCatalog
from smart_knowledge import smart_kb
from archive_image_processor import archive_image_processor
from archive_naming import archive_naming
from archive_quality_checker import archive_quality_checker

logger = logging.getLogger(__name__)


class ArchiveDigitizer:
    """
    档案数字化处理器 - 国标合规版
    
    处理流水线：
    ┌─────────────────────────────────────────────────────────┐
    │  1. 智能内容提取（知识库）                               │
    │  2. 图像处理（TIFF存储/纠偏/去黑边/OCR，新增）          │
    │  3. 智能分析（关键词/摘要/标签，知识库）                 │
    │  4. 档案属性识别（类型/期限/日期，规则引擎）             │
    │  5. 国标命名（DA/T 18档号生成，新增）                   │
    │  6. 国标元数据补全（新增）                              │
    │  7. 文件存储（按全宗/目录/年度分层）                    │
    │  8. 向量化（知识库检索，知识库）                        │
    │  9. 自动质检（DA/T 47，新增）                          │
    │ 10. 入库                                               │
    └─────────────────────────────────────────────────────────┘
    """

    # 档案类型自动识别规则
    ARCHIVE_TYPE_RULES = {
        '文书档案': ['通知', '通报', '报告', '请示', '批复', '函', '会议纪要', '决定', '意见'],
        '科技档案': ['设计', '施工', '竣工', '图纸', '技术', '研发', '项目', '工程'],
        '会计档案': ['凭证', '账簿', '报表', '发票', '收据', '审计', '财务'],
        '声像档案': ['照片', '录音', '录像', '视频', '音频', '影像'],
        '人事档案': ['简历', '考核', '任免', '奖惩', '培训', '职称'],
        '合同档案': ['合同', '协议', '备忘录', '意向书'],
    }

    # 保管期限识别规则
    RETENTION_RULES = {
        '永久': ['章程', '制度', '规划', '总结', '年报', '重要', '历史性'],
        '30年': ['计划', '报告', '请示', '批复', '合同', '协议'],
        '10年': ['通知', '通报', '简报', '临时', '一般'],
    }

    # 图像格式列表（需要图像处理流程）
    IMAGE_FORMATS = {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp', 'gif'}
    PDF_FORMAT = 'pdf'

    def __init__(self):
        self.smart_kb = smart_kb
        self.image_processor = archive_image_processor
        self.naming = archive_naming
        self.quality_checker = archive_quality_checker

    def process_digitization(self, file_path, fonds_id, catalog_id, volume_id=None,
                             uploader_id=None, metadata=None,
                             enable_image_processing=True,
                             enable_quality_check=True):
        """
        处理单份档案的完整数字化流程

        Args:
            file_path:               上传的文件路径
            fonds_id:                全宗ID
            catalog_id:              目录ID
            volume_id:               案卷ID（可选）
            uploader_id:             上传者ID
            metadata:                人工录入的元数据
            enable_image_processing: 是否启用图像处理（纠偏/TIFF存储等）
            enable_quality_check:    是否自动质检

        Returns:
            ArchiveFile 对象 或 {'error': str}
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            is_image = file_ext in self.IMAGE_FORMATS
            is_pdf = file_ext == self.PDF_FORMAT

            # ── Step 1: 内容提取（复用知识库）──────────────
            content_text = self.smart_kb.extract_content(file_path)

            # ── Step 2: 智能分析（复用知识库）──────────────
            keywords_list = self.smart_kb.generate_keywords(content_text, top_k=15)
            summary = self.smart_kb.generate_summary(content_text, max_length=300)
            tags_list = self.smart_kb.auto_tag(content_text)
            suggested_title = self.smart_kb.suggest_title(
                content_text, os.path.basename(file_path)
            )

            # ── Step 3: 智能识别档案属性 ────────────────────
            archive_type = self._detect_archive_type(content_text, tags_list)
            retention_period = self._detect_retention_period(content_text, tags_list)
            file_date = self._extract_date(content_text, metadata)
            responsibility = self._extract_responsibility(content_text, metadata)

            # ── Step 4: 件号 / 档号生成 ─────────────────────
            file_seq_num = self._get_next_seq(catalog_id, volume_id)
            file_code = f"{file_seq_num:04d}"

            fonds = ArchiveFonds.query.get(fonds_id)
            catalog = ArchiveCatalog.query.get(catalog_id)
            volume = ArchiveVolume.query.get(volume_id) if volume_id else None

            full_archive_code = self.naming.generate_archive_code(
                fonds_code=fonds.fonds_code if fonds else str(fonds_id),
                catalog_code=catalog.catalog_code if catalog else str(catalog_id),
                volume_code=volume.volume_code if volume else str(datetime.now().year),
                file_seq=file_seq_num,
                retention=retention_period,
                security=metadata.get('security_level', '公开') if metadata else '公开',
            )

            # ── Step 5: 图像处理（TIFF/纠偏/去黑边/OCR）──────
            tiff_path = None
            jpeg_path = None
            pdf_path = None
            actual_dpi = int(metadata.get('scan_resolution', '300') if metadata else '300')
            deskew_angle = 0.0
            border_removed = False
            has_ocr_layer = False
            color_mode_str = '彩色'
            quality_score = 0

            if enable_image_processing:
                if is_image:
                    img_result = self.image_processor.process_image(
                        source_path=file_path,
                        file_code=full_archive_code.replace('-', '_'),
                        enable_deskew=True,
                        enable_border_removal=True,
                        target_dpi=max(actual_dpi, 300),
                        color_mode='auto',
                    )
                    tiff_path = img_result.get('tiff_path')
                    jpeg_path = img_result.get('jpeg_path')
                    pdf_path = img_result.get('pdf_path')
                    actual_dpi = img_result.get('dpi') or actual_dpi
                    deskew_angle = img_result.get('deskew_angle', 0.0)
                    color_mode_str = img_result.get('color_mode', '彩色')
                    quality_score = img_result.get('quality_score', 0)
                    border_removed = True  # 已执行去黑边

                elif is_pdf:
                    pdf_result = self.image_processor.process_pdf(
                        pdf_path=file_path,
                        file_code=full_archive_code.replace('-', '_'),
                        enable_ocr=True,
                    )
                    pdf_path = pdf_result.get('pdf_a_path', file_path)
                    has_ocr_layer = pdf_result.get('has_ocr', False)

            # ── Step 6: 文件存储 ──────────────────────────────
            year = file_date.year if file_date else datetime.now().year
            storage_dir = self.naming.generate_storage_path(
                fonds_code=fonds.fonds_code if fonds else str(fonds_id),
                catalog_code=catalog.catalog_code if catalog else str(catalog_id),
                year=year,
                archive_code=full_archive_code,
                base_dir=current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            )

            # 主存储文件（优先TIFF，其次PDF，最后原文件）
            if tiff_path and os.path.exists(tiff_path):
                main_path = tiff_path  # TIFF已在archive_images目录，直接使用
                file_format = 'TIFF'
            elif pdf_path and os.path.exists(pdf_path):
                main_path = pdf_path
                file_format = 'PDF'
            else:
                # 原始文件复制到归档目录
                archive_filename = self.naming.generate_filename(
                    full_archive_code, file_ext
                )
                main_path = os.path.join(storage_dir, archive_filename)
                shutil.copy2(file_path, main_path)
                file_format = file_ext.upper()

            # 计算文件大小和校验和
            file_size = os.path.getsize(main_path) if os.path.exists(main_path) else 0
            file_checksum = self._calc_md5(main_path) if os.path.exists(main_path) else ''

            # ── Step 7: 向量化（复用知识库）────────────────────
            vector = self.smart_kb.generate_embedding(content_text)

            # ── Step 8: 构建元数据（含国标必填项）──────────────
            meta = metadata or {}
            title = meta.get('title') or suggested_title
            responsibility_val = meta.get('responsibility') or responsibility
            ret_period = meta.get('retention_period') or retention_period
            sec_level = meta.get('security_level', '公开')
            arch_type = meta.get('archive_type') or archive_type
            page_count = meta.get('page_count') or self._estimate_page_count(
                file_path, file_ext, len(content_text) if content_text else 0
            )

            # ── Step 9: 入库 ──────────────────────────────────
            archive_file = ArchiveFile(
                fonds_id=fonds_id,
                catalog_id=catalog_id,
                volume_id=volume_id,
                file_code=file_code,
                full_archive_code=full_archive_code,

                # 国标核心著录项
                title=title,
                responsibility=responsibility_val,
                file_date=file_date,
                file_year=year,
                retention_period=ret_period,
                security_level=sec_level,
                archive_type=arch_type,
                page_count=page_count,
                language=meta.get('language', '中文'),
                reference_number=meta.get('reference_number', ''),
                abstract=summary,
                subject_headings=';'.join(keywords_list[:5]) if keywords_list else '',

                # 物理属性
                carrier_type='数字',
                storage_location=meta.get('storage_location', ''),
                open_status=meta.get('open_status', '开放'),

                # 数字化信息
                is_digitized=True,
                digitized_at=datetime.utcnow(),
                digitized_by=uploader_id,
                scan_date=datetime.now().date(),
                scan_resolution=str(actual_dpi),
                actual_dpi=actual_dpi,
                color_mode=color_mode_str,

                # 文件路径（多格式）
                original_filename=os.path.basename(file_path),
                file_path=main_path,
                tiff_path=tiff_path,
                jpeg_path=jpeg_path,
                pdf_path=pdf_path,
                file_size=file_size,
                file_format=file_format,
                file_checksum=file_checksum,
                checksum_type='MD5',

                # 图像处理信息
                deskew_angle=deskew_angle,
                border_removed=border_removed,
                enhanced=is_image and enable_image_processing,

                # OCR
                has_ocr_layer=has_ocr_layer or bool(pdf_path),
                ocr_engine='tesseract' if has_ocr_layer else '',
                ocr_language='chi_sim+eng',

                # 智能提取内容
                content_text=content_text,
                summary=summary,
                keywords=','.join(keywords_list),
                tags=','.join(tags_list),
                embedding=vector.tobytes() if vector is not None else None,
                is_vectorized=vector is not None,

                # 质量
                quality_score=quality_score,

                # 附注
                description=meta.get('description', ''),
                created_by=uploader_id,
                status='active',
                is_active=True,
            )

            db.session.add(archive_file)
            db.session.flush()  # 先获取ID

            # ── Step 10: 自动质检 ───────────────────────────
            if enable_quality_check:
                self.quality_checker.save_report_to_archive(archive_file, db.session)
            else:
                db.session.commit()

            # 更新统计
            self._update_statistics(fonds_id, catalog_id, volume_id)

            logger.info(f"档案数字化完成: {full_archive_code} | 质检分: {archive_file.quality_score}")
            return archive_file

        except Exception as e:
            db.session.rollback()
            logger.error(f"数字化处理失败: {e}", exc_info=True)
            return {'error': str(e)}

    def process_batch(self, file_paths, fonds_id, catalog_id, volume_id=None,
                     uploader_id=None, progress_callback=None,
                     enable_image_processing=True,
                     enable_quality_check=True):
        """
        批量数字化处理

        Returns:
            dict: {
                success: [ArchiveFile],
                failed: [{file, error}],
                quality_summary: {avg_score, passed_count, ...}
            }
        """
        results = {'success': [], 'failed': [], 'quality_summary': {}}
        total = len(file_paths)
        quality_scores = []

        for i, file_path in enumerate(file_paths, 1):
            if progress_callback:
                progress_callback(i, total, os.path.basename(file_path))

            result = self.process_digitization(
                file_path, fonds_id, catalog_id, volume_id, uploader_id,
                enable_image_processing=enable_image_processing,
                enable_quality_check=enable_quality_check,
            )

            if isinstance(result, ArchiveFile):
                results['success'].append(result)
                if result.quality_score:
                    quality_scores.append(result.quality_score)
            else:
                results['failed'].append({
                    'file': os.path.basename(file_path),
                    'error': result.get('error', '未知错误')
                })

        # 质检汇总
        if quality_scores:
            results['quality_summary'] = {
                'avg_score': round(sum(quality_scores) / len(quality_scores), 1),
                'passed_count': sum(1 for s in quality_scores if s >= 80),
                'total_checked': len(quality_scores),
            }

        return results

    def run_quality_check_on_archive(self, archive_file_id: int) -> dict:
        """
        对已有档案重新执行质检

        Returns:
            质检报告 dict
        """
        af = ArchiveFile.query.get(archive_file_id)
        if not af:
            return {'error': '档案不存在'}

        report = self.quality_checker.check_archive(af)
        self.quality_checker.save_report_to_archive(af, db.session)
        return report

    def run_batch_quality_check(self, fonds_id=None, catalog_id=None,
                                 unchecked_only=True) -> dict:
        """
        批量执行质检

        Args:
            fonds_id:       限定全宗
            catalog_id:     限定目录
            unchecked_only: 只检查未质检的文件

        Returns:
            批量质检报告
        """
        query = ArchiveFile.query.filter_by(status='active')
        if fonds_id:
            query = query.filter_by(fonds_id=fonds_id)
        if catalog_id:
            query = query.filter_by(catalog_id=catalog_id)
        if unchecked_only:
            query = query.filter_by(quality_checked=False)

        archives = query.all()
        return self.quality_checker.check_batch(archives)

    def search_archives(self, query, fonds_id=None, catalog_id=None,
                       archive_type=None, year=None, top_k=20):
        """
        智能检索档案

        注意：档案检索必须基于 ArchiveFile，而不是知识库的 KnowledgeFile。
        这里统一走档案表的关键词检索，并做一个轻量相关度排序，避免结果结构错乱。
        """
        query = (query or '').strip()
        if not query:
            return []

        archive_query = ArchiveFile.query.filter(ArchiveFile.status == 'active')

        if fonds_id:
            archive_query = archive_query.filter_by(fonds_id=fonds_id)
        if catalog_id:
            archive_query = archive_query.filter_by(catalog_id=catalog_id)
        if archive_type:
            archive_query = archive_query.filter_by(archive_type=archive_type)
        if year:
            archive_query = archive_query.filter_by(file_year=year)

        search_pattern = f"%{query}%"
        archives = archive_query.filter(
            db.or_(
                ArchiveFile.title.like(search_pattern),
                ArchiveFile.keywords.like(search_pattern),
                ArchiveFile.tags.like(search_pattern),
                ArchiveFile.content_text.like(search_pattern),
                ArchiveFile.summary.like(search_pattern),
                ArchiveFile.abstract.like(search_pattern),
                ArchiveFile.responsibility.like(search_pattern),
                ArchiveFile.full_archive_code.like(search_pattern),
                ArchiveFile.reference_number.like(search_pattern),
            )
        ).limit(top_k * 5).all()

        query_terms = [term.lower() for term in re.split(r'\s+', query) if term.strip()]
        if not query_terms:
            query_terms = [query.lower()]

        results = []
        for archive in archives:
            combined_text = ' '.join(filter(None, [
                archive.title,
                archive.keywords,
                archive.tags,
                archive.summary,
                archive.abstract,
                archive.content_text,
                archive.responsibility,
                archive.full_archive_code,
                archive.reference_number,
            ])).lower()

            matched_terms = [term for term in query_terms if term in combined_text]
            if not matched_terms:
                continue

            score = len(matched_terms) / max(len(query_terms), 1)
            title_lower = (archive.title or '').lower()
            if any(term in title_lower for term in matched_terms):
                score += 0.5
            if query.lower() in (archive.full_archive_code or '').lower():
                score += 0.5

            snippet_source = archive.content_text or archive.summary or archive.abstract or archive.description or ''
            snippet = (snippet_source[:200] + '...') if len(snippet_source) > 200 else snippet_source

            results.append({
                'archive': archive,
                'score': round(score, 3),
                'snippet': snippet,
                'match_type': 'keyword'
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    # ── 私有辅助方法 ──────────────────────────────

    def _detect_archive_type(self, content, tags):
        """智能识别档案类型"""
        content_lower = content.lower() if content else ''
        for archive_type, keywords in self.ARCHIVE_TYPE_RULES.items():
            for kw in keywords:
                if kw in content_lower or kw in str(tags):
                    return archive_type
        return '文书档案'

    def _detect_retention_period(self, content, tags):
        """智能识别保管期限"""
        content_lower = content.lower() if content else ''
        for period, keywords in self.RETENTION_RULES.items():
            for kw in keywords:
                if kw in content_lower or kw in str(tags):
                    return period
        return '10年'

    def _extract_date(self, content, metadata):
        """从内容中提取日期"""
        if metadata and metadata.get('file_date'):
            val = metadata.get('file_date')
            if hasattr(val, 'year'):
                return val
            try:
                return datetime.strptime(str(val), '%Y-%m-%d')
            except Exception:
                pass

        if not content:
            return datetime.now()

        patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, content[:2000])
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except Exception:
                    continue

        return datetime.now()

    def _extract_responsibility(self, content, metadata):
        """提取责任者"""
        if metadata and metadata.get('responsibility'):
            return metadata.get('responsibility')

        if not content:
            return ''

        patterns = [
            r'([^\n]{2,20}(?:公司|单位|部门|局|厅|部|委|办|中心))[\s]*(?:文件|通知|报告)',
            r'发文单位[：:]\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content[:3000])
            if match:
                return match.group(1).strip()

        return ''

    def _estimate_page_count(self, file_path, file_format, word_count):
        """估算页数"""
        if file_format == 'pdf':
            try:
                from pypdf import PdfReader
                with open(file_path, 'rb') as f:
                    reader = PdfReader(f)
                    return len(reader.pages)
            except Exception:
                pass
        if word_count > 0:
            return max(1, word_count // 500)
        return 1

    def _get_next_seq(self, catalog_id, volume_id) -> int:
        """获取下一个件号序号"""
        query = ArchiveFile.query.filter_by(catalog_id=catalog_id)
        if volume_id:
            query = query.filter_by(volume_id=volume_id)
        last = query.order_by(ArchiveFile.id.desc()).first()
        if last and last.file_code:
            match = re.search(r'(\d+)$', last.file_code)
            if match:
                return int(match.group(1)) + 1
        return 1

    def _calc_md5(self, path: str) -> str:
        """计算MD5校验和"""
        h = hashlib.md5()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ''

    def _update_statistics(self, fonds_id, catalog_id, volume_id):
        """更新统计信息"""
        fonds = ArchiveFonds.query.get(fonds_id)
        if fonds:
            fonds.total_files = ArchiveFile.query.filter_by(fonds_id=fonds_id).count()

        if volume_id:
            volume = ArchiveVolume.query.get(volume_id)
            if volume:
                volume.total_files = ArchiveFile.query.filter_by(volume_id=volume_id).count()

        db.session.commit()


# 全局实例
archive_digitizer = ArchiveDigitizer()
