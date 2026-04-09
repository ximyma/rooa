# -*- coding: utf-8 -*-
"""
格式转换模块
支持档案常用格式互转：
  - TIFF ↔ PDF/A（双套制存储）
  - TIFF/PNG/BMP → JPEG（查阅副本）
  - 图像 → PDF/A（含OCR文字层）
  - PDF → 图像序列（分页提取）
  - 多页TIFF处理
符合 DA/T 31-2017 电子档案格式规范
"""
import os
import io
import logging
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，格式转换功能受限")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF未安装，PDF处理功能受限")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract未安装，OCR功能不可用")

try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False
    logger.warning("img2pdf未安装，图像转PDF功能受限")


class FormatConverter:
    """
    档案格式转换器

    支持格式：TIFF, JPEG, PNG, BMP, PDF
    """

    # 国标推荐参数
    TIFF_COMPRESSION = 'tiff_lzw'  # LZW无损压缩
    JPEG_QUALITY = 85              # JPEG质量
    PDF_DPI = 300                  # PDF内嵌DPI

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join('uploads', 'archive_formats')
        os.makedirs(self.output_dir, exist_ok=True)

    # ══════════════════════════════════════════
    # TIFF ↔ PDF 双向转换
    # ══════════════════════════════════════════

    def tiff_to_pdf(self, tiff_path: str, output_name: str = None,
                    dpi: int = 300) -> Optional[str]:
        """
        TIFF图像转PDF/A（无OCR，仅图像PDF）

        Args:
            tiff_path: TIFF文件路径
            output_name: 输出文件名（不含扩展名）
            dpi: 嵌入DPI

        Returns:
            PDF文件路径 或 None
        """
        if not os.path.exists(tiff_path):
            logger.error(f"TIFF文件不存在: {tiff_path}")
            return None

        if output_name is None:
            output_name = os.path.splitext(os.path.basename(tiff_path))[0]

        pdf_path = os.path.join(self.output_dir, f"{output_name}.pdf")

        # 方案1：img2pdf（最可靠）
        if IMG2PDF_AVAILABLE:
            try:
                with open(tiff_path, 'rb') as f:
                    pdf_bytes = img2pdf.convert(
                        f.read(),
                        layout_fun=img2pdf.get_layout_fun(
                            img2pdf.inch_to_dim(dpi / 72)
                        )
                    )
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"TIFF→PDF成功: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"img2pdf失败: {e}")

        # 方案2：PyMuPDF
        if PYMUPDF_AVAILABLE:
            try:
                img_doc = fitz.open(tiff_path)
                pdf_bytes = img_doc.convert_to_pdf()
                img_doc.close()

                pdf_doc = fitz.open('pdf', pdf_bytes)
                pdf_doc.save(pdf_path, deflate=True, garbage=4)
                pdf_doc.close()
                logger.info(f"TIFF→PDF(PyMuPDF)成功: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"PyMuPDF TIFF→PDF失败: {e}")

        # 方案3：Pillow（仅支持单页TIFF）
        if PIL_AVAILABLE:
            try:
                img = Image.open(tiff_path)
                img.save(pdf_path, 'PDF', resolution=dpi)
                logger.info(f"TIFF→PDF(Pillow)成功: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"Pillow TIFF→PDF失败: {e}")

        return None

    def pdf_to_tiff(self, pdf_path: str, output_name: str = None,
                    dpi: int = 300, page: int = None) -> List[str]:
        """
        PDF转TIFF（逐页转换）

        Args:
            pdf_path: PDF文件路径
            output_name: 输出文件名（不含扩展名）
            dpi: 输出DPI
            page: 指定页码（None=全部页）

        Returns:
            TIFF文件路径列表
        """
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF未安装，无法将PDF转换为TIFF")
            return []

        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return []

        if output_name is None:
            output_name = os.path.splitext(os.path.basename(pdf_path))[0]

        paths = []
        try:
            doc = fitz.open(pdf_path)
            pages = [page] if page is not None else range(len(doc))

            for i in pages:
                p = doc[i]
                # 高分辨率渲染
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = p.get_pixmap(matrix=mat, alpha=False)

                if page is not None:
                    filename = f"{output_name}.tiff"
                else:
                    filename = f"{output_name}_p{i+1:03d}.tiff"

                tiff_path = os.path.join(self.output_dir, filename)
                pix.save(tiff_path)
                paths.append(tiff_path)

            doc.close()
            logger.info(f"PDF→TIFF成功，共{len(paths)}页: {pdf_path}")

        except Exception as e:
            logger.error(f"PDF→TIFF转换失败: {e}", exc_info=True)

        return paths

    def tiff_to_jpeg(self, tiff_path: str, output_name: str = None,
                     quality: int = 85) -> Optional[str]:
        """TIFF转JPEG（日常查阅副本）"""
        if not PIL_AVAILABLE:
            return None

        if not os.path.exists(tiff_path):
            return None

        if output_name is None:
            output_name = os.path.splitext(os.path.basename(tiff_path))[0]

        jpg_path = os.path.join(self.output_dir, f"{output_name}.jpg")

        try:
            img = Image.open(tiff_path)
            # 去除透明通道
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            elif img.mode == '1':
                img = img.convert('L')

            img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
            logger.info(f"TIFF→JPEG成功: {jpg_path}")
            return jpg_path

        except Exception as e:
            logger.warning(f"TIFF→JPEG失败: {e}")
            return None

    def image_to_pdf(self, image_path: str, output_name: str = None,
                     with_ocr: bool = False, lang: str = 'chi_sim+eng',
                     dpi: int = 300) -> Optional[str]:
        """
        图像转PDF/A

        Args:
            with_ocr: 是否嵌入OCR文字层
            lang: OCR语言
        """
        if output_name is None:
            output_name = os.path.splitext(os.path.basename(image_path))[0]

        pdf_path = os.path.join(self.output_dir, f"{output_name}.pdf")

        # OCR方案
        if with_ocr and TESSERACT_AVAILABLE:
            try:
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    image_path,
                    extension='pdf',
                    lang=lang,
                    config=f'--dpi {dpi} --psm 1'
                )
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"图像→PDF(OCR)成功: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"Tesseract PDF生成失败: {e}")

        # 无OCR图像PDF
        return self.tiff_to_pdf(image_path, output_name, dpi)

    def pdf_extract_pages(self, pdf_path: str, output_dir: str = None,
                         fmt: str = 'png', dpi: int = 300) -> List[str]:
        """
        PDF分页提取为图像

        Args:
            fmt: 输出格式 png | jpg | tiff
            dpi: 渲染分辨率
        """
        if not PYMUPDF_AVAILABLE:
            return []

        if not os.path.exists(pdf_path):
            return []

        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        paths = []
        try:
            doc = fitz.open(pdf_path)
            name = os.path.splitext(os.path.basename(pdf_path))[0]

            for i in range(len(doc)):
                page = doc[i]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                filename = f"{name}_p{i+1:03d}.{fmt}"
                out_path = os.path.join(out_dir, filename)
                pix.save(out_path)
                paths.append(out_path)

            doc.close()
            logger.info(f"PDF分页提取成功，共{len(paths)}页")

        except Exception as e:
            logger.error(f"PDF分页提取失败: {e}", exc_info=True)

        return paths

    # ══════════════════════════════════════════
    # TIFF多页处理
    # ══════════════════════════════════════════

    def split_multipage_tiff(self, tiff_path: str, output_dir: str = None) -> List[str]:
        """
        拆分多页TIFF为单页TIFF
        """
        if not PIL_AVAILABLE:
            return []

        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)

        paths = []
        try:
            with Image.open(tiff_path) as img:
                name = os.path.splitext(os.path.basename(tiff_path))[0]
                for i in range(img.n_frames):
                    img.seek(i)
                    out_path = os.path.join(out_dir, f"{name}_p{i+1:04d}.tiff")
                    img.save(out_path, 'TIFF', compression=self.TIFF_COMPRESSION)
                    paths.append(out_path)

            logger.info(f"TIFF分页拆分成功，共{len(paths)}页")

        except Exception as e:
            logger.error(f"TIFF分页拆分失败: {e}", exc_info=True)

        return paths

    def merge_tiff_pages(self, page_paths: List[str], output_name: str) -> Optional[str]:
        """
        合并多页TIFF
        """
        if not PIL_AVAILABLE or not page_paths:
            return None

        output_path = os.path.join(self.output_dir, f"{output_name}.tiff")

        try:
            images = []
            for p in page_paths:
                if os.path.exists(p):
                    images.append(Image.open(p))

            if not images:
                return None

            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                compression=self.TIFF_COMPRESSION
            )
            logger.info(f"TIFF合并成功，共{len(images)}页: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"TIFF合并失败: {e}", exc_info=True)
            return None

    # ══════════════════════════════════════════
    # 批处理
    # ══════════════════════════════════════════

    def batch_convert(self, file_paths: List[str], from_fmt: str,
                     to_fmt: str, output_suffix: str = None) -> Dict[str, str]:
        """
        批量格式转换

        Args:
            file_paths: 文件路径列表
            from_fmt: 源格式 (tiff|pdf|image)
            to_fmt: 目标格式 (pdf|tiff|jpg)
            output_suffix: 输出文件后缀

        Returns:
            {源文件: 目标文件} 映射
        """
        results = {}
        suffix = output_suffix or f"_to_{to_fmt}"

        for path in file_paths:
            name = os.path.splitext(os.path.basename(path))[0]
            out_name = f"{name}{suffix}"

            try:
                if from_fmt == 'tiff' and to_fmt == 'pdf':
                    out = self.tiff_to_pdf(path, out_name)
                elif from_fmt == 'tiff' and to_fmt == 'jpg':
                    out = self.tiff_to_jpeg(path, out_name)
                elif from_fmt == 'pdf' and to_fmt == 'tiff':
                    outs = self.pdf_to_tiff(path, out_name)
                    out = outs[0] if outs else None
                elif from_fmt in ('jpg', 'png', 'bmp') and to_fmt == 'pdf':
                    out = self.image_to_pdf(path, out_name)
                else:
                    out = None

                results[path] = out

            except Exception as e:
                logger.warning(f"批量转换失败 {path}: {e}")
                results[path] = None

        return results

    # ══════════════════════════════════════════
    # 工具
    # ══════════════════════════════════════════

    def get_pdf_info(self, pdf_path: str) -> Optional[dict]:
        """获取PDF元信息（页数/DPI/是否有文字层）"""
        if not PYMUPDF_AVAILABLE or not os.path.exists(pdf_path):
            return None

        try:
            doc = fitz.open(pdf_path)
            info = {
                'page_count': len(doc),
                'has_text': any(page.get_text().strip() for page in doc),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'created': doc.metadata.get('creationDate', ''),
                'modified': doc.metadata.get('modDate', ''),
            }
            doc.close()
            return info
        except Exception:
            return None

    def get_tiff_info(self, tiff_path: str) -> Optional[dict]:
        """获取TIFF元信息（DPI/页数/色彩模式）"""
        if not PIL_AVAILABLE or not os.path.exists(tiff_path):
            return None

        try:
            with Image.open(tiff_path) as img:
                dpi = img.info.get('dpi', (72, 72))
                dpi_val = dpi[0] if isinstance(dpi, tuple) else dpi
                return {
                    'page_count': getattr(img, 'n_frames', 1),
                    'dpi': dpi_val,
                    'mode': img.mode,
                    'size': img.size,
                    'format': img.format,
                }
        except Exception:
            return None

    def get_available_features(self) -> dict:
        """返回可用功能"""
        return {
            'pillow': PIL_AVAILABLE,
            'pymupdf': PYMUPDF_AVAILABLE,
            'tesseract': TESSERACT_AVAILABLE,
            'img2pdf': IMG2PDF_AVAILABLE,
            'tiff_to_pdf': PIL_AVAILABLE or IMG2PDF_AVAILABLE or PYMUPDF_AVAILABLE,
            'pdf_to_tiff': PYMUPDF_AVAILABLE,
            'image_to_pdf': PIL_AVAILABLE or TESSERACT_AVAILABLE,
            'pdf_extract_pages': PYMUPDF_AVAILABLE,
            'split_multipage_tiff': PIL_AVAILABLE,
            'merge_tiff_pages': PIL_AVAILABLE,
        }


# 全局实例
format_converter = FormatConverter()
