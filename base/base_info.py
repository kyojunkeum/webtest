from datetime import datetime

# 시간 정의
now = datetime.now()
now_time = now.strftime("%Y-%m-%d %H:%M:%S")

# 개인정보
info_RRN = 'xxxxxx-xxxxxxx'  # 주민등록번호
info_phone = '010-xxxx-xxxx'
info_email = 'xxxxxx@xxxxxx.co.kr'
info_passport_num = 'xxxxxxxxxx'
info_passport_num_2 = 'xxxxxxxxxx'
info_credit = 'xxxx-xxxx-xxxx-xxxx'
info_CRN = 'xxx-xx-xxxxx'  # 사업자등록번호
info_HIC = 'xxxxxxxxxxx'  # 건강보험증번호
info_tel_num = 'xx-xxx-xxxx'
info_IP = 'xxx.xxx.xxx.xxx'
info_account_num = 'ssssss-ss-ssssss'  # 계좌번호
info_driver_license = '경기00-ssssss-ss'
info_FRN = 'ssssss-sssssss'  # 외국인등록번호
info_corp = 'xxxxxx-xxxxxxx'  # 법인등록번호

# 개인정보 리스트
# 본문 용
info_str_all = f'{info_RRN}, {info_phone}, {info_email}, {info_passport_num}, {info_passport_num_2}, {info_credit}, ' \
               f'{info_CRN}, {info_HIC}, {info_tel_num}, {info_IP}, {info_account_num}, {info_driver_license}, {info_FRN}, {info_corp}'

info_str_1 = f'{info_RRN}, {info_phone}, {info_email}, {info_passport_num}, {info_passport_num_2}, {info_credit}, {info_CRN}'

info_str_2 = f'{info_HIC}, {info_tel_num}, {info_IP}, {info_account_num}, {info_driver_license}, {info_FRN}, {info_corp}'

info_str_3 = f'{info_RRN}, {info_phone}, {info_email}, {info_passport_num}'

info_str_4 = f'{info_passport_num_2}, {info_credit}, {info_CRN}, {info_HIC}'

info_str_5 = f'{info_tel_num}, {info_IP}, {info_account_num}, {info_driver_license}'

info_str_6 = f'{info_FRN}, {info_corp}'

info_dict = {"주민등록번호": info_RRN, "휴대전화번호": info_phone,
             "IP": info_IP, "이메일형식": info_email,
             "계좌번호": info_account_num, "여권번호": info_passport_num,
             "운전면허번호": info_driver_license, "신용카드": info_credit,
             "외국인등록번호": info_FRN, "사업자등록번호": info_CRN,
             "법인등록번호": info_corp, "건강보험증번호": info_HIC,
             "전화번호": info_tel_num}

