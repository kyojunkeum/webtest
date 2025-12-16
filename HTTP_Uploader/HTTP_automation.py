import sys
import os
import gzip
import time
import socket
import threading
import random
import traceback
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterable
from datetime import datetime
from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QFileDialog, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QRadioButton, QPlainTextEdit, QListWidget, QHBoxLayout,
    QVBoxLayout, QScrollArea, QTableWidget, QTableWidgetItem,
    QMessageBox,
)

CRLF = b"\r\n"

# ---- 한글 폰트 설정 (Windows 기준: 맑은 고딕) ----
plt.rcParams["font.family"] = "Malgun Gothic"   # 윈도우 기본 한글폰트
plt.rcParams["axes.unicode_minus"] = False      # 마이너스 깨짐 방지


# ------------------ Core HTTP ------------------

@dataclass
class ClientOptions:
    host: str
    port: int
    path: str
    method: str  # POST/PUT/PATCH/DELETE
    keep_alive: bool
    use_chunked: bool
    chunk_size: int
    chunk_ext: str
    use_gzip: bool
    use_multipart: bool
    extra_headers: Dict[str, str]
    trailing_headers: Dict[str, str]
    connect_timeout: float = 5.0
    read_timeout: float = 5.0
    fire_and_go: bool = True
    http_version: str = "HTTP/1.1"
    body_text: Optional[bytes] = None
    file_path: Optional[str] = None
    multipart_field_name: str = "file"
    multipart_text_fields: Dict[str, str] = field(default_factory=dict)
    multipart_filename_override: Optional[str] = None
    add_x_filename_header: bool = True  # non-multipart 파일명 힌트
    delay_between: float = 0.0          # 전송 간 대기(초)


def parse_kv_lines(raw: str) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        d[k.strip()] = v.strip()
    return d


def build_request_line_and_base_headers(opts: ClientOptions, host_header: Optional[str] = None) -> bytearray:
    first = f"{opts.method} {opts.path} {opts.http_version}".encode("ascii")
    buf = bytearray(first + CRLF)
    host_val = host_header if host_header else f"{opts.host}:{opts.port}"
    buf += f"Host: {host_val}".encode("ascii") + CRLF
    buf += (b"Connection: keep-alive" if opts.keep_alive else b"Connection: close") + CRLF
    return buf


def add_header_lines(buf: bytearray, headers: Dict[str, str]):
    for k, v in headers.items():
        buf += f"{k}: {v}".encode("utf-8") + CRLF


def gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data)


def iter_file_chunks(path: str, chunk_size: int) -> Iterable[bytes]:
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def multipart_iter(
    filespec: Tuple[str, Optional[str], Iterable[bytes]],
    boundary: str,
    text_fields: Dict[str, str],
    filename_override: Optional[str],
    field_name: str,
) -> Iterable[bytes]:
    # 텍스트 필드
    for k, v in text_fields.items():
        yield f"--{boundary}\r\n".encode()
        yield f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        yield v.encode("utf-8")
        yield CRLF

    # 파일 파트
    file_path, mime, stream_iter = filespec
    filename = filename_override or (os.path.basename(file_path) if file_path else "blob")
    mime = mime or "application/octet-stream"
    yield f"--{boundary}\r\n".encode()
    yield f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
    yield f"Content-Type: {mime}\r\n\r\n".encode()
    for chunk in stream_iter:
        yield chunk
    yield CRLF

    # 종료
    yield f"--{boundary}--\r\n".encode()


def trailer_decl_str(trailers: Dict[str, str]) -> Optional[str]:
    if not trailers:
        return None
    return ", ".join(trailers.keys())


