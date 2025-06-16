import os
import uuid
import time
import re
import io
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
# import pytesseract
from pdf2image import convert_from_path
import base64

from PyPDF2 import PdfReader
from PIL import Image
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)


CHROMA_DIR = "./chroma_db"  
POPLER_PATH = r"C:\Users\201-16\Documents\poppler-24.08.0\Library\bin"

# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



# ===================
# 청크 필터링 함수 정의
# =====================
# def filter_chunk(text: str) -> bool:
#     """
#     특수문자/수식/깨진 문자가 포함된 chunk를 필터링하는 함수.
#     - 한글, 영어, 숫자, 공백, 일반적인 문장부호(.,;:!?()-[]/) 만 허용
#     - 나머지 특수문자/수식/깨진 문자는 제외
#     """
#     # 허용 문자: 한글, 영문, 숫자, 공백, 일반 문장부호
#     allowed_pattern = r'[^\uAC00-\uD7A3a-zA-Z0-9 .,;:!?()\[\]\-/]'  # 허용 외 문자
#     # 특수문자/깨진문자/수식이 있으면 False
#     if re.search(allowed_pattern, text):
#         return False
#     return True

# 깨진 텍스트 판별
def is_broken_or_missing(text: str) -> bool:
    if not text.strip():
        return True
    broken_chars = text.count("□") + text.count("�")
    ratio = broken_chars / len(text)
    return ratio > 0.05 or len(text.strip()) < 10

# 그림/표 캡션 포함 여부
def has_figure_or_table_caption(text: str) -> bool:
    patterns = ["그림 \d+", "표 \d+", r"\[그림 \d+\]", r"\[표 \d+\]"]
    return any(re.search(pat, text) for pat in patterns)

# 누락 페이지 확인
def get_missing_page_numbers(total_pages: int, parsed_docs: list) -> set:
    parsed_page_nums = set(doc.metadata.get("page", -1) for doc in parsed_docs)
    return set(range(1, total_pages + 1)) - parsed_page_nums

# 청크 필터링
def filter_chunk(text: str) -> bool:
    text = text.strip()
    if len(text) < 5:
        return False
    valid_chars = re.findall(r'[\uAC00-\uD7A3a-zA-Z0-9 .,;:!?()\[\]\-/]', text)
    return len(valid_chars) / len(text) > 0.5

# GPT-4o Vision 모델 호출
def call_vision_model_with_gpt4o(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": "이 문서 이미지를 보고 내용을 텍스트로 정확히 설명해 주세요."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}
        ],
        max_tokens=1024,
        temperature=0.2
    )
    vision_text = response.choices[0].message.content
    return vision_text

async def embed_pdf_manual(file: UploadFile, manual_type: str = "UNKNOWN") -> dict:
    import tempfile, shutil
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        # 1. manual_id 생성 (uuid)
        manual_id = str(uuid.uuid4())
        # 2. PyPDFLoader로 텍스트 추출 및 청킹
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        split_docs = splitter.split_documents(docs)
        # 3. 일반 chunk에 메타데이터 부여
        pdf_chunks = []
        existing_texts = set()
        vision_page_candidates = set()

        for idx, doc in enumerate(split_docs):
            # if not filter_chunk(doc.page_content):
            #     continue  # 특수문자/수식/깨진 문자가 포함된 청크는 저장하지 않음
            page_num = doc.metadata.get("page", 1)
            content = doc.page_content.strip()

            if is_broken_or_missing(content):
                vision_page_candidates.add(page_num)
                continue

            if has_figure_or_table_caption(content):
                vision_page_candidates.add(page_num)

            if not filter_chunk(content):
                continue

            meta = {
                "manual_id": manual_id,
                "manual_type": manual_type,
                "page_num": page_num,
                "chunk_idx": idx,
                "source": "pdf",
                "filename": file.filename,
                "uploaded_at": int(time.time())
            }
            pdf_chunks.append(Document(page_content=content, metadata=meta))
            existing_texts.add(content)
            
        total_pages = len(PdfReader(temp_path).pages)
        missing_pages = get_missing_page_numbers(total_pages, split_docs)
        vision_page_candidates.update(missing_pages)

        images = convert_from_path(temp_path, poppler_path=POPLER_PATH)
        vision_docs = []

        for page_num in sorted(vision_page_candidates):
            if page_num - 1 < len(images):
                image = images[page_num - 1]
                vision_text = call_vision_model_with_gpt4o(image)
                meta = {
                    "manual_id": manual_id,
                    "manual_type": manual_type,
                    "page_num": page_num,
                    "chunk_idx": len(pdf_chunks) + len(vision_docs),
                    "source": "gpt4o",
                    "chunk_type": "vision_extracted",
                    "filename": file.filename,
                    "uploaded_at": int(time.time())
                }
                vision_docs.append(Document(page_content=vision_text, metadata=meta))
       
                    

        # existing_texts = set(doc.page_content.strip() for doc in split_docs)
        # for idx, img in enumerate(images):
        #     ocr_text = pytesseract.image_to_string(img, lang='kor+eng').strip()
        #     if not ocr_text or ocr_text in existing_texts:
        #         continue
        #     if not filter_chunk(ocr_text):
        #         continue  # 특수문자/수식/깨진 문자가 포함된 청크는 저장하지 않음
        #     meta = {
        #         "manual_id": manual_id,
        #         "manual_type": manual_type,
        #         "page_num": idx + 1,
        #         "chunk_idx": idx,
        #         "source": "ocr",
        #         "filename": file.filename,
        #         "uploaded_at": int(time.time())
        #     }
        #     ocr_docs.append(Document(page_content=ocr_text, metadata=meta))
        #     print("✅ [5] OCR 통과한 청크 수:", len(ocr_docs))
        
        # 5. 합치기 및 벡터DB 저장
        all_docs = pdf_chunks + vision_docs
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma.from_documents(all_docs, embeddings, persist_directory=CHROMA_DIR)
        vectorstore.persist()
        return {
            "message": "PDF 임베딩 및 저장 완료",
            "manual_id": manual_id,
            "pdf_chunks": len(pdf_chunks),
            "ocr_chunks": len(vision_docs),
            "total_chunks": len(all_docs)
        }
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass 