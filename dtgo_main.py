import sys
import json
import base64
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                            QProgressBar, QLabel, QListWidget, QTableWidget, 
                            QTableWidgetItem, QTabWidget, QMessageBox, QDialog, QFormLayout, QMenu, QListWidgetItem, QScrollArea, QFileDialog, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QAction
import urllib3
from dtgo_handlers import TaskManager
from dtgo_config import Config
urllib3.disable_warnings()

class FofaThread(QThread):
    progress_signal = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished_signal = pyqtSignal(list)
    
    def __init__(self, fofa_key):
        super().__init__()
        self.fofa_key = fofa_key
        self.running = True
        
    def stop(self):
        self.running = False
        
    def run(self):
        if not self.running:
            return
        try:
            self.progress_value.emit(10)
            query = base64.b64encode("app=\"资产灯塔系统\"".encode()).decode()
            url = f"https://fofa.info/api/v1/search/all?key={self.fofa_key}&qbase64={query}&size=10000"
            response = requests.get(url)
            self.progress_value.emit(30)
            
            if not self.running:
                return
                
            data = response.json()
            if not data.get("error"):
                results = data.get("results", [])
                self.progress_value.emit(50)
                if self.running:
                    self.finished_signal.emit(results)
            else:
                self.progress_signal.emit("FOFA API 调用失败")
        except Exception as e:
            self.progress_signal.emit(f"错误: {str(e)}")

