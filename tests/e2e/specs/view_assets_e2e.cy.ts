describe("View Discovered Assets", () => {
    beforeEach(() => {
    cy.login("1234", "1234");
    cy.visit("/phase2_scan");
    cy.contains("a","View Results").first().click();
    cy.contains("a","Assets").click();
})

    it("shows discovered assets in the table", () => {
      cy.url().should("include","/assets");
      cy.contains("h2","Assets").should("be.visible");
      cy.get('input[aria-label="Search assets"]').should("be.visible");
    });

    it("opens the detail panel for an asset", () => {
      cy.get("section[data-scan-id] button").first().click();

      cy.contains("h3","Overview").should("be.visible");
      cy.contains("a", "View findings in the Findings tab").should("be.visible");
    });
  })