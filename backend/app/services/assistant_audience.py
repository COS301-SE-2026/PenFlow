from app.schemas.assistant import AssistantAudience

AUDIENCE_GUIDANCE: dict[AssistantAudience, str] = {
    AssistantAudience.EXECUTIVE: (
        "Keep the answer concise and focused on business risk, "
        "priority, likely impact, and the decision required. Avoid "
        "implementation detail unless it is necessary."
    ),
    AssistantAudience.IT_MANAGER: (
        "Focus on operational impact, ownership, remediation "
        "sequencing, dependencies, and practical next steps."
    ),
    AssistantAudience.DEVELOPER: (
        "Focus on concrete remediation steps, implementation "
        "considerations, and how to verify the fix. Do not claim "
        "that remediation has been completed."
    ),
    AssistantAudience.SECURITY: (
        "Provide technical security detail, including the recorded "
        "severity, affected assets or services, evidence, and risk "
        "rationale where available."
    ),
}


def build_audience_context(
        audience: AssistantAudience
) -> str:
    return (
        f"Audience mode: {audience.value}\n"
        f"Answer style: {AUDIENCE_GUIDANCE[audience]}"
    )