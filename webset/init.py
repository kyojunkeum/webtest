import os
import sys
import time
from dlptest.base import base
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))


# 메인 실행부
if __name__ == "__main__":

    # 로컬 아이피 설정
    base.get_local_ip()

    # Chrome 옵션 설정 (SSL 인증서 무시)
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--ignore-certificate-errors")

    # ChromeDriver 명시적으로 실행
    driver_path = r"D:\chromedriver.exe"
    service = Service(driver_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    # 웹페이지 열기
    driver.get(base.dlp_address)
    print(f'현재 주소는 : {base.dlp_address}')

    # 웹사이트 로그인
    username = "id"
    password = "password"

    success = base.login_to_website(driver, username, password)
    if success:
        print("웹사이트에 성공적으로 로그인했습니다.")
    else:
        print("웹사이트 로그인에 실패했습니다.")

    # 클라이언트 대역 설정
    start_ip = "xxx.xxx.xxx.xxx"
    end_ip = "xxx.xxx.xxx.xxx"
    success = base.configure_client_band(driver, start_ip, end_ip)
    if success:
       print("클라이언트 대역이 성공적으로 설정되었습니다.")
    else:
       print("클라이언트 대역 설정에 실패했습니다.")

    # 서비스 DB 업데이트
    success = base.update_service_db(driver)
    if success:
       print("서비스 DB가 성공적으로 업데이트되었습니다.")
    else:
       print("서비스 DB 업데이트에 실패했습니다.")

    # 서버 설정
    time.sleep(3)
    smtp_host = "xxx.xxx.xxx.xxx"
    smtp_port = "xx"
    smtp_id = "xxxxxx@xxxxx.com"
    smtp_pw = "password"
    smtp_from = "useremail"
    smtp_test_mail = "testreceiveemail"
    success = base.set_system_server(driver, smtp_host, smtp_port, smtp_id, smtp_pw, smtp_from)
    if success:
       print("관리자 서버 설정이 정상적으로 설정되었습니다.")
    else:
       print("관리자 서버 설정에 실패했습니다.")

    # 인사연동 설정
    success = base.set_insa_db(driver)
    if success:
       print("인사연동이 완료되었습니다.")
    else:
       print("인사연동이 실패했습니다.")

    # 키워드 정책 조건 생성
    success = base.create_keyword_condition(driver)
    if success:
       print("정책 조건 생성이 완료되었습니다.")
    else:
       print("정책 조건 생성이 실패했습니다.")

    # 첨부파일 정책 조건 생성
    success = base.create_attach_condition(driver)
    if success:
       print("정책 조건 생성이 완료되었습니다.")
    else:
       print("정책 조건 생성이 실패했습니다.")

    # 감시 정책 생성
    success = base.create_policy_mirror(driver)
    if success:
        print("감시 정책 생성이 완료되었습니다.")
    else:
        print("감시 정책 생성이 실패했습니다.")

    # 차단 정책 생성
    success = base.create_policy_block(driver)
    if success:
        print("차단 정책 생성이 완료되었습니다.")
    else:
        print("차단 정책 생성이 실패했습니다.")

    # 동기화 수행
    success = base.syncronize(driver)
    if success:
        print("동기화에 성공하였습니다.")
    else:
        print("동기화에 실패하였습니다.")

    # 로그레벨 설정
    success = base.set_loglevel(driver)
    if success:
        print("로그레벨 설정이 완료되었습니다.")
    else:
        print("로그레벨 설정이 실패하였습니다.")


    # JavaScript를 사용하여 알림 팝업 띄우기
    driver.execute_script("alert('DLP 웹 설정을 완료하였습니다');")

    # 브라우저 유지하기
    input("Press Enter to close the browser...")
    driver.quit()