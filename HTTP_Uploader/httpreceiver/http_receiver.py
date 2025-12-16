#!/usr/bin/env python3
import os
import sys
import time
import argparse
import threading
import traceback
from http import server
from socketserver import ThreadingMixIn

# ----------------- 설정 기본값 -----------------

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5001
DEFAULT_SAVE_DIR = "/var/tmp/uploads"

# 용량 관련 기본값 (GB 단위)
DEFAULT_MAX_TOTAL_GB = 60.0   # uploads 디렉터리에 허용할 최대 총 용량
DEFAULT_MIN_FREE_GB = 10.0     # 디스크 여유 공간이 이 값 아래로 내려가면 정리
DEFAULT_CLEANUP_INTERVAL = 10 # 정리 주기(초)

# ------------------------------------------------


class UploadHTTPServer(ThreadingMixIn, server.HTTPServer):
    """
    업로드를 처리하는 HTTP 서버.
    - save_dir: 업로드 파일 저장 위치
    - max_total_gb: save_dir 내 총 용량 상한
    - min_free_gb: 디스크 전체 여유 공간 하한
    - cleanup_interval: 백그라운드 정리 주기(초)
    """
    daemon_threads = True  # worker thread가 데몬으로 동작

    def __init__(self, server_address, RequestHandlerClass,
                 save_dir: str,
                 max_total_gb: float = DEFAULT_MAX_TOTAL_GB,
                 min_free_gb: float = DEFAULT_MIN_FREE_GB,
                 cleanup_interval: int = DEFAULT_CLEANUP_INTERVAL):
        super().__init__(server_address, RequestHandlerClass)
        self.save_dir = save_dir
        self.max_total_gb = max_total_gb
        self.min_free_gb = min_free_gb
        self.cleanup_interval = cleanup_interval
        os.makedirs(self.save_dir, exist_ok=True)

        print(f"[INFO] Upload dir: {self.save_dir}", flush=True)
        print(f"[INFO] Max uploads size: {self.max_total_gb} GB", flush=True)
        print(f"[INFO] Min free disk:   {self.min_free_gb} GB", flush=True)
        print(f"[INFO] Cleanup interval: {self.cleanup_interval} sec", flush=True)

        # 백그라운드 정리 스레드 시작
        self._start_cleanup_thread()

    # ---------- 디스크 정리 로직 ----------

    def _get_disk_usage(self):
        """
        uploads 디렉터리 용량(GB), 전체 디스크 여유 공간(GB) 계산.
        """
        dir_path = self.save_dir
        total_size = 0
        files = []

        for entry in os.scandir(dir_path):
            if entry.is_file():
                st = entry.stat()
                total_size += st.st_size
                files.append((st.st_mtime, entry.path, st.st_size))

        total_gb = total_size / (1024 ** 3)

        stv = os.statvfs(dir_path)
        free_gb = stv.f_bavail * stv.f_frsize / (1024 ** 3)

        return total_gb, free_gb, files

    def cleanup_upload_dir(self):
        """
        uploads 디렉터리의 총 용량이 max_total_gb를 넘거나
        전체 디스크 여유 공간이 min_free_gb 이하일 때
        해당 디렉터리 안의 모든 파일을 삭제.
        """
        try:
            total_gb, free_gb, files = self._get_disk_usage()

            # 정리 기준에 걸리지 않으면 바로 리턴
            if total_gb <= self.max_total_gb and free_gb >= self.min_free_gb:
                return

            print(f"[CLEANUP] 전체 삭제 시작 — uploads={total_gb:.2f}GB, free={free_gb:.2f}GB", flush=True)

            deleted_bytes = 0
            deleted_count = 0

            for _, path, size in files:
                try:
                    os.remove(path)
                    deleted_bytes += size
                    deleted_count += 1
                    print(f"[CLEANUP] 삭제: {path} ({size/1024/1024:.1f} MB)", flush=True)
                except Exception as e:
                    print(f"[CLEANUP] 삭제 실패: {path} - {e}", flush=True)

            # 삭제 후 현황 다시 계산
            new_total_gb, new_free_gb, _ = self._get_disk_usage()

            print(
                f"[CLEANUP] 전체 삭제 종료 — 삭제 파일 수={deleted_count}, "
                f"삭제 용량={deleted_bytes/1024/1024:.1f}MB, "
                f"현재 uploads={new_total_gb:.4f}GB, free={new_free_gb:.2f}GB",
                flush=True,
            )

        except Exception as e:
            print(f"[CLEANUP] 오류: {e}\n{traceback.format_exc()}", flush=True)


    def _cleanup_loop(self):
        """
        백그라운드에서 주기적으로 cleanup_upload_dir()를 호출.
        """
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self.cleanup_upload_dir()
            except Exception as e:
                print(f"[CLEANUP-THREAD] 예외: {e}\n{traceback.format_exc()}", flush=True)
                # 치명적인 에러가 아닌 한 계속 돌게 둔다.

    def _start_cleanup_thread(self):
        t = threading.Thread(target=self._cleanup_loop, daemon=True)
        t.start()
        print("[INFO] Cleanup thread started.", flush=True)

    # (선택) 너무 free space가 부족하면 아예 저장을 거부할 수도 있음
    def has_enough_space(self) -> bool:
        """
        디스크 여유 공간이 min_free_gb 이상인지 체크.
        """
        try:
            stv = os.statvfs(self.save_dir)
            free_gb = stv.f_bavail * stv.f_frsize / (1024 ** 3)
            return free_gb >= self.min_free_gb
        except Exception as e:
            print(f"[SPACE] free space 확인 실패: {e}", flush=True)
            # 문제가 생기면 보수적으로 True로 간주
            return True


class UploadHandler(server.BaseHTTPRequestHandler):
    """
    단순 HTTP 업로드 핸들러.
    - POST/PUT 요청의 바디를 그대로 파일로 저장
    - 헤더 X-Filename 이 있으면 그 이름을 파일명에 반영
    """

    server_version = "SimpleUploadHTTP/1.0"

    def do_POST(self):
        self._handle_upload()

    def do_PUT(self):
        self._handle_upload()

    def _handle_upload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        # 여유 공간이 너무 적으면 507 반환 (선택적 방어 로직)
        if not self.server.has_enough_space():
            self.send_response(507, "Insufficient Storage")
            self.end_headers()
            self.wfile.write(b"Insufficient storage on server.\n")
            self.wfile.flush()
            print("[WARN] free space 부족으로 업로드 거부.", flush=True)
            return

        # 원본 파일명 힌트 (HTTP 업로더가 X-Filename을 넣어주고 있음)
        orig_name = self.headers.get("X-Filename", "")
        orig_name = os.path.basename(orig_name) if orig_name else "upload.bin"

        ts = time.strftime("%Y%m%d-%H%M%S")
        pid = os.getpid()
        # 동일 초에 여러 요청이 들어올 수 있으니 time.time() 소수점까지 활용
        unique = f"{time.time():.6f}".split(".")[-1]

        filename = f"{ts}_{pid}_{unique}_{orig_name}"
        save_path = os.path.join(self.server.save_dir, filename)

        # 바디 읽어서 저장
        remaining = length
        written = 0

        try:
            with open(save_path, "wb") as f:
                while remaining > 0:
                    chunk = self.rfile.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
                    remaining -= len(chunk)

            # 응답
            self.send_response(200, "OK")
            self.end_headers()
            self.wfile.write(b"OK\n")
            self.wfile.flush()

            print(f"[RECV] {self.client_address[0]}:{self.client_address[1]} "
                  f"-> {save_path} ({written/1024/1024:.2f} MB)", flush=True)

        except Exception as e:
            # 저장 중 오류
            try:
                self.send_response(500, "Internal Server Error")
                self.end_headers()
                self.wfile.write(b"ERROR\n")
                self.wfile.flush()
            except Exception:
                pass

            print(f"[ERROR] 업로드 처리 실패: {e}\n{traceback.format_exc()}", flush=True)

            # 중간에 파일이 만들어졌으면 정리
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
            except Exception:
                pass

    # 너무 시끄러운 기본 로그를 막고, 필요한 경우만 print 사용
    def log_message(self, format, *args):
        return


def parse_args():
    p = argparse.ArgumentParser(description="Simple HTTP file receiver with auto cleanup.")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"바인드할 주소 (기본: {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"포트 번호 (기본: {DEFAULT_PORT})")
    p.add_argument("--save-dir", default=DEFAULT_SAVE_DIR,
                   help=f"업로드 파일 저장 디렉터리 (기본: {DEFAULT_SAVE_DIR})")
    p.add_argument("--max-total-gb", type=float, default=DEFAULT_MAX_TOTAL_GB,
                   help=f"uploads 디렉터리 최대 용량(GB) (기본: {DEFAULT_MAX_TOTAL_GB})")
    p.add_argument("--min-free-gb", type=float, default=DEFAULT_MIN_FREE_GB,
                   help=f"디스크 최소 여유 공간(GB) (기본: {DEFAULT_MIN_FREE_GB})")
    p.add_argument("--cleanup-interval", type=int, default=DEFAULT_CLEANUP_INTERVAL,
                   help=f"정리 주기(초) (기본: {DEFAULT_CLEANUP_INTERVAL})")
    return p.parse_args()


def main():
    args = parse_args()

    server_address = (args.host, args.port)
    httpd = UploadHTTPServer(
        server_address,
        UploadHandler,
        save_dir=args.save_dir,
        max_total_gb=args.max_total_gb,
        min_free_gb=args.min_free_gb,
        cleanup_interval=args.cleanup_interval,
    )

    print(f"[INFO] Listening on {args.host}:{args.port}", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt: 서버 종료 요청.", flush=True)
    finally:
        httpd.server_close()
        print("[INFO] 서버 종료 완료.", flush=True)


if __name__ == "__main__":
    main()
