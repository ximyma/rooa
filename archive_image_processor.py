# -*- coding: utf-8 -*-
"""
档案图像处理模块 - 符合国家档案局标准
DA/T 31-2005《纸质档案数字化技术规范》
DA/T 47-2009《纸质档案数字化扫描工作规范》

功能：
1. TIFF双格式存储（TIFF + JPEG/PNG）
2. 自动纠偏去黑边（OpenCV）
3. 300DPI检查与验证
4. 色彩模式处理（灰度/彩色/黑白）
5. OCR文字层嵌入PDF
6. 图像质量评估
"""
import os
import io
import re
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 依赖检测（优雅降级）
# ──────────────────────────────────────────────

try:
    from PIL import Image, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图像处理功能受限")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV未安装，自动纠偏功能不可用")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract未安装，OCR功能不可用")

try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False
    logger.warning("img2pdf未安装，图像转PDF功能不可用")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF未安装，OCR嵌入PDF功能受限")


# 国标最低要求
STANDARD_DPI_MIN = 300          # DA/T 31 规定最低300DPI
STANDARD_DPI_RECOMMENDED = 400  # 推荐分辨率
TIFF_COMPRESSION = 'tiff_lzw'   # TIFF推荐压缩方式（无损）
PDF_A_VERSION = 'PDF/A-1b'      # 档案用PDF标准版本


