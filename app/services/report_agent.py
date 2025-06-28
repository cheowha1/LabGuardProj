import os
import json
from fastapi import HTTPException 
from typing import List, Dict, Optional, Literal

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.agent_chat_service import generate_experiment_report as get_user_chat_summary_from_db

# 전역변수 설정
# tracer = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DIR = "./chroma_db"
CHAT_AGENT_LOG_FILE = "./experiment_logs.json" # 로그 파일 경로

# LLM 및 임베딩 모델 초기화
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file or system environment.")
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3, openai_api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)


# 매뉴얼 요약 검색 tool
@tool
def search_manual_context(manual_id: str, query: str = "실험 매뉴얼의 주요 내용 요약") -> str:
    """
    manual_id와 쿼리를 사용하여 매뉴얼의 'summary' 타입 청크 중 가장 관련성 높은 3개를 검색하여 반환합니다.
    이 툴은 gpt-4.1-mini의 토큰 제한을 고려하여 매뉴얼의 요약된 내용을 가져옵니다.
    query는 요약할 내용의 관련성을 높이는 데 사용될 수 있습니다.
    """
    try:    
        docs = vectorstore.similarity_search(
            query,  # 고정된 문자열이 아닌, 호출 시 전달받는 query 매개변수 사용
            k=3,
            filter={
                "$and": [
                    {"manual_id": {"$eq": manual_id}},
                    {"type": {"$eq": "summary"}}
                ]
            }
        )
        return "\n".join([doc.page_content for doc in docs]) if docs else f"manual_id '{manual_id}'에 대한 요약 없음"
    except Exception as e:
        return f"매뉴얼 요약 검색 중 오류 발생: {str(e)}"    


# # 대화 로그 요약 tool (파일 기반 - 변경 전 주석처리)
# @tool
# def analyze_experiment_logs(user_id: int, manual_id: str) -> str: 
#     """
#     user_id와 manual_id로 파일에 저장된 실험 로그를 요약하여 가져옵니다.
#     이 툴은 JSON 파일에서 실험 로그를 읽어옵니다.
#     """
#     if not os.path.exists(CHAT_AGENT_LOG_FILE):
#         return "로그 파일 없음"
#     try:
#         with open(CHAT_AGENT_LOG_FILE, "r", encoding="utf-8") as f:
#             all_logs = json.load(f)
#     except json.JSONDecodeError: #  JSON 파싱 에러 처리 (로그 파일이 비어있을 경우)
#         print(f"로그 파일이 비어있거나 유효한 JSON 형식이 아닙니다: {CHAT_AGENT_LOG_FILE}")
#         return "로그 파일 로딩 실패: 유효하지 않은 형식"
#     except Exception as e:
#         print(f"로그 파일 로딩 실패: {e}")
#         return f"로그 파일 로딩 실패: {e}"
    
#     # manual_id와 user_id 기준으로 필터링하도록 변경
#     filtered = [
#         e for e in all_logs
#         if int(e.get("user_id", "0")) == user_id and e.get("manual_id", "").strip() == manual_id.strip()
#     ]

#     if not filtered:
#         return f"해당 user_id '{user_id}'와 manual_id '{manual_id}'에 대한 로그 없음"

#     return "\n".join([f"[{e.get('timestamp','')[:16]}] [{e.get('type')}]: {e.get('content')}" for e in filtered])

# 대화 로그 요약 tool (변경 후)
@tool
def analyze_experiment_logs(user_id: int, manual_id: str) -> str:
    """
    user_id와 manual_id로 DB에 저장된 대화 로그를 요약하여 가져옵니다.
    chat_agent_service의 generate_experiment_report 함수를 호출합니다.
    """
    try:
        chat_summary = get_user_chat_summary_from_db(user_id=str(user_id), manual_id=manual_id)

        if not chat_summary or chat_summary.strip() == "":
            return f"user_id '{user_id}'와 manual_id '{manual_id}'에 대한 대화 로그 요약 없음 (DB)."
        
        return chat_summary
    
    except Exception as e:
        return f"DB 대화 로그 요약 중 오류 발생: {str(e)}"

