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
from typing import List
import json 

from PyPDF2 import PdfReader
from PIL import Image
from openai import OpenAI
from google.generativeai import configure, GenerativeModel

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment variables.")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)
configure(api_key=GOOGLE_API_KEY)


CHROMA_DIR = "./chroma_db"  
POPLER_PATH = r"C:\Users\201-13\Documents\poppler-24.08.0\Library\bin"

# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



# =====================
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

# 제미나이 모델 호출
def call_vision_model_with_gemini(image: Image.Image) -> str:
    import google.generativeai as genai
    prompt = """
다음 이미지를 사람이 직접 보는 것처럼 시각적으로 설명해 주세요.

- 도형의 모양(예: 곡선, 직선, 파이프 형태 등), 라벨(h₁, h₂ 등), 화살표 방향, 연결 관계 등을 구체적으로 묘사해 주세요.
- 이미지에 포함된 수식이나 기호는 해석하지 말고 **텍스트 그대로** 보여 주세요. 예: \\( R_A = -k[A] \\
- "그림 5", "표 3"과 같은 캡션이나 번호도 **그대로 추출**해서 말해 주세요.
- 구성 요소들의 상대적 위치(예: 왼쪽 탱크, 오른쪽 파이프 등)를 명확히 설명해 주세요.
- 사람이 그림을 보고 설명하듯, **구조와 흐름** 위주로 말해 주세요.

※ 설명은 한국어로 해주세요.
"""
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    response = model.generate_content([prompt, image])
    return response.text

