import re
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan
from app.models.user import User
from app.schemas.assistant import (
    AssistantCapability,
    AssistantLink,
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantSource,
    AssistantSourceType,
    SecurityQueryIntent,
)
from app.services.assistant_context_service import (
    AssistantContextService,
)
from app.services.assistant_conversation import (
    build_prompt_question,
    build_routing_text,
)
from app.services.assistant_data_service import AssistantDataService
from app.services.assistant_prompt_builder import (
    build_exact_lookup_prompts,
    build_finding_context_prompts,
    build_product_guide_prompts,
    build_risk_prioritization_prompts,
    build_scan_comparison_prompts,
    build_user_data_prompts,
)
from app.services.assistant_router import AssistantRouter
from app.services.product_guide_service import ProductGuideService
from app.services.rag.generation_provider_factory import (
    create_generation_provider,
)
from app.services.rag.provider_factory import (
    create_embedding_provider,
)
from app.services.rag.rag_service import RAGService
from app.services.scan_service import ScanService
from app.services.security_intelligence_service import (
    SecurityIntelligenceService,
)
from app.services.security_query_router import (
    SecurityQueryRouter,
)

FINDING_CITATION_PATTERN = re.compile(
    r"\[Finding ID:\s*([^\]\r\n]+)\]",
    re.IGNORECASE,
)


