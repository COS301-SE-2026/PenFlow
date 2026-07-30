 // View Scan Findings: navigate to a completed scan's Findings tab and see results.
describe("View Scan Findings", () => {
  beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/phase2_scan");
  });

    it("opens a completed scan's findings", () => {
      cy.contains("a", "View Results").first().click();

      cy.url().should("match", /\/phase2_scan\/results\/[^/]+$/);
      cy.contains("a", "Findings").click();
      cy.url().should("include", "/findings");

      cy.contains("h2", "Findings").should("be.visible");
      cy.get('input[aria-label="Search findings"]').should("be.visible");
    });

    it("opens the detail panel for a finding", () => {
      cy.contains("a", "View Results").first().click();
      cy.contains("a", "Findings").click();

      cy.get("section[data-scan-id] button").first().click();
      cy.contains("h3", "Description").should("be.visible");
      cy.contains("h3", "Recommendations").should("be.visible");
    });
  });