# === 실험 제목 찾기 & ID 부여 ===
def extract_experiment_titles(chunks: List[Document]) -> List[int]:
    """
    문서 청크에서 실험 제목(섹션 시작) 인덱스를 추출합니다.
    """
    # sampled_chunks_for_llm 리스트를 먼저 정의
    sampled_chunks_list = [] 
    # 전체 청크의 텍스트 양이 많을 수 있으므로, 일부만 샘플링하여 LLM에 전달합니다.
    # 여기서는 처음 20개 청크와 이후 20개 청크마다 하나씩 샘플링합니다.
    for i, chunk in enumerate(chunks):
        if i < 50 or (i % 10 == 0 and i > 0): # 처음 50개 + 이후 10개마다 1개씩 샘플링
            # 청크 내용을 500자로 제한 (토큰 비용 관리)
            preview_content = chunk.page_content[:1000]
            sampled_chunks_list.append(f"CHUNK_{i}:\n{preview_content}\n---\n")

    # 리스트를 문자열로 합쳐서 LLM에 전달할 최종 텍스트 생성
    full_text_sample_for_llm = "\n".join(sampled_chunks_list)
    
    prompt = f"""
    당신은 다양한 기술 매뉴얼에서 "실험" 섹션의 시작점을 정확하게 식별하는 전문가입니다.
    아래는 문서의 각 청크 내용(일부 샘플)입니다. 이 정보를 바탕으로, 다음 지시에 따라 **"주요 실험" 섹션의 시작 인덱스**를 찾아주세요.

    **"주요 실험"의 정의:**
    - 이 매뉴얼에서 하나의 독립적이고 완결된 **실험 과정, 방법론, 또는 연구 주제**를 나타내는 최상위 레벨의 섹션입니다.
    - 일반적으로 목차에 나타나는 항목이거나, 문서 내에서 새로운 장(Chapter), 파트(Part) 또는 큰 섹션의 시작을 의미합니다.
    - 보통 "실험 1", "제 II 장", "Part A: [실험명]", 또는 굵은 글씨와 큰 폰트로 된 제목 등이 이에 해당할 수 있습니다.

    **"주요 실험"이 아닌 경우 (새로운 실험으로 간주하지 않음):**
    - 각 "주요 실험" 내부에 있는 하위 소제목들 (예: "1. 서론", "2. 실험 이론", "3. 실험 기구", "4. 실험 순서", "5. 결과 및 토의", "6. 참고문헌").
    - 하위 절 (예: "3.1 시약 준비").
    - 단순히 페이지 번호, 장/절 번호만 있는 라인.
    - 'Abstract', '개요', '도입', '결론' 등은 특정 실험의 일부이지, 독립적인 새 실험이 아닙니다.
    - 표나 그림의 캡션, 주석, 부록, 색인 등.

    **문서 청크 내용 (샘플):**
    {full_text_sample_for_llm}

    ---
    **최종 지시사항:**
    위 기준에 따라 이 문서의 모든 **"주요 실험" 섹션이 시작되는 청크의 인덱스(CHUNK_X:)**를 모두 찾아주세요.
    답변은 **오직 JSON 배열 형태**로, 각 정수는 해당 "주요 실험" 섹션이 시작되는 청크의 인덱스여야 합니다.
    **반드시 이 JSON 형식만 반환해야 합니다.** 만약 식별된 주요 실험 섹션이 없다면 빈 배열 `[]`을 반환해주세요.

    **예시 (문서에 따라 실제 인덱스는 달라질 수 있습니다):**
    `[2, 15, 30, 45]`

    # 제ㅔ약삿항
    - 주의사항은 무시하고 최대한 많은 실험을 찾아주세요.
    """


    # --- LLM 호출 ---
    response = client.chat.completions.create(
        model="gpt-4.1-mini", 
        messages=[
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        max_tokens=256, 
        temperature=0.0, # 명확한 사실 추출을 위해 낮은 온도 유지
    )
    
    llm_output_str = response.choices[0].message.content
    llm_indices = json.loads(llm_output_str)

    print(f"✅ LLM이 식별한 실험 제목 인덱스: {llm_indices}")
    
    # LLM이 아무것도 찾지 못했을 때의 처리 (빈 리스트 반환을 가정)
    if not llm_indices:
        print("⚠️ LLM이 주요 실험 제목을 식별하지 못했습니다. 모든 청크에 단일 experiment_id를 할당합니다.")
        # 이 경우, assign_experiment_ids 함수에서 exp01 하나가 할당될 것입니다.
        # 명시적으로 [0]을 반환하여 최소한 첫 청크부터 exp01이 되도록 할 수도 있습니다.
        return [0] 
    
    return sorted(list(set(llm_indices)))

def assign_experiment_ids(chunks: List[Document], manual_id: str) -> List[Document]:
    """
    청크에 experiment_id 메타데이터를 할당합니다.
    """
    title_indexes = extract_experiment_titles(chunks) # LLM 또는 정규표현식 사용

    # 중복 제거 및 정렬
    title_indexes = sorted(list(set(title_indexes)))

    # 섹션 시작 인덱스 목록 생성 (0부터 시작하도록 보장)
    section_start_indices = [0]
    if 0 not in title_indexes: # 0이 이미 제목 인덱스에 없으면 추가
        section_start_indices.extend(title_indexes)
    else: # 0이 이미 있으면, title_indexes를 그대로 사용
        section_start_indices = title_indexes
    
    # 다시 한번 중복 제거 및 정렬
    section_start_indices = sorted(list(set(section_start_indices)))

    # 각 섹션에 experiment_id 할당
    for i in range(len(section_start_indices)):
        start_chunk_idx = section_start_indices[i]
        # 다음 섹션 시작 전까지 또는 문서 끝까지
        end_chunk_idx = section_start_indices[i+1] if i+1 < len(section_start_indices) else len(chunks)
        
        exp_id = f"{manual_id}_exp{i+1:02}" # 실험 ID는 01부터 시작

        for chunk_idx in range(start_chunk_idx, end_chunk_idx):
            # 청크 인덱스가 유효한 범위 내에 있는지 확인
            if chunk_idx < len(chunks):
                chunks[chunk_idx].metadata["experiment_id"] = exp_id
                
    return chunks

async def embed_pdf_manual(file: UploadFile, manual_type: str = "UNKNOWN", user_id: int = None) -> dict:
    import tempfile, shutil
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        # 1. manual_id 생성 (uuid)
        manual_id = str(uuid.uuid4())
        print(f"🎉 새 매뉴얼 ID 생성: {manual_id}")
        # 2. PyPDFLoader로 텍스트 추출 및 청킹
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        split_docs = splitter.split_documents(docs)
        # 3. 일반 chunk에 메타데이터 부여
        pdf_chunks = []
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
                "uploaded_at": int(time.time()),
                "user_id": user_id
            }
            pdf_chunks.append(Document(page_content=content, metadata=meta))
            # existing_texts.add(content)
            
        total_pages = len(PdfReader(temp_path).pages)
        missing_pages = get_missing_page_numbers(total_pages, split_docs)
        vision_page_candidates.update(missing_pages)

        images = convert_from_path(temp_path, poppler_path=POPLER_PATH)
        vision_docs = []

        for page_num in sorted(vision_page_candidates):
            if page_num - 1 < len(images):
                image = images[page_num - 1]
                vision_text = call_vision_model_with_gemini(image)

                # 비전 모델에서 추출한 텍스트도 필터링
                if not filter_chunk(vision_text):
                    continue

                meta = {
                    "manual_id": manual_id,
                    "manual_type": manual_type,
                    "page_num": page_num,
                    "chunk_idx": len(pdf_chunks) + len(vision_docs),
                    "source": "gemini",
                    "chunk_type": "vision_extracted",
                    "filename": file.filename,
                    "uploaded_at": int(time.time()),
                    "user_id": user_id
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
        
        # 모든 chunk에 experiment_id 할당
        all_docs = pdf_chunks + vision_docs
        all_docs = assign_experiment_ids(all_docs, manual_id)
        # 할당된 고유 experiment_id 목록 추출
        assigned_experiment_ids = sorted(list(set(doc.metadata.get("experiment_id") for doc in all_docs if "experiment_id" in doc.metadata)))
        #벡터db저장
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma.from_documents(all_docs, embeddings, persist_directory=CHROMA_DIR)
        vectorstore.persist()
        return {
            "message": "PDF 임베딩 및 저장 완료",
            "manual_id": manual_id,
            "pdf_chunks": len(pdf_chunks),
            "ocr_chunks": len(vision_docs),
            "total_chunks": len(all_docs),
            "experiment_ids": assigned_experiment_ids
        }
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass 