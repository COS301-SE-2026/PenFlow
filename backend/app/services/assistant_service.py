from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import RAGIndexStatus
from app.models.scan import Scan
from app.models.user import User
from app.schemas.assistant import (
    AssistantAnswerState,
    AssistantCapability,
    AssistantLink,
    AssistantQueryRequest,
    AssistantQueryResponse,
    AssistantSource,
    AssistantSourceMetadata,
    AssistantSourceType,
    SecurityQueryIntent,
)
from app.schemas.security_intelligence import (
    SecurityPortfolioFinding,
    SecurityPortfolioResult,
)
from app.services.assistant_answer_validator import (
    AssistantAnswerValidationError,
    AssistantAnswerValidator,
    AssistantFindingEvidence,
)
from app.services.assistant_context_service import (
    AssistantContextService,
)
from app.services.assistant_conversation import (
    build_prompt_question,
    build_routing_text,
)
from app.services.assistant_data_service import AssistantDataService
from app.services.assistant_model_router import AssistantModelRouter
from app.services.assistant_prompt_builder import (
    build_exact_lookup_prompts,
    build_finding_context_prompts,
    build_portfolio_analysis_prompts,
    build_product_guide_prompts,
    build_risk_prioritization_prompts,
    build_scan_comparison_prompts,
    build_user_data_prompts,
)
from app.services.assistant_validation_telemetry import record_validation_failure
from app.services.product_guide_service import ProductGuideService
from app.services.rag.document_builder import FINDING_DOCUMENT_SCHEMA_VERSION
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


@dataclass(frozen=True)
class FinalizedAssistantAnswer:
    answer: str
    answer_state: AssistantAnswerState