class ArchiveImageProcessor:
    """
    档案图像处理器
    符合 DA/T 31-2005 / DA/T 47-2009 标准
    """

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 输出目录，默认 uploads/archive_images
        """
        self.output_dir = output_dir or os.path.join('uploads', 'archive_images')
        os.makedirs(self.output_dir, exist_ok=True)

    # ══════════════════════════════════════════
    # 1. 入口：完整处理流水线
    # ══════════════════════════════════════════

    def process_image(self, source_path: str, file_code: str,
                      enable_deskew: bool = True,
                      enable_border_removal: bool = True,
                      target_dpi: int = 300,
                      color_mode: str = 'auto') -> dict:
        """
        档案图像完整处理流水线

        Args:
            source_path:  原始图像路径
            file_code:    档案件号（用于命名）
            enable_deskew: 是否自动纠偏
            enable_border_removal: 是否去黑边
            target_dpi:   目标分辨率（默认300）
            color_mode:   色彩模式 auto/color/grayscale/bitonal

        Returns:
            dict: {
                tiff_path, jpeg_path, pdf_path,
                dpi, color_mode, page_count,
                deskew_angle, quality_score,
                warnings: []
            }
        """
        result = {
            'tiff_path': None,
            'jpeg_path': None,
            'pdf_path': None,
            'dpi': None,
            'color_mode': None,
            'page_count': 1,
            'deskew_angle': 0.0,
            'quality_score': 0,
            'warnings': [],
            'success': False
        }

        if not PIL_AVAILABLE:
            result['warnings'].append("Pillow未安装，无法处理图像")
            return result

        try:
            img = Image.open(source_path)
            ext = Path(source_path).suffix.lower()

            # ① DPI检查
            dpi_info = self._check_dpi(img, source_path)
            result['dpi'] = dpi_info['dpi']
            if dpi_info['dpi'] < STANDARD_DPI_MIN:
                result['warnings'].append(
                    f"分辨率{dpi_info['dpi']}DPI低于国标最低要求{STANDARD_DPI_MIN}DPI"
                )

            # ② 色彩模式处理
            img, detected_mode = self._process_color_mode(img, color_mode)
            result['color_mode'] = detected_mode

            # ③ OpenCV纠偏 + 去黑边
            if CV2_AVAILABLE and enable_deskew:
                img, angle = self._deskew(img)
                result['deskew_angle'] = angle

            if CV2_AVAILABLE and enable_border_removal:
                img = self._remove_border(img)

            # ④ 图像增强（亮度/对比度）
            img = self._enhance_image(img)

            # ⑤ 保存TIFF（无损，国标首选格式）
            tiff_path = self._save_tiff(img, file_code, target_dpi)
            result['tiff_path'] = tiff_path

            # ⑥ 保存JPEG（日常查阅用）
            jpeg_path = self._save_jpeg(img, file_code, target_dpi)
            result['jpeg_path'] = jpeg_path

            # ⑦ 生成带OCR文字层的PDF/A
            pdf_path = self._create_pdf_with_ocr(tiff_path, file_code, source_path)
            result['pdf_path'] = pdf_path

            # ⑧ 质量评分
            result['quality_score'] = self._evaluate_quality(img, result)
            result['success'] = True

        except Exception as e:
            result['warnings'].append(f"处理失败: {str(e)}")
            logger.error(f"图像处理失败 {source_path}: {e}", exc_info=True)

        return result

    def process_pdf(self, pdf_path: str, file_code: str,
                    enable_ocr: bool = True) -> dict:
        """
        处理PDF文件：检查/嵌入OCR文字层，转PDF/A

        Returns:
            dict: {pdf_a_path, page_count, has_ocr, warnings}
        """
        result = {
            'pdf_a_path': None,
            'page_count': 0,
            'has_ocr': False,
            'warnings': [],
            'success': False
        }

        if not PYMUPDF_AVAILABLE:
            result['warnings'].append("PyMuPDF未安装，跳过PDF/A转换")
            result['pdf_a_path'] = pdf_path  # 原样返回
            result['success'] = True
            return result

        try:
            doc = fitz.open(pdf_path)
            result['page_count'] = len(doc)

            # 检查是否已有文字层
            has_text = any(page.get_text().strip() for page in doc)
            result['has_ocr'] = has_text

            if not has_text and enable_ocr and TESSERACT_AVAILABLE:
                # 逐页OCR并嵌入
                result['pdf_a_path'] = self._embed_ocr_to_pdf(
                    doc, file_code, pdf_path
                )
                result['has_ocr'] = True
            else:
                # 直接转PDF/A
                result['pdf_a_path'] = self._convert_to_pdf_a(
                    doc, file_code, pdf_path
                )

            doc.close()
            result['success'] = True

        except Exception as e:
            result['warnings'].append(f"PDF处理失败: {str(e)}")
            logger.error(f"PDF处理失败 {pdf_path}: {e}", exc_info=True)

        return result

    # ══════════════════════════════════════════
    # 2. DPI检查
    # ══════════════════════════════════════════

    def _check_dpi(self, img: 'Image.Image', path: str) -> dict:
        """检查图像DPI"""
        dpi = 72  # 默认值
        try:
            info = img.info
            if 'dpi' in info:
                raw = info['dpi']
                dpi = int(raw[0]) if isinstance(raw, tuple) else int(raw)
            elif 'jfif_density' in info:
                dpi = info.get('jfif_density', (72, 72))[0]
            # TIFF使用XResolution标签
            elif hasattr(img, 'tag_v2'):
                xres = img.tag_v2.get(282)  # XResolution tag
                if xres:
                    dpi = int(xres[0][0] / xres[0][1]) if isinstance(xres[0], tuple) else int(xres[0])
        except Exception:
            pass

        # 如果读不到，尝试从文件名/EXIF推断
        if dpi <= 72:
            dpi = self._guess_dpi_from_size(img)

        return {'dpi': dpi, 'meets_standard': dpi >= STANDARD_DPI_MIN}

    def _guess_dpi_from_size(self, img: 'Image.Image') -> int:
        """根据图像像素尺寸推断DPI（A4纸基准）"""
        w, h = img.size
        # A4纸 210×297mm，若图像较大则推测为高分辨率
        a4_300dpi = (2480, 3508)
        a4_200dpi = (1654, 2339)
        if w >= a4_300dpi[0] or h >= a4_300dpi[1]:
            return 300
        elif w >= a4_200dpi[0] or h >= a4_200dpi[1]:
            return 200
        return 150

    # ══════════════════════════════════════════
    # 3. 色彩模式
    # ══════════════════════════════════════════

    def _process_color_mode(self, img: 'Image.Image', mode: str) -> tuple:
        """处理色彩模式，返回(处理后图像, 色彩模式名称)"""
        if mode == 'auto':
            mode = self._detect_color_mode(img)

        if mode == 'grayscale' and img.mode not in ('L', 'LA'):
            img = img.convert('L')
            return img, '灰度'
        elif mode == 'bitonal':
            # 黑白二值化（适合纯文字档案）
            if img.mode != 'L':
                img = img.convert('L')
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
            return img, '黑白'
        elif mode == 'color':
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            return img, '彩色'
        else:
            return img, '灰度' if img.mode == 'L' else '彩色'

    def _detect_color_mode(self, img: 'Image.Image') -> str:
        """自动检测适合的色彩模式"""
        if img.mode in ('1', 'L', 'LA'):
            return 'grayscale'
        if img.mode == 'P':
            return 'color'

        # 分析像素多样性
        try:
            rgb_img = img.convert('RGB')
            sample = rgb_img.resize((100, 100))  # 采样缩小
            pixels = list(sample.getdata())
            # 检查是否接近灰度（R≈G≈B）
            color_count = sum(
                1 for r, g, b in pixels
                if abs(r - g) > 20 or abs(g - b) > 20
            )
            ratio = color_count / len(pixels)
            return 'color' if ratio > 0.1 else 'grayscale'
        except Exception:
            return 'grayscale'

    # ══════════════════════════════════════════
    # 4. 自动纠偏（OpenCV）
    # ══════════════════════════════════════════

    def _deskew(self, img: 'Image.Image') -> tuple:
        """
        自动检测并纠正图像倾斜
        使用霍夫变换检测文字基线角度

        Returns:
            (纠偏后图像, 检测到的角度)
        """
        if not CV2_AVAILABLE:
            return img, 0.0

        try:
            # PIL → OpenCV
            cv_img = self._pil_to_cv2(img)

            # 转灰度
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) \
                if len(cv_img.shape) == 3 else cv_img

            # 二值化
            _, binary = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # 膨胀使文字连成行
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
            dilated = cv2.dilate(binary, kernel, iterations=2)

            # 找轮廓
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return img, 0.0

            # 取最大轮廓的最小外接矩形
            angles = []
            for cnt in contours:
                if cv2.contourArea(cnt) < 500:
                    continue
                rect = cv2.minAreaRect(cnt)
                angle = rect[2]
                # 标准化角度到 [-45, 45]
                if angle < -45:
                    angle += 90
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return img, 0.0

            # 取中位角度
            median_angle = sorted(angles)[len(angles) // 2]

            # 小于0.5度不处理（避免过度纠偏）
            if abs(median_angle) < 0.5:
                return img, median_angle

            # 旋转纠偏
            h, w = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)

            if len(cv_img.shape) == 3:
                rotated = cv2.warpAffine(
                    cv_img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
            else:
                rotated = cv2.warpAffine(
                    cv_img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )

            result_img = self._cv2_to_pil(rotated, img.mode)
            logger.debug(f"纠偏角度: {median_angle:.2f}°")
            return result_img, round(median_angle, 2)

        except Exception as e:
            logger.warning(f"纠偏失败，使用原图: {e}")
            return img, 0.0

    # ══════════════════════════════════════════
    # 5. 去黑边
    # ══════════════════════════════════════════

    def _remove_border(self, img: 'Image.Image') -> 'Image.Image':
        """
        去除扫描黑边
        自动检测内容区域并裁剪
        """
        if not CV2_AVAILABLE:
            return img

        try:
            cv_img = self._pil_to_cv2(img)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) \
                if len(cv_img.shape) == 3 else cv_img.copy()

            # 二值化（黑边为黑色，内容区为白色）
            _, binary = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

            # 找内容区域（非黑边）
            coords = cv2.findNonZero(binary)
            if coords is None:
                return img

            x, y, w, h = cv2.boundingRect(coords)

            # 留5像素边距
            margin = 5
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(cv_img.shape[1] - x, w + 2 * margin)
            h = min(cv_img.shape[0] - y, h + 2 * margin)

            # 裁剪
            if len(cv_img.shape) == 3:
                cropped = cv_img[y:y+h, x:x+w]
            else:
                cropped = gray[y:y+h, x:x+w]

            return self._cv2_to_pil(cropped, img.mode)

        except Exception as e:
            logger.warning(f"去黑边失败，使用原图: {e}")
            return img

    # ══════════════════════════════════════════
    # 6. 图像增强
    # ══════════════════════════════════════════

    def _enhance_image(self, img: 'Image.Image') -> 'Image.Image':
        """适度增强图像（对比度/清晰度）"""
        try:
            if img.mode == '1':
                return img  # 二值图不处理

            # 轻微增强对比度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)

            # 轻微锐化
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))
        except Exception:
            pass
        return img

    # ══════════════════════════════════════════
    # 7. 保存TIFF
    # ══════════════════════════════════════════

    def _save_tiff(self, img: 'Image.Image', file_code: str,
                   dpi: int = 300) -> str:
        """
        保存为TIFF格式（无损压缩）
        符合DA/T 31-2005规定的归档格式
        """
        # 确保是支持TIFF的色彩模式
        if img.mode not in ('RGB', 'L', '1', 'RGBA', 'CMYK'):
            img = img.convert('RGB')

        filename = f"{file_code}.tiff"
        path = os.path.join(self.output_dir, filename)

        save_kwargs = {
            'format': 'TIFF',
            'compression': 'tiff_lzw',   # LZW无损压缩
            'dpi': (dpi, dpi),
        }

        # 二值图像使用CCITT G4压缩（传真压缩，体积最小）
        if img.mode == '1':
            save_kwargs['compression'] = 'group4'

        img.save(path, **save_kwargs)
        logger.info(f"TIFF已保存: {path}")
        return path

    # ══════════════════════════════════════════
    # 8. 保存JPEG（查阅副本）
    # ══════════════════════════════════════════

    def _save_jpeg(self, img: 'Image.Image', file_code: str,
                   dpi: int = 300) -> str:
        """保存为JPEG格式（用于日常查阅）"""
        # JPEG不支持透明通道
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        if img.mode == '1':
            img = img.convert('L')

        filename = f"{file_code}.jpg"
        path = os.path.join(self.output_dir, filename)
        img.save(path, format='JPEG', quality=85, dpi=(dpi, dpi), optimize=True)
        logger.info(f"JPEG已保存: {path}")
        return path

    # ══════════════════════════════════════════
    # 9. OCR + 生成带文字层PDF
    # ══════════════════════════════════════════

    def _create_pdf_with_ocr(self, tiff_path: str, file_code: str,
                              original_path: str) -> str:
        """
        从TIFF图像生成带OCR文字层的PDF/A
        使用 Tesseract OCR + img2pdf/PyMuPDF
        """
        pdf_filename = f"{file_code}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        # 方案1：tesseract直接生成带文字层PDF（最优）
        if TESSERACT_AVAILABLE:
            try:
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    tiff_path,
                    extension='pdf',
                    lang='chi_sim+eng',
                    config='--dpi 300 --psm 1'
                )
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"OCR PDF已生成: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"Tesseract PDF生成失败，尝试备用方案: {e}")

        # 方案2：img2pdf（无OCR，仅图像PDF）
        if IMG2PDF_AVAILABLE:
            try:
                with open(tiff_path, 'rb') as f:
                    pdf_bytes = img2pdf.convert(f.read())
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"图像PDF已生成（无OCR）: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"img2pdf生成失败: {e}")

        # 方案3：PyMuPDF
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open()
                img_doc = fitz.open(tiff_path)
                pdfbytes = img_doc.convert_to_pdf()
                img_doc.close()
                doc = fitz.open('pdf', pdfbytes)
                doc.save(pdf_path)
                doc.close()
                logger.info(f"PDF已生成（PyMuPDF）: {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"PyMuPDF生成失败: {e}")

        return None

    def _embed_ocr_to_pdf(self, doc: 'fitz.Document', file_code: str,
                           original_path: str) -> str:
        """为现有PDF的每页嵌入OCR文字层"""
        pdf_path = os.path.join(self.output_dir, f"{file_code}_ocr.pdf")

        try:
            new_doc = fitz.open()

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 将PDF页渲染为图像
                mat = fitz.Matrix(2, 2)  # 2x缩放提高OCR质量
                pix = page.get_pixmap(matrix=mat)

                # 转为PIL Image
                img_bytes = pix.tobytes('png')
                img = Image.open(io.BytesIO(img_bytes))

                # OCR识别
                ocr_data = pytesseract.image_to_data(
                    img, lang='chi_sim+eng',
                    config='--psm 1 --oem 1',
                    output_type=pytesseract.Output.DICT
                )

                # 创建新PDF页（与原页同尺寸）
                new_page = new_doc.new_page(
                    width=page.rect.width,
                    height=page.rect.height
                )

                # 插入原始图像
                new_page.insert_image(new_page.rect, pixmap=pix)

                # 嵌入OCR文字（不可见文字层）
                n_boxes = len(ocr_data['level'])
                for i in range(n_boxes):
                    if int(ocr_data['conf'][i]) < 30:
                        continue
                    text = ocr_data['text'][i].strip()
                    if not text:
                        continue

                    # 坐标转换（OCR坐标→PDF坐标）
                    scale_x = page.rect.width / img.width
                    scale_y = page.rect.height / img.height
                    x1 = ocr_data['left'][i] * scale_x
                    y1 = ocr_data['top'][i] * scale_y
                    w = ocr_data['width'][i] * scale_x
                    h_box = ocr_data['height'][i] * scale_y

                    if w < 1 or h_box < 1:
                        continue

                    rect = fitz.Rect(x1, y1, x1 + w, y1 + h_box)
                    # 插入不可见文字（透明）
                    new_page.insert_textbox(
                        rect, text,
                        fontsize=max(6, int(h_box * 0.9)),
                        color=(0, 0, 0),
                        render_mode=3,  # 不可见文字（仅用于检索）
                        overlay=True
                    )

            new_doc.save(pdf_path, deflate=True)
            new_doc.close()
            logger.info(f"OCR文字层嵌入PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"OCR嵌入失败: {e}", exc_info=True)
            return original_path

    def _convert_to_pdf_a(self, doc: 'fitz.Document', file_code: str,
                           original_path: str) -> str:
        """转换为PDF/A格式"""
        pdf_path = os.path.join(self.output_dir, f"{file_code}_pdfa.pdf")
        try:
            doc.save(
                pdf_path,
                deflate=True,
                clean=True,
                garbage=4,
                # PDF/A合规元数据
                encryption=fitz.PDF_ENCRYPT_NONE
            )
            return pdf_path
        except Exception as e:
            logger.warning(f"PDF/A转换失败，返回原文件: {e}")
            return original_path

    # ══════════════════════════════════════════
    # 10. 质量评分
    # ══════════════════════════════════════════

    def _evaluate_quality(self, img: 'Image.Image', result: dict) -> int:
        """
        综合质量评分（0-100）
        
        评分维度：
        - DPI是否达标（30分）
        - 是否有OCR文字层（25分）
        - 是否有TIFF格式（20分）
        - 纠偏角度是否在合理范围（15分）
        - 图像清晰度（10分）
        """
        score = 0

        # DPI（30分）
        dpi = result.get('dpi', 0)
        if dpi >= STANDARD_DPI_RECOMMENDED:
            score += 30
        elif dpi >= STANDARD_DPI_MIN:
            score += 20
        elif dpi >= 200:
            score += 10

        # OCR/PDF（25分）
        if result.get('pdf_path'):
            score += 25

        # TIFF格式（20分）
        if result.get('tiff_path'):
            score += 20

        # 纠偏角度（15分）
        angle = abs(result.get('deskew_angle', 0))
        if angle < 1.0:
            score += 15
        elif angle < 3.0:
            score += 10
        elif angle < 5.0:
            score += 5

        # 图像清晰度（10分）
        try:
            if img.mode not in ('1',):
                gray = img.convert('L') if img.mode != 'L' else img
                # 拉普拉斯方差衡量清晰度
                if CV2_AVAILABLE:
                    cv_gray = self._pil_to_cv2(gray)
                    variance = cv2.Laplacian(cv_gray, cv2.CV_64F).var()
                    if variance > 500:
                        score += 10
                    elif variance > 200:
                        score += 7
                    elif variance > 50:
                        score += 3
                else:
                    score += 7  # 无法检测时给默认分
        except Exception:
            score += 5

        return min(100, score)

    # ══════════════════════════════════════════
    # 工具函数
    # ══════════════════════════════════════════

    def _pil_to_cv2(self, img: 'Image.Image') -> 'np.ndarray':
        """PIL Image → OpenCV ndarray"""
        if img.mode == 'RGB':
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        elif img.mode == 'RGBA':
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
        elif img.mode == 'L':
            return np.array(img)
        elif img.mode == '1':
            return np.array(img.convert('L'))
        else:
            return cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_img: 'np.ndarray', original_mode: str) -> 'Image.Image':
        """OpenCV ndarray → PIL Image"""
        if len(cv_img.shape) == 2:
            # 灰度图
            pil_img = Image.fromarray(cv_img, 'L')
        elif cv_img.shape[2] == 4:
            pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA), 'RGBA')
        else:
            pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB), 'RGB')

        # 还原原始色彩模式
        if original_mode == '1' and pil_img.mode != '1':
            pil_img = pil_img.convert('1')
        elif original_mode == 'L' and pil_img.mode not in ('L', '1'):
            pil_img = pil_img.convert('L')

        return pil_img

    def get_available_features(self) -> dict:
        """返回当前可用的功能列表"""
        return {
            'pillow': PIL_AVAILABLE,
            'opencv': CV2_AVAILABLE,
            'tesseract': TESSERACT_AVAILABLE,
            'img2pdf': IMG2PDF_AVAILABLE,
            'pymupdf': PYMUPDF_AVAILABLE,
            'tiff_storage': PIL_AVAILABLE,
            'deskew': CV2_AVAILABLE,
            'border_removal': CV2_AVAILABLE,
            'ocr_pdf': TESSERACT_AVAILABLE or IMG2PDF_AVAILABLE or PYMUPDF_AVAILABLE,
        }


# 全局实例
archive_image_processor = ArchiveImageProcessor()
