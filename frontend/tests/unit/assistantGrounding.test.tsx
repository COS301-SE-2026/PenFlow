import "@testing-library/jest-dom";
import {
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { useState } from "react";

import type {
  AssistantSource,
} from "@/lib/assistantService";
import AssistantAnswerContent from "@/shared/components/AssistantAnswerContent";
import AssistantEvidenceCard from "@/shared/components/AssistantEvidenceCard";

const FINDING_ID =
  "11111111-1111-4111-8111-111111111111";

const SOURCE: AssistantSource = {
  source_type: "finding",
  source_id: FINDING_ID,
  title: "Exposed administrative service",
  severity: "critical",
  href:
    "/phase2_scan/results/" +
    "22222222-2222-4222-8222-222222222222/findings" +
    `?finding=${FINDING_ID}`,
  metadata: {
    cve_id: "CVE-2026-12345",
    cvss_score: 9.8,
    status: "open",
    is_verified: true,
    domain: "api.example.com",
    asset_identifier: "api.example.com",
    service_host: "api.example.com",
    service_port: 443,
    service_protocol: "tcp",
    change: null,
    selection_reasons: [
      "Critical severity",
      "Verified finding",
    ],
  },
};

function EvidenceHarness() {
  const [expanded, setExpanded] = useState(false);

  return (
    <AssistantEvidenceCard
      source={SOURCE}
      number={1}
      id="assistant-evidence-test"
      expanded={expanded}
      highlighted={false}
      onToggle={() => setExpanded((current) => !current)}
    />
  );
}

describe("assistant grounding UI", () => {
  test("renders and expands structured finding evidence", () => {
    render(<EvidenceHarness />);

    expect(
      screen.getByText("CVE-2026-12345"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("CVSS 9.8"),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Critical severity"),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Expand source 1",
      }),
    );

    expect(
      screen.getByText("Why PenFlow selected this"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Critical severity"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: /view evidence/i,
      }),
    ).toHaveAttribute("href", SOURCE.href);
  });

  test("turns a finding citation into a source button", () => {
    const onFindingCitation = jest.fn();

    render(
      <AssistantAnswerContent
        content={
          `Review [Finding ID: ${FINDING_ID}] first.`
        }
        citationNumbers={
          new Map([[FINDING_ID.toLowerCase(), 1]])
        }
        onFindingCitation={onFindingCitation}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name:
          `Show source 1 for finding ${FINDING_ID}`,
      }),
    );

    expect(onFindingCitation).toHaveBeenCalledWith(
      FINDING_ID,
    );
  });
});