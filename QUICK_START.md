# 🚀 快速开始

## 启动项目（Windows）

```bash
# 首次运行
setup_env.bat

# 日常启动
start.bat
```

## 访问地址

```
http://127.0.0.1:5000
```

## 默认账号

```
用户名: admin
密码: admin123
```

## 📁 项目结构

```
ooa/
├── app.py                    # 主应用
├── config.py                 # 配置文件
├── models.py                 # 数据库模型
├── forms.py                  # 表单类
├── utils.py                  # 工具函数
├── init_project.py           # 初始化脚本
├── setup_env.bat             # 环境设置
├── start.bat                # 启动脚本
├── requirements.txt          # 依赖包
├── .env.example            # 环境变量模板
├── .gitignore             # Git 忽略规则
├── venv/                 # 虚拟环境
├── templates/             # HTML 模板
├── static/               # 静态资源
└── uploads/              # 上传文件
```

## 🔧 常见问题

### Q: 提示端口被占用？
**A**: 修改 `app.py` 最后一行:
```python
app.run(debug=True, port=5001)  # 改用其他端口
```

### Q: 依赖安装失败？
**A**: 升级 pip 后重试:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Q: 数据库报错？
**A**: 删除数据库重新初始化:
```bash
del oa.db
python app.py
```

## 📁 档案数字化模块（国标合规）

### 涉及标准
| 标准 | 说明 |
|------|------|
| DA/T 18-1999 | 档案著录规则（元数据必填项） |
| DA/T 22-2015 | 归档文件整理规则（档号命名） |
| DA/T 31-2005 | 纸质档案数字化技术规范（TIFF+PDF格式） |
| DA/T 47-2009 | 纸质档案数字化扫描工作规范（DPI/质检） |

### 安装图像处理依赖

```bash
# Python 依赖（激活虚拟环境后执行）
pip install Pillow opencv-python-headless pytesseract img2pdf PyMuPDF pypdf

# Tesseract OCR 引擎（Windows）
# 1. 下载安装器（选 5.x 版本）
#    https://github.com/UB-Mannheim/tesseract/releases
# 2. 安装时勾选 "Chinese Simplified" 中文语言包
# 3. 运行检测脚本
install_tesseract.bat
```

### 数据库迁移（已有系统升级）

```bash
# 如果数据库已存在且需要添加国标字段
python migrate_archive_standard.py
```

### 新模块文件

| 文件 | 功能 |
|------|------|
| `archive_image_processor.py` | 图像处理：TIFF存储/纠偏/去黑边/DPI校验/OCR嵌入PDF |
| `archive_naming.py` | 国标档号命名：生成/验证/批量重命名 |
| `archive_quality_checker.py` | 6维自动质检：DPI/格式/OCR/元数据/档号/图像质量 |
| `archive_digitizer.py` | 完整10步数字化流水线 |
| `migrate_archive_standard.py` | 数据库字段迁移脚本 |

### 访问质检仪表板

```
http://127.0.0.1:5000/archive/quality
```

### API 接口

```
POST /archive/api/quality_check/<id>     # 单档质检
POST /archive/api/quality_check/batch   # 批量质检
GET  /archive/api/quality_check/report/<id>  # 查看质检报告
POST /archive/api/naming/generate       # 生成标准档号
POST /archive/api/naming/validate       # 验证档号格式
GET  /archive/api/image/features        # 查询图像处理功能
```

## 📞 获取帮助

详细说明请查看:
- `OPTIMIZATION_REPORT.md` - 优化报告
- `SECURITY_FIXES.md` - 安全修复说明
- `readme.txt` - 原项目说明