# 보고서 생성
@tool
def generate_report_draft(
    manual_summary: str,   
    chat_summary: str,
    report_style: str = "business",   # or "personal"
    manual_id: str = "",
    selected_title: str = "",
    researcher: str = "",
    company: str = "",
    achieved: str = "",
    is_successful: bool = False,
    user_id: Optional[int] = None, 
    user_type: str = "",             # "신입" 또는 "경력"
    top_k: int = 5,
    current_step: str = ""
) -> str:
    """매뉴얼 요약과 대화 요약, 스타일 및 실험자 정보를 받아 보고서 내용을 생성합니다."""

    tone = "격식체 (~합니다)" if report_style == "business" else "개인체 (~했다 등)"
    purpose = (
        "기업 보고용 공식 문서 스타일로 작성하세요."
        if report_style == "business"
        else "개인 기록용 자유로운 일지 스타일로 작성하세요."
    )

    # user_id는 int 타입으로 들어와도 f-string에서 자동으로 문자열로 변환
    # 실험 테이블 생겨서 수정해야할수도 있음 - 실험제목 -> title로 변경가능
    prompt_template = f"""
당신은 AI 실험 보조 비서입니다.

[기본 실험 정보]
- 매뉴얼 ID: {manual_id}
- 실험 제목: {selected_title}   
- 실험자: {researcher}
- 소속 회사: {company}
- 실험 목적 달성 여부: {achieved}
- 실험 성공 여부: {"성공" if is_successful else "실패"}
- 실험자 숙련도: {user_type}#
- 현재 실험 단계: {current_step}

[대화 로그 요약]
{chat_summary}

[참고용 매뉴얼 관련 요약 내용]
{manual_summary}

# 보고서 항목:
1. 실험 제목: '{selected_title}'를 사용
2. 실험 목적: 대화 로그 요약과 매뉴얼 관련 요약 내용을 기반으로 유추하여 작성
3. 사용 장비: 대화 로그 요약 또는 매뉴얼 관련 요약 내용을 기반으로 작성
4. 사용 시약: 대화 로그 요약 또는 매뉴얼 관련 요약 내용을 기반으로 작성
5. 실험 순서: 실제 수행된 단계(대화 로그 요약에서 유추) 위주로 작성
6. 내용
    - 주요 이슈 및 해결 과정: 대화 로그 요약에서 나타난 문제점과 해결 노력을 포함
    - 실험 성공 여부: '{is_successful}' 결과를 반영하여 작성
    - 실패 시 원인 분석: 실험이 실패했을 경우, 대화 로그 요약 내용에서 원인을 분석
    - 종합 고찰 및 마무리 문장: 실험 전반에 대한 고찰과 마무리 문장을 작성

- 문체는 {tone}으로 작성하며, {purpose}에 맞게 작성
- 각 항목은 Markdown 번호로 구분하고, 각 항목은 줄바꿈 포함하여 가독성 있게 작성
- 전체 분량은 500자 이상이 되도록 상세하게 작성
    """

    try:
        response = llm.invoke(prompt_template)
        return response.content
    except Exception as e:
        return f"보고서 생성 실패: {e}"


# 보고서 초안 생성 (1차)
# @tool
# def generate_report_draft(manual_summary: str, chat_summary: str, report_style: str = "business") -> str:
#     """매뉴얼 요약과 대화 요약, 스타일을 받아 보고서 초안을 생성합니다."""
#     tone = "격식체 (~합니다)" if report_style == "business" else "개인체 (~했다 등)"
#     purpose = "기업 보고용 공식 문서 스타일로 작성하세요." if report_style == "business" else "개인 기록용 자유로운 일지 스타일로 작성하세요."
#     prompt_template = f"""
# 당신은 AI 실험 보조 비서입니다.
# [대화 요약 내용]
# {chat_summary}

# [참고용 매뉴얼 요약]
# {manual_summary}

# # 보고서 항목:
# 1. 실험 제목
# 2. 실험 목적 (대화에서 유추)
# 3. 사용 장비 (대화 또는 매뉴얼 기반)
# 4. 사용 시약 (대화 또는 매뉴얼 기반)
# 5. 실험 순서 (실제 수행된 단계 위주)
# 6. 내용
#     - 주요 이슈 및 해결 과정
#     - 실험 성공 여부
#     - 실패 시 원인 분석
#     - 종합 고찰 및 마무리 문장

# - 문체는 {tone}
# - {purpose}
# - 항목은 Markdown 번호로 구분, 줄바꿈 포함, 약 500자 이상
#     """
#     try:
#         response = llm.invoke(prompt_template)
#         return response.content
#     except:
#         return "보고서 생성 실패"



# # 에이전트 클래스 정의 (변경 전)
# class ReportAgent:
#     def __init__(self):
#         self.llm = llm
#         self.tools = [search_manual_context, analyze_experiment_logs, generate_report_draft]

#         self.prompt = ChatPromptTemplate.from_messages([
#             ("system", """
#             당신은 실험 보고서  생성 AI입니다. 다음 절차를 따르세요:
#             1. search_manual_context → manual_id 기반 매뉴얼 요약 검색
#             2. analyze_experiment_logs → user_id + manual_id 로그 요약
#             3. generate_report_draft → 요약 기반 보고서 초안 생성
#             """),
#             ("human", "{input}\n{agent_scratchpad}")
#         ])
#         self.agent_executor = AgentExecutor(
#             agent=create_openai_tools_agent(self.llm, self.tools, self.prompt),
#             tools=self.tools,
#             verbose=True,
#             handle_parsing_errors=True,
#             max_iterations=5,  # 무한 루프 방지 추가
#             tracer=tracer  # LangSmith 트레이서 연동
#         )

