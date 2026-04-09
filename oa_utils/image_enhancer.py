# -*- coding: utf-8 -*-
"""
图像增强模块
提供专注的图像增强能力：
  - 自动纠偏（基于OpenCV霍夫变换）
  - 边界检测与裁剪（去黑边）
  - 亮度/对比度调整
  - 锐化/去噪
  - 二值化（适合纯文字档案）
"""
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图像增强功能不可用")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV未安装，纠偏/去边功能不可用")


class ImageEnhancer:
    """
    档案图像增强处理器

    典型流水线：
      enhance(source) → deskew() → remove_border() → adjust_contrast() → sharpen()
    """

    def __init__(self):
        self.last_deskew_angle = 0.0
        self.last_border_removed = False

    # ──────────────────────────────────────────────
    # 完整增强流水线
    # ──────────────────────────────────────────────

    def enhance(self, source, mode='auto') -> 'Image.Image':
        """
        完整增强流水线

        Args:
            source: 文件路径(str) 或 PIL Image 对象
            mode: auto | grayscale | bitonal | color

        Returns:
            PIL Image（增强后）
        """
        img = self._load_image(source)
        if img is None:
            return None

        # 色彩模式
        img = self._apply_color_mode(img, mode)

        # 纠偏
        if CV2_AVAILABLE:
            img, self.last_deskew_angle = self._deskew(img)

        # 去黑边
        if CV2_AVAILABLE:
            img = self._remove_border(img)
            self.last_border_removed = True

        # 对比度
        img = self._adjust_contrast(img, factor=1.1)

        # 锐化
        img = self._sharpen(img, strength=80)

        return img

    # ──────────────────────────────────────────────
    # 单独功能
    # ──────────────────────────────────────────────

    def deskew(self, source) -> Tuple[Optional['Image.Image'], float]:
        """
        单独执行纠偏

        Returns:
            (纠偏后图像, 角度值)
        """
        img = self._load_image(source)
        if img is None:
            return None, 0.0
        return self._deskew(img)

    def remove_border(self, source, threshold: int = 30,
                      margin: int = 5) -> Optional['Image.Image']:
        """
        单独去黑边

        Args:
            threshold: 二值化阈值（越小越敏感）
            margin: 裁剪边距（像素）
        """
        img = self._load_image(source)
        if img is None:
            return None
        return self._remove_border(img, threshold, margin)

    def binarize(self, source, threshold: int = 128) -> Optional['Image.Image']:
        """
        简单二值化（适合文字档案）
        threshold: 0-255，默认128
        """
        img = self._load_image(source)
        if img is None:
            return None
        return self._binarize(img, threshold)

    def auto_binarize(self, source) -> Optional['Image.Image']:
        """Otsu自动阈值二值化"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._auto_binarize(img)

    def adjust_brightness(self, source, factor: float = 1.2) -> Optional['Image.Image']:
        """调整亮度（1.0=不变，>1.0变亮，<1.0变暗）"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._adjust_brightness(img, factor)

    def adjust_contrast(self, source, factor: float = 1.1) -> Optional['Image.Image']:
        """调整对比度"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._adjust_contrast(img, factor)

    def sharpen(self, source, strength: int = 80) -> Optional['Image.Image']:
        """锐化（strength: 0-200）"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._sharpen(img, strength)

    def denoise(self, source) -> Optional['Image.Image']:
        """去噪（中值滤波）"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._denoise(img)

    def resize(self, source, width: int, height: int,
               maintain_aspect: bool = True) -> Optional['Image.Image']:
        """调整尺寸"""
        img = self._load_image(source)
        if img is None:
            return None
        return self._resize(img, width, height, maintain_aspect)

    def to_grayscale(self, source) -> Optional['Image.Image']:
        """转灰度"""
        img = self._load_image(source)
        if img is None:
            return None
        return img.convert('L')

    # ──────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────

    def _load_image(self, source) -> Optional['Image.Image']:
        if PIL_AVAILABLE is False:
            return None
        if isinstance(source, Image.Image):
            return source
        if isinstance(source, str):
            try:
                return Image.open(source)
            except Exception as e:
                logger.warning(f"无法打开图像 {source}: {e}")
                return None
        if isinstance(source, (bytes, io.BytesIO)):
            try:
                return Image.open(io.BytesIO(source) if isinstance(source, bytes) else source)
            except Exception:
                return None
        return None

    def _apply_color_mode(self, img: 'Image.Image', mode: str) -> 'Image.Image':
        if mode == 'grayscale':
            return img.convert('L') if img.mode != 'L' else img
        elif mode == 'bitonal':
            return self._auto_binarize(img)
        elif mode == 'color':
            return img.convert('RGB') if img.mode not in ('RGB', 'RGBA') else img
        elif mode == 'auto':
            # 自动检测
            if img.mode in ('1', 'L'):
                return img
            try:
                gray = img.convert('L')
                stat = ImageStat.Stat(gray)
                mean = stat.mean[0]
                # 文字档案通常是白底黑字，均值偏高→灰度
                if 100 < mean < 200:
                    return gray
                return img
            except Exception:
                return img
        return img

    def _deskew(self, img: 'Image.Image') -> Tuple['Image.Image', float]:
        """霍夫变换自动纠偏"""
        if not CV2_AVAILABLE:
            return img, 0.0

        try:
            cv_img = self._pil_to_cv2(img)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) \
                if len(cv_img.shape) == 3 else cv_img.copy()

            # 自适应二值化
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 21, 10
            )

            # 膨胀使文字连成行
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 5))
            dilated = cv2.dilate(binary, kernel, iterations=2)

            # 找轮廓
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return img, 0.0

            angles = []
            for cnt in contours:
                if cv2.contourArea(cnt) < 500:
                    continue
                rect = cv2.minAreaRect(cnt)
                angle = rect[2]
                if angle < -45:
                    angle += 90
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return img, 0.0

            # 中位角度
            median_angle = sorted(angles)[len(angles) // 2]

            if abs(median_angle) < 0.3:
                return img, 0.0

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

            result = self._cv2_to_pil(rotated, img.mode)
            return result, round(float(median_angle), 2)

        except Exception as e:
            logger.warning(f"纠偏失败: {e}")
            return img, 0.0

    def _remove_border(self, img: 'Image.Image',
                       threshold: int = 30,
                       margin: int = 5) -> 'Image.Image':
        """去除黑边"""
        if not CV2_AVAILABLE:
            return img

        try:
            cv_img = self._pil_to_cv2(img)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) \
                if len(cv_img.shape) == 3 else cv_img.copy()

            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            coords = cv2.findNonZero(binary)

            if coords is None:
                return img

            x, y, w, h = cv2.boundingRect(coords)
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(cv_img.shape[1] - x, w + 2 * margin)
            h = min(cv_img.shape[0] - y, h + 2 * margin)

            if len(cv_img.shape) == 3:
                cropped = cv_img[y:y+h, x:x+w]
            else:
                cropped = gray[y:y+h, x:x+w]

            return self._cv2_to_pil(cropped, img.mode)

        except Exception as e:
            logger.warning(f"去黑边失败: {e}")
            return img

    def _binarize(self, img: 'Image.Image', threshold: int) -> 'Image.Image':
        """简单阈值二值化"""
        gray = img.convert('L') if img.mode != 'L' else img
        return gray.point(lambda x: 0 if x < threshold else 255, '1')

    def _auto_binarize(self, img: 'Image.Image') -> 'Image.Image':
        """Otsu自动阈值二值化"""
        if not CV2_AVAILABLE:
            gray = img.convert('L') if img.mode != 'L' else img
            return gray.point(lambda x: 0 if x < 128 else 255, '1')

        try:
            gray = img.convert('L') if img.mode != 'L' else img
            cv_gray = self._pil_to_cv2(gray)
            _, binary = cv2.threshold(cv_gray, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return Image.fromarray(binary, 'L')
        except Exception:
            return self._binarize(img, 128)

    def _adjust_contrast(self, img: 'Image.Image', factor: float) -> 'Image.Image':
        if img.mode == '1':
            return img
        try:
            enhancer = ImageEnhance.Contrast(img)
            return enhancer.enhance(factor)
        except Exception:
            return img

    def _adjust_brightness(self, img: 'Image.Image', factor: float) -> 'Image.Image':
        if img.mode == '1':
            return img
        try:
            enhancer = ImageEnhance.Brightness(img)
            return enhancer.enhance(factor)
        except Exception:
            return img

    def _sharpen(self, img: 'Image.Image', strength: int = 80) -> 'Image.Image':
        if img.mode == '1':
            return img
        try:
            # strength: 0-200 → radius: 0.5-2, percent: 50-150
            radius = 0.5 + (strength / 200) * 1.5
            percent = 50 + (strength / 200) * 100
            return img.filter(
                ImageFilter.UnsharpMask(
                    radius=radius,
                    percent=int(percent),
                    threshold=3
                )
            )
        except Exception:
            return img

    def _denoise(self, img: 'Image.Image') -> 'Image.Image':
        if not CV2_AVAILABLE:
            return img.filter(ImageFilter.MedianFilter(size=3))

        try:
            cv_img = self._pil_to_cv2(img.convert('RGB'))
            denoised = cv2.fastNlMeansDenoisingColored(cv_img, None, 10, 10, 7, 21)
            return self._cv2_to_pil(denoised, 'RGB')
        except Exception:
            return img.filter(ImageFilter.MedianFilter(size=3))

    def _resize(self, img: 'Image.Image', width: int, height: int,
                maintain_aspect: bool = True) -> 'Image.Image':
        if maintain_aspect:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            return img
        return img.resize((width, height), Image.Resampling.LANCZOS)

    def _pil_to_cv2(self, img: 'Image.Image') -> 'np.ndarray':
        if img.mode == 'RGB':
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        elif img.mode == 'RGBA':
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
        elif img.mode == 'L':
            return np.array(img)
        else:
            return cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_img: 'np.ndarray', original_mode: str) -> 'Image.Image':
        if len(cv_img.shape) == 2:
            return Image.fromarray(cv_img, 'L')
        elif cv_img.shape[2] == 4:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)
            return Image.fromarray(rgb, 'RGBA')
        else:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb, 'RGB')

    def get_features(self) -> dict:
        """返回可用功能"""
        return {
            'pillow': PIL_AVAILABLE,
            'opencv': CV2_AVAILABLE,
            'deskew': CV2_AVAILABLE,
            'border_removal': CV2_AVAILABLE,
            'binarize': PIL_AVAILABLE,
            'sharpen': PIL_AVAILABLE,
            'denoise': PIL_AVAILABLE or CV2_AVAILABLE,
        }


# 全局实例
image_enhancer = ImageEnhancer()
