import json
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import socket

# 임시 경로 저장
temp_path = os.getcwd()

# 현재 실행되고 있는 파일 위치로 이동
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# 상위 경로 이동 후 pipeline 경로 이동
os.chdir('..')
os.chdir('./pipeline')
with open('info.json', 'r') as f:
    json_data = json.load(f)
    # dlp_address = json_data[f'{label_name}']['dlp_address']
    # device_type = json_data[f'{label_name}']['device_type']
    # dlp_client_address = json_data[f'{label_name}']['dlp_client_address']

# 임시로 저장했던 경로로 이동
os.chdir(temp_path)

def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        label_name = None
        if local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        elif local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        elif local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        elif local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        elif local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        elif local_ip == 'xxx.xxx.xxx.xxx':
            label_name = 'xxx_xxx_PC'
        else:
            # IP가 미리 정의되지 않았을 때 기본값 할당
            label_name = 'default_label'  # 기본 라벨 또는 빈 값 설정
            print(f"Warning: IP {local_ip} not recognized, using default label.")


        # json_data에서 해당 label_name이 존재하는지 확인하고 처리
        dlp_address = json_data.get(label_name, {}).get('dlp_address', 'http://default_address.com')

        # 만약 기본 주소가 사용된 경우 경고 메시지 출력
        if dlp_address == 'http://default_address.com':
            print(f"Warning: No address found for label '{label_name}', using default address.")

        return local_ip, label_name, dlp_address  # local_ip, label_name, dlp_address 반환

    except Exception as e:
        print("Error:", e)
        return None

local_ip, label_name, dlp_address = get_local_ip()
print(f'현재 주소는 : {local_ip}, {label_name}, {dlp_address}')

# 임시 경로 저장
temp_path = os.getcwd()

# 현재 실행되고 있는 파일 위치로 이동
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# 상위 경로 이동 후 pipeline 경로 이동
os.chdir('..')
os.chdir('./pipeline')
with open('info.json', 'r') as f:
    json_data = json.load(f)
    dlp_address = json_data[f'{label_name}']['dlp_address']
    device_type = json_data[f'{label_name}']['device_type']
    # dlp_client_address = json_data[f'{label_name}']['dlp_client_address']

# 임시로 저장했던 경로로 이동
os.chdir(temp_path)

