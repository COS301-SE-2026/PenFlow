import os 
import logging 
import requests 
from typing import Any 

from app.queue.celery_app import celery_app 
from app.services.typosquat_service import TyposquatService 
from app.services.brand_signals_service import BrandSignalService 
from app.services.brand_scoring_service import BrandScoringService 

logger = logging.getLogger(__name__)

BACKEND_API_URL = os.getenv(
    "BACKEND_API_URL", 
    "http://penflow-backend.penflow.local:3001/api/v1"
)

@celery_app.task(
    name="brand.monitor_domain",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_brand_monitoring_task(self: Any, brand_monitoring_id: str, domain: str) -> dict[str, Any]:
    logger.info(f"[BrandMonitor] Starting brand impersonation scan for: {domain}")

    mutation = TyposquatService.generate_candidates(domain)
    logger.info(f"[BrandMonitor] Generated {len(mutation)} permutation candidates for {domain}")

    discovered_candidates = [] 

    for mut in mutations:
        candidate_domain = mut["candidate_domain"]
        signals = BrandSignalService.gather_signals(candidate_domain)

        if signals.get("is_resolvable"):
            score, risk_level, evidence = BrandScoringService.evaluate(mut, signals)
            discovered_candidates.append({
                "candidate_domain": candidate_domain, 
                "normalized_domain": mut["normalized_domain"],
                "risk_score": score, 
                "risk_level": risk_level, 
                "evidence": evidence,
            })

    logger.info(
        f"[BrandMonitor] Found {len(discovered_candidates)} active/resolving candidates for {domain}"
    )

    payload = {
        "brand_monitoring_id": brand_monitoring_id,
        "candidates": discovered_candidates,
    }

    try:
        response = requests.post(
            f"{BACKEND_API_URL}/brand-intelligence/internal/ingest", 
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.error(f"[BrandMonitor] Failed to ingest results into backend: {exc}")
        raise exc 

    return {
        "status": "completed", 
        "brand_monitoring_id": brand_monitoring_id, 
        "candidates_found": len(discovered_candidates),
    }