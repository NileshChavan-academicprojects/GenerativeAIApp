#!/usr/bin/env python3
import sys, os, re, time, queue, signal, subprocess, threading, tempfile
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal, QObject, QRegExp
from PyQt5.QtGui import QTextCursor, QFont, QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QTextEdit, QPushButton, QMessageBox, QDockWidget,
                             QAction, QTabWidget, QComboBox, QWizard, QWizardPage,
                             QLabel, QLineEdit, QSlider, QFileDialog, QHBoxLayout,
                             QToolBar, QDialog, QInputDialog, QListWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView
try:
    QtCore.qRegisterMetaType(QTextCursor, "QTextCursor")
except AttributeError:
    print("Warning: qRegisterMetaType not available; QTextCursor may not be properly registered.")
import google.generativeai as genai

class SecurityError(Exception):
    pass

class APIError(Exception):
    pass

class WorkerSignals(QObject):
    result = pyqtSignal(str)
    error = pyqtSignal(str)
    ui_update = pyqtSignal(bool)
    code_modification = pyqtSignal(str)

class CodeEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setLineWrapMode(QTextEdit.NoWrap)

class ProjectWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.addPage(self.createIntroPage())
        self.addPage(self.createTemplatePage())
        self.addPage(self.createDependencyPage())
        self.addPage(self.createConclusionPage())
    def createIntroPage(self):
        page = QWizardPage()
        page.setTitle("Project Information")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter Project Name:"))
        self.project_name = QLineEdit()
        layout.addWidget(self.project_name)
        page.setLayout(layout)
        return page
    def createTemplatePage(self):
        page = QWizardPage()
        page.setTitle("Project Template")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a template (stubbed):"))
        self.template = QLineEdit("default")
        layout.addWidget(self.template)
        page.setLayout(layout)
        return page
    def createDependencyPage(self):
        page = QWizardPage()
        page.setTitle("Dependency Management")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Dependencies will be auto-installed (stubbed)."))
        page.setLayout(layout)
        return page
    def createConclusionPage(self):
        page = QWizardPage()
        page.setTitle("Finish")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Click Finish to scaffold your project."))
        page.setLayout(layout)
        return page
    def accept(self):
        project_name = self.project_name.text()
        QMessageBox.information(self, "Project Created", f"Project '{project_name}' created successfully (stub).")
        super().accept()

class ActivityLogWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Activity log...")
    def log(self, message: str):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        self.append(f"{timestamp} {message}")
    def exportLogs(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt)")
        if fname:
            with open(fname, "w") as f:
                f.write(self.toPlainText())
            QMessageBox.information(self, "Export Logs", "Logs exported successfully.")

class GenerativeAIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant Pro")
        self.setGeometry(100, 100, 1400, 900)
        self.dark_mode = False
        self.running_tasks = []
        self.history = []
        self.history_index = -1
        self.security_level = 3
        self.init_api()
        self.init_models()
        self.init_ui()
        self.init_workers()
        self.init_menu()
        self.init_toolbar()
        self.init_auto_save()
        self.init_command_palette()
        self.activity_log("Application started.")
    def init_api(self):
        self.api_key = os.getenv('GOOGLE_API_KEY_2')
        if not self.api_key:
            raise APIError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=self.api_key)
        self.primary_model_name = "Gemini Pro"
        self.safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"}]
    def init_models(self):
        self.available_models = {"Gemini Pro": genai.GenerativeModel('gemini-pro'), "GPT-4": None, "Claude": None, "Mistral": None}
        self.selected_model = "Gemini Pro"
    def init_ui(self):
        self.create_tabs()
        self.create_terminal()
        self.create_dock_widgets()
        self.setup_styles()
        self.apply_current_style()
    def create_tabs(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.chat_tab = QWidget()
        chat_layout = QVBoxLayout(self.chat_tab)
        self.text_entry = QTextEdit()
        self.text_entry.setPlaceholderText("Enter your query...")
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.safe_generate_content)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        chat_layout.addWidget(self.text_entry)
        chat_layout.addWidget(self.generate_btn)
        chat_layout.addWidget(self.output_area)
        self.tab_widget.addTab(self.chat_tab, "Chat")
        self.live_preview_tab = QWidget()
        live_layout = QVBoxLayout(self.live_preview_tab)
        self.live_preview = QWebEngineView()
        live_layout.addWidget(self.live_preview)
        self.tab_widget.addTab(self.live_preview_tab, "Live Preview")
        self.code_editor_tab = QWidget()
        code_layout = QVBoxLayout(self.code_editor_tab)
        self.edit_instructions = QLineEdit()
        self.edit_instructions.setPlaceholderText("Enter instructions for code modifications")
        code_layout.addWidget(self.edit_instructions)
        self.apply_changes_btn = QPushButton("Apply Changes")
        self.apply_changes_btn.clicked.connect(self.apply_code_changes)
        code_layout.addWidget(self.apply_changes_btn)
        self.code_editor = CodeEditor()
        self.code_editor.setPlaceholderText("Code will be displayed here...")
        code_layout.addWidget(self.code_editor)
        self.run_external_btn = QPushButton("Run Python Externally")
        self.run_external_btn.clicked.connect(self.run_external_python_code)
        code_layout.addWidget(self.run_external_btn)
        self.tab_widget.addTab(self.code_editor_tab, "Code Editor")
    def create_terminal(self):
        self.terminal_dock = QDockWidget("Terminal", self)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal_dock.setWidget(self.terminal)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)
    def create_dock_widgets(self):
        self.log_dock = QDockWidget("Activity Log", self)
        self.log_widget = ActivityLogWidget()
        self.log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.log_dock)
        self.file_explorer_dock = QDockWidget("File Explorer", self)
        self.file_explorer = QListWidget()
        for fname in ["index.html", "style.css", "app.js", "script.py"]:
            self.file_explorer.addItem(fname)
        self.file_explorer_dock.setWidget(self.file_explorer)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_explorer_dock)
    def setup_styles(self):
        self.style_settings = {"light": {"background": "#FFFFFF", "text": "#000000", "button": "#007ACC", "border": "#CCCCCC", "terminal_bg": "#F0F0F0", "terminal_text": "#333333"}, "dark": {"background": "#2D2D2D", "text": "#FFFFFF", "button": "#1E1E1E", "border": "#3E3E3E", "terminal_bg": "#1E1E1E", "terminal_text": "#CCCCCC"}, "high_contrast": {"background": "#000000", "text": "#FFFF00", "button": "#333333", "border": "#FFFFFF", "terminal_bg": "#000000", "terminal_text": "#FFFF00"}}
    def apply_current_style(self):
        mode = "high_contrast" if self.dark_mode and getattr(self, "high_contrast", False) else ("dark" if self.dark_mode else "light")
        style = self.style_settings[mode]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {style['background']};
                color: {style['text']};
            }}
            QTextEdit {{
                background-color: {style['background']};
                border: 1px solid {style['border']};
                padding: 5px;
            }}
            QPushButton {{
                background-color: {style['button']};
                color: {style['text']};
                padding: 8px;
                border-radius: 4px;
            }}
            QDockWidget::title {{
                background: {style['button']};
                padding: 4px;
            }}
        """)
        self.terminal.setStyleSheet(f"""
            background-color: {style['terminal_bg']};
            color: {style['terminal_text']};
            font-family: Consolas;
            font-size: 12pt;
            border: none;
        """)
    def init_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        self.model_selector = QComboBox()
        self.model_selector.addItems(list(self.available_models.keys()))
        self.model_selector.currentTextChanged.connect(self.change_model)
        toolbar.addWidget(QLabel(" Model: "))
        toolbar.addWidget(self.model_selector)
        toolbar.addSeparator()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search code/files...")
        self.search_bar.returnPressed.connect(self.perform_search)
        toolbar.addWidget(QLabel(" Search: "))
        toolbar.addWidget(self.search_bar)
    def init_auto_save(self):
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_code)
        self.auto_save_timer.start(60000)
    def auto_save_code(self):
        code = self.code_editor.toPlainText()
        if code:
            autosave_path = os.path.join(tempfile.gettempdir(), "autosave_code.txt")
            with open(autosave_path, "w") as f:
                f.write(code)
            self.activity_log(f"Code auto-saved to {autosave_path}.")
    def init_command_palette(self):
        shortcut = QAction(self)
        shortcut.setShortcut("Ctrl+Shift+P")
        shortcut.triggered.connect(self.show_command_palette)
        self.addAction(shortcut)
    def show_command_palette(self):
        commands = ["Reload Live Preview", "Auto Save Now", "Start Collaboration", "Load Plugin"]
        cmd, ok = QInputDialog.getItem(self, "Command Palette", "Select a command:", commands, 0, False)
        if ok and cmd:
            if cmd == "Reload Live Preview":
                self.update_live_preview_from_code_editor()
            elif cmd == "Auto Save Now":
                self.auto_save_code()
            elif cmd == "Start Collaboration":
                QMessageBox.information(self, "Collaboration", "Collaboration session started (stub).")
            elif cmd == "Load Plugin":
                fname, _ = QFileDialog.getOpenFileName(self, "Load Plugin", "", "Python Files (*.py)")
                if fname:
                    QMessageBox.information(self, "Plugin", f"Plugin {fname} loaded (stub).")
            self.activity_log(f"Command executed: {cmd}")
    def init_workers(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.signals = WorkerSignals()
        self.signals.code_modification.connect(self.handle_code_modification_result)
        self.queue = queue.Queue()
        self.init_signals()
        self.start_queue_processor()
    def init_signals(self):
        self.signals.result.connect(self.handle_result)
        self.signals.error.connect(self.show_error)
        self.signals.ui_update.connect(self.toggle_ui_state)
        self.text_entry.textChanged.connect(self.save_to_history)
    def start_queue_processor(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_terminal_queue)
        self.timer.start(50)
    def safe_generate_content(self):
        try:
            self.validate_input()
            self.toggle_ui_state(False)
            future = self.executor.submit(self.generate_content_worker)
            self.running_tasks.append(future)
        except Exception as e:
            self.signals.error.emit(str(e))
    def generate_content_worker(self):
        try:
            prompt = self.text_entry.toPlainText().strip()
            output_text = ""
            model_used = self.selected_model
            try:
                if model_used == "Gemini Pro":
                    response = self.available_models[model_used].generate_content(prompt, safety_settings=self.safety_settings)
                    output_text = response.text
                else:
                    time.sleep(1)
                    output_text = f"Simulated output from {model_used} for prompt: {prompt}"
                self.activity_log(f"Generated content using {model_used}.")
            except Exception as primary_error:
                self.activity_log(f"{model_used} failed ({primary_error}); falling back to Gemini Pro.")
                response = self.available_models["Gemini Pro"].generate_content(prompt, safety_settings=self.safety_settings)
                output_text = response.text
            self.signals.result.emit(output_text)
        except Exception as e:
            self.signals.error.emit(f"API Error: {str(e)}")
        finally:
            self.signals.ui_update.emit(True)
    def handle_result(self, text: str):
        self.output_area.clear()
        self.animate_text_output(text)
    def animate_text_output(self, text: str):
        self.output_area.clear()
        index = 0
        def update_text():
            nonlocal index
            if index < len(text):
                current_text = text[:index + 1]
                self.output_area.setPlainText(current_text)
                cursor = self.output_area.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.output_area.setTextCursor(cursor)
                self.output_area.ensureCursorVisible()
                index += 1
                QTimer.singleShot(20, update_text)
            else:
                self.process_code_blocks(text)
        update_text()
    def process_code_blocks(self, text: str):
        code_blocks = self.extract_code_blocks(text)
        html_code = ""
        css_code = ""
        js_code = ""
        for lang, blocks in code_blocks.items():
            if lang == 'html':
                for block in blocks:
                    html_code += block.strip() + "\n"
            elif lang == 'css':
                for block in blocks:
                    css_code += block.strip() + "\n"
            elif lang == 'javascript':
                for block in blocks:
                    js_code += block.strip() + "\n"
            elif lang in ['python', 'bash']:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                for i, block in enumerate(blocks):
                    ext = "py" if lang == "python" else "sh"
                    file_path = os.path.join(desktop_path, f"code_{i+1}.{ext}")
                    with open(file_path, 'w') as f:
                        f.write(block.strip())
                    cmd = f'python "{file_path}"' if lang == 'python' else f'bash "{file_path}"'
                    self.execute_safe_command(cmd)
            else:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                for i, block in enumerate(blocks):
                    file_path = os.path.join(desktop_path, f"code_{i+1}.{lang}")
                    with open(file_path, 'w') as f:
                        f.write(block.strip())
                    self.queue.put(f"{lang.upper()} file created: {file_path}")
        if html_code or css_code or js_code:
            if not html_code:
                html_code = "<div></div>"
            if "<html" not in html_code.lower():
                combined_html = f"""<html>
