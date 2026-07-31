//view service
//have to already have a active scan
describe("View Discovered Services", () => {
    beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/phase2_scan");
      cy.contains("a", "View Results").first().click();
      cy.contains("a", "Services").click();
    })
    //discovered service
    it("shows discovered services in the table",() => {
      cy.url().should("include", "/services");
      cy.contains("h2", "Services").should("be.visible");
      cy.get('input[aria-label="Search services"]').should("be.visible");
    })

    //detail panel
    it("opens the detail panel for a service", () => {
      cy.get("section[data-scan-id] button").first().click();

      cy.contains("h3", "Overview").should("be.visible");
      cy.contains("dt", "Protocol").should("be.visible");
      cy.contains("dt", "Port").should("be.visible");
    });

    it("closes the service detail panel", () => {
      cy.get("section[data-scan-id] button").first().click();
      cy.contains("h3", "Overview").should("be.visible");

      cy.get('button[aria-label="Close service details"]').click();
      cy.contains("h3", "Overview").should("not.exist");
    });
  });