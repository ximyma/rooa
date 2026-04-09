import os
import sys
import subprocess
import threading
import queue
import tempfile
import logging
import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from docx import Document as DocxDocument
from PyPDF2 import PdfMerger
import time

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LibreOfficeController:
    """LibreOffice控制类"""
    @staticmethod
    def find_soffice():
        """查找LibreOffice可执行文件路径"""
        # Windows默认安装路径
        paths = [
            "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
            "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
            # macOS路径
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            # Linux路径
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/opt/libreoffice/program/soffice"
        ]
        
        # 检查环境变量中的路径
        if "LIBREOFFICE_PATH" in os.environ:
            paths.insert(0, os.environ["LIBREOFFICE_PATH"])
        
        # 遍历所有可能的路径
        for path in paths:
            if os.path.exists(path):
                logging.info(f"找到LibreOffice: {path}")
                return path
        
        # 如果未找到，尝试通过命令查找
        try:
            which_path = subprocess.check_output(["which", "soffice"], stderr=subprocess.PIPE)
            if which_path:
                return which_path.decode().strip()
        except:
            pass
        
        raise FileNotFoundError(
            "未检测到LibreOffice安装\n"
            "请确认已安装LibreOffice或设置LIBREOFFICE_PATH环境变量"
        )

    @classmethod
    # def convert(cls, input_file, output_format, output_dir):
    #     """执行文件转换"""
    #     soffice_path = cls.find_soffice()
        
    #     cmd = [
    #         soffice_path,
    #         "--headless",          # 无界面模式
    #         "--norestore",         # 不恢复会话
    #         "--nodefault",         # 不启动初始向导
    #         "--nologo",            # 不显示启动画面
    #         "--convert-to", output_format,
    #         "--outdir", output_dir,
    #         input_file
    #     ]
        
    #     try:
    #         result = subprocess.run(
    #             cmd,
    #             check=True,
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE,
    #             timeout=180,      # 2分钟超时
    #             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    #         )
    #         return True
    #     except subprocess.TimeoutExpired:
    #         raise RuntimeError("转换操作超时（超过2分钟）")
    #     except subprocess.CalledProcessError as e:
    #         error_output = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
    #         raise RuntimeError(f"LibreOffice转换错误: {error_output}")
    #     except Exception as e:
    #         raise RuntimeError(f"转换过程中发生意外错误: {str(e)}")

    def convert(cls, input_file, output_format, output_dir):
        """完全重写的转换方法，解决所有权限问题"""
        soffice_path = cls.find_soffice()
        
        # 1. 创建安全的工作环境
        work_dir = tempfile.mkdtemp(prefix='docconv_')
        temp_input = os.path.join(work_dir, os.path.basename(input_file))
        temp_output = os.path.join(work_dir, "output")
        
        try:
            # 2. 复制文件到工作目录（解决原始文件权限问题）
            import shutil
            shutil.copy2(input_file, temp_input)
            
            # 3. 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 4. 构造LibreOffice命令
            cmd = [
                soffice_path,
                "--headless",
                "--norestore",
                "--nodefault",
                "--nologo",
                "--convert-to", output_format,
                "--outdir", work_dir,
                temp_input
            ]
            
            # 5. Windows特殊处理
            if sys.platform == "win32":
                from subprocess import CREATE_NO_WINDOW
                kwargs = {
                    'creationflags': CREATE_NO_WINDOW,
                    'shell': True  # 使用shell解决某些系统权限问题
                }
            else:
                kwargs = {}
            
            # 6. 执行转换
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5分钟超时
                **kwargs
            )
            
            # 7. 查找生成的文件
            output_files = [
                f for f in os.listdir(work_dir) 
                if f.startswith(os.path.splitext(os.path.basename(temp_input))[0]) and 
                f != os.path.basename(temp_input)
            ]
            
            if not output_files:
                raise RuntimeError("未生成输出文件，可能是格式不支持")
            
            # 8. 移动结果文件
            for file in output_files:
                src = os.path.join(work_dir, file)
                dst = os.path.join(output_dir, file)
                
                # 处理目标文件已存在的情况
                if os.path.exists(dst):
                    try:
                        os.remove(dst)
                    except PermissionError:
                        # 如果无法删除，尝试重命名
                        new_name = f"{os.path.splitext(dst)[0]}_{int(time.time())}{os.path.splitext(dst)[1]}"
                        dst = new_name
                
                shutil.move(src, dst)
            
            return True
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("转换超时，请检查文件是否损坏")
        except Exception as e:
            raise RuntimeError(f"转换失败: {str(e)}")
        finally:
            # 9. 清理工作目录
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except:
                pass
        