class AssistantService:
    @staticmethod
    def ensure_finding_citations(
        answer: str,
        finding_ids: Sequence[UUID],
    ) -> str:
        allowed_ids = {
            str(finding_id).casefold(): str(finding_id)
            for finding_id in finding_ids
        }

        def sanitize_citations(
                match: re.Match[str],
        ) -> str:
            candidate = match.group(1).strip().casefold()
            canonical = allowed_ids.get(candidate)

            if canonical is None:
                return ""

            return f"[Finding ID: {canonical}]"

        sanitized_answer = FINDING_CITATION_PATTERN.sub(
            sanitize_citations,
            answer,
        )

        sanitized_answer = re.sub(
            r"[ \t]+([,.;:])",
            r"\1",
            sanitized_answer,
        ).strip()

        normalized_answer = sanitized_answer.casefold()

        missing_citations = [
            f"[Finding ID: {finding_id}]"
            for finding_id in finding_ids
            if (
                f"[Finding ID: {finding_id}]".casefold()
                not in normalized_answer
            )
        ]

        if not missing_citations:
            return sanitized_answer

        label = (
            "Source"
            if len(missing_citations) == 1
            else "Sources"
        )

        return (
            f"{sanitized_answer.rstrip()}\n\n"
            f"{label}: {' '.join(missing_citations)}"
        )


    @staticmethod
    async def answer_risk_prioritization_question(
        db: AsyncSession,
        scan_id: UUID,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        findings = await SecurityIntelligenceService.prioritize_scan_findings(
            db,
            scan_id=scan_id,
            limit=5,
        )

        if not findings:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "PenFlow found no open or in-progress "
                    "findings to prioritize for this scan."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.RISK_PRIORITIZATION,
            )

        prompt_question = build_prompt_question(
            request
        )

        system_prompt, user_prompt = build_risk_prioritization_prompts(
            question=prompt_question,
            audience=request.audience,
            findings=findings,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        answer = AssistantService.ensure_finding_citations(
            answer=answer,
            finding_ids=[
                finding.finding_id
                for finding in findings
            ],
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(finding.finding_id),
                title=finding.title,
                severity=finding.severity,
                href=(
                    f"/phase2_scan/results/{scan_id}/findings"
                    f"?finding={finding.finding_id}"
                ),
            )
            for finding in findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.SECURITY_ANALYSIS,
            sources=sources,
            security_intent=SecurityQueryIntent.RISK_PRIORITIZATION,
        )


    @staticmethod
    async def answer_product_question(
        request: AssistantQueryRequest,
        capability: AssistantCapability,
    ) -> AssistantQueryResponse:
        routing_question = build_routing_text(request)
        prompt_question = build_prompt_question(request)

        articles = ProductGuideService.search(
            routing_question,
            limit=3,
        )

        system_prompt, user_prompt = build_product_guide_prompts(
            question=prompt_question,
            audience=request.audience,
            articles=articles,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        source_type = (
            AssistantSourceType.NAVIGATION
            if capability == AssistantCapability.NAVIGATION
            else AssistantSourceType.PRODUCT_GUIDE
        )

        sources = [
            AssistantSource(
                source_type=source_type,
                source_id=article.slug,
                title=article.title,
                href=(
                    article.links[0].href
                    if article.links
                    else None
                ),
            )
            for article in articles
        ]

        links_by_href = {
            link.href: AssistantLink(
                label=link.label,
                href=link.href,
            )
            for article in articles
            for link in article.links
        }

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=capability,
            sources=sources,
            links=list(links_by_href.values()),
        )


    @staticmethod
    async def answer_user_data_question(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        prompt_question = build_prompt_question(request)

        data_result = await AssistantDataService.collect(
            db,
            user=user,
            request=request,
        )

        system_prompt, user_prompt = build_user_data_prompts(
            question=prompt_question,
            audience=request.audience,
            intent=data_result.intent.value,
            evidence=data_result.evidence,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.USER_DATA,
            sources=data_result.sources,
            links=data_result.links,
        )


    @staticmethod
    async def answer_finding_question(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        prompt_question = build_prompt_question(request)

        context_result = await AssistantContextService.get_finding_context(
            db,
            user=user,
            request=request,
        )

        system_prompt, user_prompt = build_finding_context_prompts(
            question=prompt_question,
            audience=request.audience,
            evidence=context_result.evidence,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.FINDING_EXPLANATION,
            sources=context_result.sources,
            links=context_result.links,
        )


    @staticmethod
    async def answer_exact_lookup_question(
        db: AsyncSession,
        scan_id: UUID,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        result = await SecurityIntelligenceService.lookup_exact_scan_findings(
            db,
            scan_id=scan_id,
            request=request,
            limit=5,
        )

        if result.identifier_type is None:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "Provide a complete CVE identifier or finding UUID "
                    "so PenFlow can perform an exact lookup within this scan."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.EXACT_LOOKUP,
            )

        if not result.findings:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "PenFlow found no finding matching "
                    f"{result.identifier_value} within this "
                    "authorized scan."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.EXACT_LOOKUP,
            )

        prompt_question = build_prompt_question(request)

        system_prompt, user_prompt = build_exact_lookup_prompts(
            question=prompt_question,
            audience=request.audience,
            result=result,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        answer = AssistantService.ensure_finding_citations(
            answer=answer,
            finding_ids=[
                finding.finding_id
                for finding in result.findings
            ],
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(finding.finding_id),
                title=finding.title,
                severity=finding.severity,
                href=(
                    f"/phase2_scan/results/{scan_id}/findings"
                    f"?finding={finding.finding_id}"
                ),
            )
            for finding in result.findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.SECURITY_ANALYSIS,
            sources=sources,
            security_intent=SecurityQueryIntent.EXACT_LOOKUP,
        )


    @staticmethod
    async def answer_scan_comparison_question(
        db: AsyncSession,
        current_scan: Scan,
        user_id: UUID,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        result = await SecurityIntelligenceService.compare_with_previous_scan(
            db,
            current_scan=current_scan,
            user_id=user_id,
        )

        if not result.comparison_available:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "PenFlow could not find an earlier completed "
                    "scan of the same domain and scan type to use "
                    "as a comparison baseline."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.SCAN_COMPARISON,
            )

        findings = [
            *result.new_findings[:5],
            *result.persistent_findings[:5],
            *result.no_longer_detected[:5],
        ]

        if not findings:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "Neither scan contains findings, so PenFlow "
                    "found no security-finding changes to compare."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.SCAN_COMPARISON,
            )

        prompt_question = build_prompt_question(request)

        system_prompt, user_prompt = build_scan_comparison_prompts(
            question=prompt_question,
            audience=request.audience,
            result=result,
            findings=findings,
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        answer = AssistantService.ensure_finding_citations(
            answer=answer,
            finding_ids=[
                finding.finding_id
                for finding in findings
            ],
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(finding.finding_id),
                title=finding.title,
                severity=finding.severity,
                href=(
                    f"/phase2_scan/results/"
                    f"{finding.scan_id}/findings"
                    f"?finding={finding.finding_id}"
                ),
            )
            for finding in findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.SECURITY_ANALYSIS,
            sources=sources,
            security_intent=SecurityQueryIntent.SCAN_COMPARISON,
        )


    @staticmethod
    async def answer_security_question(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        security_intent = SecurityQueryRouter.classify(
            request
        )

        scan_id = request.context.scan_id

        if scan_id is None:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "Open a PenFlow scan before asking a question "
                    "about findings, vulnerabilities, or remediation."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                links=[
                    AssistantLink(
                        label="Open scans",
                        href="/phase2_scan",
                    )
                ],
                security_intent=security_intent,
            )

        current_scan = await ScanService.require_scan_access(
            db,
            scan_id=scan_id,
            user_id=user.id,
        )

        if (
            security_intent == SecurityQueryIntent.RISK_PRIORITIZATION
        ):
            return await AssistantService.answer_risk_prioritization_question(
                db,
                scan_id=scan_id,
                request=request,
            )

        if (
            security_intent == SecurityQueryIntent.EXACT_LOOKUP
        ):
            return await AssistantService.answer_exact_lookup_question(
                db,
                scan_id=scan_id,
                request=request,
            )

        if (
            security_intent == SecurityQueryIntent.SCAN_COMPARISON
        ):
            return await AssistantService.answer_scan_comparison_question(
                db,
                current_scan=current_scan,
                user_id=user.id,
                request=request,
            )

        embedding_provider = create_embedding_provider()
        generation_provider = create_generation_provider()

        await RAGService.index_scan_findings(
            db,
            scan_id=scan_id,
            embedding_service=embedding_provider,
        )

        prompt_question = build_prompt_question(request)
        retrieval_question = build_routing_text(request)

        rag_answer = await RAGService.answer_question(
            db,
            scan_id=scan_id,
            question=prompt_question,
            retrieval_question=retrieval_question,
            limit=5,
            embedding_service=embedding_provider,
            generation_provider=generation_provider,
        )

        answer = AssistantService.ensure_finding_citations(
            answer=rag_answer.answer,
            finding_ids=[
                source.finding_id
                for source in rag_answer.sources
            ],
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(source.finding_id),
                title=source.title,
                severity=source.severity,
                href=(
                    f"/phase2_scan/results/{scan_id}/findings"
                    f"?finding={source.finding_id}"
                ),
            )
            for source in rag_answer.sources
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=AssistantCapability.SECURITY_ANALYSIS,
            sources=sources,
            security_intent=security_intent,
        )


    @staticmethod
    def pending_capability_response(
        request: AssistantQueryRequest,
        capability: AssistantCapability,
    ) -> AssistantQueryResponse:
        if capability == AssistantCapability.PRODUCT_HELP:
            answer = (
                "The PenFlow product guide is not connected yet. "
                "This capability will be added in the next subset."
            )
            links: list[AssistantLink] = []

        elif capability == AssistantCapability.NAVIGATION:
            answer = (
                "PenFlow navigation assistance is not connected yet. "
                "This capability will be added with the product guide."
            )
            links = []

        elif capability == AssistantCapability.USER_DATA:
            answer = (
                "Live account information is not connected yet. "
                "The upcoming read-only data tools will answer "
                "questions about schedules, scans, domains, and reports."
            )
            links = [
                AssistantLink(
                    label="View scheduled scans",
                    href="/scheduled-scans",
                )
            ]

        elif capability == AssistantCapability.FINDING_EXPLANATION:
            answer = (
                "Contextual finding explanations are not connected yet. "
                "The selected finding will be supported by the context "
                "assistant subset."
            )
            links = []

        else:
            answer = (
                "I can help with PenFlow product guidance, navigation, "
                "your authorized PenFlow data, and security analysis. "
                "I do not have enough context to answer that question yet."
            )
            links = []

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            capability=capability,
            links=links,
        )
    

    @staticmethod
    async def answer(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        capability = AssistantRouter.classify(request)

        if capability in {
            AssistantCapability.PRODUCT_HELP,
            AssistantCapability.NAVIGATION,
        }:
            return await AssistantService.answer_product_question(
                request=request,
                capability=capability,
            )   

        if capability == AssistantCapability.USER_DATA:
            return await AssistantService.answer_user_data_question(
                db,
                user=user,
                request=request,
            )

        if capability == AssistantCapability.FINDING_EXPLANATION:
            return await AssistantService.answer_finding_question(
                db,
                user=user,
                request=request,
            )

        if capability == AssistantCapability.SECURITY_ANALYSIS:
            return await AssistantService.answer_security_question(
                db,
                user=user,
                request=request,
            )

        return AssistantService.pending_capability_response(
            request=request,
            capability=capability,
        )