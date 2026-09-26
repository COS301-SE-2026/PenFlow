import {
  CircleAlert,
  ShieldAlert,
} from "lucide-react";

import type {
  AssistantAnswerState,
} from "@/lib/assistantService";

export default function AssistantAnswerStateNotice({
  state,
}: {
  state: AssistantAnswerState;
}) {
  if(state === "complete") {
    return null;
  }

  if(state === "insufficient_evidence") {
    return (
      <div role="status" className="mb-3 flex items-start gap-2 rounded-lg border-amber-400/30 
      bg-amber-400/10 px-3 py-2 text-xs leading-5 text-amber-200">
        <CircleAlert aria-hidden="true" size={15} className="mt-0.5 shrink-0" />
        <span>
          PenFlow could not find enough authorized evidence to answer this fully.
        </span>
      </div>
    );
  }

  return (
    <div role="status" className="mb-3 flex items-start gap-2 rounded-lg border-red-400/30 
    bg-red-400/10 px-3 py-2 text-xs leading-5 text-red-200">
      <ShieldAlert aria-hidden="true" size={15} className="mt-0.5 shrink-0" />
      <span>
        PenFlow could not safely validate the generated explanation. Review the linked evidence directly.
      </span>
    </div>
  );
}