import hashlib
import os
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.rag_repository import RAGRepository
from app.schemas.assistant import AssistantAudience
from app.schemas.rag import (
    RAGAnswerSource,
    RAGAskResponse,
    RAGSearchResult,
)
from app.services.rag.document_builder import (
    FINDING_DOCUMENT_SCHEMA_VERSION,
    build_finding_text,
)
from app.services.rag.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.services.rag.generation_provider import GenerationProvider
from app.services.rag.prompt_builder import build_grounded_answer_prompts


class RAGService:
    RRF_K = 60
    MAX_CANDIDATES = 30

    @staticmethod
    async def index_scan_findings(
        db: AsyncSession,
        scan_id: UUID,
        embedding_service: EmbeddingProvider,
    ) -> dict[str, int]:
        scan = await RAGRepository.get_scan_for_indexing(
            db,
            scan_id,
        )

        if scan is None:
            raise ValueError(
                f"Scan {scan_id} was not found."
            )

        force_reindex = (
            scan.rag_document_schema_version
            != FINDING_DOCUMENT_SCHEMA_VERSION
        )

        await RAGRepository.mark_scan_indexing(
            db,
            scan_id,
        )

        try:
            findings = (
                await RAGRepository.list_enriched_findings_for_scan(
                    db,
                    scan_id,
                )
            )

            existing_chunks = await RAGRepository.list_chunks_for_scan(
                db,
                scan_id,
            )


            existing_by_finding_id = {
                chunk.finding_id: chunk
                for chunk in existing_chunks
            }

            pending: list[tuple[Any, str, str]] = []
            unchanged = 0

            for finding in findings:
                content = build_finding_text(finding)
                content_hash = hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()

                existing = existing_by_finding_id.get(finding.id)

                if (
                    not force_reindex
                    and existing is not None
                    and existing.content_hash == content_hash
                    and existing.embedding_model == embedding_service.model
                ):
                    unchanged += 1
                    continue

                pending.append((finding, content, content_hash))

            embeddings = (
                await embedding_service.embed_batch(
                    [
                        content
                        for _, content, _ in pending
                    ]
                )
                if pending
                else []
            )

            rows: list[dict[str, Any]] = []

            for (
                finding,
                content,
                content_hash,
            ), embedding in zip(
                pending,
                embeddings,
                strict=True,
            ):
                rows.append(
                    {
                        "finding_id": finding.id,
                        "scan_id": scan_id,
                        "content": content,
                        "content_hash": content_hash,
                        "embedding_model": embedding_service.model,
                        "embedding": embedding,
                    }
                )

            await RAGRepository.synchronize_chunks(
                db,
                scan_id=scan_id,
                rows=rows,
                current_finding_ids=[
                    finding.id
                    for finding in findings
                ],
            )

            await RAGRepository.mark_scan_index_ready(
                db,
                scan_id,
                document_schema_version=FINDING_DOCUMENT_SCHEMA_VERSION,
                embedding_model=embedding_service.model,
            )

            return {
                "total_findings": len(findings),
                "indexed": len(rows),
                "unchanged": unchanged,
            }

        except Exception as exc:
            await db.rollback()

            failure_reason = (
                "Embedding generation failed."
                if isinstance(exc, EmbeddingProviderError)
                else "Finding indexing failed."
            )

            await RAGRepository.mark_scan_index_failed(
                db,
                scan_id,
                failure_reason=failure_reason,
            )

            raise


    @staticmethod
    def fuse_ranked_results(
        *,
        vector_rows: list[
            tuple[Any, Any, float]
        ],
        text_rows: list[
            tuple[Any, Any, float]
        ],
        limit: int,
    ) -> list[tuple[Any, Any, float]]:
        candidates: dict[
            UUID,
            tuple[Any, Any],
        ] = {}

        scores: dict[UUID, float] = {}
        distances: dict[UUID, float] = {}

        for rank, (
            chunk,
            finding,
            distance,
        ) in enumerate(
            vector_rows,
            start=1,
        ):
            finding_id = finding.id

            candidates[finding_id] = (
                chunk,
                finding,
            )
            distances[finding_id] = distance
            scores[finding_id] = (
                scores.get(finding_id, 0.0)
                + 1.0 / (RAGService.RRF_K + rank)
            )

        for rank, (
            chunk,
            finding,
            _text_rank,
        ) in enumerate(
            text_rows,
            start=1,
        ):
            finding_id = finding.id

            candidates.setdefault(
                finding_id,
                (
                    chunk,
                    finding,
                ),
            )

            scores[finding_id] = (
                scores.get(finding_id, 0.0)
                + 1.0 / (RAGService.RRF_K + rank)
            )

        ordered_ids = sorted(
            scores,
            key=lambda finding_id: (
                -scores[finding_id],
                distances.get(
                    finding_id,
                    float("inf"),
                ),
                str(finding_id),
            ),
        )

        return [
            (
                candidates[finding_id][0],
                candidates[finding_id][1],
                distances.get(
                    finding_id,
                    1.0,
                ),
            )
            for finding_id in ordered_ids[:limit]
        ]


    @staticmethod
    async def search_scan(
        db: AsyncSession,
        scan_id: UUID,
        question: str,
        limit: int,
        embedding_service: EmbeddingProvider,
        retrieval_mode_override: str | None = None,
    ) -> list[RAGSearchResult]:
        query_embedding = await embedding_service.embed(
            question
        )

        configured_retrieval_mode = (
            retrieval_mode_override
            or os.getenv("RAG_RETRIEVAL_MODE")
            or "vector"
        )

        retrieval_mode = (
            configured_retrieval_mode.strip().casefold()
        )

        if retrieval_mode not in {
            "vector",
            "hybrid",
        }:
            retrieval_mode = "vector"

        candidate_limit = min(
            max(limit * 3, limit),
            RAGService.MAX_CANDIDATES,
        )

        vector_rows = await RAGRepository.search_scan(
            db,
            scan_id=scan_id,
            embedding_model=embedding_service.model,
            query_embedding=query_embedding,
            limit=(
                candidate_limit
                if retrieval_mode == "hybrid"
                else limit
            ),
        )

        max_distance_value = os.getenv(
            "RAG_MAX_VECTOR_DISTANCE",
            "0.65",
        )

        try:
            max_vector_distance = float(max_distance_value)

        except ValueError:
            max_vector_distance = 0.65

        max_vector_distance = min(
            max(max_vector_distance, 0.0),
            2.0,
        )

        vector_rows = [
            row
            for row in vector_rows
            if row[2] <= max_vector_distance
        ]

        if retrieval_mode == "hybrid":
            text_rows = await RAGRepository.search_scan_text(
                db,
                scan_id=scan_id,
                embedding_model=embedding_service.model,
                question=question,
                limit=candidate_limit,
            )

            rows = RAGService.fuse_ranked_results(
                vector_rows=vector_rows,
                text_rows=text_rows,
                limit=limit,
            )

        else:
            rows = vector_rows

        results: list[RAGSearchResult] = []

        for chunk, finding, distance in rows:
            severity = (
                finding.severity.value
                if hasattr(finding.severity, "value")
                else str(finding.severity)
            )
            status = (
                finding.status.value
                if hasattr(finding.status, "value")
                else str(finding.status)
            )
            scan = finding.scan
            asset = finding.asset
            service = finding.service

            results.append(
                RAGSearchResult(
                    finding_id=finding.id,
                    title=finding.title,
                    severity=severity,
                    distance=distance,
                    content=chunk.content,
                    cvss_score=(
                        float(finding.cvss_score)
                        if finding.cvss_score is not None
                        else None
                    ),
                    cve_id=finding.cve_id,
                    status=status,
                    is_verified=finding.is_verified,
                    domain=(
                        str(scan.domain)
                        if scan is not None
                        else None
                    ),
                    asset_identifier=(
                        asset.identifier
                        if asset is not None
                        else None
                    ),
                    service_host=(
                        service.host
                        if service is not None
                        else None
                    ),
                    service_port=(
                        service.port
                        if service is not None
                        else None
                    ),
                    service_protocol=(
                        service.protocol
                        if service is not None
                        else None
                    ),
                )
            )

        return results


    @staticmethod
    async def answer_question(
        db: AsyncSession,
        scan_id: UUID,
        question: str,
        limit: int,
        embedding_service: EmbeddingProvider,
        generation_provider: GenerationProvider,
        retrieval_question: str | None = None,
        audience: AssistantAudience = AssistantAudience.SECURITY,
    ) -> RAGAskResponse:
        results = await RAGService.search_scan(
            db,
            scan_id=scan_id,
            question=retrieval_question or question,
            limit=limit,
            embedding_service=embedding_service,
        )

        sources = [
            RAGAnswerSource(
                finding_id=result.finding_id,
                title=result.title,
                severity=result.severity,
                evidence_content=result.content,
                cvss_score=result.cvss_score,
                cve_id=result.cve_id,
                status=result.status,
                is_verified=result.is_verified,
                domain=result.domain,
                asset_identifier=result.asset_identifier,
                service_host=result.service_host,
                service_port=result.service_port,
                service_protocol=result.service_protocol,
            )
            for result in results
        ]

        if not results:
            return RAGAskResponse(
                question=question,
                answer=(
                    "No indexed PenFlow evidence was available "
                    "for this scan, so the question cannot be "
                    "answered from scan evidence."
                ),
                sources=[],
            )

        system_prompt, user_prompt = (
            build_grounded_answer_prompts(
                question=question,
                results=results,
                audience=audience,
            )
        )

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return RAGAskResponse(
            question=question,
            answer=answer,
            sources=sources,
        )