class HttpConnection:
    def __init__(self, opts: ClientOptions):
        self.opts = opts
        self.sock: Optional[socket.socket] = None
        self.last_status: Optional[int] = None
        self.last_reason: Optional[str] = None
        self.last_raw_response: Optional[bytes] = None

    def connect(self):
        self.sock = socket.create_connection((self.opts.host, self.opts.port), timeout=self.opts.connect_timeout)
        self.sock.settimeout(self.opts.read_timeout)

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    def _minimal_read_response(self):
        """
        서버에서 오는 HTTP 응답의 맨 앞 부분만 읽어서
        상태코드와 이유문구를 파싱한다.
        실패하면 None 반환.
        """
        try:
            if not self.sock:
                return None
            self.sock.settimeout(1.0)
            data = b""
            # 헤더부(최소 첫 라인 + 몇 줄) 정도만 최대 8KB 읽기
            while b"\r\n\r\n" not in data and len(data) < 8192:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk

            if not data:
                return None

            self.last_raw_response = data

            # 첫 줄 파싱: HTTP/1.1 200 OK
            first_line, *_ = data.split(b"\r\n", 1)
            parts = first_line.split()
            if len(parts) < 2:
                return None

            # parts[1] 이 상태코드
            try:
                status = int(parts[1])
            except ValueError:
                return None

            reason = b" ".join(parts[2:]).decode("ascii", "ignore") if len(parts) > 2 else ""
            self.last_status = status
            self.last_reason = reason
            return status, reason
        except Exception:
            return None

    def send_request_content_length(self, body_iter: Iterable[bytes], declared_len: int, filename_for_header: Optional[str]):
        buf = build_request_line_and_base_headers(self.opts)
        if self.opts.use_gzip:
            buf += b"Content-Encoding: gzip\r\n"
        buf += f"Content-Length: {declared_len}".encode("ascii") + CRLF
        # 비멀티파트 파일 전송 시, 서버가 파일명을 알 수 있도록 헤더 보강
        if filename_for_header and self.opts.add_x_filename_header and "X-Filename" not in self.opts.extra_headers:
            buf += f"X-Filename: {filename_for_header}".encode("utf-8") + CRLF
        if trailer_decl_str(self.opts.trailing_headers):
            buf += b"X-Warning: Trailer headers require chunked encoding\r\n"
        add_header_lines(buf, self.opts.extra_headers)
        buf += CRLF
        assert self.sock
        self.sock.sendall(buf)
        for part in body_iter:
            self.sock.sendall(part)

        if self.opts.fire_and_go:
            return self._minimal_read_response()
        return None

    def send_request_chunked(self, body_iter: Iterable[bytes], filename_for_header: Optional[str]):
        buf = build_request_line_and_base_headers(self.opts)
        buf += b"Transfer-Encoding: chunked\r\n"
        if self.opts.use_gzip:
            buf += b"Content-Encoding: gzip\r\n"
        # 파일명 보강
        if filename_for_header and self.opts.add_x_filename_header and "X-Filename" not in self.opts.extra_headers:
            buf += f"X-Filename: {filename_for_header}".encode("utf-8") + CRLF
        tdecl = trailer_decl_str(self.opts.trailing_headers)
        if tdecl:
            buf += f"Trailer: {tdecl}".encode("ascii") + CRLF
        add_header_lines(buf, self.opts.extra_headers)
        buf += CRLF
        assert self.sock
        self.sock.sendall(buf)

        ext = ""
        ce = self.opts.chunk_ext.strip()
        if ce:
            if not ce.startswith(";"):
                ce = ";" + ce
            ext = ce

        for part in body_iter:
            if not part:
                continue
            size_hex = f"{len(part):X}".encode("ascii")
            self.sock.sendall(size_hex + ext.encode("ascii") + CRLF + part + CRLF)

        self.sock.sendall(b"0" + ext.encode("ascii") + CRLF)
        for k, v in self.opts.trailing_headers.items():
            self.sock.sendall(f"{k}: {v}".encode("utf-8") + CRLF)
        self.sock.sendall(CRLF)

        if self.opts.fire_and_go:
            return self._minimal_read_response()
        return None

    def perform(self):
        filename_hint = os.path.basename(self.opts.file_path) if self.opts.file_path else None

        # multipart
        if self.opts.use_multipart:
            boundary = f"----PyBlastBoundary{int(time.time()*1000)}"
            file_iter = iter_file_chunks(self.opts.file_path, self.opts.chunk_size) if self.opts.file_path else [self.opts.body_text or b""]
            filespec = (self.opts.file_path or "", None, file_iter)
            body_stream = multipart_iter(
                filespec, boundary, self.opts.multipart_text_fields,
                self.opts.multipart_filename_override, self.opts.multipart_field_name
            )
            self.opts.extra_headers.setdefault("Content-Type", f"multipart/form-data; boundary={boundary}")

            if self.opts.use_gzip:
                data = b"".join(body_stream)
                gz = gzip_bytes(data)
                if self.opts.use_chunked:
                    return self.send_request_chunked([gz], filename_hint)
                else:
                    return self.send_request_content_length([gz], len(gz), filename_hint)
            else:
                if self.opts.use_chunked:
                    return self.send_request_chunked(body_stream, filename_hint)
                else:
                    parts = [p for p in body_stream]
                    total = sum(len(p) for p in parts)
                    return self.send_request_content_length(parts, total, filename_hint)

        # non-multipart (raw file)
        if self.opts.file_path:
            if self.opts.use_chunked:
                if self.opts.use_gzip:
                    with open(self.opts.file_path, "rb") as f:
                        gz = gzip_bytes(f.read())
                    return self.send_request_chunked([gz], filename_hint)
                else:
                    return self.send_request_chunked(iter_file_chunks(self.opts.file_path, self.opts.chunk_size),
                                                         filename_hint)
            else:
                if self.opts.use_gzip:
                    with open(self.opts.file_path, "rb") as f:
                        gz = gzip_bytes(f.read())
                    return self.send_request_content_length([gz], len(gz), filename_hint)

                else:
                    fsize = os.path.getsize(self.opts.file_path)
                    return self.send_request_content_length(iter_file_chunks(self.opts.file_path, 8192), fsize,
                                                            filename_hint)

        # text body
        body = self.opts.body_text or b""
        if self.opts.use_gzip:
            body = gzip_bytes(body)
        if self.opts.use_chunked:
            return self.send_request_chunked([body], None)
        else:
            return self.send_request_content_length([body], len(body), None)


# ------------------ Worker ------------------

