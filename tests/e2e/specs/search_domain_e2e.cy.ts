// Search Domains: filter the domain table by search text.
describe("Search Domains", () => {
const domain = `e2e-search-${Date.now()}.example.com`;
    beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/domains");
    });

    it("adds a domain then finds it via search", () => {
    cy.get('button[aria-pressed]').contains("Add Domain").click();
    cy.get("#new-domain").type(domain);
    cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

    cy.get('input[placeholder="Search domains..."]').type(domain);

      // Wait out the 350ms debounce before asserting.
    cy.contains("td", domain, { timeout: 5000 }).should("be.visible");
    });

    it("shows no results for a search term that matches nothing", () => {
      cy.get('input[placeholder="Search domains..."]').type("no-such-domain-xyz");

      cy.contains("No domains found.", { timeout: 5000 }).should("be.visible");
    });
  });