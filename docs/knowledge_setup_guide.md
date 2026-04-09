# 智能知识库 - 安装配置指南

## ✅ 已完成

### 1. 嵌入模型
- **位置**: `C:\Users\Administrator\Desktop\ooa\models\all-MiniLM-L6-v2`
- **大小**: ~87MB
- **状态**: ✅ 已复制完成

### 2. 配置文件更新
- **文件**: `smart_knowledge.py`
- **修改**: 模型路径改为本地相对路径

---

## 📥 待安装: TesseractOCR

由于网络限制无法自动下载，请手动安装：

### 步骤1: 下载安装程序
1. 访问: https://github.com/UB-Mannheim/tesseract/releases
2. 下载最新版: `tesseract-ocr-w64-setup-5.3.x.exe`
3. 运行安装程序
4. **重要**: 记住安装路径（默认 `C:\Program Files\Tesseract-OCR`）

### 步骤2: 下载中文字库
1. 访问: https://github.com/tesseract-ocr/tessdata
2. 下载 `chi_sim.traineddata`（简体中文）
3. 将文件放到 Tesseract 的 `tessdata` 文件夹内
   - 例如: `C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata`

### 步骤3: 验证安装
打开命令提示符，运行：
```cmd
tesseract --version
tesseract --list-langs
```
应该能看到 `chi_sim` 在语言列表中。

---

## 🔧 配置检查脚本

运行 `install_tesseract.bat` 可以：
- 检查 Tesseract 是否已安装
- 检查中文字库是否存在
- 提示下载链接

---

## 🚀 启动知识库

安装完成后，启动 OA 系统：

```bash
cd C:\Users\Administrator\Desktop\ooa
python app.py
```

访问: http://localhost:5000/knowledge/personal

---

## 📋 功能测试清单

- [ ] 拖拽上传多个文件
- [ ] 图片文件自动OCR识别
- [ ] 自动生成关键词和标签
- [ ] 自动生成文档摘要
- [ ] 智能搜索功能

---

## ⚠️ 注意事项

1. **首次启动较慢** - 需要加载 87MB 的嵌入模型
2. **内存占用** - 批量处理大文件时可能占用较多内存
3. **OCR速度** - 图片识别较慢，请耐心等待

---

## 🔗 相关链接

- Tesseract 下载: https://github.com/UB-Mannheim/tesseract/releases
- 中文字库: https://github.com/tesseract-ocr/tessdata
- 模型信息: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