def do_click(driver, by_method, identifier, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by_method, identifier))
        )
        element.click()
    except NoSuchElementException:
        print(f"Element not found: {identifier}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    return True

def do_send_keys(driver, by_method, identifier, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by_method, identifier))
        )
        element.send_keys(value)
    except NoSuchElementException:
        print(f"Element not found: {identifier}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    return True

def do_get_text(driver, by_method, identifier, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by_method, identifier))
        )
        txt = element.text
        return txt
    except NoSuchElementException:
        print(f"Element not found: {identifier}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def is_element_id_exist(driver, element):
    try:
        driver.find_element(By.ID, element)
    except:
        return False
    return True

def get_table_data(driver, table_name):
    table = driver.find_element(By.ID, table_name)
    tbody = table.find_element(By.TAG_NAME, 'tbody')
    tr = tbody.find_elements(By.TAG_NAME, 'tr')
    return tr

def login_to_website(driver, username, password):
    try:
        # WebDriverWait을 사용하여 ID 입력 필드가 로드될 때까지 기다림
        do_send_keys(driver, By.ID, "j_username", username)
        # WebDriverWait을 사용하여 비밀번호 입력 필드가 로드될 때까지 기다림
        do_send_keys(driver, By.ID, "j_password", password)

        # 로그인 버튼 클릭
        do_click(driver, By.ID, "btn_Login")
        time.sleep(3)

        # 중복로그인 확인창에서 [확인] 클릭
        driver.find_element(By.ID, 'modal_cancel').click()

        print("로그인 성공")
        return True

    except Exception as e:
        print(f"로그인 중 오류 발생: {e}")
        return False

def configure_client_band(driver, start_ip, end_ip):
    try:
        # 제품 설정 클릭
        do_click(driver, By.XPATH, '//*[@id="root"]/a')
        time.sleep(0.5)
        # 제품 기본 설정 클릭
        do_click(driver, By.XPATH, '//*[@id="side_basic"]')
        time.sleep(0.5)
        # 클라이언트 대역 설정 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[2]/a')
        time.sleep(0.5)

        # 클라이언트 대역 추가
        print("클라이언트 대역 설정 시작")
        time.sleep(2)
        # 시작 IP 입력
        do_send_keys(driver, By.ID, "sInputIp", start_ip)
        time.sleep(1)
        # 종료 IP 입력
        do_send_keys(driver, By.ID, "eInputIp", end_ip)
        time.sleep(1)
        # 대역 추가 클릭
        do_click(driver, By.NAME, 'addClientBand')
        # 엔진 반영 클릭
        do_click(driver, By.NAME, 'create')
        # 코어 재기동 여부 팝업창에서 '확인' 클릭
        do_click(driver, By.ID, 'modal_ok')
        time.sleep(15)
        # 클라이언트 대역 반영 완료창에서 '확인' 클릭
        do_click(driver, By.ID, 'modal_cancel')
        time.sleep(2)
        print("-> 클라이언트 대역 설정 완료\n")
        return True

    except Exception as e:
        print(f"클라이언트 대역 설정 중 오류 발생: {e}")
        return False

def update_service_db(driver):
    try:
        print("서비스 DB (패턴 DB) 업데이트 시작")
        # 시스템 클릭
        do_click(driver, By.XPATH, '//*[@id="system"]/a')
        time.sleep(0.5)
        # DBMS 클릭
        do_click(driver, By.XPATH, '//*[@id="side_dbms"]')
        time.sleep(0.5)
        # 서비스DB 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[3]/a')
        time.sleep(0.5)
        # 수동 업데이트 클릭
        do_click(driver, By.NAME, 'ok')
        time.sleep(1)
        # 업데이트 진행 여부 팝업창에서 [확인] 클릭
        do_click(driver, By.ID, 'modal_ok')
        time.sleep(3)
        # 업데이트 완료 확인
        cmt = do_get_text(driver, By.ID, 'modal_content')
        if cmt == '업데이트를 완료 하였습니다.':
            print("-> 서비스 DB 업데이트 완료")
            time.sleep(2)
        else:
            print("업데이트 실패")
            time.sleep(2)
            return False
        # 확인 버튼 클릭하여 팝업 닫기
        do_click(driver, By.ID, 'modal_cancel')
        time.sleep(1)

        return True
    except Exception as e:
        print(f"업데이트 중 오류 발생: {e}")
        return False

# 서버 설정
def set_system_server(driver, smtp_host, smtp_port, smtp_id, smtp_pw, smtp_from):
    try:
        print("관리자 메뉴 서버 설정 시작")
        # 관리자 메뉴 클릭
        do_click(driver, By.XPATH, '//*[@id="side_user"]')
        time.sleep(1)
        # 서버 설정 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[4]/ul/li[2]/a')
        time.sleep(1)

        # SMTP 추가 여부 확인
        msg = do_get_text(driver, By.XPATH, '//*[@id="smtp_list"]/tbody/tr/td')
        if msg == '생성된 항목이 없습니다.':
            # SMTP 서버 / 인증정보 추가 클릭
            do_click(driver, By.NAME, 'addSmtpServer')
            # smtp 서버 정보 입력
            do_send_keys(driver, By.ID, "smtp_host", smtp_host)
            do_send_keys(driver, By.ID, "smtp_port", smtp_port)
            do_send_keys(driver, By.ID, "smtp_id", smtp_id)
            do_send_keys(driver, By.ID, "smtp_pw", smtp_pw)
            do_send_keys(driver, By.ID, "smtp_from", smtp_from)
            do_click(driver, By.ID, 'smtp_register') # 저장 버튼
            do_click(driver, By.ID, 'modal_cancel') # 저장 완료창에서 확인 버튼
            print(f'-> SMTP 서버 추가 완료')
        else:
            print(f'-> SMTP 서버가 이미 추가되어 있습니다.')
        # 로그 상세기능 잠금 여부 확인 및 비활성화
        if is_element_id_exist(driver, 'logLock'):
            toggle = driver.find_element(By.ID, 'logLock')
            if toggle.is_selected() is True:
                driver.find_element(By.XPATH, '//*[@id="info3"]/div/div/div[3]/div/div/label/span').click()
                time.sleep(1)
                print("-> 로그 상세기능 잠금 해제 완료")
            else:
                print("-> 로그 상세기능 잠금 해제되어 있음")
        # 메신저 수신 메시지 설정 여부 확인 및 활성화
        # if is_element_id_exist(driver, 'messengerRecvMessageLogEnable'):
        #     toggle = driver.find_element(By.ID, 'messengerRecvMessageLogEnable')
        #     if toggle.is_selected() is False:
        #         span_element = WebDriverWait(driver, 10).until(
        #             EC.presence_of_element_located((By.CSS_SELECTOR,
        #                                             '#info4 > div > div > div:nth-child(2) > div > div:nth-child(1) > label > span'))
        #         )
        #         print(span_element.text)
        #         print(span_element.get_attribute('outerHTML'))
        #         driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", span_element)
        #         driver.execute_script("arguments[0].click();", span_element)
        #         time.sleep(1)
        #         print("-> 메신저 수신 로깅 ON 변경 완료")
        #     else:
        #         print("-> 메신저 수신 로깅 ON 설정되어 있음")
        # 개인정보 체크 패턴 여부 확인 및 활성화
        if is_element_id_exist(driver, 'patternPaPcCheckDbEnable'):
            toggle = driver.find_element(By.ID, 'patternPaPcCheckDbEnable')
            if toggle.is_selected() is False:
                driver.find_element(By.XPATH, '//*[@id="info4"]/div/div/div[3]/div/div[1]/label/span').click()
                time.sleep(1)
                print("-> 개인정보 체크 패턴 ON 변경 완료")
            else:
                print("-> 개인정보 체크 패턴 ON 설정되어 있음")
        else:
            print("-> 개인정보 패턴 체크 UI 없음")
        # 저장 클릭
        driver.find_element(By.NAME, 'ok').click()
        time.sleep(5)
        # 확인 클릭
        do_click(driver, By.ID, 'modal_ok')
        time.sleep(5)
        # 확인 클릭
        do_click(driver, By.ID, 'modal_ok')
        time.sleep(30)
        return True
    except Exception as e:
        print(f"서버 설정 중 오류 발생: {e}")
        return False

# 인사 연동 설정
def set_insa_db(driver):
    try:
        print("인사 연동 설정 시작")

        # 연동 DB 등록
        count = create_insa_db(driver)
        if count == 1:
            pass
        elif count == 0:
            print("인사 연동 설정을 계속 진행합니다.")
            # 맵핑 설정
            mapping_insa_db(driver)
            # 연동 설정
            setting_insa_db(driver)
            # 실행 및 스케쥴 -> 실행
            exe_insa_db(driver)
        else:
            print("인사 연동 설정 중 오류가 발생했습니다.")

        return True
    except Exception as e:
        # 예외 발생 시 처리할 내용을 작성합니다.
        print(f"An error occurred: {e}")
        return False

def create_insa_db(driver):
    # 설정 클릭
    do_click(driver, By.XPATH, '//*[@id="setting"]/a')
    time.sleep(0.5)
    # 인사 연동 클릭
    do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/a')
    time.sleep(0.5)
    # 인사DB 등록 클릭
    do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[1]/a')
    time.sleep(0.5)

    # 연동 테이블 가져와서 추가 여부를 확인
    db_table = get_table_data(driver, 'insa_db_list')
    body = db_table[0].find_elements(By.TAG_NAME, 'td')
    if body[0].text == '생성된 항목이 없습니다.':
        # 별칭 입력
        driver.find_element(By.ID, 'db_alias').send_keys('test')
        time.sleep(0.5)
        # 유형 선택
        Select(driver.find_element(By.ID, "db_kind_select")).select_by_visible_text("MariaDB")
        time.sleep(0.5)
        # 아이피 입력
        driver.find_element(By.ID, 'db_ip').send_keys('xxx.xxx.xxx.xxx')
        time.sleep(0.5)
        # 계정 입력
        driver.find_element(By.ID, 'db_con_usr').send_keys('root')
        time.sleep(0.5)
        # 패스워드 입력
        driver.find_element(By.ID, 'db_con_pw').send_keys('password')
        time.sleep(0.5)
        # DATABASE 명 입력
        driver.find_element(By.ID, 'db_con_database').send_keys('eeeeeee')
        time.sleep(0.5)
        # 저장 클릭
        driver.find_element(By.NAME, 'save').click()
        time.sleep(1)
        # [확인] 클릭
        driver.find_element(By.ID, 'modal_ok').click()
        time.sleep(1)
        # 정상적 저장 여부 확인창에서 [확인] 클릭
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, 'modal_title')))
        cmt = driver.find_element(By.ID, 'modal_content').text
        if cmt == '정상적으로 저장 되었습니다.':
            driver.find_element(By.ID, 'modal_cancel').click()
            print("인사DB가 등록되었습니다.")
            return 0
        elif cmt == '연결에 실패하였습니다. 입력하신 정보는 저장하시겠습니까?':
            return -1
    else:
        print("-> 이미 연동 DB가 등록되어 있습니다.")
        return 1