class LoginThread(QThread):
    progress_signal = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    success_signal = pyqtSignal(dict)
    
    def __init__(self, target, total_targets, current_index):
        super().__init__()
        self.target = target
        self.total_targets = total_targets
        self.current_index = current_index
        self.running = True
        
    def stop(self):
        self.running = False
        
    def run(self):
        if not self.running:
            return
            
        try:
            url = f"https://{self.target}/api/user/login"
            data = {"username": "admin", "password": "arlpass"}
            response = requests.post(url, json=data, verify=False, timeout=5)
            result = response.json()
            
            progress = 50 + int((self.current_index + 1) / self.total_targets * 50)
            self.progress_value.emit(progress)
            
            if result.get("code") == 200:
                self.success_signal.emit({
                    "target": self.target,
                    "token": result["data"]["token"]
                })
            self.progress_signal.emit(f"登录 {self.target}: {'成功' if result.get('code') == 200 else '失败'}")
        except Exception as e:
            error_msg = str(e)
            if "Max retries exceeded" in error_msg:
                error_msg = "连接超时"
            elif "Connection" in error_msg:
                error_msg = "连接失败"
            self.progress_signal.emit(f"登录 {self.target} 失败: {error_msg}")

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setFixedSize(400, 200)
        
        # 应用对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 4px;
            }
            QLabel {
                color: #424242;
                font-weight: bold;
                padding: 5px 0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #E3F2FD;
                selection-color: #1976D2;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
                padding: 9px 20px 7px 20px;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # FOFA API Key 输入框
        self.fofa_key_input = QLineEdit()
        self.fofa_key_input.setText(self.config.get_fofa_key())
        self.fofa_key_input.setPlaceholderText("请输入您的 FOFA API Key")
        form_layout.addRow("FOFA API Key:", self.fofa_key_input)
        
        # 添加表单布局
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
                padding: 9px 20px 7px 20px;
            }
        """)
        
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        # 添加按钮布局
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def save_settings(self):
        try:
            if self.config.set_fofa_key(self.fofa_key_input.text()):
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "保存失败",
                    "无法保存配置文件，请检查程序是否有写入权限。",
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"保存设置时发生错误：{str(e)}",
                QMessageBox.StandardButton.Ok
            )

class TaskConfirmDialog(QDialog):
    def __init__(self, info_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("确认提交")
        self.setFixedSize(600, 400)
        
        # 应用对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 4px;
            }
            QLabel {
                color: #424242;
                padding: 10px;
                font-size: 12px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
                padding: 9px 20px 7px 20px;
            }
            QScrollArea {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9E9E9E;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.setup_ui(info_text)
        
    def setup_ui(self, info_text):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # 添加任务信息文本
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.PlainText)
        content_layout.addWidget(info_label)
        
        # 设置内容容器的布局
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        
        # 添加滚动区域到主布局
        layout.addWidget(scroll_area)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 添加确认和取消按钮
        confirm_button = QPushButton("确认")
        cancel_button = QPushButton("取消")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
                padding: 9px 20px 7px 20px;
            }
        """)
        
        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        
        # 添加按钮布局到主布局
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class AddBeaconDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加灯塔")
        self.setFixedSize(400, 200)
        
        # 应用对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 4px;
            }
            QLabel {
                color: #424242;
                font-weight: bold;
                padding: 5px 0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 输入框
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("例如: example.com:5003")
        self.username_input = QLineEdit()
        self.username_input.setText("admin")  # 默认用户名
        self.password_input = QLineEdit()
        self.password_input.setText("arlpass")  # 默认密码
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("灯塔地址:", self.address_input)
        form_layout.addRow("用户名:", self.username_input)
        form_layout.addRow("密码:", self.password_input)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        login_btn = QPushButton("登录")
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
            }
        """)
        
        login_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(login_btn)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_inputs(self):
        return {
            'address': self.address_input.text().strip(),
            'username': self.username_input.text().strip(),
            'password': self.password_input.text().strip()
        }

class DTGO(QMainWindow):
    def __init__(self):
        super().__init__()
        # 定义主题颜色
        self.THEME_COLORS = {
            'primary': '#2196F3',
            'secondary': '#4CAF50',
            'warning': '#FFC107',
            'error': '#F44336',
            'background': '#F5F5F5',
            'text': '#212121',
        }
        
        # 优化按钮样式
        self.BUTTON_STYLE = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #0D47A1;
                padding: 9px 20px 7px 20px;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: rgba(255, 255, 255, 0.7);
            }
        """
        
        # 优化表格样式
        self.TABLE_STYLE = """
            QTableWidget {
                background-color: white;
                alternate-background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #EEEEEE;
                selection-background-color: #E3F2FD;
                selection-color: #1976D2;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #FAFAFA;
                padding: 8px;
                border: none;
                border-right: 1px solid #E0E0E0;
                border-bottom: 1px solid #E0E0E0;
                font-weight: bold;
                color: #424242;
            }
            QHeaderView::section:checked {
                background-color: #E3F2FD;
            }
        """
        
        # 优化列表样式
        self.LIST_STYLE = """
            QListWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
                border-left: 3px solid #1976D2;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
        """
        
        # 优化进度条样式
        self.PROGRESS_BAR_STYLE = """
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #E0E0E0;
                text-align: center;
                color: white;
                font-weight: bold;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #64B5F6);
                border-radius: 4px;
            }
        """
        
        # 优化状态标签样式
        self.STATUS_LABEL_STYLE = """
            QLabel {
                color: #616161;
                padding: 8px;
                border-top: 1px solid #E0E0E0;
                background-color: #FAFAFA;
                font-size: 11px;
            }
        """
        
        # 优化文本输入框样式
        self.TEXT_EDIT_STYLE = """
            QTextEdit {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #E3F2FD;
                selection-color: #1976D2;
            }
            QTextEdit:focus {
                border: 1px solid #2196F3;
            }
        """
        
        # 优化标签样式
        self.LABEL_STYLE = """
            QLabel {
                color: #424242;
                font-weight: bold;
                padding: 8px 0;
                font-size: 13px;
            }
        """
        
        # 优化标签页样式
        self.TAB_STYLE = """
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 10px 15px;
                margin-right: 2px;
                color: #757575;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
                color: #2196F3;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #F5F5F5;
                color: #424242;
            }
        """
        
        # 添加滚动条样式
        self.SCROLLBAR_STYLE = """
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9E9E9E;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #F5F5F5;
                height: 10px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #BDBDBD;
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #9E9E9E;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """
        
        # 添加菜单样式
        self.MENU_STYLE = """
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px 0;
            }
            QMenu::item {
                padding: 8px 25px;
                border: none;
                color: #424242;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QMenu::item:disabled {
                color: #BDBDBD;
            }
            QMenu::separator {
                height: 1px;
                background: #E0E0E0;
                margin: 5px 0;
            }
        """
        
        # 添加对话框样式
        self.DIALOG_STYLE = """
            QDialog {
                background-color: white;
                border-radius: 4px;
            }
            QDialog QLabel {
                color: #424242;
            }
            QDialog QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                selection-background-color: #E3F2FD;
                selection-color: #1976D2;
            }
            QDialog QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """
        
        self.setWindowTitle("灯塔狩猎者 (DTGO) by 小艾搞安全")
        self.setGeometry(100, 100, 1200, 800)
        self.config = Config()
        self.successful_beacons = self.config.get_successful_beacons()
        self.active_threads = []
        self.scanning = False
        self.task_threads = []
        self.max_status_length = 50
        self.task_running = False
        self.active_beacon_tasks = {}
        self.task_records = self.config.get_task_records()
        self.status_check_timer = QTimer()
        self.status_check_timer.setInterval(120000)
        self.status_check_timer.timeout.connect(self.check_running_tasks)
        self.status_check_timer.start()
        
        # 设置应用全局样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #F5F5F5;
            }}
            QWidget {{
                font-family: "Microsoft YaHei", "Segoe UI", Arial;
                font-size: 12px;
            }}
            {self.SCROLLBAR_STYLE}
            {self.MENU_STYLE}
        """)
        
        self.initUI()
        self.load_cached_beacons()
        
    def closeEvent(self, event):
        # 停止所有活动线程
        self.scanning = False
        for thread in self.active_threads:
            if hasattr(thread, 'stop'):
                thread.stop()
            if thread.isRunning():
                thread.wait()
                
        # 停止所有任务线程
        for thread in self.task_threads:
            if hasattr(thread, 'stop'):
                thread.stop()
            if thread.isRunning():
                thread.wait()
                
        # 停止所有任务
        for task_manager in self.active_beacon_tasks.values():
            task_manager.stop()
            task_manager.wait()
        self.status_check_timer.stop()  # 停止定时器
        event.accept()
        
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        
        # 左侧布局
        left_layout = QVBoxLayout()
        
        # 顶部按钮和进度条布局
        top_layout = QHBoxLayout()
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet(self.BUTTON_STYLE)
        
        self.fofa_scan_btn = QPushButton("扫描灯塔")
        self.fofa_scan_btn.clicked.connect(self.start_scan)
        self.fofa_scan_btn.setStyleSheet(self.BUTTON_STYLE)
        
        # 添加"添加灯塔"按钮
        add_beacon_btn = QPushButton("添加灯塔")
        add_beacon_btn.clicked.connect(self.show_add_beacon_dialog)
        add_beacon_btn.setStyleSheet(self.BUTTON_STYLE)
        
        self.stop_scan_btn = QPushButton("终止扫描")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        self.stop_scan_btn.setStyleSheet(self.BUTTON_STYLE)
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setStyleSheet(self.PROGRESS_BAR_STYLE)
        
        # 按新顺序添加按钮到布局
        top_layout.addWidget(settings_btn)
        top_layout.addWidget(self.fofa_scan_btn)
        top_layout.addWidget(add_beacon_btn)  # 移到终止扫描前面
        top_layout.addWidget(self.stop_scan_btn)
        top_layout.addWidget(self.scan_progress)
        left_layout.addLayout(top_layout)
        
        # 灯塔列表和目标输入区域的水平布局
        middle_layout = QHBoxLayout()
        
        # 灯塔列表
        beacon_layout = QVBoxLayout()
        beacon_label = QLabel("灯塔列表")
        self.beacon_list = QListWidget()
        self.beacon_list.setStyleSheet(self.LIST_STYLE)
        self.beacon_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.beacon_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.beacon_list.customContextMenuRequested.connect(self.show_beacon_context_menu)
        beacon_layout.addWidget(beacon_label)
        beacon_layout.addWidget(self.beacon_list)
        middle_layout.addLayout(beacon_layout)
        
        # 目标输入区域
        target_layout = QVBoxLayout()
        target_header = QHBoxLayout()
        submit_btn = QPushButton("提交任务")
        submit_btn.clicked.connect(self.submit_tasks)
        submit_btn.setStyleSheet(self.BUTTON_STYLE)
        target_label = QLabel("目标列表")
        target_header.addWidget(submit_btn)
        target_header.addWidget(target_label)
        target_header.addStretch()
        
        self.target_input = QTextEdit()
        target_layout.addLayout(target_header)
        target_layout.addWidget(self.target_input)
        middle_layout.addLayout(target_layout)
        
        left_layout.addLayout(middle_layout)
        
        # 结果标签页
        self.result_tabs = QTabWidget()
        self.asset_table = QTableWidget()
        self.domain_table = QTableWidget()
        self.leak_table = QTableWidget()
        
        # 设置表格样式
        for table in [self.asset_table, self.domain_table, self.leak_table]:
            table.setStyleSheet(self.TABLE_STYLE)
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
        
        self.setup_tables()
        
        self.result_tabs.addTab(self.asset_table, "资产列表")
        self.result_tabs.addTab(self.domain_table, "子域名")
        self.result_tabs.addTab(self.leak_table, "信息泄露")
        left_layout.addWidget(self.result_tabs)
        
        # 状态栏
        self.status_label = QLabel()
        self.status_label.setStyleSheet(self.STATUS_LABEL_STYLE)
        left_layout.addWidget(self.status_label)
        
        # 添加左侧布局到主布局
        main_layout.addLayout(left_layout, stretch=2)
        
        # 右侧任务记录列表
        task_layout = QVBoxLayout()
        task_label = QLabel("任务记录")
        self.task_list = QListWidget()
        self.task_list.setStyleSheet(self.LIST_STYLE)
        self.task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.show_task_context_menu)
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_list)
        
        # 添加右侧布局到主布局
        main_layout.addLayout(task_layout, stretch=1)
        
        central_widget.setLayout(main_layout)
        
        # 加载任务记录
        self.load_task_records()
        
        # 应用标签样式
        beacon_label.setStyleSheet(self.LABEL_STYLE)
        target_label.setStyleSheet(self.LABEL_STYLE)
        task_label.setStyleSheet(self.LABEL_STYLE)
        
        # 应用文本输入框样式
        self.target_input.setStyleSheet(self.TEXT_EDIT_STYLE)
        
        # 应用标签页样式
        self.result_tabs.setStyleSheet(self.TAB_STYLE)
        
    def setup_tables(self):
        self.asset_table.setColumnCount(5)
        self.asset_table.setHorizontalHeaderLabels(["网站", "标题", "IP", "Server", "指纹"])
        
        self.domain_table.setColumnCount(3)
        self.domain_table.setHorizontalHeaderLabels(["域名", "类型", "IP"])
        
        self.leak_table.setColumnCount(2)
        self.leak_table.setHorizontalHeaderLabels(["URL", "标题"])
        
        for table in [self.asset_table, self.domain_table, self.leak_table]:
            table.horizontalHeader().setStretchLastSection(True)

    def show_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.setStyleSheet(self.DIALOG_STYLE)  # 应用对话框样式
        dialog.exec()
        
    def start_scan(self):
        fofa_key = self.config.get_fofa_key()
        if not fofa_key:
            QMessageBox.warning(self, "警告", "请在设置中配置FOFA API Key")
            return
            
        self.scanning = True
        self.stop_scan_btn.setEnabled(True)
        self.fofa_scan_btn.setEnabled(False)
        self.scan_progress.setValue(0)
        
        self.fofa_thread = FofaThread(fofa_key)
        self.fofa_thread.progress_signal.connect(self.update_status)
        self.fofa_thread.progress_value.connect(self.scan_progress.setValue)
        self.fofa_thread.finished_signal.connect(self.handle_fofa_results)
        self.active_threads.append(self.fofa_thread)
        self.fofa_thread.start()
        
    def stop_scan(self):
        self.scanning = False
        self.stop_scan_btn.setEnabled(False)
        self.fofa_scan_btn.setEnabled(True)
        self.status_label.setText("扫描已终止")
        self.scan_progress.setValue(0)
        
        # 终止并清理所有活动线程
        for thread in self.active_threads:
            if hasattr(thread, 'stop'):
                thread.stop()
            if thread.isRunning():
                thread.wait(100)  # 等待最多100ms
                thread.terminate()  # 强制终止
                thread.wait()  # 等待线程结束
                
        self.active_threads.clear()
        
    def handle_fofa_results(self, results):
        if not self.scanning:
            return
            
        self.beacon_list.clear()
        total_targets = len(results)
        for i, result in enumerate(results):
            if not self.scanning:
                break
            target = f"{result[0]}"
            self.try_login(target, total_targets, i)
        
    def try_login(self, target, total_targets, current_index):
        if not self.scanning:
            return
            
        login_thread = LoginThread(target, total_targets, current_index)
        login_thread.progress_signal.connect(self.update_status)
        login_thread.progress_value.connect(self.scan_progress.setValue)
        login_thread.success_signal.connect(self.handle_login_success)
        self.active_threads.append(login_thread)
        login_thread.start()
        
    def handle_login_success(self, beacon_info):
        self.successful_beacons[beacon_info["target"]] = beacon_info
        self.beacon_list.addItem(beacon_info["target"])
        self.config.save_successful_beacons(self.successful_beacons)
        
    def submit_tasks(self):
        """提交任务"""
        selected_items = self.beacon_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择灯塔")
            return
            
        targets = self.target_input.toPlainText().strip().split('\n')
        targets = [t.strip() for t in targets if t.strip()]  # 清理空行
        if not targets:
            QMessageBox.warning(self, "警告", "请输入目标")
            return
            
        # 获取可用的灯塔列表（优先选择没有任务的灯塔）
        available_beacons = []
        for item in selected_items:
            beacon_target = item.text()
            if beacon_target in self.successful_beacons:
                is_busy = beacon_target in self.active_beacon_tasks
                available_beacons.append((beacon_target, is_busy))
        
        # 按是否繁忙排序，空闲的灯塔优先
        available_beacons.sort(key=lambda x: x[1])
        
        if not available_beacons:
            QMessageBox.warning(self, "警告", "没有可用的灯塔")
            return
        
        # 分配任务
        task_assignments = {}  # {beacon_target: [targets]}
        beacon_index = 0
        beacon_count = len(available_beacons)
        
        for target in targets:
            # 选择下一个可用的灯塔
            beacon_target = available_beacons[beacon_index][0]
            
            # 初始化任务列表
            if beacon_target not in task_assignments:
                task_assignments[beacon_target] = []
            
            # 添加任务
            task_assignments[beacon_target].append(target)
            
            # 更新灯塔索引
            beacon_index = (beacon_index + 1) % beacon_count
        
        # 构建确认信息
        info_text = "任务分配情况：\n\n"
        for beacon_target, target_list in task_assignments.items():
            status = "（正在运行任务）" if beacon_target in self.active_beacon_tasks else "（空闲）"
            info_text += f"{beacon_target}{status}:\n"
            for target in target_list:
                info_text += f"  - {target}\n"
            info_text += "\n"
        
        # 使用自定义确认对话框
        dialog = TaskConfirmDialog(info_text, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for beacon_target, target_list in task_assignments.items():
                beacon_info = self.successful_beacons[beacon_target]
                task_manager = TaskManager(beacon_info, target_list)
                
                # 连接信号
                task_manager.progress_signal.connect(self.update_status)
                task_manager.result_signal.connect(self.handle_task_results)
                task_manager.error_signal.connect(self.update_status)
                task_manager.token_expired_signal.connect(self.handle_token_expired)
                task_manager.task_created_signal.connect(
                    lambda t, b=beacon_target: self.handle_task_created(b, t)
                )
                task_manager.task_completed_signal.connect(
                    lambda t, b=beacon_target: self.handle_task_completed(b, t)
                )
                
                # 启动任务
                task_manager.start()
                
                # 更新灯塔状态
                self.active_beacon_tasks[beacon_target] = task_manager
                self.update_beacon_item_color(beacon_target)
            
            self.status_label.setText(f"已提交 {len(targets)} 个任务到 {len(task_assignments)} 个灯塔")

    def handle_task_created(self, beacon_target, task_id):
        """处理新建任务"""
        if beacon_target not in self.task_records:
            self.task_records[beacon_target] = {}
        
        self.task_records[beacon_target][task_id] = "运行中"
        self.config.save_task_records(self.task_records)
        
        # 添加到任务列表
        item = QListWidgetItem(f"{beacon_target} => {task_id} [运行中]")
        self.set_task_item_color(item, "运行中")
        self.task_list.addItem(item)

    def handle_task_completed(self, beacon_target, task_id):
        """处理任务完成"""
        if beacon_target in self.task_records:
            self.task_records[beacon_target][task_id] = "已结束"
            self.config.save_task_records(self.task_records)
            
            # 更新任务列表中的状态
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                if f"{beacon_target} => {task_id}" in item.text():
                    item.setText(f"{beacon_target} => {task_id} [已结束]")
                    self.set_task_item_color(item, "已结束")
                    break

    def handle_task_results(self, results):
        # 更新资产表格，避免重复添加
        existing_assets = set()
        for row in range(self.asset_table.rowCount()):
            existing_assets.add(self.asset_table.item(row, 0).text())
        
        # 更新资产表格
        for site_info in results["assets"]:
            site, title, ip, server, finger = site_info  # 解包五个值
            if site not in existing_assets:
                row = self.asset_table.rowCount()
                self.asset_table.insertRow(row)
                self.asset_table.setItem(row, 0, QTableWidgetItem(site))
                self.asset_table.setItem(row, 1, QTableWidgetItem(title))
                self.asset_table.setItem(row, 2, QTableWidgetItem(ip))
                self.asset_table.setItem(row, 3, QTableWidgetItem(server))
                self.asset_table.setItem(row, 4, QTableWidgetItem(finger))
                existing_assets.add(site)
            
        # 更新子域名表格，避免重复添加
        existing_domains = set()
        for row in range(self.domain_table.rowCount()):
            existing_domains.add(self.domain_table.item(row, 0).text())
        
        # 更新子域名表格
        for domain_info in results.get("domains", []):
            domain, type_, ips = domain_info
            if domain not in existing_domains:
                row = self.domain_table.rowCount()
                self.domain_table.insertRow(row)
                self.domain_table.setItem(row, 0, QTableWidgetItem(domain))
                self.domain_table.setItem(row, 1, QTableWidgetItem(type_))
                self.domain_table.setItem(row, 2, QTableWidgetItem(ips))
                existing_domains.add(domain)
            
        # 更新泄露表格，避免重复添加
        existing_leaks = set()
        for row in range(self.leak_table.rowCount()):
            existing_leaks.add(self.leak_table.item(row, 0).text())
        
        # 更新泄露表格
        for url, title in results["leaks"]:
            if url not in existing_leaks:
                row = self.leak_table.rowCount()
                self.leak_table.insertRow(row)
                self.leak_table.setItem(row, 0, QTableWidgetItem(url))
                self.leak_table.setItem(row, 1, QTableWidgetItem(title))
                existing_leaks.add(url)
            
        # 自动调整所有表格的列宽
        for table in [self.asset_table, self.domain_table, self.leak_table]:
            table.resizeColumnsToContents()
        
    def load_cached_beacons(self):
        for target in self.successful_beacons:
            item = QListWidgetItem(target)
            self.beacon_list.addItem(item)
            
    def update_status(self, message):
        if "成功" in message or "失败" in message:
            # 截断过长的消息
            if len(message) > self.max_status_length:
                message = message[:self.max_status_length] + "..."
            self.status_label.setText(message)

    def show_beacon_context_menu(self, position):
        menu = QMenu()
        menu.setStyleSheet(self.MENU_STYLE)  # 应用菜单样式
        
        # 添加全选动作
        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self.beacon_list.selectAll)
        menu.addAction(select_all_action)
        
        # 添加复制动作
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self.copy_selected_beacons)
        menu.addAction(copy_action)
        
        # 添加删除动作
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_selected_beacons)
        menu.addAction(delete_action)
        
        # 如果列表不为空，才显示菜单
        if self.beacon_list.count() > 0:
            # 根据是否有选中项启用/禁用复制和删除菜单
            has_selection = len(self.beacon_list.selectedItems()) > 0
            copy_action.setEnabled(has_selection)
            delete_action.setEnabled(has_selection)
            menu.exec(self.beacon_list.mapToGlobal(position))

    def copy_selected_beacons(self):
        selected_items = self.beacon_list.selectedItems()
        if not selected_items:
            return
        
        # 将选中的灯塔地址组合成文本，每个地址一行
        text = "\n".join(item.text() for item in selected_items)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setText(text)
        clipboard.setMimeData(mime_data)
        
        # 显示提示消息
        count = len(selected_items)
        self.status_label.setText(f"已复制 {count} 个灯塔地址到剪贴板")

    def delete_selected_beacons(self):
        # 获取所有选中的项目
        selected_items = self.beacon_list.selectedItems()
        if not selected_items:
            return
        
        # 确认删除
        count = len(selected_items)
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {count} 个灯塔吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除选中的项目
            for item in selected_items:
                target = item.text()
                # 从列表中移除
                self.beacon_list.takeItem(self.beacon_list.row(item))
                # 从存储中移除
                if target in self.successful_beacons:
                    del self.successful_beacons[target]
            
            # 更新配置文件
            self.config.save_successful_beacons(self.successful_beacons)

    def update_beacon_item_color(self, beacon_target):
        """更新灯塔项的颜色"""
        for i in range(self.beacon_list.count()):
            item = self.beacon_list.item(i)
            if item.text() == beacon_target:
                if beacon_target in self.active_beacon_tasks:
                    # 设置为蓝色表示正在执行任务
                    item.setBackground(Qt.GlobalColor.lightGray)
                    item.setForeground(Qt.GlobalColor.blue)
                else:
                    # 恢复默认颜色
                    item.setBackground(Qt.GlobalColor.white)
                    item.setForeground(Qt.GlobalColor.black)
                break

    def handle_token_expired(self, beacon_target):
        """处理token过期"""
        # 从灯塔列表和存储中移除过期的灯塔
        for i in range(self.beacon_list.count()):
            item = self.beacon_list.item(i)
            if item.text() == beacon_target:
                self.beacon_list.takeItem(i)
                if beacon_target in self.successful_beacons:
                    del self.successful_beacons[beacon_target]
                self.config.save_successful_beacons(self.successful_beacons)
                break
        
        self.status_label.setText(f"灯塔 {beacon_target} 认证失败，已移除")

    def load_task_records(self):
        """加载任务记录到列表"""
        self.task_list.clear()
        for beacon, tasks in self.task_records.items():
            for task_id, status in tasks.items():
                item = QListWidgetItem(f"{beacon} => {task_id} [{status}]")
                self.set_task_item_color(item, status)
                self.task_list.addItem(item)

    def set_task_item_color(self, item, status):
        """设置任务项的颜色"""
        if status == "运行中":
            item.setForeground(Qt.GlobalColor.blue)
        elif status == "已结束":
            item.setForeground(Qt.GlobalColor.green)
        else:
            item.setForeground(Qt.GlobalColor.black)

    def show_task_context_menu(self, position):
        menu = QMenu()
        menu.setStyleSheet(self.MENU_STYLE)  # 应用菜单样式
        
        # 添加全选动作
        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self.task_list.selectAll)
        menu.addAction(select_all_action)
        
        # 添加导出动作
        export_action = QAction("导出到XLSX", self)
        export_action.triggered.connect(self.export_selected_tasks)
        menu.addAction(export_action)
        
        # 添加删除动作
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_selected_tasks)
        menu.addAction(delete_action)
        
        if self.task_list.count() > 0:
            has_selection = len(self.task_list.selectedItems()) > 0
            export_action.setEnabled(has_selection)
            delete_action.setEnabled(has_selection)
            menu.exec(self.task_list.mapToGlobal(position))

    def export_selected_tasks(self):
        """导出选中任务的详细结果"""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "导出任务结果",
            "",
            "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_name:
            return
        
        try:
            results = []
            total_items = len(selected_items)
            progress_dialog = QProgressDialog("正在获取任务结果...", "取消", 0, total_items, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            
            for i, item in enumerate(selected_items):
                if progress_dialog.wasCanceled():
                    break
                
                text = item.text()
                beacon, rest = text.split(" => ")
                task_id = rest.split(" [")[0]
                
                if beacon not in self.successful_beacons:
                    continue
                
                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"正在获取任务 {task_id} 的结果...")
                
                # 获取任务结果
                task_result = self.get_task_results(beacon, task_id)
                if task_result:
                    results.append(task_result)
            
            progress_dialog.setValue(total_items)
            
            if results:
                if file_name.endswith('.xlsx'):
                    self.export_to_excel(results, file_name)
                else:
                    self.export_to_csv(results, file_name)
                
                self.status_label.setText(f"已导出 {len(results)} 个任务的结果到 {file_name}")
            else:
                QMessageBox.warning(self, "导出失败", "没有找到可导出的结果")
            
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出失败: {str(e)}")

    def get_task_results(self, beacon, task_id):
        """获取单个任务的所有结果"""
        try:
            headers = {"Token": self.successful_beacons[beacon]["token"]}
            base_url = f"https://{beacon}/api"
            
            # 获取资产列表
            assets_response = requests.get(
                f"{base_url}/site/?page=1&size=1000&task_id={task_id}",
                headers=headers,
                verify=False
            )
            
            # 获取子域名列表
            domains_response = requests.get(
                f"{base_url}/domain/?page=1&size=1000&task_id={task_id}",
                headers=headers,
                verify=False
            )
            
            # 获取信息泄露列表
            leaks_response = requests.get(
                f"{base_url}/fileleak/?page=1&size=1000&task_id={task_id}",
                headers=headers,
                verify=False
            )
            
            return {
                'beacon': beacon,
                'task_id': task_id,
                'assets': assets_response.json().get('items', []) if assets_response.status_code == 200 else [],
                'domains': domains_response.json().get('items', []) if domains_response.status_code == 200 else [],
                'leaks': leaks_response.json().get('items', []) if leaks_response.status_code == 200 else []
            }
        except Exception as e:
            self.status_label.setText(f"获取任务 {task_id} 结果失败: {str(e)}")
            return None

    def export_to_excel(self, results, file_name):
        """导出结果到Excel文件"""
        import pandas as pd
        from datetime import datetime
        
        with pd.ExcelWriter(file_name) as writer:
            # 导出资产列表
            assets_data = []
            for result in results:
                for asset in result['assets']:
                    assets_data.append({
                        '灯塔地址': result['beacon'],
                        '任务ID': result['task_id'],
                        '网站': asset.get('site', ''),
                        '标题': asset.get('title', ''),
                        'IP': asset.get('ip', ''),
                        'Server': asset.get('http_server', ''),
                        '指纹': ', '.join([f"{f['name']}{f.get('version', '')}" for f in asset.get('finger', [])])
                    })
            if assets_data:
                pd.DataFrame(assets_data).to_excel(writer, sheet_name='资产列表', index=False)
            
            # 导出子域名列表
            domains_data = []
            for result in results:
                for domain in result['domains']:
                    domains_data.append({
                        '灯塔地址': result['beacon'],
                        '任务ID': result['task_id'],
                        '域名': domain.get('domain', ''),
                        '类型': domain.get('type', ''),
                        'IP列表': ', '.join(domain.get('ips', []))
                    })
            if domains_data:
                pd.DataFrame(domains_data).to_excel(writer, sheet_name='子域名列表', index=False)
            
            # 导出信息泄露列表
            leaks_data = []
            for result in results:
                for leak in result['leaks']:
                    leaks_data.append({
                        '灯塔地址': result['beacon'],
                        '任务ID': result['task_id'],
                        'URL': leak.get('url', ''),
                        '标题': leak.get('title', '')
                    })
            if leaks_data:
                pd.DataFrame(leaks_data).to_excel(writer, sheet_name='信息泄露列表', index=False)

    def export_to_csv(self, results, file_name):
        """导出结果到CSV文件"""
        base_name = file_name.rsplit('.', 1)[0]
        
        # 导出资产列表
        assets_file = f"{base_name}_assets.csv"
        with open(assets_file, 'w', encoding='utf-8') as f:
            f.write("灯塔地址,任务ID,网站,标题,IP,Server,指纹\n")
            for result in results:
                for asset in result['assets']:
                    finger_str = ','.join([f"{f['name']}{f.get('version', '')}" for f in asset.get('finger', [])])
                    f.write(f"{result['beacon']},{result['task_id']},"
                           f"{asset.get('site', '')},{asset.get('title', '')},"
                           f"{asset.get('ip', '')},{asset.get('http_server', '')},"
                           f"{finger_str}\n")
        
        # 导出子域名列表
        domains_file = f"{base_name}_domains.csv"
        with open(domains_file, 'w', encoding='utf-8') as f:
            f.write("灯塔地址,任务ID,域名,类型,IP列表\n")
            for result in results:
                for domain in result['domains']:
                    ips_str = ','.join(domain.get('ips', []))
                    f.write(f"{result['beacon']},{result['task_id']},"
                           f"{domain.get('domain', '')},{domain.get('type', '')},"
                           f"{ips_str}\n")
        
        # 导出信息泄露列表
        leaks_file = f"{base_name}_leaks.csv"
        with open(leaks_file, 'w', encoding='utf-8') as f:
            f.write("灯塔地址,任务ID,URL,标题\n")
            for result in results:
                for leak in result['leaks']:
                    f.write(f"{result['beacon']},{result['task_id']},"
                           f"{leak.get('url', '')},{leak.get('title', '')}\n")

    def delete_selected_tasks(self):
        """删除选中的任务记录和远程灯塔记录"""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_items)} 条任务记录吗？\n(同时会删除灯塔系统中的任务数据)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                text = item.text()
                beacon, rest = text.split(" => ")
                task_id = rest.split(" [")[0]
                
                # 删除远程灯塔记录
                if beacon in self.successful_beacons:
                    beacon_info = {
                        "target": beacon,
                        "token": self.successful_beacons[beacon]["token"]
                    }
                    task_manager = TaskManager(beacon_info, [])
                    task_manager.progress_signal.connect(self.update_status)
                    task_manager.error_signal.connect(self.update_status)
                    task_manager.token_expired_signal.connect(self.handle_token_expired)
                    
                    if task_manager.delete_task(task_id):
                        self.status_label.setText(f"成功删除灯塔 {beacon} 的任务 {task_id}")
                        # 从本地记录中删除
                        if beacon in self.task_records:
                            if task_id in self.task_records[beacon]:
                                del self.task_records[beacon][task_id]
                            if not self.task_records[beacon]:
                                del self.task_records[beacon]
                        # 从列表中删除
                        self.task_list.takeItem(self.task_list.row(item))
                    else:
                        self.status_label.setText(f"删除灯塔 {beacon} 的任务 {task_id} 失败")
                        continue  # 如果远程删除失败，不删除本地记录
            
            # 保存更新后的记录
            self.config.save_task_records(self.task_records)

    def check_running_tasks(self):
        """检查所有运行中的任务状态"""
        running_tasks = {}  # {beacon: [task_ids]}
        
        # 收集所有运行中的任务
        for beacon, tasks in self.task_records.items():
            running = [task_id for task_id, status in tasks.items() if status == "运行中"]
            if running:
                running_tasks[beacon] = running
        
        if not running_tasks:
            return
            
        # 检查每个灯塔的任务状态
        for beacon, task_ids in running_tasks.items():
            if beacon not in self.successful_beacons:
                continue
                
            try:
                self.check_beacon_tasks(beacon, task_ids)
            except Exception as e:
                self.status_label.setText(f"检查灯塔 {beacon} 任务状态失败: {str(e)}")

    def check_beacon_tasks(self, beacon, task_ids, retry=True):
        """检查单个灯塔的任务状态，支持token过期重试"""
        try:
            url = f"https://{beacon}/api/task/?page=1&size=100"
            headers = {"Token": self.successful_beacons[beacon]["token"]}
            response = requests.get(url, headers=headers, verify=False)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    tasks = {item["_id"]: item["status"] for item in result.get("items", [])}
                    
                    # 更新任务状态
                    for task_id in task_ids:
                        if task_id in tasks and tasks[task_id] == "done":
                            self.update_task_status(beacon, task_id, "已结束")
                elif result.get("code") == 401 and retry:  # token过期
                    # 尝试刷新token
                    if self.refresh_beacon_token(beacon):
                        # 刷新成功，重试检查
                        self.check_beacon_tasks(beacon, task_ids, retry=False)
                    else:
                        # 刷新失败，移除灯塔
                        self.handle_token_expired(beacon)
        except Exception as e:
            if retry:
                # 发生错误时尝试刷新token重试
                if self.refresh_beacon_token(beacon):
                    self.check_beacon_tasks(beacon, task_ids, retry=False)
                else:
                    raise e
            else:
                raise e

    def refresh_beacon_token(self, beacon):
        """刷新灯塔token"""
        try:
            url = f"https://{beacon}/api/user/login"
            data = {"username": "admin", "password": "arlpass"}
            response = requests.post(url, json=data, verify=False, timeout=5)
            result = response.json()
            
            if result.get("code") == 200:
                self.successful_beacons[beacon]["token"] = result["data"]["token"]
                self.config.save_successful_beacons(self.successful_beacons)
                return True
            return False
        except:
            return False

    def update_task_status(self, beacon, task_id, status):
        """更新任务状态"""
        # 更新内存中的记录
        if beacon in self.task_records and task_id in self.task_records[beacon]:
            self.task_records[beacon][task_id] = status
            
            # 更新列表显示
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                if f"{beacon} => {task_id}" in item.text():
                    item.setText(f"{beacon} => {task_id} [{status}]")
                    self.set_task_item_color(item, status)
                    break
            
            # 保存到配置文件
            self.config.save_task_records(self.task_records)

    def show_add_beacon_dialog(self):
        """显示添加灯塔对话框"""
        dialog = AddBeaconDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            inputs = dialog.get_inputs()
            self.add_beacon(inputs)

    def add_beacon(self, inputs):
        """添加新的灯塔"""
        address = inputs['address']
        
        # 检查是否已存在
        if address in self.successful_beacons:
            QMessageBox.warning(
                self,
                "添加失败",
                "该灯塔已在列表中，无需重复添加。",
                QMessageBox.StandardButton.Ok
            )
            return
        
        try:
            # 尝试登录
            url = f"https://{address}/api/user/login"
            data = {
                "username": inputs['username'],
                "password": inputs['password']
            }
            response = requests.post(url, json=data, verify=False, timeout=5)
            result = response.json()
            
            if result.get("code") == 200:
                # 登录成功，添加到列表
                self.successful_beacons[address] = {
                    "token": result["data"]["token"]
                }
                self.config.save_successful_beacons(self.successful_beacons)
                
                # 更新界面
                self.beacon_list.addItem(address)
                QMessageBox.information(
                    self,
                    "添加成功",
                    "灯塔添加成功！",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "登录失败",
                    "用户名或密码错误。",
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "连接失败",
                f"无法连接到灯塔：{str(e)}",
                QMessageBox.StandardButton.Ok
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DTGO()
    window.show()
    sys.exit(app.exec()) 