class SenderWorker(threading.Thread):
    def __init__(
        self,
        idx: int,
        all_items: List,
        log_cb,
        status_cb,
        stats_cb,
        base_opts: ClientOptions,
        repeat: int,
        stop_flag: threading.Event,
        random_mode: bool,
        log_every: int,
    ):
        super().__init__(daemon=True)
        self.idx = idx
        self.all_items = all_items
        self.log = log_cb
        self.status_cb = status_cb
        self.stats_cb = stats_cb
        self.base_opts = base_opts
        self.repeat = repeat          # 0이면 무한
        self.stop_flag = stop_flag
        self.random_mode = random_mode
        self.log_every = max(1, log_every)
        self.sent_count = 0

    def run(self):
        try:
            cycle = 0
            while not self.stop_flag.is_set() and (self.repeat == 0 or cycle < self.repeat):
                cycle += 1
                items = list(self.all_items)
                if self.random_mode:
                    random.shuffle(items)

                for item in items:
                    if self.stop_flag.is_set():
                        break

                    desc = self._desc(item)
                    self.status_cb(self.idx, desc)

                    # 이 요청에서 보낼(예상) 바이트 수
                    est_bytes = self._estimate_bytes(item)

                    try:
                        opts = self._clone_opts_for_item(item)
                        conn = HttpConnection(opts)

                        # 요청 시작 시각
                        t0 = time.monotonic()
                        resp = None
                        elapsed_ms = None

                        try:
                            conn.connect()
                            # resp = (status, reason) 또는 None
                            resp = conn.perform()
                            elapsed_ms = (time.monotonic() - t0) * 1000.0
                        except (TimeoutError, socket.timeout):
                            self.sent_count += 1
                            msg = (
                                f"[TIMEOUT] [스레드 {self.idx}] 전송 실패: Timeout — {desc} "
                                f"(DUT/서버 응답 없음, 차단 가능성 높음)"
                            )
                            self.log(msg)

                            # 그래프/통계용 기록 (status_code = None, elapsed_ms=None)
                            if self.stats_cb:
                                self.stats_cb(est_bytes, None, None)
                            continue
                        except ConnectionResetError:
                            self.sent_count += 1
                            msg = (
                                f"[RESET] [스레드 {self.idx}] 전송 실패: Connection reset — {desc} "
                                f"(전송 중 DUT/서버가 연결을 강제로 끊음, 차단 가능성 높음)"
                            )
                            self.log(msg)

                            if self.stats_cb:
                                self.stats_cb(est_bytes, None, None)
                            continue
                        finally:
                            conn.close()

                        # 여기까지 왔으면 소켓 예외는 없음
                        self.sent_count += 1

                        status_str = "응답 없음"
                        verdict = "알 수 없음"
                        tag = "[INFO]"
                        status_code = None

                        if resp is None:
                            verdict = "차단 의심(응답 없음/짧은 응답)"
                            tag = "[BLOCK]"
                        else:
                            status, reason = resp
                            status_code = status
                            status_str = f"{status} {reason}"
                            if 200 <= status < 300:
                                verdict = "성공"
                                tag = "[SUCCESS]"
                            elif 400 <= status < 500:
                                verdict = "차단/클라이언트 오류"
                                tag = "[BLOCK]"
                            elif 500 <= status < 600:
                                verdict = "서버 오류(또는 DUT 차단)"
                                tag = "[SERVER_ERR]"
                            else:
                                verdict = "기타 응답"
                                tag = "[INFO]"

                        # ---- 그래프/통계용 콜백 호출 ----
                        if self.stats_cb:
                            self.stats_cb(est_bytes, status_code, elapsed_ms)

                        # 성공 로그는 log_every 간격으로, 나머지는 항상
                        if tag != "[SUCCESS]" or (self.sent_count % self.log_every == 0):
                            msg = (
                                f"{tag} [스레드 {self.idx}] 전송 결과 "
                                f"(#{self.sent_count}, 반복={cycle if self.repeat>0 else '∞'}): "
                                f"{desc} — {verdict} (응답={status_str})"
                            )
                            self.log(msg)

                        if self.base_opts.delay_between > 0:
                            time.sleep(self.base_opts.delay_between)

                    except Exception as e:
                        self.log(f"[ERROR] [스레드 {self.idx}] 전송 중 예외: {e}\n{traceback.format_exc()}")

            # 스레드 작업 종료 표시
            self.status_cb(self.idx, "-")

        except Exception as e:
            self.log(f"[FATAL] [스레드 {self.idx}] 치명 오류: {e}\n{traceback.format_exc()}")


    def _clone_opts_for_item(self, item) -> ClientOptions:
        o = self.base_opts
        new = ClientOptions(
            host=o.host, port=o.port, path=o.path, method=o.method, keep_alive=o.keep_alive,
            use_chunked=o.use_chunked, chunk_size=o.chunk_size, chunk_ext=o.chunk_ext,
            use_gzip=o.use_gzip, use_multipart=o.use_multipart,
            extra_headers=dict(o.extra_headers), trailing_headers=dict(o.trailing_headers),
            connect_timeout=o.connect_timeout, read_timeout=o.read_timeout,
            fire_and_go=o.fire_and_go, http_version=o.http_version,
            body_text=o.body_text, file_path=o.file_path,
            multipart_field_name=o.multipart_field_name,
            multipart_text_fields=dict(o.multipart_text_fields),
            multipart_filename_override=o.multipart_filename_override,
            add_x_filename_header=o.add_x_filename_header,
            delay_between=o.delay_between,
        )
        if isinstance(item, tuple) and item[0] == "__TEXT__":
            new.file_path = None
            new.body_text = item[1].encode("utf-8")
        else:
            new.file_path = item if item else None
        return new

    def _desc(self, item):
        if isinstance(item, tuple) and item[0] == "__TEXT__":
            return f"텍스트({len(item[1])}자)"
        elif item:
            return os.path.basename(item)
        return "빈 바디"

    def _estimate_bytes(self, item) -> int:
        """
        대략적인 전송 바디 크기 추정.
        - 텍스트: UTF-8 바이트 길이
        - 파일: 파일 크기
        """
        try:
            if isinstance(item, tuple) and item[0] == "__TEXT__":
                return len(item[1].encode("utf-8"))
            elif isinstance(item, str) and item:
                return os.path.getsize(item)
        except Exception:
            pass
        return 0


# ------------------ GUI ------------------

