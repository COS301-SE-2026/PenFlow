//filter/Search Findings by search text and serverity
//assume at least 1 findings
describe('filter/Search Findings', () => {
    beforeEach(() => {
    cy.login("1234", "1234");
    cy.visit("/phase2_scan");
    cy.contains("a", "View Results").first().click();
    cy.contains("a", "Findings").click();
    });
    it("filters findings by severity", () => {
      cy.get('select[aria-label="Severity filter"], select').contains("option", "Critical")
        .parent()
        .select("Critical");

      cy.get("section[data-scan-id]").then(($section) => {
        const noResults = $section.find(':contains("No findings match your filters.")').length > 0;
        if (noResults) {
          cy.wrap($section).contains("No findings match your filters.").should("be.visible");
          return;
        }
        // Every visible severity badge should read critical, case-insensitively.
        cy.wrap($section)
          .find("h3")
          .parent()
          .siblings()
          .find("span")
          .filter((_, el) => /critical|high|medium|low/i.test(el.textContent ?? ""))
          .each(($badge) => {
            expect($badge.text().toLowerCase()).to.eq("critical");
          });
      });
      
    });
    //search
     it("finds a finding by searching its title", () => {
    cy.get("section[data-scan-id] h3").first().invoke("text").then((title) => {
      const term = title.trim().split(" ")[0];
      cy.get('input[aria-label="Search findings"]').type(term);

      cy.contains("h3", title).should("be.visible");
    });
  });
  
})