# 에이전트 클래스 정의 (변경 후)
class ReportAgent:
    def __init__(self):
        self.llm = llm 
        self.tools = [search_manual_context, analyze_experiment_logs, generate_report_draft]
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            당신은 AI 실험 보고서 초안 생성 에이전트입니다. 사용자의 요청을 바탕으로 다음 절차를 따르세요:
            1. `search_manual_context` 툴을 사용하여 `manual_id` 기반 **매뉴얼 관련 요약 청크**를 검색합니다. (사용자 요청에서 쿼리 추출)
            2. `analyze_experiment_logs` 툴을 사용하여 `user_id`와 `manual_id` 기반 **대화 로그 요약**을 가져옵니다.
            3. `generate_report_draft` 툴을 사용하여 매뉴얼 관련 요약 청크, 대화 로그 요약, 그리고 추가 실험 정보를 바탕으로 최종 보고서 초안을 생성합니다.
            """),
            MessagesPlaceholder(variable_name="chat_history"), 
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"), 
        ])
        
        self.agent_executor = AgentExecutor(
            agent=create_openai_tools_agent(self.llm, self.tools, self.prompt),
            tools=self.tools,
            verbose=True, 
            handle_parsing_errors=True, 
            max_iterations=10, 
        )

    # 보고서 텍스트 내용 생성 함수 (외부 호출용)
    async def generate_report_text_draft(
        self,
        manual_id: str,
        user_id: int,
        report_style: Literal["personal", "business"] = "business",
        selected_title: str = "",
        researcher: str = "",
        company: str = "",
        achieved: Literal["종료", "진행중"] = "종료",
        is_successful: bool = False,
        user_type: Literal["신입", "경력"] = "경력",
        top_k: int = 5,
        current_step: Optional[str] = None
    ) -> str:
        """
        프론트엔드 파라미터를 바탕으로 에이전트를 실행하여 보고서 초안을 생성합니다.
        """
        # 이 쿼리는 search_manual_context 툴에서 벡터 DB 검색에 사용됩니다.
        manual_context_query = f"'{selected_title}' 실험 매뉴얼 내용 요약. 현재 단계: '{current_step}'"
        if not current_step:
            manual_context_query = f"'{selected_title}' 실험 매뉴얼의 주요 내용 요약."


        full_query = (
            f"매뉴얼 ID '{manual_id}', 사용자 ID '{user_id}'의 실험 보고서 내용을 '{report_style}' 스타일로 생성해줘. "
            f"실험 제목: '{selected_title}', 실험자: '{researcher}', 소속 회사: '{company}', "
            f"실험 목적 달성 여부: '{achieved}', 실험 성공 여부: {'성공' if is_successful else '실패'}, "
            f"실험자 숙련도: '{user_type}', 현재 실험 단계: '{current_step}'"
        )

        try:
            result = await self.agent_executor.invoke(
                {
                    "input": full_query,
                    "chat_history": [], 
                    "user_id": user_id, 
                    "manual_id": manual_id, 
                    "selected_title": selected_title,
                    "researcher": researcher,
                    "company": company,
                    "achieved": achieved,
                    "is_successful": is_successful,
                    "user_type": user_type,
                    "current_step": current_step,
                    "report_style": report_style,
                    "query": manual_context_query # search_manual_context 툴의 query 인자로 전달
                }
            )
            return result.get("output", "보고서 초안 생성 실패")
        except Exception as e:
            print(f"에이전트 실행 오류: {e}")
            raise HTTPException(status_code=500, detail=f"보고서 초안 생성 중 에이전트 실행 오류: {str(e)}")
        
    # # 보고서 텍스트 내용 생성 함수 (외부 호출용) (변경 전)
    # def generate_report_text_draft(self, manual_id: str, 
    #     user_id: int,
    #     report_style: str = "business",
    #     selected_title: str = "",
    #     researcher: str = "",
    #     company: str = "",
    #     achieved: str = "",
    #     is_successful: bool = False,
    #     user_type: str = "",
    #     top_k: int = 5,
    #     current_step: str = ""
    #     ) -> str:
    #     # 변경: experiment_id 제거, generate_report_draft 툴에 필요한 새로운 파라미터들을 쿼리에 포함
    #     full_query = f"""
    #         manual_id '{manual_id}', user_id '{user_id}'의 실험 보고서 초안을 '{report_style}' 스타일로 생성해줘.
    #         실험 제목: '{selected_title}', 실험자: '{researcher}', 소속 회사: '{company}',
    #         실험 목적 달성 여부: '{achieved}', 실험 성공 여부: {'성공' if is_successful else '실패'},
    #         실험자 숙련도: '{user_type}', 현재 실험 단계: '{current_step}'
    #         """
    #     try:
    #         result = self.agent_executor.invoke({"input": full_query}) # ⬅️ 수정된 full_query 사용
    #         return result.get("output", "보고서 초안 생성 실패")
    #     except Exception as e:
    #         return f"에이전트 실행 오류: {e}"