def mapping_insa_db(driver):
    # 인사DB 맵핑 클릭
    do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[2]/a')
    time.sleep(0.5)

    for info in range(1, 4):
        # 사용자 정보 탭 설정
        if info == 1:
            driver.find_element(By.NAME, 'use_tbl').click()
        elif info == 2:
            driver.find_element(By.NAME, 'group_tbl').click()
        elif info == 3:
            driver.find_element(By.NAME, 'ip_tbl').click()
        time.sleep(0.5)
        # 연동 DB, 기본 테이블 선택
        wait = WebDriverWait(driver, 10)
        select_element = wait.until(EC.presence_of_element_located((By.ID, "conDb_select")))
        Select(select_element).select_by_visible_text("test [mariadb / xxx.xxx.xxx.xxx] - None")
        time.sleep(1)
        if info == 1 or info == 3:
            wait = WebDriverWait(driver, 10)
            select_element = wait.until(EC.presence_of_element_located((By.ID, "default_tbl")))
            Select(select_element).select_by_visible_text("user_new")
        if info == 2:
            wait = WebDriverWait(driver, 10)
            select_element = wait.until(EC.presence_of_element_located((By.ID, "default_tbl")))
            Select(select_element).select_by_visible_text("groupname")
        time.sleep(0.5)
        # 연동 컬럼명 선택
        col_name = ''
        if info == 1:
            for col_num in range(1, 9):
                if col_num == 1 or col_num == 3:
                    col_name = 'id'
                elif col_num == 2:
                    col_name = 'group'
                elif col_num == 4:
                    col_name = 'name'
                elif col_num == 5:
                    col_name = 'cellphone'
                elif col_num == 6:
                    col_name = 'email'
                elif col_num == 7:
                    col_name = 'level'
                elif col_num == 8:
                    col_name = 'expire'
                Select(driver.find_element(By.XPATH, f'//*[@id="rule_list"]/tbody/tr[{col_num}]/td[5]/select')).select_by_visible_text(col_name)
        elif info == 2:
            for col_num in range(1, 4):
                if col_num == 1:
                    col_name = 'group_code'
                elif col_num == 2:
                    col_name = 'group_name'
                elif col_num == 3:
                    col_name = 'group_upper'
                Select(driver.find_element(By.XPATH, f'//*[@id="rule_list"]/tbody/tr[{col_num}]/td[5]/select')).select_by_visible_text(col_name)
        elif info == 3:
            for col_num in range(1, 3):
                if col_num == 1:
                    col_name = 'id'
                elif col_num == 2:
                    col_name = 'ipaddress'
                Select(driver.find_element(By.XPATH, f'//*[@id="rule_list"]/tbody/tr[{col_num}]/td[5]/select')).select_by_visible_text(col_name)
        # 저장 클릭
        driver.find_element(By.NAME, 'save').click()
        time.sleep(1)
        # 저장 여부 확인창에서 [확인] 클릭
        driver.find_element(By.ID, 'modal_ok').click()
        time.sleep(1)
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'modal_title')))
        cmt = driver.find_element(By.ID, 'modal_content').text
        if cmt == '성공적으로 저장하였습니다.':
            driver.find_element(By.ID, 'modal_ok').click()
        else:
            print("인사DB 맵핑 중 문제가 발생했습니다.")
            return False
        # 사용자 정보 -> 매핑 상태 확인
        Select(driver.find_element(By.ID, "conDb_select")).select_by_visible_text(
            "test [mariadb / 172.16.150.139] - Mapping")
        time.sleep(1)
        mapping_status = driver.find_element(By.XPATH, '//*[@id="rule_mode"]/label/font').text
        if mapping_status == 'Complete':
            pass
        else:
            print("인사DB 등록 상태 확인 중 문제가 발생했습니다.")
            return False
    print("맵핑이 완료되었습니다.")

