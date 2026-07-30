//view domains
describe("View Domain", () => {
    const domain = `e2e-view-${Date.now()}.example.com`;
    beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/domains");
});

//open detail panel
it("adds a domain then opens its detail panel from the table", () => {
    cy.get('button[aria-pressed]').contains("Add Domain").click();
    cy.get("#new-domain").type(domain);
    cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

    cy.contains("td", domain).click();

    cy.contains("h2", domain).should("be.visible");
    cy.contains("Pending verification").should("be.visible");
    cy.contains("Added on").should("be.visible");
    cy.contains("Verify ownership").should("be.visible");
    });
//close the detail panel
it("closes the detail panel", () => {
      cy.contains("td", domain).click();
      cy.contains("h2", domain).should("be.visible");

      cy.get('button[aria-label="Close domain details"]').click();
      cy.contains("h2", domain).should("not.exist");
    });
  });