<head>
<style>
{css_code}
</style>
</head>
<body>
{html_code}
<script>
{js_code}
</script>
</body>
</html>"""
            else:
                combined_html = html_code
                if css_code:
                    combined_html = re.sub(r'(</head>)', f'<style>{css_code}</style>\\1', combined_html, flags=re.IGNORECASE)
                if js_code:
                    combined_html = re.sub(r'(</body>)', f'<script>{js_code}</script>\\1', combined_html, flags=re.IGNORECASE)
            self.live_preview.setHtml(combined_html)
            self.queue.put("Live preview updated with web code.")
            self.animate_code_update(combined_html)
            self.activity_log("Code editor updated with generated web code.")
    def extract_code_blocks(self, text: str) -> Dict[str, List[str]]:
        patterns = {
            'python': r'```python\s*(.*?)\s*```',
            'javascript': r'```javascript\s*(.*?)\s*```',
            'html': r'```html\s*(.*?)\s*```',
            'css': r'```css\s*(.*?)\s*```',
            'bash': r'```bash\s*(.*?)\s*```'
        }
        return {lang: re.findall(pattern, text, re.DOTALL) for lang, pattern in patterns.items()}
    def apply_code_changes(self):
        instructions = self.edit_instructions.text().strip()
        if not instructions:
            QMessageBox.warning(self, "No Instructions", "Please enter instructions for code modification.")
            return
        self.apply_changes_btn.setEnabled(False)
        current_code = self.code_editor.toPlainText()
        self.executor.submit(self.apply_code_changes_worker, instructions, current_code)
    def apply_code_changes_worker(self, instructions, current_code):
        prompt = (f"Please update the following code according to these instructions:\n\nInstructions:\n{instructions}\n\nCode:\n{current_code}")
        try:
            response = self.available_models["Gemini Pro"].generate_content(prompt, safety_settings=self.safety_settings)
            new_code = response.text
        except Exception as e:
            self.signals.error.emit(f"Error modifying code: {e}")
            return
        self.signals.code_modification.emit(new_code)
    def handle_code_modification_result(self, new_code):
        self.animate_code_update(new_code)
        self.apply_changes_btn.setEnabled(True)
        self.activity_log("Code editor updated with modifications.")
    def animate_code_update(self, new_code):
        self.code_editor.clear()
        lines = new_code.splitlines()
        index = 0
        def update_line():
            nonlocal index
            if index < len(lines):
                current_text = "\n".join(lines[:index + 1])
                self.code_editor.setPlainText(current_text)
                cursor = self.code_editor.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.code_editor.setTextCursor(cursor)
                self.code_editor.ensureCursorVisible()
                index += 1
                QTimer.singleShot(100, update_line)
            else:
                self.update_live_preview_from_code_editor()
        update_line()
    def update_live_preview_from_code_editor(self):
        code = self.code_editor.toPlainText().strip()
        if not code:
            return
        if "<html" not in code.lower():
            code = f"""<html>