def setting_insa_db(driver):
    # 연동설정 클릭
    do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[4]/a')
    time.sleep(0.5)
    # 연동 방법 -> 초기화 후 등록, 사내 조직도를 통한 사용자 처리 여부 '포함' 으로 선택
    driver.find_element(By.XPATH, '//*[@id="setting_one_panel"]/div[2]/div/div[2]/div/div[2]/div/label').click()
    time.sleep(1)
    driver.find_element(By.XPATH, '//*[@id="setting_one_panel"]/div[3]/div/div[2]/div/div[2]/div/label').click()
    # 저장
    driver.find_element(By.NAME, 'save').click()
    time.sleep(1)
    driver.find_element(By.ID, 'modal_ok').click()
    time.sleep(1)
    print("연동 설정이 완료되었습니다.")

def exe_insa_db(driver):
    # 실행 및 스케쥴 클릭
    do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[5]/a')
    time.sleep(0.5)
    # 지금실행 클릭
    do_click(driver, By.ID, 'executeButton')
    time.sleep(1)
    # 팝업창에서 [확인] 클릭
    alert = driver.switch_to.alert
    alert.accept()
    time.sleep(30)
    # 인사연동 진행 팝업창에서 [확인] 클릭
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.element_to_be_clickable((By.ID, 'modal_cancel')))
    element.click()
    time.sleep(2)

