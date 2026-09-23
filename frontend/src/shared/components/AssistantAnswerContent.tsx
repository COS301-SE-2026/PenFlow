import { Fragment } from "react";

function renderInlineText(value: string) {
  return value.split(/(\*\*[^*]+\*\*)/g)
  .map((part, index) => {
    const bold = part.startsWith("**") &&
      part.endsWith("**");

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
} : {
  content: string;
}) {
  return (
    <div className="grid gap-2 text-sm leading-6 text-foreground">
      {content.split("\n").map((line, index) => {
        const normalized = line.trim();

        if(!normalized) {
          return <div key={`space-${index}`} className="h-1" />
        }

        if(normalized.startsWith("- ")) {
          return (
            <div key={`bullet-${index}`} className="flex items-start gap-2">
              <span aria-hidden="true" className="text-brand-cyan">
                •
              </span>

              <p className="m-0">
                {renderInlineText(normalized.slice(2))}
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
                {renderInlineText(numbered[2])}
              </p>
            </div>
          );
        }

        return (
          <p key={`line-${index}`} className="m-0">
            {renderInlineText(normalized)}
          </p>
        );
      })}
    </div>
  );
}