<head>
<style></style>
</head>
<body>
{code}
</body>
</html>"""
        self.live_preview.setHtml(code)
        self.activity_log("Live preview updated with edited code.")
    def run_external_python_code(self):
        code = self.code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "No Code", "There is no code to run!")
            return
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
        temp_file.write(code)
        temp_file.close()
        self.activity_log(f"Python code saved to temporary file: {temp_file.name}")
        if sys.platform.startswith('win'):
            command = f'start cmd /k python "{temp_file.name}"'
            subprocess.Popen(command, shell=True)
        elif sys.platform.startswith('linux'):
            command = f'xterm -hold -e python3 "{temp_file.name}"'
            subprocess.Popen(command, shell=True)
        elif sys.platform.startswith('darwin'):
            command = f'osascript -e \'tell application "Terminal" to do script "python3 \\"{temp_file.name}\\""\'' 
            subprocess.Popen(command, shell=True)
        else:
            QMessageBox.warning(self, "Unsupported OS", "External execution is not supported on this OS.")
    def validate_input(self):
        text = self.text_entry.toPlainText().strip()
        if len(text) < 10:
            raise ValueError("Query too short (minimum 10 characters)")
        if len(text) > 5000:
            raise ValueError("Query too long (maximum 5000 characters)")
        if re.search(r'\b(password|secret|key)\b', text, re.I):
            raise SecurityError("Query contains sensitive keywords")
        self.activity_log("Input validated.")
    def process_terminal_queue(self):
        while not self.queue.empty():
            try:
                output = self.queue.get_nowait()
                self.terminal.append(output)
                self.terminal.ensureCursorVisible()
            except queue.Empty:
                break
    def execute_safe_command(self, command: str):
        unsafe_patterns = ['rm ', 'del ', 'format ', 'chmod', 'sudo']
        if any(p in command for p in unsafe_patterns):
            raise SecurityError("Blocked potentially dangerous command")
        self.queue.put(f"$ {command}")
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        while proc.poll() is None:
            output = proc.stdout.readline()
            if output:
                self.queue.put(output.strip())
    def toggle_dark_mode(self, enabled: bool):
        self.dark_mode = enabled
        self.apply_current_style()
    def toggle_ui_state(self, enabled: bool):
        self.generate_btn.setEnabled(enabled)
        self.text_entry.setReadOnly(not enabled)
        self.generate_btn.setText("Processing..." if not enabled else "Generate")
    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
    def save_to_history(self):
        current_text = self.text_entry.toPlainText()
        if self.history and self.history[-1] == current_text:
            return
        self.history.append(current_text)
        self.history_index = len(self.history) - 1
    def perform_search(self):
        query = self.search_bar.text().strip()
        QMessageBox.information(self, "Search", f"Search for '{query}' not yet implemented (stub).")
        self.activity_log(f"Search performed for: {query}")
    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menubar.addMenu("View")
        self.dark_mode_action = QAction("Dark Mode", self, checkable=True)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)
        self.high_contrast_action = QAction("High Contrast Mode", self, checkable=True)
        self.high_contrast_action.triggered.connect(lambda enabled: self.toggle_dark_mode(enabled))
        view_menu.addAction(self.high_contrast_action)
        project_menu = menubar.addMenu("Project")
        new_project_action = QAction("New Project", self)
        new_project_action.triggered.connect(self.new_project)
        project_menu.addAction(new_project_action)
        start_collab_action = QAction("Start Collaboration", self)
        start_collab_action.triggered.connect(lambda: QMessageBox.information(self, "Collaboration", "Collaboration session started (stub)."))
        project_menu.addAction(start_collab_action)
        load_plugin_action = QAction("Load Plugin", self)
        load_plugin_action.triggered.connect(lambda: QFileDialog.getOpenFileName(self, "Load Plugin", "", "Python Files (*.py)"))
        project_menu.addAction(load_plugin_action)
    def new_project(self):
        wizard = ProjectWizard(self)
        wizard.exec_()
        self.activity_log("New project wizard completed.")
    def change_model(self, model_name: str):
        self.selected_model = model_name
        self.activity_log(f"Selected model changed to {model_name}.")
    def activity_log(self, message: str):
        self.log_widget.log(message)
    def closeEvent(self, event):
        self.executor.shutdown(wait=False)
        os.kill(os.getpid(), signal.SIGTERM)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = GenerativeAIApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Fatal Error", f"Application failed to start:\n{str(e)}")
        sys.exit(1)
