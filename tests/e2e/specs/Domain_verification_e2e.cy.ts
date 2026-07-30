// Domain Verification: add a domain, see it listed as pending, and verify ownership.
describe("Domain Verification", () => {
  beforeEach(() => {
    cy.login("1234", "1234");
    cy.visit("/domains");
  });

 it("adds a new domain and shows it as pending", () => {
    const domain = `e2e-test-${Date.now()}.example.com`;

    cy.get('button[aria-pressed]').contains("Add Domain").click();
    cy.get("#new-domain").type(domain);
    cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

    cy.contains("td", domain).parents("tr").within(() => {
      cy.contains("Pending").should("be.visible");
      cy.contains("button", "Verify").should("be.visible");
    });
  });

  it("records a real last-checked timestamp when Verify is pressed", () => {
    const domain = `e2e-check-${Date.now()}.example.com`;

    cy.get('button[aria-pressed]').contains("Add Domain").click();
    cy.get("#new-domain").type(domain);
    cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

    // Before verifying, the row has never been checked.
    cy.contains("td", domain).parents("tr").within(() => {
      cy.contains("Never").should("be.visible");
    });
    //press verify
    cy.contains("td", domain).parents("tr").within(() => {
      cy.contains("button", "Verify").click();
    });

    cy.contains("td", domain).parents("tr").within(() => {
      //wait for 15000 15 seconds check it text never gonee
      cy.contains("Never", { timeout: 15_000 }).should("not.exist");
      cy.get("td").eq(3).invoke("text").should("not.be.empty");
    });
  });
});

