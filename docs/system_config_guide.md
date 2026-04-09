# OA系统配置管理文档

## 概述

系统配置页面允许管理员在网页上配置：
- 嵌入模型路径
- OCR (Tesseract) 路径和字库
- 知识库功能开关
- AI对话参数
- 监测任务设置

---

## 访问配置页面

**路径**: `/admin/system_config`

**权限**: 仅管理员 (role='admin')

**导航**: 顶部菜单 → 系统管理 → ⚙️ 系统配置

---

## 配置项说明

### 1. 嵌入模型配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 模型路径 | `models/all-MiniLM-L6-v2` | 支持相对路径或绝对路径 |
| 使用本地模型 | ✓ | 启用后离线运行 |
| 批量处理大小 | 10 | 每批处理的文件数 |
| 最大文件大小 | 50MB | 单个文件上限 |
| 自动提取关键词 | ✓ | 上传时自动提取 |
| 自动生成摘要 | ✓ | 上传时自动生成 |
| 自动打标签 | ✓ | 上传时自动分类 |

**当前状态**: 页面会显示模型路径是否存在

### 2. OCR 文字识别配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 启用 OCR | ✗ | 总开关 |
| Tesseract 路径 | `C:\Program Files\Tesseract-OCR\tesseract.exe` | 可执行文件 |
| Tessdata 目录 | `C:\Program Files\Tesseract-OCR\tessdata` | 语言模型目录 |
| 识别语言 | chi_sim, eng | 简体中文+英文 |

**状态检查**:
- ✓ 文件存在
- ✗ 文件不存在
- ⚠ 缺少中文字库

### 3. AI 对话配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 默认模型 | deepseek | 默认使用的AI模型 |
| Temperature | 0.7 | 创造性程度 (0-2) |
| 最大 Token | 2000 | 单次回复最大长度 |

### 4. 监测配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 自动运行 | ✓ | 定时自动监测 |
| 检查间隔 | 24小时 | 监测频率 |
| 逾期通知 | ✓ | 逾期时发送通知 |

---

## 配置文件位置

```
ooa/
├── config/
│   └── system_config.json    # 配置文件
├── models/
│   └── all-MiniLM-L6-v2/     # 嵌入模型
├── config_manager.py         # 配置管理模块
└── init_config.py            # 初始化脚本
```

---

## 使用流程

### 首次配置

1. **复制嵌入模型** (已完成)
   ```
   ooa/models/all-MiniLM-L6-v2/
   ```

2. **安装 TesseractOCR** (需手动)
   - 下载安装程序
   - 安装到默认路径
   - 下载中文字库 `chi_sim.traineddata`

3. **启动 OA 系统**
   ```bash
   python app.py
   ```

4. **访问配置页面**
   - 登录管理员账号
   - 进入 系统管理 → 系统配置

5. **配置 OCR**
   - 启用 OCR 功能
   - 确认路径正确
   - 点击"测试 OCR"验证

6. **保存配置**
   - 点击"保存所有配置"

---

## API 接口

### 获取配置
```
GET /admin/system_config
```

### 保存配置
```
POST /admin/system_config/save
Content-Type: application/json

{
  "section": "ocr",
  "values": {
    "enabled": true,
    "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
  }
}
```

### 测试配置
```
POST /admin/system_config/test
Content-Type: application/json

{
  "type": "embedding"  // 或 "ocr"
}
```

---

## 故障排除

### 嵌入模型测试失败
- 检查模型路径是否正确
- 确认 `sentence-transformers` 已安装
- 查看控制台错误信息

### OCR 测试失败
- 确认 Tesseract 已正确安装
- 检查路径是否包含空格（需要正确处理）
- 确认中文字库已下载到 tessdata 目录

### 配置保存失败
- 检查 config 目录是否有写入权限
- 查看 `config/system_config.json` 是否被占用

---

## 相关文件

- `config_manager.py` - 配置管理核心
- `smart_knowledge.py` - 智能知识库（使用配置）
- `templates/admin/system_config.html` - 配置页面
- `init_config.py` - 配置初始化脚本
