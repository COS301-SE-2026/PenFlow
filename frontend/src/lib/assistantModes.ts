import type {
  AssistantAudience,
} from "@/lib/assistantService";

export type AssistantAnswerMode = AssistantAudience;

export interface AssistantAnswerModeOption {
  value: AssistantAnswerMode;
  label: string;
  description: string;
  audience: AssistantAudience;
}

export const ASSISTANT_ANSWER_MODES:
  readonly AssistantAnswerModeOption[] = [
    {
      value: "executive",
      label: "Executive",
      description: "Business risk and decisions",
      audience: "executive",
    },
    {
      value: "it_manager",
      label: "IT Manager",
      description: "Ownership and operational priorities",
      audience: "it_manager",
    },
    {
      value: "security",
      label: "Security",
      description: "Evidence and technical risk",
      audience: "security",
    },
    {
      value: "developer",
      label: "Developer",
      description: "Remediation and verification",
      audience: "developer",
    },
  ];

export function assistantModeOption(
  mode: AssistantAnswerMode,
): AssistantAnswerModeOption {
  const option = ASSISTANT_ANSWER_MODES.find(
    (candidate) => candidate.value === mode,
  );

  if(!option) {
    throw new Error(`Unsupported assistant answer mode: ${mode}`);
  }

  return option;
}

export function assistantAudienceForMode(
  mode: AssistantAnswerMode,
): AssistantAudience {
  return assistantModeOption(mode).audience;
}

export function assistantAnswerModeLabel(
  mode: AssistantAnswerMode,
): string {
  return assistantModeOption(mode).label;
}