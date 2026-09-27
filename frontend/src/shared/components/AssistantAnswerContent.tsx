import { Fragment } from "react";

const INLINE_TOKEN_PATTERN =
  /(\*\*[^*]+\*\*|\[Finding ID:\s*[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\])/gi;

const FINDING_CITATION_PATTERN =
  /^\[Finding ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\]$/i;
  
interface AssistantAnswerContentProps {
  content: string;
  citationNumbers?: ReadonlyMap<string, number>;
  onFindingCitation?: (findingId: string) => void;
}

function renderInlineText(
  value: string,
  citationNumbers?: ReadonlyMap<string, number>,
  onFindingCitation?: (findingId: string) => void,
) {
  return value.split(INLINE_TOKEN_PATTERN).map((part, index) => {
    const citation = part.match(FINDING_CITATION_PATTERN);

    if(citation) {
      const findingId = citation[1];
      const citationNumber = citationNumbers?.get(
        findingId.toLowerCase(),
      );

      if(citationNumber !== undefined && onFindingCitation) {
        return (
          <button key={`${findingId}-${index}`} type="button" aria-label={`Show source ${citationNumber} for finding ${findingId}`} 
          onClick={() => onFindingCitation(findingId)} className="mx-0.5 inline-flex rounded-md border border-brand-cyan/30 bg-brand-cyan/10 
          px-1.5 py-0.5 align-baseline text-[10px] font-semibold text-brand-cyan transition hover:bg-brand-cyan/20">
            [{citationNumber}]
          </button>
        );
      }
    }

    const bold = part.startsWith("**") && part.endsWith("**");
    if(bold) {
      return (
        <strong key={`${part}-${index}`} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }

    return (
      <Fragment key={`${part}-${index}`}>
        {part}
      </Fragment>
    );
  });
}

export default function AssistantAnswerContent({
  content,
  citationNumbers,
  onFindingCitation,
}: AssistantAnswerContentProps) {
  return (
    <div className="grid min-w-0 gap-2 break-words text-sm leading-6 text-foreground">
      {content.split("\n").map((line, index) => {
        const normalized = line.trim();

        if(!normalized) {
          return (<div key={`space-${index}`} className="h-1" />);
        }

        if(normalized.startsWith("- ")) {
          return (
            <div key={`bullet-${index}`} className="flex items-start gap-2">
              <span aria-hidden="true" className="text-brand-cyan">
                •
              </span>

              <p className="m-0">
                {renderInlineText(normalized.slice(2), citationNumbers, onFindingCitation)}
              </p>
            </div>
          );
        }

        const numbered = normalized.match(/^(\d+\.)\s+(.*)$/);

        if(numbered) {
          return (
            <div key={`number-${index}`} className="flex items-start gap-2">
              <span className="font-semibold text-brand-cyan">
                {numbered[1]}
              </span>
              <p className="m-0">
                {renderInlineText(numbered[2], citationNumbers, onFindingCitation)}
              </p>
            </div>
          );
        }

        return (
          <p key={`line-${index}`} className="m-0">
            {renderInlineText(normalized, citationNumbers, onFindingCitation)}
          </p>
        );
      })}
    </div>
  );
}