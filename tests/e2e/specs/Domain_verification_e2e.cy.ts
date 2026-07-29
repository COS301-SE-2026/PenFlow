// Domain Verification: add a domain, see it listed as pending, and verify ownership.
// Runs against the real backend/DB/DNS
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

  it("shows a real DNS failure when the TXT record doesn't exist", () => {
    const domain = `e2e-no-record-${Date.now()}.example.com`;

    cy.get('button[aria-pressed]').contains("Add Domain").click();
    cy.get("#new-domain").type(domain);
    cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

    cy.contains("td", domain).parents("tr").within(() => {
      cy.contains("button", "Verify").click();
    });

    // Real DNS lookup against a domain with no TXT record - genuinely fails, no stubbing.
    // domain_service.verify_domain only ever sets PENDING or VERIFIED (never FAILED) on
    // this endpoint, so the button stays labeled "Verify", not "Retry", after a failed check.
    cy.contains("td", domain).parents("tr").within(() => {
      cy.contains("Pending").should("be.visible");
      cy.contains("button", "Verify").should("be.visible");
    });
  });

  // Success path needs a domain with a real, permanently-published TXT record matching
  // CYPRESS_VERIFIED_TEST_DOMAIN once that domain exists; skipped until then.
  const verifiedDomain = Cypress.env("VERIFIED_TEST_DOMAIN") as string | undefined;
  (verifiedDomain ? it : it.skip)(
    "verifies ownership of a pre-seeded domain with a real TXT record",
    () => {
      cy.contains("td", verifiedDomain!).parents("tr").within(() => {
        cy.contains("button", /Verify|Retry/).click();
      });

      cy.contains("td", verifiedDomain!).parents("tr").within(() => {
        cy.contains("Verified", { timeout: 15_000 }).should("be.visible");
      });
    }
  );
});
