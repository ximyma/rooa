# -*- coding: utf-8 -*-
"""
档案国标命名规则模块
基于以下标准：
  - DA/T 18-1999  《档案著录规则》
  - DA/T 22-2015  《归档文件整理规则》
  - GB/T 9705-2008 《文书档案案卷格式》
  - DA/T 31-2005  《纸质档案数字化技术规范》（命名格式）

命名格式：
  全宗号-目录号-案卷号-件号[_页号]
  例：Q1-WS-2024001-0001
      Q1-WS-2024001-0001_P001（多页时加页号）

文件类型后缀约定：
  归档原件：.tiff / .pdf（PDF/A）
  查阅副本：.jpg
  OCR文档：_ocr.pdf
"""

import re
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 国标档案类型代码
# DA/T 22-2015 附录B
# ──────────────────────────────────────────────
ARCHIVE_TYPE_CODES = {
    '文书档案': 'WS',
    '科技档案': 'KJ',
    '会计档案': 'KU',
    '声像档案': 'SX',
    '照片档案': 'ZP',
    '录音档案': 'LY',
    '录像档案': 'LX',
    '人事档案': 'RS',
    '合同档案': 'HT',
    '实物档案': 'SW',
    '电子档案': 'DZ',
    '其他': 'QT',
}

# 保管期限代码
RETENTION_CODES = {
    '永久': 'Y',
    '30年': '30',
    '10年': '10',
    '长期': 'C',
    '短期': 'D',
}

# 密级代码
SECURITY_CODES = {
    '公开': '',
    '内部': 'N',
    '秘密': 'S',
    '机密': 'J',
    '绝密': 'Z',
}


