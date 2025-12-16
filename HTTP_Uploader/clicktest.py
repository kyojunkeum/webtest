import sys
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QSpinBox, QComboBox, QCheckBox, QShortcut, QRadioButton, QButtonGroup, QMessageBox, QListWidgetItem, QListWidget, QAbstractItemView
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence, QColor
import pyautogui

# FailSafe 비활성화 (주의: 권장되지 않음)
pyautogui.FAILSAFE = False

class Action:
    def __init__(self, action_type, x=0, y=0, text="", wait_time=0, key=""):
        self.action_type = action_type
        self.x = x
        self.y = y
        self.text = text
        self.wait_time = wait_time
        self.key = key

    def __str__(self):
        if self.action_type == "click":
            return f"클릭: ({self.x}, {self.y})"
        elif self.action_type == "type":
            return f"입력: '{self.text}'"
        elif self.action_type == "wait":
            return f"대기: {self.wait_time}초"
        elif self.action_type == "key":
            return f"키 입력: {self.key}"

class ActionThread(QThread):
    update_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()

    def __init__(self, actions, repeat_count):
        super().__init__()
        self.actions = actions
        self.repeat_count = repeat_count
        self.is_running = True

    def run(self):
        iteration = 0
        while (self.repeat_count == -1 or iteration < self.repeat_count) and self.is_running:
            for idx, action in enumerate(self.actions):
                if not self.is_running:
                    break
                if action.action_type == "click":
                    pyautogui.moveTo(action.x, action.y)
                    pyautogui.click()
                elif action.action_type == "type":
                    pyautogui.write(action.text)
                elif action.action_type == "wait":
                    time.sleep(action.wait_time)
                elif action.action_type == "key":
                    if '+' in action.key:
                        keys = action.key.split('+')
                        pyautogui.hotkey(*keys)
                    else:
                        pyautogui.press(action.key)
                self.update_signal.emit(iteration + 1, idx)
                time.sleep(0.1)  # 작은 지연 추가
            iteration += 1
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemMoved = None

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.itemMoved:
            self.itemMoved(self.currentRow())

class MouseControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.actions = []
        self.action_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('고급 마우스 및 키보드 제어 프로그램')
        self.setGeometry(300, 300, 600, 700)

        layout = QVBoxLayout()

        # 실시간 마우스 좌표 표시
        self.mouse_pos_label = QLabel('마우스 좌표: (0, 0)')
        layout.addWidget(self.mouse_pos_label)

        # 마우스 좌표 갱신 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_mouse_position)
        self.timer.start(100)  # 100ms마다 갱신

        # 동작 선택
        action_layout = QHBoxLayout()
        self.action_combo = QComboBox()
        self.action_combo.addItems(["마우스 클릭", "텍스트 입력", "대기", "키 입력"])
        self.action_combo.currentTextChanged.connect(self.on_action_changed)
        action_layout.addWidget(QLabel('동작:'))
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        # 마우스 좌표 입력
        coord_layout = QHBoxLayout()
        self.x_input = QSpinBox()
        self.x_input.setRange(-9999, 9999)  # 음수 허용
        self.y_input = QSpinBox()
        self.y_input.setRange(-9999, 9999)  # 음수 허용
        coord_layout.addWidget(QLabel('X:'))
        coord_layout.addWidget(self.x_input)
        coord_layout.addWidget(QLabel('Y:'))
        coord_layout.addWidget(self.y_input)
        layout.addLayout(coord_layout)

        # 텍스트 입력
        self.text_input = QLineEdit()
        layout.addWidget(QLabel('텍스트 입력:'))
        layout.addWidget(self.text_input)

        # 대기 시간 설정
        wait_layout = QHBoxLayout()
        self.wait_time = QSpinBox()
        self.wait_time.setRange(0, 3600)
        wait_layout.addWidget(QLabel('대기 시간 (초):'))
        wait_layout.addWidget(self.wait_time)
        layout.addLayout(wait_layout)

        # 키 입력
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("예: shift+f4, ctrl+c, alt+tab")
        key_input_layout = QVBoxLayout()
        key_input_layout.addWidget(QLabel('키 입력 (키 조합은 +로 구분):'))
        key_input_layout.addWidget(self.key_input)
        key_input_info = QLabel("? 키 입력 도움말")
        key_input_info.setStyleSheet("color: blue; text-decoration: underline;")
        key_input_info.mousePressEvent = self.show_key_input_help
        key_input_layout.addWidget(key_input_info)
        layout.addLayout(key_input_layout)

        # 동작 추가 버튼
        self.add_button = QPushButton('동작 추가 (F2)')
        self.add_button.clicked.connect(self.add_action)
        layout.addWidget(self.add_button)

        # 동작 목록
        self.action_list = DraggableListWidget()
        self.action_list.itemMoved = self.on_item_moved
        layout.addWidget(self.action_list)

        # 동작 관리 버튼들
        action_buttons_layout = QHBoxLayout()
        self.delete_button = QPushButton('선택한 동작 삭제')
        self.delete_button.clicked.connect(self.delete_action)
        self.move_up_button = QPushButton('위로 이동')
        self.move_up_button.clicked.connect(self.move_action_up)
        self.move_down_button = QPushButton('아래로 이동')
        self.move_down_button.clicked.connect(self.move_action_down)
        action_buttons_layout.addWidget(self.delete_button)
        action_buttons_layout.addWidget(self.move_up_button)
        action_buttons_layout.addWidget(self.move_down_button)
        layout.addLayout(action_buttons_layout)

        # 반복 설정
        repeat_layout = QHBoxLayout()
        self.repeat_group = QButtonGroup(self)

        self.no_repeat_radio = QRadioButton('반복 안 함')
        self.finite_repeat_radio = QRadioButton('지정된 횟수만큼 반복')
        self.infinite_repeat_radio = QRadioButton('무한 반복')

        self.repeat_group.addButton(self.no_repeat_radio)
        self.repeat_group.addButton(self.finite_repeat_radio)
        self.repeat_group.addButton(self.infinite_repeat_radio)

        repeat_layout.addWidget(self.no_repeat_radio)
        repeat_layout.addWidget(self.finite_repeat_radio)
        repeat_layout.addWidget(self.infinite_repeat_radio)

        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 9999)
        self.repeat_count.setValue(1)
        repeat_layout.addWidget(QLabel('반복 횟수:'))
        repeat_layout.addWidget(self.repeat_count)

        layout.addLayout(repeat_layout)

        # 실행 및 중지 버튼
        run_stop_layout = QHBoxLayout()
        self.run_button = QPushButton('실행')
        self.run_button.clicked.connect(self.run_actions)
        self.stop_button = QPushButton('중지')
        self.stop_button.clicked.connect(self.stop_actions)
        self.stop_button.setEnabled(False)
        run_stop_layout.addWidget(self.run_button)
        run_stop_layout.addWidget(self.stop_button)
        layout.addLayout(run_stop_layout)

        # 진행 상황 표시
        self.progress_label = QLabel('대기 중')
        layout.addWidget(self.progress_label)

        self.setLayout(layout)

        # 단축키 설정
        self.shortcut = QShortcut(QKeySequence("F2"), self)
        self.shortcut.activated.connect(self.capture_mouse_position)

        # 긴급 중지 단축키
        self.emergency_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        self.emergency_shortcut.activated.connect(self.emergency_stop)

        # 초기 상태 설정
        self.on_action_changed(self.action_combo.currentText())

    def show_key_input_help(self, event):
        help_text = """
        키 입력 가이드:
        - 단일 키: 'f4', 'a', '1', 'enter', 'space' 등
        - 키 조합: 'shift+f4', 'ctrl+c', 'alt+tab' 등

        주요 특수 키:
        shift, ctrl, alt, win, enter, space, tab,
        backspace, delete, esc, insert, home, end, pageup, pagedown
        up, down, left, right (화살표 키),
        f1, f2, ..., f12 (펑션 키)

        예시:
        - 'shift+f4'
        - 'ctrl+alt+delete'
        - 'win+r'
        - 'ctrl+shift+esc'
        """
        QMessageBox.information(self, "키 입력 도움말", help_text)

    def update_mouse_position(self):
        x, y = pyautogui.position()
        self.mouse_pos_label.setText(f'마우스 좌표: ({x}, {y})')

    def capture_mouse_position(self):
        x, y = pyautogui.position()
        self.x_input.setValue(x)
        self.y_input.setValue(y)
        if self.action_combo.currentText() == "마우스 클릭":
            self.add_action()

    def on_action_changed(self, action):
        self.x_input.setEnabled(action == "마우스 클릭")
        self.y_input.setEnabled(action == "마우스 클릭")
        self.text_input.setEnabled(action == "텍스트 입력")
        self.wait_time.setEnabled(action == "대기")
        self.key_input.setEnabled(action == "키 입력")

    def add_action(self):
        action_type = self.action_combo.currentText()
        if action_type == "마우스 클릭":
            action = Action("click", self.x_input.value(), self.y_input.value())
        elif action_type == "텍스트 입력":
            action = Action("type", text=self.text_input.text())
        elif action_type == "대기":
            action = Action("wait", wait_time=self.wait_time.value())
        elif action_type == "키 입력":
            action = Action("key", key=self.key_input.text())

        self.actions.append(action)
        self.action_list.addItem(str(action))

    def delete_action(self):
        current_row = self.action_list.currentRow()
        if current_row != -1:
            del self.actions[current_row]
            self.action_list.takeItem(current_row)

    def move_action_up(self):
        current_row = self.action_list.currentRow()
        if current_row > 0:
            self.actions[current_row], self.actions[current_row - 1] = self.actions[current_row - 1], self.actions[current_row]
            item = self.action_list.takeItem(current_row)
            self.action_list.insertItem(current_row - 1, item)
            self.action_list.setCurrentRow(current_row - 1)

    def move_action_down(self):
        current_row = self.action_list.currentRow()
        if current_row < self.action_list.count() - 1:
            self.actions[current_row], self.actions[current_row + 1] = self.actions[current_row + 1], self.actions[current_row]
            item = self.action_list.takeItem(current_row)
            self.action_list.insertItem(current_row + 1, item)
            self.action_list.setCurrentRow(current_row + 1)

    def on_item_moved(self, new_index):
        self.actions.insert(new_index, self.actions.pop(self.action_list.currentRow()))

    def run_actions(self):
        if self.infinite_repeat_radio.isChecked():
            repeat_count = -1  # 무한 반복을 위한 특별한 값
        elif self.finite_repeat_radio.isChecked():
            repeat_count = self.repeat_count.value()
        else:
            repeat_count = 1  # 반복 안 함

        self.action_thread = ActionThread(self.actions, repeat_count)
        self.action_thread.update_signal.connect(self.update_progress)
        self.action_thread.finished_signal.connect(self.on_action_finished)
        self.action_thread.start()

        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_actions(self):
        if self.action_thread:
            self.action_thread.stop()

    def emergency_stop(self):
        self.stop_actions()
        QMessageBox.information(self, "긴급 중지", "프로그램이 긴급 중지되었습니다.")

    def update_progress(self, iteration, action_index):
        self.progress_label.setText(f"반복 {iteration}, 동작 {action_index + 1}/{len(self.actions)}")

        # 현재 실행 중인 동작 하이라이트
        for i in range(self.action_list.count()):
            item = self.action_list.item(i)
            if i == action_index:
                item.setBackground(QColor(255, 255, 0))  # 노란색 배경
            else:
                item.setBackground(QColor(255, 255, 255))  # 흰색 배경

    def on_action_finished(self):
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_label.setText("완료")

        # 모든 동작의 배경색을 원래대로 되돌림
        for i in range(self.action_list.count()):
            item = self.action_list.item(i)
            item.setBackground(QColor(255, 255, 255))  # 흰색 배경

        QMessageBox.information(self, "실행 완료", "모든 동작이 완료되었습니다.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_action()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MouseControlApp()
    ex.show()
    sys.exit(app.exec_())