class AssistantService:
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

        finalized_answer = (
            AssistantService.finalize_structured_finding_answer(
                raw_output=answer,
                evidence=[
                    AssistantFindingEvidence(
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        cvss_score=finding.cvss_score,
                        cves=(
                            (finding.cve_id,)
                            if finding.cve_id
                            else ()
                        ),
                    )
                    for finding in findings
                ],
                allowed_entity_ids=[scan_id],
                allowed_links=[
                    (
                        f"/phase2_scan/results/{scan_id}/findings"
                        f"?finding={finding.finding_id}"
                    )
                    for finding in findings
                ],
            )
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
                metadata=AssistantSourceMetadata(
                    cve_id=finding.cve_id,
                    cvss_score=finding.cvss_score,
                    status=finding.status,
                    is_verified=finding.is_verified,
                    selection_reasons=finding.priority_reasons,
                ),
            )
            for finding in findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=finalized_answer.answer,
            answer_state=finalized_answer.answer_state,
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
            intent=(
                data_result.engagement_intent.value
                if data_result.engagement_intent
                else data_result.intent.value
            ),
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

        finalized_answer = (
            AssistantService.finalize_structured_finding_answer(
                raw_output=answer,
                evidence=context_result.grounding_evidence,
                allowed_entity_ids=context_result.authorized_entity_ids,
                allowed_links=context_result.allowed_links,
            )
        )

        return AssistantQueryResponse(
            question=request.question,
            answer=finalized_answer.answer,
            answer_state=finalized_answer.answer_state,
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
                answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
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

        finalized_answer = (
            AssistantService.finalize_structured_finding_answer(
                raw_output=answer,
                evidence=[
                    AssistantFindingEvidence(
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        cvss_score=finding.cvss_score,
                        cves=(
                            (finding.cve_id,)
                            if finding.cve_id
                            else ()
                        ),
                    )
                    for finding in result.findings
                ],
                allowed_entity_ids=[scan_id],
                allowed_links=[
                    (
                        f"/phase2_scan/results/{scan_id}/findings"
                        f"?finding={finding.finding_id}"
                    )
                    for finding in result.findings
                ],
            )
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
                metadata=AssistantSourceMetadata(
                    cve_id=finding.cve_id,
                    cvss_score=finding.cvss_score,
                    status=finding.status,
                    is_verified=finding.is_verified,
                    selection_reasons=[finding.match_reason],
                ),
            )
            for finding in result.findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=finalized_answer.answer,
            answer_state=finalized_answer.answer_state,
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
                answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
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

        finalized_answer = (
            AssistantService.finalize_structured_finding_answer(
                raw_output=answer,
                evidence=[
                    AssistantFindingEvidence(
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        cvss_score=finding.cvss_score,
                        cves=(
                            (finding.cve_id,)
                            if finding.cve_id
                            else ()
                        ),
                    )
                    for finding in findings
                ],
                allowed_entity_ids=[
                    result.current_scan_id,
                    *(
                        [result.baseline_scan_id]
                        if result.baseline_scan_id
                        is not None
                        else []
                    ),
                    *[
                        finding.scan_id
                        for finding in findings
                    ],
                    *[
                        finding.previous_finding_id
                        for finding in findings
                        if finding.previous_finding_id
                        is not None
                    ],
                ],
                allowed_links=[
                    (
                        f"/phase2_scan/results/"
                        f"{finding.scan_id}/findings"
                        f"?finding={finding.finding_id}"
                    )
                    for finding in findings
                ],
            )
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
                metadata=AssistantSourceMetadata(
                    cve_id=finding.cve_id,
                    cvss_score=finding.cvss_score,
                    status=finding.status,
                    is_verified=finding.is_verified,
                    asset_identifier=finding.asset_identifier,
                    service_host=finding.service_host,
                    service_port=finding.service_port,
                    service_protocol=finding.service_protocol,
                    change=finding.change,
                    selection_reasons=[
                        {
                            "new": "Detected in the current scan",
                            "persistent": "Detected in both scans",
                            "no_longer_detected": "Not detected in the current scan",
                        }[finding.change]
                    ],
                ),
            )
            for finding in findings
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=finalized_answer.answer,
            answer_state=finalized_answer.answer_state,
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

        if (
            security_intent
            == SecurityQueryIntent.PORTFOLIO_ANALYSIS
        ):
            return await (
                AssistantService.answer_portfolio_analysis_question(
                    db,
                    user_id=user.id,
                    request=request,
                )
            )

        scan_id = request.context.scan_id

        if scan_id is None:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "Open a PenFlow scan before asking a question "
                    "about findings, vulnerabilities, or remediation."
                ),
                answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
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

        if (
            current_scan.rag_index_status
            == RAGIndexStatus.INDEXING
        ):
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "PenFlow is still preparing the security evidence "
                    "for this scan. Please try this question again shortly."
                ),
                answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=security_intent,
            )

        embedding_provider = create_embedding_provider()

        index_is_current = (
            current_scan.rag_index_status == RAGIndexStatus.READY
            and current_scan.rag_document_schema_version == FINDING_DOCUMENT_SCHEMA_VERSION
            and current_scan.rag_embedding_model == embedding_provider.model
        )

        if not index_is_current:
            await RAGService.index_scan_findings(
                db,
                scan_id=scan_id,
                embedding_service=embedding_provider,
            )

        generation_provider = create_generation_provider()

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
            audience=request.audience,
        )

        if rag_answer.sources:
            finalized_answer = (
                AssistantService.finalize_structured_finding_answer(
                    raw_output=rag_answer.answer,
                    evidence=[
                        AssistantFindingEvidence(
                            finding_id=source.finding_id,
                            severity=source.severity,
                            cvss_score=source.cvss_score,
                            cves=(
                                (source.cve_id,)
                                if source.cve_id
                                else ()
                            ),
                        )
                        for source in rag_answer.sources
                    ],
                    allowed_entity_ids=[scan_id],
                    allowed_links=[
                        (
                            f"/phase2_scan/results/{scan_id}/findings"
                            f"?finding={source.finding_id}"
                        )
                        for source in rag_answer.sources
                    ],
                )
            )
            answer = finalized_answer.answer
            answer_state= finalized_answer.answer_state

        else:
            answer = rag_answer.answer
            answer_state = AssistantAnswerState.INSUFFICIENT_EVIDENCE

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
                metadata=AssistantSourceMetadata(
                    cve_id=source.cve_id,
                    cvss_score=source.cvss_score,
                    status=source.status,
                    is_verified=source.is_verified,
                    domain=source.domain,
                    asset_identifier=source.asset_identifier,
                    service_host=source.service_host,
                    service_port=source.service_port,
                    service_protocol=source.service_protocol,
                    selection_reasons=["Relevant to your question"],
                ),
            )
            for source in rag_answer.sources
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=answer,
            answer_state=answer_state,
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
        route_decision = await AssistantModelRouter.classify(request)
        capability = route_decision.capability

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


    @staticmethod
    def build_portfolio_validation_fallback(
        result: SecurityPortfolioResult,
        findings: Iterable[
            SecurityPortfolioFinding
        ],
    ) -> FinalizedAssistantAnswer:
        top_domain = result.domains[0]
        selected_findings = tuple(findings)

        top_finding_ids = {
            finding.finding_id
            for finding in top_domain.top_findings
        }

        supporting_findings = [
            finding
            for finding in selected_findings
            if finding.finding_id
            in top_finding_ids
        ]

        if not supporting_findings:
            citations = " ".join(
                (
                    "[Finding ID: "
                    f"{finding.finding_id}]"
                )
                for finding in selected_findings
            )

            fallback = (
                "I couldn't safely validate the generated "
                "explanation against the available PenFlow "
                "evidence. Review the cited findings directly."
            )

            if citations:
                fallback = (
                    f"{fallback}\n\nSources: {citations}"
                )

            return FinalizedAssistantAnswer(
                answer=fallback,
                answer_state=AssistantAnswerState.VALIDATION_FALLBACK,
            )

        if result.domain_count == 1:
            ranking = (
                f"{top_domain.domain} is the only domain "
                "with current portfolio evidence, so it "
                "ranks first"
            )
        else:
            ranking = (
                f"{top_domain.domain} ranks first among "
                f"{result.domain_count} domains"
            )

        finding_label = (
            "finding"
            if top_domain.active_finding_count == 1
            else "findings"
        )

        severity_values = (
            (
                "critical",
                top_domain.severity_counts.critical,
            ),
            (
                "high",
                top_domain.severity_counts.high,
            ),
            (
                "medium",
                top_domain.severity_counts.medium,
            ),
            (
                "low",
                top_domain.severity_counts.low,
            ),
            (
                "informational",
                top_domain.severity_counts.info,
            ),
        )

        severity_summary = ", ".join(
            f"{count} {severity}"
            for severity, count in severity_values
            if count
        )

        answer = (
            f"{ranking} under PenFlow's deterministic "
            "severity weighting, with a risk score of "
            f"{top_domain.risk_score}. It has "
            f"{top_domain.active_finding_count} open or "
            f"in-progress {finding_label}"
        )

        if severity_summary:
            answer = (
                f"{answer}: {severity_summary}."
            )

        else:
            answer = f"{answer}."

        citations = " ".join(
            (
                "[Finding ID: "
                f"{finding.finding_id}]"
            )
            for finding in supporting_findings
        )

        return FinalizedAssistantAnswer(
            answer=(
                f"{answer}\n\nSources: {citations}"
            ),
            answer_state=AssistantAnswerState.COMPLETE,
        )


    @classmethod
    def finalize_structured_finding_answer(
        cls,
        *,
        raw_output: str,
        evidence: Iterable[AssistantFindingEvidence],
        allowed_entity_ids: Iterable[UUID] = (),
        allowed_links: Iterable[str] = (),
        validation_fallback: (
            FinalizedAssistantAnswer | None
        ) = None,
    ) -> FinalizedAssistantAnswer:
        normalized_evidence = tuple(evidence)

        try:
            generated = (
                AssistantAnswerValidator.validate_structured(
                    raw_output=raw_output,
                    evidence=normalized_evidence,
                    allowed_entity_ids=allowed_entity_ids,
                    allowed_links=allowed_links,
                    require_finding_citation=True,
                )
            )

        except AssistantAnswerValidationError:
            record_validation_failure(
                "empty_generation"
                if not raw_output.strip()
                else "unsupported_reference"
            )

            if validation_fallback is not None:
                return validation_fallback

            citations = " ".join(
                f"[Finding ID: {item.finding_id}]"
                for item in normalized_evidence
            )

            fallback = (
                "I couldn't safely validate the generated explanation "
                "against the available PenFlow evidence. Review the "
                "cited findings directly."
            )

            if citations:
                fallback = (
                    f"{fallback}\n\nSources: {citations}"
                )

            return FinalizedAssistantAnswer(
                answer=fallback,
                answer_state=AssistantAnswerState.VALIDATION_FALLBACK,
            )

        return FinalizedAssistantAnswer(
            answer=generated.answer,
            answer_state=(
                AssistantAnswerState.INSUFFICIENT_EVIDENCE
                if generated.insufficient_evidence
                else AssistantAnswerState.COMPLETE
            )
        )


    @staticmethod
    async def answer_portfolio_analysis_question(
        db: AsyncSession,
        user_id: UUID,
        request: AssistantQueryRequest,
    ) -> AssistantQueryResponse:
        result = (
            await SecurityIntelligenceService.analyze_portfolio(
                db,
                user_id=user_id,
            )
        )

        if not result.portfolio_available:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    "PenFlow could not find any completed scans "
                    "for your domains, so there is no portfolio "
                    "security evidence to analyze yet."
                ),
                answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.PORTFOLIO_ANALYSIS,
                links=[
                    AssistantLink(
                        label="Start a scan",
                        href="/phase2_scan",
                    )
                ],
            )

        if result.active_finding_count == 0:
            return AssistantQueryResponse(
                question=request.question,
                answer=(
                    f"PenFlow reviewed the latest completed scan "
                    f"for {result.domain_count} "
                    f"{'domain' if result.domain_count == 1 else 'domains'} "
                    "and found no open or in-progress findings."
                ),
                capability=AssistantCapability.SECURITY_ANALYSIS,
                security_intent=SecurityQueryIntent.PORTFOLIO_ANALYSIS,
            )

        findings = (
            SecurityIntelligenceService.select_portfolio_evidence(
                result,
                limit=10,
            )
        )

        system_prompt, user_prompt = (
            build_portfolio_analysis_prompts(
                question=build_prompt_question(
                    request
                ),
                audience=request.audience,
                result=result,
                findings=findings,
            )
        )

        generation_provider = create_generation_provider()

        answer = await generation_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        finalized_answer = (
            AssistantService.finalize_structured_finding_answer(
                raw_output=answer,
                evidence=[
                    AssistantFindingEvidence(
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        cvss_score=finding.cvss_score,
                        cves=(
                            (finding.cve_id,)
                            if finding.cve_id
                            else ()
                        ),
                    )
                    for finding in findings
                ],
                allowed_entity_ids=[
                    *[
                        domain.scan_id
                        for domain in result.domains
                    ],
                    *[
                        finding.scan_id
                        for finding in findings
                    ],
                ],
                allowed_links=[
                    *[
                        (
                            f"/phase2_scan/results/"
                            f"{finding.scan_id}/findings"
                            f"?finding={finding.finding_id}"
                        )
                        for finding in findings
                    ],
                    *[
                        (
                            f"/phase2_scan/results/"
                            f"{domain.scan_id}"
                        )
                        for domain in result.domains[:5]
                    ],
                ],
                validation_fallback=(
                    AssistantService.build_portfolio_validation_fallback(
                        result=result,
                        findings=findings,
                    )
                ),
            )
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(finding.finding_id),
                title=(
                    f"{finding.domain}: "
                    f"{finding.title}"
                ),
                severity=finding.severity,
                href=(
                    f"/phase2_scan/results/"
                    f"{finding.scan_id}/findings"
                    f"?finding={finding.finding_id}"
                ),
                metadata=AssistantSourceMetadata(
                    cve_id=finding.cve_id,
                    cvss_score=finding.cvss_score,
                    status=finding.status,
                    is_verified=finding.is_verified,
                    domain=finding.domain,
                    asset_identifier=finding.asset_identifier,
                    service_port=finding.service_port,
                    selection_reasons=[
                        (
                            "Selected from the latest "
                            f"completed scan for {finding.domain}"
                        ),
                    ],
                ),
            )
            for finding in findings
        ]

        links = [
            AssistantLink(
                label=(
                    f"View {domain.domain}"
                ),
                href=(
                    f"/phase2_scan/results/"
                    f"{domain.scan_id}"
                ),
            )
            for domain in result.domains[:5]
        ]

        return AssistantQueryResponse(
            question=request.question,
            answer=finalized_answer.answer,
            answer_state=finalized_answer.answer_state,
            capability=AssistantCapability.SECURITY_ANALYSIS,
            sources=sources,
            links=links,
            security_intent=SecurityQueryIntent.PORTFOLIO_ANALYSIS,
        )