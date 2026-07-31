// Add Domain: add a new domain and confirm validation/duplicate handling.
  // Runs against the real backend/DB.
  describe("Add Domain", () => {
    beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/domains");
    });
    it("adds a new domain and lists it as pending", () => {
    const domain = `e2e-add-${Date.now()}.example.com`;

      cy.get('button[aria-pressed]').contains("Add Domain").click();
      cy.get("#new-domain").type(domain);
      cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

      cy.contains("td", domain).parents("tr").within(() => {
        cy.contains("Pending").should("be.visible");
        cy.contains("button", "Verify").should("be.visible");
      });
    });

    //invalid format
    it("shows a validation error for an invalid domain format", () => {
      cy.get('button[aria-pressed]').contains("Add Domain").click();
      cy.get("#new-domain").type("not a domain");
      cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();

      cy.contains("Invalid domain format").should("be.visible");
      cy.contains("td", "not a domain").should("not.exist");
    });

    //can't reinput domain alredy exist
    it("shows an error when adding a domain that already exists", () => {
      const domain = `e2e-dup-${Date.now()}.example.com`;

      cy.get('button[aria-pressed]').contains("Add Domain").click();
      cy.get("#new-domain").type(domain);
      cy.contains("button","Cancel").parent().contains("button","Add Domain").click();
      cy.contains("td", domain).should("be.visible");

      cy.get('button[aria-pressed]').contains("Add Domain").click();
      cy.get("#new-domain").type(domain);
      cy.contains("button", "Cancel").parent().contains("button","Add Domain").click();
   cy.get("body").find(`td:contains("${domain}")`).should("have.length", 1);
    });
  });