class UploaderGUI(QWidget):
    status_signal = Signal(int, str)  # (thread_idx, desc)


    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTTP Uploader")
        self.resize(1200, 900)

        self._apply_dark_theme()
        self._build_ui()

        # 로그 버퍼(A)
        self._log_buf = deque()
        self._log_lock = threading.Lock()
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(100)  # 100ms마다 플러시
        self._log_timer.timeout.connect(self._flush_log_buffer)
        self._log_timer.start()
        self.logview.document().setMaximumBlockCount(5000)  # 최근 5,000줄만 유지

        # ★ 통계 카운터 초기화
        self.total_sent = 0
        self.total_success = 0
        self.total_block = 0  # BLOCK + SERVER_ERR + TIMEOUT + RESET 포함
        self.total_timeout = 0
        self.total_reset = 0
        self.total_server_err = 0

        # 스레드 상태 업데이트 제한(B)
        self._last_status: Dict[int, float] = {}
        self._status_min_interval = 0.2  # 초
        self.status_signal.connect(self._update_thread_status)

        self.work_threads: List[SenderWorker] = []
        self.stop_event = threading.Event()

        # 시작/정지 시간
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None

        # === 전송 기록(그래프용) : 초 단위 버킷 ===
        self._start_monotonic = 0.0
        self.bucket_lock = threading.Lock()
        # key = sec(int), value = 합계
        self.bucket_bytes = {}  # 초당 전송 바이트 합계
        self.bucket_success = {}  # 초당 성공 건수
        self.bucket_block = {}  # 초당 차단/오류 건수
        self.bucket_lat_sum = {}  # 초당 응답시간 합(ms)
        self.bucket_lat_cnt = {}  # 초당 응답시간 샘플 수

    # 다크 테마
    def _apply_dark_theme(self):
        app = QApplication.instance()
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(20, 20, 20))
        palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)

        self.setStyleSheet("""
            QGroupBox{
                border:1px solid #454545; border-radius:6px;
                margin-top:12px;
            }
            QGroupBox::title{
                subcontrol-origin: margin; left:10px;
                padding:0 4px; color:#d0d0d0;
            }
            QLabel{ color:#dddddd; }
            QLineEdit,QPlainTextEdit,QTextEdit,QListWidget,QTableWidget{
                border:1px solid #555; border-radius:4px; padding:4px;
            }
            QPushButton{
                border:1px solid #5a5a5a; padding:6px 10px; border-radius:6px;
            }
            QPushButton:hover{ border:1px solid #8aa8ff; }

            /* 체크박스: 흰색 박스 + 클릭 시 파란색 동그라미 느낌 */
            QCheckBox{
                color:#dddddd;
            }
            QCheckBox::indicator {
                width: 9px;
                height: 9px;
                border: 2px solid #ffffff;
                border-radius: 2px;               /* 살짝 둥근 흰색 박스 */
                background-color: #ffffff;
            }
            QCheckBox::indicator:unchecked:hover {
                background-color: #dddddd;
            }
            QCheckBox::indicator:checked {
                background-color: #4f8cff;         /* 파란색 바탕 */
                border: 2px solid #ffffff;
            }

            /* 라디오 버튼도 비슷한 느낌으로 */
            QRadioButton{
                color:#dddddd;
            }
            QRadioButton::indicator {
                width: 8px;
                height: 8px;
                border: 2px solid #ffffff;
                border-radius: 4px;                /* 흰색 동그라미 */
                background-color: #ffffff;
            }
            QRadioButton::indicator:unchecked:hover {
                background-color: #dddddd;
            }
            QRadioButton::indicator:checked {
                background-color: #4f8cff;         /* 파란색 작은 동그라미 */
                border: 2px solid #ffffff;
            }
        """)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QGridLayout(container)

        # 서버
        srv = QGroupBox("서버")
        g1 = QGridLayout()
        self.ed_host = QLineEdit("xxx.xxx.xxx.xxx")
        self.ed_port = QSpinBox(); self.ed_port.setRange(1, 65535); self.ed_port.setValue(5001)
        self.ed_path = QLineEdit("/upload")
        g1.addWidget(QLabel("주소"), 0, 0); g1.addWidget(self.ed_host, 0, 1)
        g1.addWidget(QLabel("포트"), 1, 0); g1.addWidget(self.ed_port, 1, 1)
        g1.addWidget(QLabel("전송할 URL 경로"), 2, 0); g1.addWidget(self.ed_path, 2, 1)
        srv.setLayout(g1)

        # HTTP 옵션
        opt = QGroupBox("HTTP 옵션")
        g2 = QGridLayout()
        self.cb_method = QComboBox(); self.cb_method.addItems(["POST", "PUT", "PATCH", "DELETE"])
        self.keep_alive = QCheckBox("연결 유지(keep-alive)"); self.keep_alive.setChecked(True)
        self.use_chunked = QCheckBox("청크 전송(Transfer-Encoding: chunked)")
        self.ed_chunk_size = QSpinBox(); self.ed_chunk_size.setRange(1, 10_000_000); self.ed_chunk_size.setValue(65536)
        self.ed_chunk_ext = QLineEdit("")
        self.use_gzip = QCheckBox("본문 압축(Content-Encoding: gzip)")
        g2.addWidget(QLabel("메서드"), 0, 0); g2.addWidget(self.cb_method, 0, 1)
        g2.addWidget(self.keep_alive, 0, 2)
        g2.addWidget(self.use_chunked, 1, 0)
        g2.addWidget(QLabel("청크 크기(bytes)"), 1, 1); g2.addWidget(self.ed_chunk_size, 1, 2)
        g2.addWidget(QLabel("청크 확장자(chunk extensions, 예: foo=1)"), 2, 0); g2.addWidget(self.ed_chunk_ext, 2, 1, 1, 2)
        g2.addWidget(self.use_gzip, 3, 0, 1, 3)
        opt.setLayout(g2)

        # 바디
        body = QGroupBox("본문(Body)")
        g3 = QGridLayout()
        help_body = QLabel(
            "※ ‘텍스트’는 순수 문자열을 그대로 본문으로 보냅니다.\n"
            "   ‘파일(단일 본문)’은 위의 파일 경로 한 개를 HTTP 본문으로 사용합니다.\n"
            "   ‘멀티파트(파일 + 텍스트 필드)’는 업로드 폼처럼 파일과 추가 필드를 함께 보냅니다."
        )
        help_body.setWordWrap(True)

        self.rb_text = QRadioButton("텍스트"); self.rb_text.setChecked(True)
        self.rb_file = QRadioButton("파일(단일 본문)")
        self.rb_multipart = QRadioButton("멀티파트(파일 + 텍스트 필드)")

        self.txt_body = QPlainTextEdit()

        self.ed_file = QLineEdit()
        self.btn_file = QPushButton("파일 찾기…")
        self.btn_file.clicked.connect(self._browse_file)

        self.ed_mpart_field = QLineEdit("file")
        self.ed_mpart_textfields = QPlainTextEdit(
            "# 한 줄에 하나씩 k: v 형식으로 입력\n"
            "field1: value1\nfield2: value2"
        )
        self.ed_mpart_filename_override = QLineEdit("")
        mpart_help = QLabel("※ 서버에서 받는 필드명이 다르면 ‘파일 필드명’을 서버 규격에 맞게 바꿔주세요.\n"
                            "   파일명 강제지정은 Content-Disposition의 filename= 값에 반영됩니다.")
        mpart_help.setWordWrap(True)

        g3.addWidget(help_body, 0, 0, 1, 3)
        g3.addWidget(self.rb_text, 1, 0); g3.addWidget(self.rb_file, 1, 1); g3.addWidget(self.rb_multipart, 1, 2)
        g3.addWidget(QLabel("텍스트 본문"), 2, 0); g3.addWidget(self.txt_body, 2, 1, 1, 2)

        g3.addWidget(QLabel("파일 경로(텍스트/파일/멀티파트 공통)"), 3, 0)
        g3.addWidget(self.ed_file, 3, 1); g3.addWidget(self.btn_file, 3, 2)

        g3.addWidget(QLabel("멀티파트: 파일 필드명(name)"), 4, 0); g3.addWidget(self.ed_mpart_field, 4, 1)
        g3.addWidget(QLabel("멀티파트: 추가 텍스트(한 줄에 하나, k: v)"), 5, 0)
        g3.addWidget(self.ed_mpart_textfields, 5, 1, 1, 2)
        g3.addWidget(QLabel("멀티파트: 파일명 강제 지정(선택)"), 6, 0)
        g3.addWidget(self.ed_mpart_filename_override, 6, 1, 1, 2)
        g3.addWidget(mpart_help, 7, 0, 1, 3)
        body.setLayout(g3)

        # 헤더
        hdr = QGroupBox("헤더")
        g4 = QGridLayout()
        self.ed_headers = QPlainTextEdit(
            "# 예시\n"
            "User-Agent: http-blast-uploader/1.2\n"
            "Pragma: no-cache\n"
            "# 필요시 여기에 Authorization, Cookie 등 추가"
        )
        self.ed_trailers = QPlainTextEdit(
            "# chunked 전송일 때만 의미 있는 트레일러 헤더 예시\n"
            "X-Trailer: done"
        )
        hdr_help = QLabel("※ 각 줄을 '이름: 값' 형식으로 입력합니다.\n"
                          "   Host, Connection, Content-Length/Transfer-Encoding 등은 프로그램이 자동으로 채웁니다.")
        hdr_help.setWordWrap(True)
        g4.addWidget(QLabel("추가 헤더(한 줄에 하나, '이름: 값')"), 0, 0)
        g4.addWidget(self.ed_headers, 1, 0)
        g4.addWidget(QLabel("트레일러 헤더(chunked일 때 사용, '이름: 값')"), 2, 0)
        g4.addWidget(self.ed_trailers, 3, 0)
        g4.addWidget(hdr_help, 4, 0)
        hdr.setLayout(g4)

        # 전송 속도/방식
        speed = QGroupBox("전송 속도 / 선택 방식")
        gspeed = QGridLayout()
        self.ed_delay_ms = QSpinBox()
        self.ed_delay_ms.setRange(0, 60_000)
        self.ed_delay_ms.setValue(0)
        self.cb_pick_mode = QComboBox()
        self.cb_pick_mode.addItems(["파일 목록 순서대로", "파일 목록에서 무작위"])
        self.ed_log_every = QSpinBox()
        self.ed_log_every.setRange(1, 1000000)
        self.ed_log_every.setValue(1)
        gspeed.addWidget(QLabel("요청 간 대기(ms) (0ms : 쉬지 않고 전송, 100ms : 0.1초 간격, 1000ms : 1초 간격)"), 0, 0)
        gspeed.addWidget(self.ed_delay_ms, 0, 1)
        gspeed.addWidget(QLabel("파일 선택 방식"), 1, 0)
        gspeed.addWidget(self.cb_pick_mode, 1, 1)
        gspeed.addWidget(QLabel("로그 표시 간격(건마다, 1=매건)"), 2, 0)
        gspeed.addWidget(self.ed_log_every, 2, 1)
        speed.setLayout(gspeed)

        # 파일 목록
        srcb = QGroupBox("파일 목록(배치 전송)")
        g6 = QGridLayout()
        self.file_list = QListWidget()
        self.btn_add_files = QPushButton("파일 추가…")
        self.btn_clear_files = QPushButton("목록 비우기")
        self.ed_folder = QLineEdit("")
        self.btn_folder = QPushButton("폴더에서 모두 추가…")
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_clear_files.clicked.connect(self._clear_file_list)
        self.btn_folder.clicked.connect(self._browse_folder)

        g6.addWidget(QLabel("여기에 쌓인 파일을 스레드가 나눠서 보냅니다."), 0, 0, 1, 3)
        g6.addWidget(self.file_list, 1, 0, 1, 3)
        g6.addWidget(self.btn_add_files, 2, 0)
        g6.addWidget(self.btn_clear_files, 2, 1)
        g6.addWidget(self.btn_folder, 2, 2)
        g6.addWidget(QLabel("선택한 폴더 경로(선택)"), 3, 0)
        g6.addWidget(self.ed_folder, 3, 1, 1, 2)
        srcb.setLayout(g6)

        # 실행 / 시작시간
        runb = QGroupBox("실행")
        g5 = QGridLayout()
        self.ed_threads = QSpinBox()
        self.ed_threads.setRange(1, 16)
        self.ed_threads.setValue(4)
        self.ed_threads.setToolTip("최소 1, 최대 16 스레드까지 설정할 수 있습니다.")
        # self.ed_threads = QSpinBox(); self.ed_threads.setRange(1, 16); self.ed_threads.setValue(4)
        self.ed_repeat = QSpinBox(); self.ed_repeat.setRange(0, 1_000_000); self.ed_repeat.setValue(1)
        self.fire_and_go = QCheckBox("응답 최소 읽기(Fire-and-go)"); self.fire_and_go.setChecked(True)
        self.btn_start = QPushButton("시작")
        self.btn_stop = QPushButton("정지")
        self.btn_show_charts = QPushButton("그래프 보기")

        self.btn_start.clicked.connect(self._start_run)
        self.btn_stop.clicked.connect(self._stop_run)
        self.btn_show_charts.clicked.connect(self._show_charts)

        self.time_label = QLabel("시작/정지 시각: -")

        g5.addWidget(QLabel("동시 전송(스레드, 1~16개)"), 0, 0); g5.addWidget(self.ed_threads, 0, 1)
        g5.addWidget(QLabel("반복(회) — 0이면 무한"), 0, 2); g5.addWidget(self.ed_repeat, 0, 3)
        g5.addWidget(self.fire_and_go, 1, 0, 1, 4)
        hbtn = QHBoxLayout(); hbtn.addWidget(self.btn_start); hbtn.addWidget(self.btn_stop); hbtn.addWidget(self.btn_show_charts)

        g5.addLayout(hbtn, 2, 0, 1, 4)
        g5.addWidget(self.time_label, 3, 0, 1, 4)
        runb.setLayout(g5)

        # 스레드 상태 테이블
        thb = QGroupBox("스레드 상태(실시간)")
        gth = QVBoxLayout()
        self.thread_table = QTableWidget(0, 2)
        self.thread_table.setHorizontalHeaderLabels(["스레드", "현재 전송 파일"])
        self.thread_table.horizontalHeader().setStretchLastSection(True)
        gth.addWidget(self.thread_table)
        thb.setLayout(gth)

        # 로그
        self.logview = QTextEdit()
        self.logview.setReadOnly(True)

        # ★ 통계 라벨 추가
        self.lbl_stats = QLabel("총 전송: 0  |  성공: 0  |  차단/오류: 0 (차단율 0.0%)")
        self.lbl_stats.setAlignment(Qt.AlignLeft)

        # 배치
        layout.addWidget(srv,   0, 0, 1, 1)
        layout.addWidget(opt,   0, 1, 1, 1)
        layout.addWidget(body,  1, 0, 1, 2)
        layout.addWidget(hdr,   2, 0, 1, 2)
        layout.addWidget(speed, 3, 0, 1, 2)
        layout.addWidget(srcb,  4, 0, 1, 2)
        layout.addWidget(runb,  5, 0, 1, 2)
        layout.addWidget(thb,   6, 0, 1, 2)

        # ★ 통계 라벨을 로그 위에
        layout.addWidget(self.lbl_stats, 7, 0, 1, 2)
        layout.addWidget(self.logview, 8, 0, 1, 2)

        layout.setRowStretch(8, 1)

    def _show_charts(self):
        with self.bucket_lock:
            if not self.bucket_bytes:
                QMessageBox.information(self, "그래프", "수집된 전송 기록이 없습니다.\n시험을 한 번 실행한 뒤 눌러주세요.")
                return

            # 버킷 복사
            bytes_b = dict(self.bucket_bytes)
            succ_b = dict(self.bucket_success)
            block_b = dict(self.bucket_block)
            lat_sum_b = dict(self.bucket_lat_sum)
            lat_cnt_b = dict(self.bucket_lat_cnt)

        max_sec = max(bytes_b.keys() | succ_b.keys() | block_b.keys() | lat_sum_b.keys())  # set union
        nsec = max_sec + 1

        x_sec = list(range(nsec))

        # 1) 초당 트래픽(Mbps)
        bytes_per_sec = [0] * nsec
        for s, val in bytes_b.items():
            if 0 <= s < nsec:
                bytes_per_sec[s] = val
        mbps = [(b * 8.0) / 1_000_000 for b in bytes_per_sec]

        # 2) 초당 성공/차단 건수
        success_per_sec = [0] * nsec
        block_per_sec = [0] * nsec
        for s, val in succ_b.items():
            if 0 <= s < nsec:
                success_per_sec[s] = val
        for s, val in block_b.items():
            if 0 <= s < nsec:
                block_per_sec[s] = val

        # 3) 초당 평균 응답시간(ms) (없으면 0 또는 None)
        avg_rt = [0.0] * nsec
        for s in range(nsec):
            cnt = lat_cnt_b.get(s, 0)
            if cnt > 0:
                avg_rt[s] = lat_sum_b.get(s, 0.0) / cnt
            else:
                avg_rt[s] = 0.0

        fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

        # 1. 트래픽
        axes[0].plot(x_sec, mbps)
        axes[0].set_ylabel("트래픽 (Mbps)")
        axes[0].set_title("가동 시간에 따른 전송 트래픽")

        # 2. 성공/차단
        axes[1].plot(x_sec, success_per_sec, label="성공(2xx~3xx)")
        axes[1].plot(x_sec, block_per_sec, label="차단/오류(응답 없음 포함)")
        axes[1].set_ylabel("건수")
        axes[1].set_title("가동 시간에 따른 성공/차단 건수")
        axes[1].legend()

        # 3. 평균 응답시간
        axes[2].plot(x_sec, avg_rt)
        axes[2].set_xlabel("가동 후 시간 (초)")
        axes[2].set_ylabel("평균 응답 시간 (ms)")
        axes[2].set_title("가동 시간에 따른 평균 응답 시간")

        plt.tight_layout()
        plt.show()

    # ---------- UI helpers ----------

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path:
            self.ed_file.setText(path)
            self.rb_file.setChecked(True)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            self.ed_folder.setText(folder)
            added = 0
            for name in os.listdir(folder):
                p = os.path.join(folder, name)
                if os.path.isfile(p):
                    self.file_list.addItem(p); added += 1
            self._log_enqueue(f"[안내] 폴더에서 {added}개 파일 추가.")

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "파일들 선택")
        for p in paths:
            if os.path.isfile(p):
                self.file_list.addItem(p)
        if paths:
            self._log_enqueue(f"[안내] {len(paths)}개 파일 추가.")

    def _clear_file_list(self):
        self.file_list.clear()
        self._log_enqueue("[안내] 파일 목록을 비웠습니다.")

    # ---------- Log (A) ----------

    def _log_enqueue(self, s: str):
        with self._log_lock:
            self._log_buf.append(s)

    def _flush_log_buffer(self):
        batch = []
        with self._log_lock:
            while self._log_buf and len(batch) < 500:
                batch.append(self._log_buf.popleft())

        if not batch:
            return

        last = batch[-1]
        others = len(batch) - 1
        if others > 0:
            summary = f"{last} 외 {others}건"
        else:
            summary = last

        # 색상만 태그로 판단 (통계는 여기서 건드리지 않음)
        if last.startswith("[SUCCESS]"):
            last_tag = "success"
        elif last.startswith("[BLOCK]"):
            last_tag = "block"
        elif last.startswith("[TIMEOUT]"):
            last_tag = "timeout"
        elif last.startswith("[RESET]"):
            last_tag = "reset"
        elif last.startswith("[SERVER_ERR]"):
            last_tag = "server_err"
        elif last.startswith("[ERROR]") or last.startswith("[FATAL]"):
            last_tag = "error"
        else:
            last_tag = "info"

        default_color = self.logview.palette().color(QPalette.Text)

        if last_tag == "success":
            color = QColor("#80ff80")
        elif last_tag in ("block", "server_err"):
            color = QColor("#ff8080")
        elif last_tag in ("timeout", "reset"):
            color = QColor("#ffcc66")
        elif last_tag == "error":
            color = QColor("#ff5555")
        else:
            color = default_color

        self.logview.setTextColor(color)
        self.logview.append(summary)
        self.logview.setTextColor(default_color)

        self._update_stats_label()

    def _update_stats_label(self):
        if self.total_sent > 0:
            block_rate = (self.total_block * 100.0) / self.total_sent
        else:
            block_rate = 0.0

        self.lbl_stats.setText(
            f"총 전송: {self.total_sent}  |  "
            f"성공: {self.total_success}  |  "
            f"차단/오류: {self.total_block} (차단율 {block_rate:.1f}%)  |  "
            f"타임아웃: {self.total_timeout}  |  "
            f"RST: {self.total_reset}  |  "
            f"5xx: {self.total_server_err}"
        )

    # ---------- Thread status (B) ----------

    def _reset_thread_table(self, threads: int):
        self.thread_table.setRowCount(threads)
        self._last_status.clear()
        for i in range(threads):
            self.thread_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.thread_table.setItem(i, 1, QTableWidgetItem("-"))

    def _update_thread_status(self, thread_idx: int, desc: str):
        now = time.monotonic()
        last = self._last_status.get(thread_idx, 0.0)
        if desc != "-" and now - last < self._status_min_interval:
            return
        self._last_status[thread_idx] = now
        row = thread_idx - 1
        if 0 <= row < self.thread_table.rowCount():
            self.thread_table.setItem(row, 1, QTableWidgetItem(desc))

    # ---------- Run ----------

    def _start_run(self):
        try:
            self.stop_event.clear()

            # 통계/기록 초기화
            self.total_sent = 0
            self.total_success = 0
            self.total_block = 0
            self.total_timeout = 0
            self.total_reset = 0
            self.total_server_err = 0
            self._update_stats_label()

            # 그래프용 버킷 초기화
            self._start_monotonic = time.monotonic()
            with self.bucket_lock:
                self.bucket_bytes.clear()
                self.bucket_success.clear()
                self.bucket_block.clear()
                self.bucket_lat_sum.clear()
                self.bucket_lat_cnt.clear()

            host = self.ed_host.text().strip()
            port = int(self.ed_port.value())
            path = self.ed_path.text().strip()
            method = self.cb_method.currentText().strip().upper()
            keep_alive = self.keep_alive.isChecked()
            use_chunked = self.use_chunked.isChecked()
            chunk_size = int(self.ed_chunk_size.value())
            chunk_ext = self.ed_chunk_ext.text().strip()
            use_gzip = self.use_gzip.isChecked()

            use_multipart = self.rb_multipart.isChecked()
            is_file = self.rb_file.isChecked()
            is_text = self.rb_text.isChecked()

            text_body = self.txt_body.toPlainText()
            single_file_path = self.ed_file.text().strip() if (is_file or use_multipart) else None

            m_field = self.ed_mpart_field.text().strip() or "file"
            m_text_fields = parse_kv_lines(self.ed_mpart_textfields.toPlainText())
            m_fname_override = self.ed_mpart_filename_override.text().strip() or None

            extra_headers = parse_kv_lines(self.ed_headers.toPlainText())
            trailing_headers = parse_kv_lines(self.ed_trailers.toPlainText())

            threads = int(self.ed_threads.value())
            repeat = int(self.ed_repeat.value())  # 0 -> 무한
            fire_and_go = self.fire_and_go.isChecked()
            delay_ms = int(self.ed_delay_ms.value())
            delay_between = delay_ms / 1000.0
            random_mode = (self.cb_pick_mode.currentIndex() == 1)
            log_every = int(self.ed_log_every.value())

            base = ClientOptions(
                host=host, port=port, path=path, method=method, keep_alive=keep_alive,
                use_chunked=use_chunked, chunk_size=chunk_size, chunk_ext=chunk_ext,
                use_gzip=use_gzip, use_multipart=use_multipart,
                extra_headers=extra_headers, trailing_headers=trailing_headers,
                fire_and_go=fire_and_go, delay_between=delay_between
            )

            if is_text and not use_multipart:
                base.body_text = text_body.encode("utf-8")
                base.file_path = None
            else:
                base.file_path = single_file_path

            base.multipart_field_name = m_field
            base.multipart_text_fields = m_text_fields
            base.multipart_filename_override = m_fname_override

            all_items: List = []
            # 파일 목록
            for i in range(self.file_list.count()):
                p = self.file_list.item(i).text()
                if os.path.isfile(p):
                    all_items.append(p)

            # 목록이 비어 있으면 폴더 또는 단일/텍스트/빈 바디
            folder = self.ed_folder.text().strip()
            if not all_items and folder and os.path.isdir(folder):
                for name in os.listdir(folder):
                    p = os.path.join(folder, name)
                    if os.path.isfile(p):
                        all_items.append(p)
                if all_items:
                    self._log_enqueue(f"[안내] 폴더에서 {len(all_items)}개 파일을 큐에 등록.")

            if not all_items:
                if is_text and not use_multipart:
                    all_items.append(("__TEXT__", text_body))
                elif single_file_path:
                    all_items.append(single_file_path)
                else:
                    all_items.append(None)

            self._log_enqueue(
                f"[시작] 항목 {len(all_items)}개. 스레드={threads}, 반복={repeat if repeat>0 else '무한'}, "
                f"메서드={method}, {'chunked' if use_chunked else 'content-length'}, "
                f"{'gzip' if use_gzip else 'no-gzip'}, keep-alive={keep_alive}, "
                f"지연={delay_ms}ms, 선택방식={'랜덤' if random_mode else '순차'}, 로그간격={log_every}"
            )

            # 시작/정지 시간 UI
            self.start_time = datetime.now()
            self.stop_time = None
            self.time_label.setText(f"시작/정지 시각: 시작 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 스레드 테이블 초기화
            self._reset_thread_table(threads)

            # 스레드 가동
            self.work_threads = []
            for i in range(threads):
                thr = SenderWorker(
                    idx=i + 1,
                    all_items=all_items,
                    log_cb=self._log_enqueue,
                    status_cb=lambda tid, desc: self.status_signal.emit(tid, desc),
                    stats_cb=lambda b, code, el: self._on_stats(b, code, el),  # ★ 추가
                    base_opts=base,
                    repeat=repeat,
                    stop_flag=self.stop_event,
                    random_mode=random_mode,
                    log_every=log_every,
                )
                thr.start()
                self.work_threads.append(thr)

            # 감시자
            def watcher():
                for t in self.work_threads:
                    t.join()
                self._log_enqueue("[완료] 모든 스레드 종료.")

            threading.Thread(target=watcher, daemon=True).start()

        except Exception as e:
            self._log_enqueue(f"[오류] {e}\n{traceback.format_exc()}")

    def _on_stats(self, bytes_sent: int, status_code: Optional[int], elapsed_ms: Optional[float]):
        # 1) 누적 통계 업데이트
        self.total_sent += 1

        if status_code is None:
            # timeout / reset / 응답 없음 계열은 run()에서 이미 로그 태그로 나감
            self.total_block += 1
            self.total_timeout += 1  # 필요하면 timeout/ reset 구분해서 넘겨도 됨
        else:
            if 200 <= status_code < 300:
                self.total_success += 1
            elif 400 <= status_code < 500:
                self.total_block += 1
            elif 500 <= status_code < 600:
                self.total_server_err += 1
            else:
                # 필요시 기타 분류
                pass

        self._update_stats_label()

        # 2) 초 단위 버킷 업데이트 (그래프용)
        t_rel = time.monotonic() - self._start_monotonic
        sec = int(t_rel)
        b = bytes_sent or 0

        with self.bucket_lock:
            # 전송 바이트
            self.bucket_bytes[sec] = self.bucket_bytes.get(sec, 0) + b

            # 성공 / 차단 건수
            if status_code is None:
                self.bucket_block[sec] = self.bucket_block.get(sec, 0) + 1
            else:
                if 200 <= status_code < 400:
                    self.bucket_success[sec] = self.bucket_success.get(sec, 0) + 1
                else:
                    self.bucket_block[sec] = self.bucket_block.get(sec, 0) + 1

            # 응답 시간 (평균값용)
            if elapsed_ms is not None:
                self.bucket_lat_sum[sec] = self.bucket_lat_sum.get(sec, 0.0) + elapsed_ms
                self.bucket_lat_cnt[sec] = self.bucket_lat_cnt.get(sec, 0) + 1

    def _stop_run(self):
        self.stop_event.set()
        self._log_enqueue("[정지] 중지 요청됨. 진행 중 작업이 마무리되면 종료됩니다.")
        if self.start_time and not self.stop_time:
            self.stop_time = datetime.now()
            self.time_label.setText(
                f"시작/정지 시각: 시작 {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} / "
                f"정지 {self.stop_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )


# ---------- Main ----------

def main():
    app = QApplication(sys.argv)
    gui = UploaderGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
