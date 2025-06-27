import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
from typing import Optional

from app.models.reports import Report
from sqlalchemy.orm import Session

# 폰트 등록
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "..", "fonts", "NanumBarunGothic.ttf")
BOLD_FONT_PATH = os.path.join(BASE_DIR, "..", "fonts", "NanumBarunGothicBold.ttf")

if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"폰트 파일이 없습니다: {FONT_PATH}")
else:
    pdfmetrics.registerFont(TTFont('NanumBarunGothic', FONT_PATH))

if not os.path.exists(BOLD_FONT_PATH):
    raise FileNotFoundError(f"볼드 폰트 파일이 없습니다: {BOLD_FONT_PATH}")
else:
    pdfmetrics.registerFont(TTFont('NanumBarunGothicBd', BOLD_FONT_PATH))
    

def create_report_pdf(summary: str, selected_title: str, researcher: str, company: str,
                      achieved: str, is_successful: bool = True,
                      current_step: Optional[str] = None,  
                      fail_reason: str = "",
                      report_style: str = "personal", 
                      output_dir: str = "static/reports") -> str:
    """
    생성된 텍스트와 메타데이터를 기반으로 PDF 파일을 생성하는 함수
    """
    def draw_footer(c, page_number):
        c.setFont("NanumBarunGothic", 9)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(letter[0] / 2, 30, f"랩가드 (LabGuard) - Page {page_number}")
        c.setFillColorRGB(0, 0, 0)

    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime("%Y.%m.%d")
    safe_title = selected_title.replace(":", "_").replace("/", "_").replace("\\", "_")
    filename = f"{output_dir}/report_{safe_title}_{report_style}_{today}_{os.urandom(4).hex()}.pdf"

    c = canvas.Canvas(filename, pagesize=letter)
    
    page_num = 1
    y = letter[1] - 80

    draw_footer(c, page_num)
    
    c.setFont("NanumBarunGothic", 16)
    c.drawString(50, y, f"[{'공식 실험 보고서' if report_style == 'business' else '개인 실험 기록'}]")
    y -= 30
    
    c.setFont("NanumBarunGothic", 10)
    display_status = f"상태: {achieved}"
    if achieved == '종료':
        display_status += f" ({'성공' if is_successful else '실패'})"    

    meta_info = [
        f"실험 제목: {selected_title}",
        f"소속: {company}",
        f"연구자: {researcher}",
        f"작성일: {datetime.now().strftime('%Y.%m.%d')}",
        display_status
    ]
    for info in meta_info:
        c.drawString(50, y, info)
        y -= 18
    y -= 10
    c.line(50, y, letter[0] - 50, y)
    y -= 24

    lines = summary.split("\n")
    for line in lines:
        stripped_line = line.strip()
        
        if stripped_line.startswith(("##", "#", "---")):
            continue

        if y < 80:
            c.showPage()
            page_num += 1
            draw_footer(c, page_num)
            y = letter[1] - 80

        is_heading = False
        is_sub_heading = False
        
        if stripped_line and stripped_line[0].isdigit() and '.' in stripped_line.split(' ')[0]:
            try:
                first_part = stripped_line.split(' ')[0]
                if '.' in first_part:
                    int(first_part.split('.')[0]) 
                    is_heading = True
            except ValueError:
                is_heading = False

        if is_heading:
            c.setFont("NanumBarunGothicBd", 14)
            y -= 18
            wrapped_text = simpleSplit(stripped_line, "NanumBarunGothicBd", 14, letter[0] - 100)
            
        elif stripped_line.startswith(('-', '*', '▶')):
            c.setFont("NanumBarunGothic", 12)
            y -= 14
            wrapped_text = simpleSplit(stripped_line, "NanumBarunGothic", 12, letter[0] - 110)
            is_sub_heading = True
            
        else:
            c.setFont("NanumBarunGothic", 11)
            wrapped_text = simpleSplit(stripped_line, "NanumBarunGothic", 11, letter[0] - 100)
        
        for text_part in wrapped_text:
            if y < 80:
                c.showPage()
                page_num += 1
                draw_footer(c, page_num)
                y = letter[1] - 80
                if is_heading: 
                    c.setFont("NanumBarunGothicBd", 14)
                elif is_sub_heading:
                    c.setFont("NanumBarunGothic", 12)
                else: 
                    c.setFont("NanumBarunGothic", 11)

            if is_sub_heading:
                c.drawString(60, y, text_part)
            else:
                c.drawString(50, y, text_part)
            
            y -= 18

        if is_heading:
            y -= 5

    if achieved == "종료" and not is_successful and fail_reason:
        if y < 150:
            c.showPage()
            page_num += 1
            draw_footer(c, page_num)
            y = letter[1] - 80

        y -= 24
        c.line(50, y, letter[0] - 50, y)
        y -= 24
        
        c.setFont("NanumBarunGothicBd", 14)
        c.drawString(50, y, "실패 원인 상세 분석")
        y -= 24
        
        c.setFont("NanumBarunGothic", 11)
        wrapped_fail_reason = simpleSplit(fail_reason, "NanumBarunGothic", 11, letter[0] - 100)
        for text_part in wrapped_fail_reason:
            if y < 50:
                c.showPage()
                page_num += 1
                draw_footer(c, page_num)
                y = letter[1] - 80
                c.setFont("NanumBarunGothic", 11)
            c.drawString(50, y, text_part)
            y -= 16

    if y < 50:
        c.showPage()
        page_num += 1
        draw_footer(c, page_num)
        y = letter[1] - 80
    
    c.setFont("NanumBarunGothic", 11)
    c.drawString(50, y, f"이상으로 '{selected_title}'에 대한 실험 리포트를 마칩니다.")
    y -= 18

    try:
        c.save()
        print(f"보고서가 PDF로 저장되었습니다: {filename}")
        return filename
    except Exception as e:
        print(f"[PDF 저장 중 오류 발생]: {e}")
        raise

def save_report_metadata(
    db: Session,
    user_id: int,
    manual_id: str,
    # experiment_id: str,
    file_path: str,
    report_type: str = "business",
    status: str = "created"
):
    report = Report(
        user_id=user_id,
        manual_id=manual_id,
        # experiment_id=experiment_id,
        file_path=file_path,
        report_type=report_type,
        status=status
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