class DocumentProcessor:
    """文档处理器主类"""
    # 支持的文件格式和描述
    SUPPORTED_FORMATS = {
        'doc': 'Word 97-2003',
        'docx': 'Word 2007+',
        'pdf': 'PDF',
        'xls': 'Excel 97-2003',
        'xlsx': 'Excel 2007+',
        'ppt': 'PowerPoint 97-2003',
        'pptx': 'PowerPoint 2007+',
        'odt': 'OpenDocument Text',
        'ods': 'OpenDocument Spreadsheet',
        'odp': 'OpenDocument Presentation'
    }

    # 支持的转换类型映射
    CONVERSION_MAP = {
        # Word格式转换
        ('doc', 'docx'): 'docx',
        ('doc', 'pdf'): 'pdf',
        ('doc', 'odt'): 'odt',
        ('docx', 'pdf'): 'pdf',
        ('docx', 'doc'): 'doc',
        ('docx', 'odt'): 'odt',
        ('odt', 'docx'): 'docx',
        ('odt', 'pdf'): 'pdf',
        
        # Excel格式转换
        ('xls', 'xlsx'): 'xlsx',
        ('xls', 'pdf'): 'pdf',
        ('xls', 'ods'): 'ods',
        ('xlsx', 'pdf'): 'pdf',
        ('xlsx', 'xls'): 'xls',
        ('xlsx', 'ods'): 'ods',
        ('ods', 'xlsx'): 'xlsx',
        ('ods', 'pdf'): 'pdf',
        
        # PowerPoint格式转换
        ('ppt', 'pptx'): 'pptx',
        ('ppt', 'pdf'): 'pdf',
        ('ppt', 'odp'): 'odp',
        ('pptx', 'pdf'): 'pdf',
        ('pptx', 'ppt'): 'ppt',
        ('pptx', 'odp'): 'odp',
        ('odp', 'pptx'): 'pptx',
        ('odp', 'pdf'): 'pdf'
    }

    def __init__(self, root):
        """初始化"""
        self.root = root
        self.root.title("全能文档转换工具 (LibreOffice版) v3.0")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        
        # LibreOffice控制器
        self.libreoffice = LibreOfficeController()
        
        # 初始化变量
        self._init_variables()
        # 设置UI
        self._setup_ui()
        # 绑定事件
        self._bind_events()
        
        # 状态标签
        self.status_label = ttk.Label(
            self.root, 
            text="就绪 | 使用LibreOffice作为转换引擎",
            relief=SUNKEN,
            anchor=W
        )
        self.status_label.pack(side=BOTTOM, fill=X)

    def _init_variables(self):
        """初始化程序变量"""
        self.input_files = []
        self.output_folder = ""
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = []
        self.task_queue = queue.Queue()
        self.is_running = False
        self.operation_mode = "conversion"  # conversion or merge
        
        # 合并设置变量
        self.batch_size_var = IntVar(value=3)
        self.merge_format_var = StringVar(value="pdf")
        self.naming_rule_var = StringVar(value="combined")
        
        # 操作类型变量
        self.operation_var = StringVar(value="conversion")

    def _setup_ui(self):
        """构建用户界面"""
        # 主面板布局
        self.main_paned = ttk.PanedWindow(self.root, orient=HORIZONTAL)
        self.main_paned.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板
        self.left_panel = ttk.Frame(self.main_paned, width=350)
        self.main_paned.add(self.left_panel, weight=0)
        
        # 右侧面板
        self.right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_panel, weight=1)
        
        # 输入设置区域
        self._create_input_section()
        # 输出设置区域
        self._create_output_section()
        # 操作类型选择
        self._create_operation_selector()
        # 转换设置
        self._create_conversion_settings()
        # 合并设置
        self._create_merge_settings()
        # 进度显示
        self._create_progress_section()
        # 日志区域
        self._create_log_section()
        # 控制按钮
        self._create_control_buttons()

    def _create_input_section(self):
        """创建输入设置区域"""
        frame = ttk.LabelFrame(self.left_panel, text="输入设置", padding=10)
        frame.pack(fill=X, padx=5, pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X)
        
        ttk.Button(
            btn_frame, 
            text="添加文件",
            command=self._add_files,
            width=10
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="添加文件夹",
            command=self._add_folder,
            width=10
        ).pack(side=LEFT, padx=5)
        
        self.input_label = ttk.Label(
            frame,
            text="未选择任何文件",
            wraplength=330
        )
        self.input_label.pack(fill=X, pady=(5, 0))

    def _create_output_section(self):
        """创建输出设置区域"""
        frame = ttk.LabelFrame(self.left_panel, text="输出设置", padding=10)
        frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Button(
            frame,
            text="选择输出位置",
            command=self._select_output,
            width=15
        ).pack()
        
        self.output_label = ttk.Label(
            frame,
            text="未设置输出目录",
            wraplength=330
        )
        self.output_label.pack(fill=X, pady=(5, 0))

    def _create_operation_selector(self):
        """创建操作类型选择"""
        frame = ttk.LabelFrame(self.left_panel, text="处理类型", padding=10)
        frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Radiobutton(
            frame,
            text="格式转换",
            variable=self.operation_var,
            value="conversion",
            command=self._toggle_settings
        ).grid(row=0, column=0, sticky=W, padx=5, pady=2)
        
        ttk.Radiobutton(
            frame,
            text="文档合并",
            variable=self.operation_var,
            value="merge",
            command=self._toggle_settings
        ).grid(row=0, column=1, sticky=W, padx=5, pady=2)

    def _create_conversion_settings(self):
        """创建转换设置"""
        self.conv_frame = ttk.LabelFrame(
            self.left_panel, 
            text="转换设置", 
            padding=10
        )
        self.conv_frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Label(
            self.conv_frame,
            text="目标格式:"
        ).grid(row=0, column=0, sticky=W, padx=5, pady=2)
        
        self.conv_format = ttk.Combobox(
            self.conv_frame,
            values=list(self.SUPPORTED_FORMATS.keys()),
            state="readonly",
            width=8
        )
        self.conv_format.current(0)
        self.conv_format.grid(row=0, column=1, sticky=W, padx=5, pady=2)

    def _create_merge_settings(self):
        """创建合并设置"""
        self.merge_frame = ttk.LabelFrame(
            self.left_panel,
            text="合并设置",
            padding=10
        )
        self.merge_frame.pack_forget()  # 默认隐藏
        
        # 批量大小设置
        batch_frame = ttk.Frame(self.merge_frame)
        batch_frame.grid(row=0, column=0, columnspan=2, sticky=W, pady=2)
        
        ttk.Label(batch_frame, text="每").pack(side=LEFT)
        self.batch_size = ttk.Spinbox(
            batch_frame,
            from_=2,
            to=20,
            width=3,
            textvariable=self.batch_size_var
        )
        self.batch_size.pack(side=LEFT, padx=2)
        ttk.Label(batch_frame, text="个文件合并").pack(side=LEFT)
        
        # 输出格式
        ttk.Label(
            self.merge_frame,
            text="输出格式:"
        ).grid(row=1, column=0, sticky=W, padx=5, pady=2)
        
        self.merge_format = ttk.Combobox(
            self.merge_frame,
            values=["pdf", "docx"],
            textvariable=self.merge_format_var,
            state="readonly",
            width=8
        )
        self.merge_format.grid(row=1, column=1, sticky=W, padx=5, pady=2)
        
        # 命名规则
        ttk.Label(
            self.merge_frame,
            text="命名方式:"
        ).grid(row=2, column=0, sticky=W, padx=5, pady=2)
        
        self.naming_rule = ttk.Combobox(
            self.merge_frame,
            values=["combined", "sequential"],
            textvariable=self.naming_rule_var,
            state="readonly",
            width=8
        )
        self.naming_rule.grid(row=2, column=1, sticky=W, padx=5, pady=2)

    def _create_progress_section(self):
        """创建进度显示"""
        frame = ttk.Frame(self.left_panel)
        frame.pack(fill=X, padx=5, pady=10)
        
        self.progress = ttk.Progressbar(
            frame,
            orient=HORIZONTAL,
            mode='determinate',
            length=200
        )
        self.progress.pack(fill=X, expand=True)
        
        self.progress_label = ttk.Label(
            frame,
            text="等待操作...",
            anchor=CENTER
        )
        self.progress_label.pack(fill=X)

    def _create_log_section(self):
        """创建日志显示区域"""
        frame = ttk.LabelFrame(
            self.right_panel,
            text="处理日志",
            padding=10
        )
        frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 日志文本框
        self.log_text = Text(
            frame,
            wrap=WORD,
            state=DISABLED,
            font=('Consolas', 10),
            padx=5,
            pady=5
        )
        
        # 滚动条
        scrollbar = ttk.Scrollbar(
            frame,
            command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 配置标签样式
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('ERROR', foreground='red')

    def _create_control_buttons(self):
        """创建控制按钮"""
        frame = ttk.Frame(self.left_panel)
        frame.pack(fill=X, padx=5, pady=10)
        
        ttk.Button(
            frame,
            text="开始",
            command=self.start_processing
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            frame,
            text="停止",
            command=self.stop_processing
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            frame,
            text="清空日志",
            command=self.clear_logs
        ).pack(side=RIGHT, padx=5)
        
        ttk.Button(
            frame,
            text="导出日志",
            command=self.export_logs
        ).pack(side=RIGHT, padx=5)

    def _bind_events(self):
        """绑定事件处理"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _toggle_settings(self):
        """切换设置面板显示"""
        if self.operation_var.get() == "conversion":
            self.conv_frame.pack(fill=X, padx=5, pady=5)
            self.merge_frame.pack_forget()
        else:
            self.conv_frame.pack_forget()
            self.merge_frame.pack(fill=X, padx=5, pady=5)

    def start_processing(self):
        """开始处理任务"""
        if not self._validate_inputs():
            return
        
        self._prepare_for_processing()
        
        if self.operation_var.get() == "conversion":
            self._start_conversion()
        else:
            self._start_merging()

    def _validate_inputs(self):
        """验证输入有效性"""
        if not self.input_files:
            messagebox.showwarning("警告", "请先选择输入文件或文件夹")
            return False
            
        if not self.output_folder:
            messagebox.showwarning("警告", "请选择输出文件夹")
            return False
            
        if self.operation_var.get() == "merge":
            try:
                batch_size = self.batch_size_var.get()
                if batch_size < 2 or batch_size > 20:
                    messagebox.showwarning("警告", "批量大小必须为2-20的整数")
                    return False
            except:
                messagebox.showwarning("警告", "请输入有效的整数")
                return False
                
        return True

    def _prepare_for_processing(self):
        """准备处理任务"""
        self.is_running = True
        self.completed_tasks = 0
        self.failed_tasks = []
        self.clear_logs()
        self.progress['value'] = 0
        self.progress_label.config(text="准备开始...")

    def _start_conversion(self):
        """启动格式转换任务"""
        for file_path in self.input_files:
            self.task_queue.put(file_path)
        
        self.total_tasks = len(self.input_files)
        
        # 创建4个工作线程
        for _ in range(4):
            worker = threading.Thread(
                target=self._conversion_worker,
                daemon=True
            )
            worker.start()
        
        self._monitor_progress()

    def _conversion_worker(self):
        """转换工作线程"""
        while self.is_running and not self.task_queue.empty():
            try:
                file_path = self.task_queue.get_nowait()
                self._process_conversion(file_path)
            except queue.Empty:
                break
            except Exception as e:
                self._log_error(f"处理异常: {str(e)}")
            finally:
                self.task_queue.task_done()

    # def _process_conversion(self, file_path):
    #     """处理单个文件转换"""
    #     try:
    #         filename = os.path.basename(file_path)
    #         src_ext = os.path.splitext(filename)[1][1:].lower()
    #         dst_ext = self.conv_format.get()
            
    #         if (src_ext, dst_ext) not in self.CONVERSION_MAP:
    #             raise ValueError(f"不支持的转换类型: {src_ext} 到 {dst_ext}")
            
    #         output_name = f"{os.path.splitext(filename)[0]}.{dst_ext}"
    #         output_path = os.path.join(self.output_folder, output_name)
            
    #         if os.path.exists(output_path):
    #             raise FileExistsError(f"目标文件已存在: {output_path}")
            
    #         # 使用LibreOffice进行转换
    #         self.libreoffice.convert(
    #             file_path,
    #             self.CONVERSION_MAP[(src_ext, dst_ext)],
    #             self.output_folder
    #         )
            
    #         self.completed_tasks += 1
    #         self._log_message(f"转换成功: {filename}")
            
    #     except Exception as e:
    #         self.failed_tasks.append(file_path)
    #         self._log_error(f"{os.path.basename(file_path)} 转换失败: {str(e)}")

    def check_system_permissions():
        """检查系统权限"""
        issues = []
        
        # 检查临时目录权限
        try:
            test_dir = tempfile.mkdtemp()
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            os.rmdir(test_dir)
        except Exception as e:
            issues.append(f"临时目录访问失败: {str(e)}")
        
        # 检查LibreOffice执行权限
        try:
            lo_path = LibreOfficeController.find_soffice()
            if not os.access(lo_path, os.X_OK):
                issues.append(f"无权限执行LibreOffice: {lo_path}")
        except Exception as e:
            issues.append(f"LibreOffice检测失败: {str(e)}")
        
        return issues

    # 在程序启动时调用
    permission_issues = check_system_permissions()
    if permission_issues:
        messagebox.showwarning(
            "权限问题",
            "发现以下权限问题:\n\n" + "\n".join(permission_issues) +
            "\n\n建议以管理员身份运行程序。"
        )

    def _process_conversion(self, file_path):
        """增强的错误处理"""
        try:
            filename = os.path.basename(file_path)
            src_ext = os.path.splitext(filename)[1][1:].lower()
            dst_ext = self.conv_format.get()
            
            if (src_ext, dst_ext) not in self.CONVERSION_MAP:
                raise ValueError(f"不支持的转换类型: {src_ext} 到 {dst_ext}")
            
            output_name = f"{os.path.splitext(filename)[0]}.{dst_ext}"
            output_path = os.path.join(self.output_folder, output_name)
            
            # 检查文件是否被其他程序锁定
            try:
                with open(file_path, 'rb') as test_lock:
                    pass
            except IOError as e:
                raise RuntimeError(f"文件被锁定或不可访问: {str(e)}")
            
            # 检查输出目录权限
            if not os.access(self.output_folder, os.W_OK):
                raise RuntimeError("输出目录没有写入权限")
            
            # 记录详细转换信息
            self._log_message(f"开始转换: {filename} -> {output_name}")
            
            # 使用LibreOffice进行转换
            start_time = datetime.datetime.now()
            self.libreoffice.convert(
                file_path,
                self.CONVERSION_MAP[(src_ext, dst_ext)],
                self.output_folder
            )
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            self._log_message(f"转换成功: {filename} (耗时{duration:.2f}秒)")
            self.completed_tasks += 1
            
        except Exception as e:
            error_msg = f"{filename} 转换失败: {str(e)}"
            self.failed_tasks.append((file_path, error_msg))
            self._log_error(error_msg)
            
            # 特殊处理权限错误
            if "拒绝访问" in str(e) or "WinError 5" in str(e):
                self._log_message("提示：请尝试以管理员身份运行程序", "WARNING")

    def _start_merging(self):
        """启动文档合并任务"""
        try:
            batch_size = self.batch_size_var.get()
            if batch_size < 2 or batch_size > 20:
                raise ValueError("批量大小必须在2-20之间")
            
            self.total_tasks = len(self.input_files) // batch_size + 1
            merge_thread = threading.Thread(
                target=self._process_merging,
                daemon=True
            )
            merge_thread.start()
            self._monitor_progress()
        except Exception as e:
            self._log_error(str(e))
            messagebox.showerror("参数错误", str(e))

    def _process_merging(self):
        """处理文档合并"""
        try:
            batch_size = self.batch_size_var.get()
            output_format = self.merge_format_var.get()
            naming_rule = self.naming_rule_var.get()
            
            groups = [
                self.input_files[i:i+batch_size] 
                for i in range(0, len(self.input_files), batch_size)
            ]
            
            for idx, group in enumerate(groups):
                if not self.is_running:
                    break
                
                base_names = [os.path.splitext(os.path.basename(f))[0] for f in group]
                if naming_rule == "combined":
                    output_name = "_".join(base_names[:3]) + ("_etc" if len(base_names) > 3 else "")
                else:
                    output_name = f"merged_{idx+1:03d}"
                
                output_path = os.path.join(
                    self.output_folder, 
                    f"{output_name}.{output_format}"
                )
                
                if os.path.exists(output_path):
                    raise FileExistsError(f"目标文件已存在: {output_path}")
                
                self._merge_files(group, output_path, output_format)
                self.completed_tasks += 1
                self._log_message(f"合并成功: {output_name}.{output_format}")
                
        except Exception as e:
            self.failed_tasks.append(str(e))
            self._log_error(f"合并失败: {str(e)}")

    def _merge_files(self, files, output_path, output_format):
        """合并多个文件"""
        if output_format == 'pdf':
            merger = PdfMerger()
            temp_files = []
            
            try:
                for file in files:
                    if file.lower().endswith('.pdf'):
                        merger.append(file)
                    else:
                        # 转换为临时PDF
                        temp_pdf = os.path.join(
                            tempfile.gettempdir(),
                            f"temp_{os.path.basename(file)}.pdf"
                        )
                        self.libreoffice.convert(
                            file, 
                            'pdf',
                            os.path.dirname(temp_pdf)
                        )
                        merger.append(temp_pdf)
                        temp_files.append(temp_pdf)
                
                merger.write(output_path)
                merger.close()
            finally:
                # 清理临时文件
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
        else:
            merged_doc = DocxDocument()
            temp_files = []
            
            try:
                for doc_file in files:
                    if not doc_file.lower().endswith(('.docx', '.odt')):
                        # 转换为临时DOCX
                        temp_docx = os.path.join(
                            tempfile.gettempdir(),
                            f"temp_{os.path.basename(doc_file)}.docx"
                        )
                        self.libreoffice.convert(
                            doc_file,
                            'docx',
                            os.path.dirname(temp_docx)
                        )
                        doc_file = temp_docx
                        temp_files.append(temp_docx)
                    
                    doc = DocxDocument(doc_file)
                    for element in doc.element.body:
                        merged_doc.element.body.append(element)
                
                merged_doc.save(output_path)
            finally:
                # 清理临时文件
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass

    def _monitor_progress(self):
        """监控处理进度"""
        if self.is_running:
            progress = (self.completed_tasks + len(self.failed_tasks)) / max(1, self.total_tasks) * 100
            self.progress["value"] = progress
            self.progress_label.config(
                text=f"处理中: {self.completed_tasks}/{self.total_tasks} "
                     f"({int(progress)}%)"
            )
            
            if (self.completed_tasks + len(self.failed_tasks)) >= self.total_tasks:
                self.is_running = False
                self._show_results()
            else:
                self.root.after(200, self._monitor_progress)
        else:
            self._show_results()

    def _show_results(self):
        """显示处理结果"""
        success = self.completed_tasks
        failed = len(self.failed_tasks)
        
        if failed == 0:
            msg = f"所有{success}个任务处理成功！"
            self.progress_label.config(text=msg)
        else:
            msg = f"处理完成！\n成功: {success}\n失败: {failed}"
            if failed > 0:
                msg += "\n失败文件/原因:\n" + "\n".join(
                    f"{os.path.basename(f)}" if isinstance(f, str) and os.path.exists(f) 
                    else str(f) 
                    for f in self.failed_tasks[:3]
                )
                if failed > 3:
                    msg += f"\n...等{failed}个错误"
        
        messagebox.showinfo("处理结果", msg)
        self.progress_label.config(text="操作完成" if failed == 0 else "操作完成（有失败任务）")

    def stop_processing(self):
        """停止处理任务"""
        self.is_running = False
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        self.progress_label.config(text="操作已停止")
        self._log_message("用户手动停止操作", "WARNING")

    def _log_message(self, message, level="INFO"):
        """记录日志信息"""
        self.log_text.config(state=NORMAL)
        self.log_text.insert(
            END,
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n",
            (level,)
        )
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        self.log_text.update()

    def _log_error(self, message):
        """记录错误信息"""
        self.failed_tasks.append(message)
        self._log_message(message, "ERROR")

    def _add_files(self):
        """添加文件"""
        filetypes = [
            ("所有支持的文件", "*.doc;*.docx;*.pdf;*.xls;*.xlsx;*.ppt;*.pptx;*.odt;*.ods;*.odp"),
            ("Word文件", "*.doc;*.docx"),
            ("Excel文件", "*.xls;*.xlsx"),
            ("PowerPoint文件", "*.ppt;*.pptx"),
            ("PDF文件", "*.pdf"),
            ("OpenDocument文件", "*.odt;*.ods;*.odp"),
            ("所有文件", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=filetypes
        )
        
        if files:
            self.input_files = list(files)
            count = len(self.input_files)
            self.input_label.config(
                text=f"已选择{count}个文件\n"
                     f"首个文件: {os.path.basename(self.input_files[0])}" + 
                     ("..." if count > 1 else "")
            )

    def _add_folder(self):
        """添加文件夹"""
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            self.input_files = []
            extensions = (
                '.doc', '.docx', '.pdf', 
                '.xls', '.xlsx', 
                '.ppt', '.pptx',
                '.odt', '.ods', '.odp'
            )
            
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(extensions):
                        self.input_files.append(os.path.join(root, f))
            
            count = len(self.input_files)
            if count > 0:
                self.input_label.config(
                    text=f"从文件夹选择{count}个文件\n"
                         f"路径: {folder}"
                )
            else:
                self.input_label.config(text="所选文件夹中没有支持的文件")
                messagebox.showwarning("警告", "所选文件夹中没有支持的文件格式")

    def _select_output(self):
        """选择输出目录"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=folder)

    def export_logs(self):
        """导出日志文件"""
        log_content = self.log_text.get("1.0", END).strip()
        if not log_content:
            messagebox.showwarning("警告", "没有可导出的日志内容")
            return
        
        default_name = f"document_converter_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self._log_message(f"日志已导出到: {file_path}")
            except Exception as e:
                self._log_error(f"日志导出失败: {str(e)}")

    def clear_logs(self):
        """清空日志"""
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)
        self._log_message("日志已清空")

    def _on_close(self):
        """关闭窗口事件处理"""
        if self.is_running:
            if not messagebox.askokcancel("退出", "当前有任务正在执行，确定要退出吗？"):
                return
        
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    # 检查LibreOffice是否可用
    try:
        LibreOfficeController.find_soffice()
    except Exception as e:
        messagebox.showerror(
            "初始化错误",
            f"无法启动程序:\n{str(e)}\n"
            "请确保已安装LibreOffice并配置正确路径"
        )
        sys.exit(1)
    
    # 创建主窗口
    root = Tk()
    
    # 设置窗口图标（如果有）
    try:
        if sys.platform == "win32":
            root.iconbitmap(default='icon.ico')
        else:
            img = PhotoImage(file='icon.png')
            root.tk.call('wm', 'iconphoto', root._w, img)
    except:
        pass
    
    # 创建主应用
    app = DocumentProcessor(root)
    
    # 启动主循环
    root.mainloop()
    