# 키워드 정책 조건 추가
def create_keyword_condition(driver):
    try :
        count = 0
        # 키워드 조건 생성
        # 정책 클릭
        do_click(driver, By.XPATH, '//*[@id="policy"]/a')
        time.sleep(0.5)
        # 정책 조건 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/a')
        time.sleep(0.5)
        # 키워드 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[3]/a')
        time.sleep(1)
        # 키워드 조건이 존재하는지 확인
        tr = get_table_data(driver, 'keywordlist_table')
        for td in tr:
            body_0 = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, './/td[1]'))
            )  # 요소를 사용할 때까지 대기
            if body_0.text == '생성된 항목이 없습니다.':
                break
            body_1 = td.find_elements(By.TAG_NAME, 'td')[1]
            if body_1.text == "키워드테스트":
                count = 1
                print("-> 이미 생성된 조건이 있음")
                break
            else:
                pass
        # 키워드 조건이 없으면 키워드 조건 생성
        if count == 0:
            # 키워드 생성 버튼 클릭
            do_click(driver, By.NAME, 'create')
            time.sleep(1)
            # 조건 이름 및 키워드 입력 후 저장
            do_send_keys(driver, By.XPATH, '//*[@id="keyword_add"]/div/div[2]/div/div/input', "키워드테스트")
            do_send_keys(driver, By.XPATH, '//*[@id="add_keyword"]', "키워드테스트")
            time.sleep(1)
            # 추가 클릭
            do_click(driver, By.NAME, 'add')
            time.sleep(1)
            # 저장 클릭
            do_click(driver, By.NAME, 'ok')
            print("-> 키워드 조건 1 생성 완료")
            time.sleep(2)

            # 키워드 생성 버튼 클릭
            do_click(driver, By.NAME, 'create')
            time.sleep(1)
            # 조건 이름 및 키워드 입력 후 저장
            do_send_keys(driver, By.XPATH, '//*[@id="keyword_add"]/div/div[2]/div/div/input', "수산아이앤티")
            do_send_keys(driver, By.XPATH, '//*[@id="add_keyword"]', "수산아이앤티")
            time.sleep(1)
            # 추가 클릭
            do_click(driver, By.NAME, 'add')
            time.sleep(1)
            # 저장 클릭
            do_click(driver, By.NAME, 'ok')
            print("-> 키워드 조건 2 생성 완료")
            time.sleep(2)

            # 키워드 생성 버튼 클릭
            do_click(driver, By.NAME, 'create')
            time.sleep(1)
            # 조건 이름 및 키워드 입력 후 저장
            do_send_keys(driver, By.XPATH, '//*[@id="keyword_add"]/div/div[2]/div/div/input', "일지매")
            do_send_keys(driver, By.XPATH, '//*[@id="add_keyword"]', "일지매")
            time.sleep(1)
            # 추가 클릭
            do_click(driver, By.NAME, 'add')
            time.sleep(1)
            # 저장 클릭
            do_click(driver, By.NAME, 'ok')
            print("-> 키워드 조건 3 생성 완료")
            time.sleep(2)


        else:
            pass

        return True
    except Exception as e:
        print(f"Error in create_policy_block: {e}")
    return False

