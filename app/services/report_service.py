from app.db.database import SessionLocal
from app.crud import chat_log_crud, experiment
from app.services.agent_chat_service import experiment_logger
from app.schemas.report import AnalysisMethod
from datetime import datetime
from typing import List, Dict, Tuple
import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType, Tool
from dotenv import load_dotenv, find_dotenv

# 환경 변수 로드
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")



def generate_experiment_report_with_react(experiment_id: int) -> Tuple[str, AnalysisMethod, Dict]:
    """
    ReAct agent를 사용한 고도화된 실험 리포트 생성.
    실험 로그와 채팅 기록을 분석하여 개선점까지 포함한 리포트를 생성합니다.
    
    Args:
        experiment_id (int): 실험 ID
        
    Returns:
        Tuple[str, AnalysisMethod, Dict]: (리포트 텍스트, 분석 방법, 메타데이터)
    """
    db = SessionLocal()
    try:
        # 1. 실험 기본 정보 조회
        exp = experiment.get_experiment_by_id(db, experiment_id)
        if not exp:
            metadata = {
                "experiment_name": None,
                "user_id": None,
                "has_experiment_logs": False,
                "has_chat_logs": False,
                "generated_at": datetime.now()
            }
            report_text = f"# 🚫 실험을 찾을 수 없습니다\n\nExperiment ID: {experiment_id}\n\n해당 실험이 존재하지 않습니다."
            return report_text, AnalysisMethod.LLM_DIRECT, metadata
        
        # 2. 모든 관련 데이터 수집
        experiment_name = getattr(exp, 'name', f'실험 {experiment_id}')
        user_id_str = str(exp.user_id) if exp.user_id else "unknown"
        
        # JSON 실험 로그 수집
        experiment_logs = experiment_logger.get_user_experiments(user_id_str, limit=100)
        
        # DB 채팅 로그 수집  
        chat_logs = chat_log_crud.load_chat_logs(db, experiment_id)
        
        # 메타데이터 수집
        metadata = {
            "experiment_name": experiment_name,
            "user_id": exp.user_id,
            "has_experiment_logs": bool(experiment_logs),
            "has_chat_logs": bool(chat_logs),
            "total_experiment_logs": len(experiment_logs) if experiment_logs else 0,
            "total_chat_logs": len(chat_logs) if chat_logs else 0,
            "generated_at": datetime.now()
        }
        
        # 3. 데이터를 하나의 context로 통합
        context = f"""
실험명: {experiment_name}
실험 ID: {experiment_id}
사용자 ID: {exp.user_id}
생성일: {exp.created_at if hasattr(exp, 'created_at') else 'N/A'}
설명: {getattr(exp, 'description', 'N/A')}

=== 실험 진행 로그 (JSON) ===
"""
        
        if experiment_logs:
            for log in experiment_logs:
                log_type = log.get('type', 'unknown')
                timestamp = log.get('timestamp', 'N/A')[:16]
                content = log.get('content', 'N/A')
                context += f"[{log_type}] {timestamp}: {content}\n"
        else:
            context += "실험 로그가 없습니다.\n"
        
        context += "\n=== Q&A 채팅 로그 (DB) ===\n"
        
        if chat_logs:
            for i, chat in enumerate(chat_logs, 1):
                timestamp = chat.created_at.strftime('%Y-%m-%d %H:%M:%S') if chat.created_at else 'N/A'
                context += f"[{chat.sender}] {timestamp}: {chat.message}\n"
        else:
            context += "채팅 로그가 없습니다.\n"
        
        # 4. ReAct Agent 설정
        try:
            # LLM 초기화
            llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                openai_api_key=OPENAI_API_KEY,
                temperature=0.3
            )
            print(f"✅ LLM 초기화 성공")
            
            # Tool 정의
            def lookup_func(query: str) -> str:
                """실험 데이터 조회 도구 (임시 구현)"""
                return f"데이터 조회: {query}"
            
            tools = [
                Tool(
                    name="experiment_data_lookup",
                    func=lookup_func,
                    description="실험 데이터와 채팅 기록을 조회하고 분석합니다. 추가 정보가 필요할 때 사용하세요."
                )
            ]
            
            # ReAct Agent 초기화 (여러 AgentType 시도)
            agent_types = [
                AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                AgentType.REACT_DOCSTORE,
                AgentType.CONVERSATIONAL_REACT_DESCRIPTION
            ]
            
            react_agent = None
            for agent_type in agent_types:
                try:
                    react_agent = initialize_agent(
                        tools=tools,
                        llm=llm,
                        agent=agent_type,
                        verbose=True,
                        max_iterations=3,
                        early_stopping_method="generate",
                        handle_parsing_errors=True  # 파싱 에러 자동 처리
                    )
                    print(f"✅ ReAct Agent 초기화 성공 (AgentType: {agent_type})")
                    break
                except Exception as type_error:
                    print(f"⚠️ AgentType {agent_type} 실패: {type_error}")
                    continue
            
            if react_agent is None:
                raise Exception("모든 AgentType 초기화 실패")
            
        except Exception as agent_error:
            print(f"❌ ReAct Agent 초기화 실패: {agent_error}")
            # Fallback: 간단한 LLM 호출
            print("🔄 Fallback: 직접 LLM 호출로 전환합니다.")
            
            try:
                # 직접 LLM 호출 (Tool 시뮬레이션 포함)
                tool_simulation = f"Tool 호출 시뮬레이션: experiment_data_lookup('실험 데이터 분석')\n결과: 데이터 조회: 실험 데이터 분석\n\n"
                
                fallback_prompt = f"""
너는 화학공학 실험 분석 도우미야.
실험 로그와 채팅 기록을 분석해서
1) 진행 상황 요약
2) 문제점 및 원인 분석
3) 개선 방안
4) 결론
을 반드시 포함해 마크다운 리포트를 작성해.

{tool_simulation}

# 🔬 실험 분석 리포트: 실험 {experiment_id}

## 📊 실험 개요
[기본 정보 요약]

## 🧪 진행 상황 분석  
[실험 로그 기반 진행상황 요약]

## ⚠️ 문제점 및 이슈 분석
[발견된 문제점들과 원인 분석]

## 💡 개선 방안 제안
[구체적인 개선사항 제시]

## 📋 결론 및 권고사항
[최종 결론과 다음 단계 제안]

=== 분석할 실험 데이터 ===
{context}

위 데이터를 바탕으로 종합 분석 리포트를 작성해주세요.
"""
                
                result = llm.invoke(fallback_prompt)
                fallback_result = result.content if hasattr(result, 'content') else str(result)
                
                final_report = f"""
{fallback_result}

---
**생성 정보:**
- 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 분석 방법: LLM Direct Call (Agent Fallback)
- 실험 ID: {experiment_id}

_ReAct Agent 초기화 실패로 직접 LLM 호출을 사용했습니다._
"""
                return final_report, AnalysisMethod.AGENT_FALLBACK, metadata
                
            except Exception as fallback_error:
                error_report = f"# ❌ Agent 초기화 오류\n\nExperiment ID: {experiment_id}\n\nAgent 오류: {str(agent_error)}\nFallback 오류: {str(fallback_error)}"
                return error_report, AnalysisMethod.LLM_DIRECT, metadata
        
        # 5. ReAct Agent 실행
        try:
            print(f"\n🤖 ReAct Agent가 실험 {experiment_id} 분석을 시작합니다...")
            
            # OpenAI API 키 확인
            if not OPENAI_API_KEY:
                print("❌ OpenAI API 키가 설정되지 않았습니다.")
                error_report = f"# ❌ API 키 오류\n\nExperiment ID: {experiment_id}\n\nOpenAI API 키가 설정되지 않았습니다."
                return error_report, AnalysisMethod.LLM_DIRECT, metadata
            
            # Agent 프롬프트 (더 명확한 ReAct 형식 요구)
            agent_prompt = f"""
당신은 화학공학 실험 분석 전문가입니다.
주어진 실험 데이터를 분석하여 종합 리포트를 작성해야 합니다.

실험 분석을 위해 experiment_data_lookup 도구를 사용해서 추가 정보를 확인하세요.

다음 형식을 반드시 따라주세요:
Action: experiment_data_lookup
Action Input: 실험 데이터 종합 분석

분석 결과는 다음 형식의 마크다운 리포트로 작성해주세요:

# 🔬 실험 분석 리포트: 실험 {experiment_id}

## 📊 실험 개요
## 🧪 진행 상황 분석  
## ⚠️ 문제점 및 이슈 분석
## 💡 개선 방안 제안
## 📋 결론 및 권고사항

=== 분석할 실험 데이터 ===
{context}
"""
            
            # ReAct Agent 실행
            agent_result = react_agent.run(agent_prompt)
            
            # 6. 리포트 후처리
            final_report = f"""
{agent_result}

---
**생성 정보:**
- 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 분석 방법: ReAct Agent (GPT-4o-mini)
- 실험 ID: {experiment_id}

_이 리포트는 ReAct Agent가 실험 데이터를 분석하여 자동 생성했습니다._
"""
            return final_report, AnalysisMethod.REACT_AGENT, metadata
            
        except Exception as agent_error:
            print(f"❌ ReAct Agent 실행 오류: {agent_error}")
            print(f"❌ 오류 타입: {type(agent_error).__name__}")
            
            # 파싱 에러일 경우 Fallback으로 처리
            if "parsing" in str(agent_error).lower() or "output" in str(agent_error).lower():
                print("🔄 파싱 에러 감지, Fallback LLM 호출로 전환합니다.")
                
                try:
                    # 직접 LLM 호출 (Tool 시뮬레이션 포함)
                    tool_simulation = f"Tool 호출 시뮬레이션: experiment_data_lookup('실험 데이터 종합 분석')\n결과: 데이터 조회 완료\n\n"
                    
                    fallback_prompt = f"""
{tool_simulation}

너는 화학공학 실험 분석 도우미야.
실험 로그와 채팅 기록을 분석해서 마크다운 리포트를 작성해.

# 🔬 실험 분석 리포트: 실험 {experiment_id}

## 📊 실험 개요
[기본 정보 요약]

## 🧪 진행 상황 분석  
[실험 로그 기반 진행상황 요약]

## ⚠️ 문제점 및 이슈 분석
[발견된 문제점들과 원인 분석]

## 💡 개선 방안 제안
[구체적인 개선사항 제시]

## 📋 결론 및 권고사항
[최종 결론과 다음 단계 제안]

=== 분석할 실험 데이터 ===
{context}

위 데이터를 바탕으로 종합 분석 리포트를 작성해주세요.
"""
                    
                    result = llm.invoke(fallback_prompt)
                    fallback_result = result.content if hasattr(result, 'content') else str(result)
                    
                    final_report = f"""
{fallback_result}

---
**생성 정보:**
- 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 분석 방법: LLM Direct Call (Agent Parsing Error Fallback)
- 실험 ID: {experiment_id}

_ReAct Agent 파싱 에러로 인해 직접 LLM 호출을 사용했습니다._
"""
                    return final_report, AnalysisMethod.PARSING_ERROR_FALLBACK, metadata
                    
                except Exception as fallback_error:
                    print(f"❌ Fallback LLM 호출도 실패: {fallback_error}")
                    error_report = f"""
# ❌ 분석 실패

**Experiment ID:** {experiment_id}  
**Agent 오류:** {str(agent_error)}
**Fallback 오류:** {str(fallback_error)}
**발생 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

모든 분석 방법이 실패했습니다. 관리자에게 문의하세요.
"""
                    return error_report, AnalysisMethod.LLM_DIRECT, metadata
            
            # 다른 에러의 경우
            import traceback
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            
            error_report = f"""
# ❌ ReAct Agent 분석 실패

**Experiment ID:** {experiment_id}  
**오류 내용:** {str(agent_error)}  
**발생 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ReAct Agent 분석 중 오류가 발생했습니다. 관리자에게 문의하세요.
"""
            return error_report, AnalysisMethod.LLM_DIRECT, metadata
        
    except Exception as e:
        metadata = {
            "experiment_name": None,
            "user_id": None,
            "has_experiment_logs": False,
            "has_chat_logs": False,
            "generated_at": datetime.now()
        }
        error_report = f"# ❌ ReAct 리포트 생성 오류\n\nExperiment ID: {experiment_id}\n\n오류 내용: {str(e)}"
        return error_report, AnalysisMethod.LLM_DIRECT, metadata
    
    finally:
        db.close()

 