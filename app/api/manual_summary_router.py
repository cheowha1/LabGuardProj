from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document

from app.db.database import get_db
from app.dependencies import get_current_user
from app.services.manual_summary import (
    summarize_experiment_chunks,
    summarize_experiments_by_manual_id,
    save_summaries_to_json,
    parse_summary_to_structured_dict
)
from app.schemas.manual_summary import (
    ExperimentSummaryResponse,
    ManualSummaryResponse,
    StructuredSummaryResponse,
    ExportSummaryResponse,
    ExperimentCountResponse
)
import os

router = APIRouter(prefix="/manual-summary", tags=["manual-summary"])

# Chroma DB 설정
CHROMA_DIR = "./chroma_db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@router.get("/experiment/{experiment_id}", response_model=ExperimentSummaryResponse)
async def summarize_single_experiment(
    experiment_id: str,
    current_user=Depends(get_current_user)
):
    """
    특정 experiment_id의 청크들을 요약합니다.
    """
    try:
        # Chroma DB에서 해당 experiment_id의 청크들 조회
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        # 메타데이터 필터링으로 특정 experiment_id 청크만 조회
        collection = vectorstore._collection
        results = collection.get(
            where={"experiment_id": experiment_id}
        )
        
        if not results['documents']:
            raise HTTPException(status_code=404, detail=f"Experiment ID '{experiment_id}'에 해당하는 청크를 찾을 수 없습니다.")
        
        # Document 객체 생성
        chunks = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            chunks.append(Document(page_content=doc, metadata=meta))
        
        # 요약 생성
        summary_result = summarize_experiment_chunks(chunks)
        
        return ExperimentSummaryResponse(**summary_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 생성 중 오류 발생: {str(e)}")


@router.get("/manual/{manual_id}", response_model=ManualSummaryResponse)
async def summarize_manual_experiments(
    manual_id: str,
    current_user=Depends(get_current_user)
):
    """
    특정 manual_id의 모든 실험들을 요약합니다.
    """
    try:
        # Chroma DB에서 해당 manual_id의 모든 청크들 조회
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        collection = vectorstore._collection
        results = collection.get(
            where={"manual_id": manual_id}
        )
        
        if not results['documents']:
            raise HTTPException(status_code=404, detail=f"Manual ID '{manual_id}'에 해당하는 청크를 찾을 수 없습니다.")
        
        # Document 객체 생성
        chunks = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            chunks.append(Document(page_content=doc, metadata=meta))
        
        # 매뉴얼 전체 실험 요약 생성
        summaries = summarize_experiments_by_manual_id(manual_id, chunks)
        
        # 응답 형식에 맞게 변환
        experiment_summaries = [
            ExperimentSummaryResponse(**summary) for summary in summaries
        ]
        
        return ManualSummaryResponse(
            manual_id=manual_id,
            experiment_summaries=experiment_summaries,
            total_experiments=len(experiment_summaries)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매뉴얼 요약 생성 중 오류 발생: {str(e)}")


@router.get("/experiment/{experiment_id}/structured", response_model=StructuredSummaryResponse)
async def get_structured_experiment_summary(
    experiment_id: str,
    current_user=Depends(get_current_user)
):
    """
    특정 experiment_id의 요약을 6개 항목으로 구조화하여 반환합니다.
    """
    try:
        # 먼저 일반 요약 생성
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        collection = vectorstore._collection
        results = collection.get(
            where={"experiment_id": experiment_id}
        )
        
        if not results['documents']:
            raise HTTPException(status_code=404, detail=f"Experiment ID '{experiment_id}'에 해당하는 청크를 찾을 수 없습니다.")
        
        # Document 객체 생성
        chunks = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            chunks.append(Document(page_content=doc, metadata=meta))
        
        # 요약 생성
        summary_result = summarize_experiment_chunks(chunks)
        
        # 구조화된 요약으로 파싱
        structured_summary = parse_summary_to_structured_dict(summary_result["summary"])
        
        return StructuredSummaryResponse(
            experiment_id=experiment_id,
            structured_summary=structured_summary,
            chunk_count=summary_result["chunk_count"],
            created_at=summary_result["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"구조화된 요약 생성 중 오류 발생: {str(e)}")


@router.get("/manual/{manual_id}/experiment-count", response_model=ExperimentCountResponse)
async def get_experiment_count(
    manual_id: str,
    current_user=Depends(get_current_user)
):
    """
    특정 매뉴얼의 실험 개수를 반환합니다. (프론트엔드 진행률 표시용)
    """
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        collection = vectorstore._collection
        results = collection.get(
            where={"manual_id": manual_id}
        )
        
        if not results['documents']:
            raise HTTPException(status_code=404, detail=f"Manual ID '{manual_id}'에 해당하는 데이터를 찾을 수 없습니다.")
        
        # 고유한 experiment_title 추출
        experiment_titles = set()
        for meta in results['metadatas']:
            if 'experiment_title' in meta:
                experiment_titles.add(meta['experiment_title'])
        
        experiment_count = len(experiment_titles)
        
        return ExperimentCountResponse(
            manual_id=manual_id,
            experiment_count=experiment_count,
            message=f"매뉴얼 '{manual_id}'에 총 {experiment_count}개의 실험이 있습니다."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실험 개수 조회 중 오류 발생: {str(e)}")


@router.get("/experiments", response_model=List[str])
async def list_available_experiments(
    manual_id: Optional[str] = Query(None, description="특정 매뉴얼의 실험만 조회"),
    current_user=Depends(get_current_user)
):
    """
    사용 가능한 experiment_id 목록을 반환합니다.
    """
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        collection = vectorstore._collection
        
        # 필터 조건 설정
        where_filter = {}
        if manual_id:
            where_filter["manual_id"] = manual_id
        
        results = collection.get(where=where_filter if where_filter else None)
        
        # 고유한 experiment_id 추출
        experiment_ids = set()
        for meta in results['metadatas']:
            if 'experiment_id' in meta:
                experiment_ids.add(meta['experiment_id'])
        
        return sorted(list(experiment_ids))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실험 목록 조회 중 오류 발생: {str(e)}")


@router.post("/export/{manual_id}", response_model=ExportSummaryResponse)
async def export_manual_summaries_to_json(
    manual_id: str,
    output_filename: Optional[str] = Query(None, description="출력 파일명 (기본값: manual_id_summaries.json)"),
    current_user=Depends(get_current_user)
):
    """
    특정 매뉴얼의 모든 실험 요약을 JSON 파일로 내보냅니다.
    """
    try:
        # 매뉴얼 요약 생성
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        
        collection = vectorstore._collection
        results = collection.get(
            where={"manual_id": manual_id}
        )
        
        if not results['documents']:
            raise HTTPException(status_code=404, detail=f"Manual ID '{manual_id}'에 해당하는 청크를 찾을 수 없습니다.")
        
        # Document 객체 생성
        chunks = []
        for doc, meta in zip(results['documents'], results['metadatas']):
            chunks.append(Document(page_content=doc, metadata=meta))
        
        # 요약 생성
        summaries = summarize_experiments_by_manual_id(manual_id, chunks)
        
        # 파일명 설정
        if not output_filename:
            output_filename = f"{manual_id}_summaries.json"
        
        # JSON 파일로 저장
        output_path = f"./exports/{output_filename}"
        os.makedirs("./exports", exist_ok=True)
        
        success = save_summaries_to_json(summaries, output_path)
        
        if success:
            return ExportSummaryResponse(
                message="요약 결과가 성공적으로 내보내졌습니다.",
                output_path=output_path,
                total_experiments=len(summaries)
            )
        else:
            raise HTTPException(status_code=500, detail="JSON 파일 저장에 실패했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"내보내기 중 오류 발생: {str(e)}") 