# 첨부파일 정책 조건 추가
def create_attach_condition(driver):
    try :

        count = 0
        # 첨부파일 조건 생성
        # 첨부파일 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[2]/ul/li[4]/a')
        time.sleep(1)
        # 첨부파일 조건이 존재하는지 확인
        tr = get_table_data(driver, 'attach_file_table')
        for td in tr:
            body_0 = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, './/td[1]'))
            )  # 요소를 사용할 때까지 대기
            if body_0.text == '생성된 항목이 없습니다.':
                break
            body_1 = td.find_elements(By.TAG_NAME, 'td')[1]
            if body_1.text == "첨부파일테스트":
                count = 1
                print("-> 이미 생성된 조건이 있음")
                break
            else:
                pass
        # 첨부파일 조건이 없으면 첨부파일 조건 생성
        if count == 0:
            # 첨부파일 생성 버튼 클릭
            do_click(driver, By.NAME, 'create')
            time.sleep(1)
            # 조건 이름 및 키워드 입력 후 저장
            do_send_keys(driver, By.XPATH, '//*[@id="attach_file_add"]/div/div[3]/div/div[2]/input', "첨부파일테스트")
            time.sleep(1)
            # 파일 타입 토글 활성화
            do_click(driver, By.XPATH, '//*[@id="attach_file_add"]/div/div[6]/div/label[2]/div')
            time.sleep(1)
            # 파일 타입 전체 추가 클릭
            do_click(driver, By.NAME, 'fileTypeAddALL')
            time.sleep(1)
            # 저장 클릭
            do_click(driver, By.NAME, 'ok')
            time.sleep(1)
            # 팝업창에서 확인 클릭
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, 'modal_title')))
            driver.find_element(By.ID, 'modal_cancel').click()
            do_click(driver, By.NAME, 'ok')
            print("-> 첨부파일 조건 생성 완료")
            time.sleep(2)

        else:
            pass

        return True
    except Exception as e:
        print(f"Error in create_policy_block: {e}")
        return False


# 감시 정책 반복문 활용
def create_policy_mirror(driver):
    try:
        policy_details = [
            {"name": "전체감시_개인정보", "tab_name": "pattern", "tab_xpath": '//*[@id="tab_detail"]/div[1]/div[2]/input'},
            {"name": "전체감시_키워드", "tab_name": "keyword", "tab_xpath": '//*[@id="tab_detail"]/div[2]/div[2]/input'},
            {"name": "전체감시_첨부파일", "tab_name": "attachfile", "tab_xpath": '//*[@id="tab_detail"]/div[3]/div[2]/input'},
            {"name": "전체감시_기본", "tab_name": None, "tab_xpath": None},
        ]

        # 정책 관리 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[1]/a')
        time.sleep(1)
        # 서비스 정책 관리 클릭
        do_click(driver, By.XPATH, '//*[@id="menu_group"]/div[2]/div/ul/li[1]/ul/li/a')
        time.sleep(1)

        for policy in policy_details:
            create_policy_mirror_sub(driver, policy["name"], policy["tab_name"], policy["tab_xpath"])

        return True
    except Exception as e:
        print(f"Error in create_policy_mirror: {e}")
        return False

