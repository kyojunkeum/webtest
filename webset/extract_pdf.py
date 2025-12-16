from pdfminer.high_level import extract_text
from openpyxl import Workbook

# PDF 파일에서 텍스트 추출
pdf_file_path = 'D:/오픈소스 취약점_xxx.xxx.xxx.xxx.pdf'
text = extract_text(pdf_file_path)

# 텍스트에서 데이터 추출
data = []

# 텍스트를 분석하여 필요한 정보를 추출하는 예시
lines = text.split('\n')
current_data = {}

# 각 줄을 처리하면서 현재 줄, 다음 줄, 다다음 줄을 함께 추출
for i in range(len(lines) - 4):  # 다음 줄까지 처리해야 하므로 len(lines) - 4
    line = lines[i].strip()               # 현재 줄 공백 제거
    next_line = lines[i + 1].strip()      # 다음 줄 공백 제거
    next_next_line = lines[i + 2].strip()  # 다다음 줄 공백 제거
    next_next_next_line = lines[i + 3].strip()  # 네 번째 줄 공백 제거
    next_next_next_next_line = lines[i + 4].strip()  # 다섯 번째 줄 공백 제거

    if 'CVSS' in line:  # 위험도 정보가 있는 줄
        current_data['위험도'] = line
    elif 'NVT' in line:  # 요약 제목 정보가 있는 줄
        current_data['요약 제목'] = line
    elif 'Solution' in line:
        current_data['OS'] = next_next_next_next_line
    elif 'Vulnerability Insight' in line:
        current_data['취약점 인사이트'] = f"{line} {next_line} {next_next_line} {next_next_next_line} {next_next_next_next_line}"
    elif 'path / port' in line:
        current_data['설치 경로/포트'] = f"{line} {next_line} {next_next_line}"
    elif 'Solution type' in line:
        current_data['해결 방법'] = f"{line} {next_line}"

    # 모든 데이터가 수집되면 current_data를 한 번에 추가하고 초기화
    if '위험도' in current_data and '요약 제목' in current_data and '취약점 인사이트' in current_data and '설치 경로/포트' in current_data and '해결 방법' in current_data:
        data.append(current_data)  # current_data가 완전하면 리스트에 추가
        current_data = {}  # 데이터를 추가한 후 초기화

# 엑셀 파일로 저장하기 위해 openpyxl 사용
wb = Workbook()
ws = wb.active

# 헤더 추가
ws.append(["위험도", "요약 제목", "영향받는 소프트웨어/OS", "취약점 인사이트", "설치 경로/포트", "해결 방법"])

# 데이터 추가
for row in data:
    ws.append([
        row.get("위험도", ""),
        row.get("요약 제목", ""),
        row.get("OS", ""),
        row.get("취약점 인사이트", ""),
        row.get("설치 경로/포트", ""),
        row.get("해결 방법", "")
    ])

# 엑셀 파일로 저장
wb.save('vulnerability_report13.xlsx')