class ArchiveNamingService:
    """
    档案国标命名服务
    
    档号组成（DA/T 18）：
        全宗号 - 目录号 - 案卷号 - 件号
    
    文件命名（DA/T 31）：
        {档号}_{年度}_{流水号}.{扩展名}
    """

    def __init__(self):
        pass

    # ══════════════════════════════════════════
    # 1. 生成完整档号
    # ══════════════════════════════════════════

    def generate_archive_code(
        self,
        fonds_code: str,       # 全宗号  如 Q1
        catalog_code: str,     # 目录号  如 WS（文书）
        volume_code: str,      # 案卷号  如 2024001
        file_seq: int,         # 件号序号  如 1
        retention: str = '30年',
        security: str = '公开',
    ) -> str:
        """
        生成符合DA/T 18标准的完整档号

        格式：全宗号·目录号·案卷号·件号
        示例：Q1-WS-2024001-0001
        """
        # 规范化各字段
        fonds = self._clean_code(fonds_code)
        catalog = self._clean_code(catalog_code)
        volume = self._clean_code(volume_code)
        seq = f"{int(file_seq):04d}"  # 4位补零

        parts = [fonds, catalog, volume, seq]
        archive_code = '-'.join(filter(None, parts))

        # 如有密级前缀
        sec = SECURITY_CODES.get(security, '')
        if sec:
            archive_code = f"{sec}·{archive_code}"

        return archive_code

    def generate_volume_code(
        self,
        fonds_code: str,
        catalog_code: str,
        year: int,
        seq: int,
        archive_type: str = '文书档案',
    ) -> str:
        """
        生成案卷号
        格式：年度+类型代码+顺序号
        示例：2024WS001
        """
        type_code = ARCHIVE_TYPE_CODES.get(archive_type, 'QT')
        return f"{year}{type_code}{seq:03d}"

    # ══════════════════════════════════════════
    # 2. 生成文件名（存储用）
    # ══════════════════════════════════════════

    def generate_filename(
        self,
        archive_code: str,
        file_type: str = 'tiff',
        page_num: int = None,
        is_ocr: bool = False,
        is_access_copy: bool = False,
    ) -> str:
        """
        生成符合DA/T 31标准的存储文件名

        Args:
            archive_code:  档号（如 Q1-WS-2024001-0001）
            file_type:     文件类型 tiff/jpg/pdf
            page_num:      页号（多页图像时使用）
            is_ocr:        是否是OCR版本
            is_access_copy: 是否是查阅副本

        Returns:
            文件名字符串（不含路径）
        """
        # 清理档号中的非法文件名字符
        safe_code = self._safe_filename(archive_code)

        parts = [safe_code]

        if page_num is not None:
            parts.append(f"P{page_num:03d}")

        if is_ocr:
            parts.append('ocr')

        if is_access_copy:
            parts.append('copy')

        name = '_'.join(parts)

        # 确定扩展名
        ext_map = {
            'tiff': '.tiff',
            'tif': '.tiff',
            'jpg': '.jpg',
            'jpeg': '.jpg',
            'pdf': '.pdf',
            'png': '.png',
        }
        ext = ext_map.get(file_type.lower(), f'.{file_type.lower()}')

        return f"{name}{ext}"

    def generate_storage_path(
        self,
        fonds_code: str,
        catalog_code: str,
        year: int,
        archive_code: str,
        base_dir: str = 'uploads/archives',
    ) -> str:
        """
        生成符合国标的存储目录路径

        目录结构：
            {base_dir}/
            └── {全宗号}/
                └── {目录号}/
                    └── {年度}/
                        └── {档号}.tiff

        Returns:
            完整目录路径（不含文件名）
        """
        parts = [
            base_dir,
            self._clean_code(fonds_code),
            self._clean_code(catalog_code),
            str(year),
        ]
        path = os.path.join(*parts)
        os.makedirs(path, exist_ok=True)
        return path

    # ══════════════════════════════════════════
    # 3. 验证档号格式
    # ══════════════════════════════════════════

    def validate_archive_code(self, code: str) -> dict:
        """
        验证档号是否符合国标格式

        Returns:
            {'valid': bool, 'errors': [], 'warnings': []}
        """
        result = {'valid': True, 'errors': [], 'warnings': []}

        if not code:
            result['valid'] = False
            result['errors'].append("档号不能为空")
            return result

        # 去除密级前缀
        clean = re.sub(r'^[NSSJZ]·', '', code)
        parts = clean.split('-')

        if len(parts) < 2:
            result['valid'] = False
            result['errors'].append(f"档号格式错误：应至少包含全宗号和目录号，当前：{code}")
            return result

        # 全宗号检查
        fonds = parts[0]
        if not re.match(r'^[A-Za-z0-9\u4e00-\u9fff]+$', fonds):
            result['warnings'].append(f"全宗号包含特殊字符: {fonds}")

        # 件号应为4位数字
        if len(parts) >= 4:
            seq = parts[3]
            if not re.match(r'^\d{4}$', seq):
                result['warnings'].append(f"件号建议为4位数字，当前: {seq}")

        # 长度检查
        if len(code) > 50:
            result['warnings'].append(f"档号较长（{len(code)}字符），建议控制在50字符以内")

        return result

    # ══════════════════════════════════════════
    # 4. 批量重命名
    # ══════════════════════════════════════════

    def batch_rename_files(
        self,
        files_info: list,
        dry_run: bool = True,
    ) -> list:
        """
        批量按国标规则重命名档案文件

        Args:
            files_info: [{'old_path': str, 'archive_code': str, 'file_type': str}]
            dry_run:    True则只返回计划，不实际执行

        Returns:
            [{'old': str, 'new': str, 'status': 'ok'/'skip'/'error', 'msg': str}]
        """
        results = []

        for item in files_info:
            old_path = item.get('old_path', '')
            archive_code = item.get('archive_code', '')
            file_type = item.get('file_type', 'tiff')

            if not old_path or not os.path.exists(old_path):
                results.append({
                    'old': old_path,
                    'new': None,
                    'status': 'skip',
                    'msg': '文件不存在'
                })
                continue

            # 生成新文件名
            new_name = self.generate_filename(archive_code, file_type)
            dir_path = os.path.dirname(old_path)
            new_path = os.path.join(dir_path, new_name)

            if not dry_run:
                try:
                    os.rename(old_path, new_path)
                    status = 'ok'
                    msg = '重命名成功'
                except Exception as e:
                    status = 'error'
                    msg = str(e)
                    new_path = old_path
            else:
                status = 'dry_run'
                msg = '（预览，未执行）'

            results.append({
                'old': old_path,
                'new': new_path,
                'status': status,
                'msg': msg
            })

        return results

    # ══════════════════════════════════════════
    # 5. 解析档号
    # ══════════════════════════════════════════

    def parse_archive_code(self, code: str) -> dict:
        """
        解析档号各组成部分

        Returns:
            {'fonds_code', 'catalog_code', 'volume_code', 'file_seq', 'security'}
        """
        result = {
            'fonds_code': '',
            'catalog_code': '',
            'volume_code': '',
            'file_seq': '',
            'security': '公开',
            'raw': code,
        }

        if not code:
            return result

        # 检测密级前缀
        sec_match = re.match(r'^([NSSJZ])·(.+)$', code)
        if sec_match:
            sec_char = sec_match.group(1)
            code = sec_match.group(2)
            for name, char in SECURITY_CODES.items():
                if char == sec_char:
                    result['security'] = name
                    break

        parts = code.split('-')
        if len(parts) >= 1:
            result['fonds_code'] = parts[0]
        if len(parts) >= 2:
            result['catalog_code'] = parts[1]
        if len(parts) >= 3:
            result['volume_code'] = parts[2]
        if len(parts) >= 4:
            result['file_seq'] = parts[3]

        return result

    # ══════════════════════════════════════════
    # 工具函数
    # ══════════════════════════════════════════

    def _clean_code(self, code: str) -> str:
        """清理代码字段（去空格，转大写）"""
        if not code:
            return ''
        return str(code).strip().upper()

    def _safe_filename(self, name: str) -> str:
        """将名称转换为安全的文件名"""
        # 替换不允许的字符
        safe = re.sub(r'[\\/:*?"<>|·]', '_', name)
        # 去除首尾空格和点
        safe = safe.strip('. ')
        return safe or 'unnamed'

    def get_type_code(self, archive_type: str) -> str:
        """获取档案类型代码"""
        return ARCHIVE_TYPE_CODES.get(archive_type, 'QT')

    def get_retention_code(self, retention: str) -> str:
        """获取保管期限代码"""
        return RETENTION_CODES.get(retention, '')

    def list_archive_type_codes(self) -> dict:
        """返回所有档案类型代码"""
        return ARCHIVE_TYPE_CODES.copy()


# 全局实例
archive_naming = ArchiveNamingService()