def create_policy_mirror_sub(driver, policy_name, tab_name, tab_xpath):
    # 정책 생성 클릭
    do_click(driver, By.NAME, 'create')
    time.sleep(1)
    # 정책 이름 입력
    do_send_keys(driver, By.XPATH, '//*[@id="rule_add"]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/input', policy_name)
    time.sleep(0.5)
    # 정책 종류 감시로 선택
    do_click(driver, By.XPATH, '//*[@id="rule_add"]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[2]/label[3]/input')
    time.sleep(0.5)
    # 부서 선택
    do_click(driver, By.XPATH, '//*[@id="group_select"]/div[1]/i')
    time.sleep(1)
    # 회사 선택
    do_click(driver, By.CLASS_NAME, 'dynatree-checkbox')
    time.sleep(1)
    # 확인 선택
    do_click(driver, By.ID, 'target_modal_ok')
    time.sleep(1)
    # 지원 서비스 전체 선택
    do_click(driver, By.ID, 'is_all')
    time.sleep(1)

    if tab_name and tab_xpath:
        # 탭 이동 및 선택
        element = driver.find_element(By.NAME, tab_name)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].setAttribute('class', 'active')", element)
        time.sleep(1)
        tab_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, tab_name))
        )
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(1)
        # 세부 조건 전체 선택
        do_click(driver, By.XPATH, tab_xpath)
        time.sleep(1)

    # 저장 클릭
    element = driver.find_element(By.NAME, 'ok')
    driver.execute_script("arguments[0].scrollIntoView();", element)
    element.click()
    time.sleep(2)
    # 확인 클릭
    do_click(driver, By.ID, 'modal_cancel')
    time.sleep(1)

# 차단 정책 생성
def create_policy_block(driver):
    try:
        policy_details = [
            {"name": "전체차단_개인정보", "tab_name": "pattern", "tab_xpath": '//*[@id="tab_detail"]/div[1]/div[2]/input'},
            {"name": "전체차단_키워드", "tab_name": "keyword", "tab_xpath": '//*[@id="tab_detail"]/div[2]/div[2]/input'},
            {"name": "전체차단_첨부파일", "tab_name": "attachfile", "tab_xpath": '//*[@id="tab_detail"]/div[3]/div[2]/input'},
        ]

        for policy in policy_details:
            create_policy_block_sub(driver, policy["name"], policy["tab_name"], policy["tab_xpath"])

        return True
    except Exception as e:
        print(f"Error in create_policy_block: {e}")
        return False

def create_policy_block_sub(driver, policy_name, tab_name, tab_xpath):
    # 정책 생성 클릭
    do_click(driver, By.NAME, 'create')
    time.sleep(1)
    # 정책 이름 입력
    do_send_keys(driver, By.XPATH, '//*[@id="rule_add"]/div[2]/div[1]/div[1]/div[2]/div[1]/div/div[2]/input', policy_name)
    time.sleep(0.5)
    # 정책 종류 차단으로 선택
    do_click(driver, By.XPATH, '//*[@id="rule_add"]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[2]/label[1]/input')
    time.sleep(0.5)
    # 부서 선택
    do_click(driver, By.XPATH, '//*[@id="group_select"]/div[1]/i')
    time.sleep(1)
    # 회사 선택
    do_click(driver, By.CLASS_NAME, 'dynatree-checkbox')
    time.sleep(1)
    # 확인 선택
    do_click(driver, By.ID, 'target_modal_ok')
    time.sleep(1)
    # 지원 서비스 전체 선택
    do_click(driver, By.ID, 'is_all')
    time.sleep(1)

    if tab_name and tab_xpath:
        # 탭 이동 및 선택
        element = driver.find_element(By.NAME, tab_name)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].setAttribute('class', 'active')", element)
        time.sleep(1)
        tab_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, tab_name))
        )
        driver.execute_script("arguments[0].click();", tab_element)
        time.sleep(1)
        # 세부 조건 전체 선택
        do_click(driver, By.XPATH, tab_xpath)
        time.sleep(1)

    # 저장 클릭
    element = driver.find_element(By.NAME, 'ok')
    driver.execute_script("arguments[0].scrollIntoView();", element)
    element.click()
    time.sleep(2)
    # 확인 클릭
    do_click(driver, By.ID, 'modal_cancel')
    time.sleep(1)

def syncronize(driver):
    try:

        # 정책 클릭
        do_click(driver, By.XPATH, '//*[@id="policy"]/a')
        time.sleep(0.5)
        # 클러스터링인 경우, 동기화 클릭
        if device_type == 'cluster' or device_type == 'cluster+segment':
            element = driver.find_element(By.ID, 'synchronization')
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.click()
            time.sleep(1)
            # 확인 클릭
            do_click(driver, By.ID, 'modal_ok')
            time.sleep(1)
            # 데이터 동기화 클릭
            do_click(driver, By.ID, 'sync_confirm_btn')
            time.sleep(5)
            # 확인 클릭
            do_click(driver, By.ID, 'modal_cancel')
            time.sleep(1)
            # 닫기 클릭
            do_click(driver, By.XPATH, '//*[@id="sync_info_modal"]/div/div/div[3]/button[2]')
            time.sleep(1)
            # 반영 클릭
            do_click(driver, By.ID, 'apply')
            # 팝업 내 반영 클릭
            do_click(driver, By.ID, 'apply_confirm_btn')
            # 확인 클릭
            do_click(driver, By.ID, 'modal_ok')
            time.sleep(10)
            # 반영 후 확인 클릭
            do_click(driver, By.ID, 'modal_cancel')
            time.sleep(1)

            print("동기화 및 반영이 완료되었습니다.")


        else:
            # 클러스터링이 아닌 경우, 반영 클릭
            do_click(driver, By.ID, 'apply')
            # 팝업 내 반영 클릭
            do_click(driver, By.ID, 'apply_confirm_btn')
            # 확인 클릭
            do_click(driver, By.ID, 'modal_ok')
            time.sleep(10)
            # 반영 후 확인 클릭
            do_click(driver, By.ID, 'modal_cancel')
            time.sleep(1)

            print("반영이 완료되었습니다.")

        return True
    except Exception as e:
        print(f"Error in create_policy_mirror: {e}")
        return False

# 로그레벨 설정
def set_loglevel(driver):
    try:
        # 로그레벨 URL로 이동
        driver.get(f'{dlp_address}/root/loglevel')

        # Object Console 선택
        do_click(driver, By.ID, 'object_console')
        # Object Syslog 선택
        do_click(driver, By.ID, 'object_syslog')
        # trace 버전 선택
        select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="page-wrapper"]/div/div[3]/div/div[2]/div/div[3]/div/select'))
        )
        Select(select_element).select_by_visible_text("Trace")
        time.sleep(0.5)
        # 확인
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'ok'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        do_click(driver, By.NAME, 'ok')
        time.sleep(2)
        # 확인 2
        do_click(driver, By.ID, 'modal_cancel')
        time.sleep(2)

        # 세그먼트 2
        wait = WebDriverWait(driver, 10)
        select_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='segmentSelect']")))
        Select(select_element).select_by_visible_text("세그먼트2")
        time.sleep(1)
        # Object Console 선택
        do_click(driver, By.ID, 'object_console')
        # Object Syslog 선택
        do_click(driver, By.ID, 'object_syslog')
        # trace 버전 선택
        select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="page-wrapper"]/div/div[3]/div/div[2]/div/div[3]/div/select'))
        )
        Select(select_element).select_by_visible_text("Trace")
        time.sleep(0.5)
        # 확인
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'ok'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        do_click(driver, By.NAME, 'ok')
        time.sleep(2)
        # 확인 2
        do_click(driver, By.ID, 'modal_cancel')
        time.sleep(2)

        return True
    except Exception as e:
        print(f"Error in create_policy_mirror: {e}")
        return False


