//generate or view phase2 report
//download phase2 report (active report)
describe("Generate/View Phase 2 Report", () => {
  beforeEach(() => {
    cy.login("1234", "1234");
    cy.getCookie("logged_in").should("have.property", "value", "1");
  })

  it("downloads the PDF report from an active vulnerability scan", () => {
    cy.visit("/phase2_scan")
    //open latest result and find active vulnerability scan tag and click download pdf
    cy.contains("h2", "Latest Results")
      .closest("section")
      .contains('[data-slot="card"]', "Active Vulnerability Scan")
      .contains("a", "View Results")
      .click();
    cy.url().should("match", /\/phase2_scan\/results\/[^/]+$/);

    cy.contains("a", "Download Report")
      .should("have.attr", "href")
      .and("include", "/pdf");

    cy.contains("a", "Download Report").should("have.attr", "target", "_blank");
  });

    //checks if it a pdf
  it("serves a valid PDF at the report URL for an active vulnerability scan", () => {
    cy.visit("/phase2_scan");
    cy.contains("h2", "Latest Results")
      .closest("section")
      .contains('[data-slot="card"]', "Active Vulnerability Scan")
      .contains("a", "View Results")
      .click();

    cy.contains("a", "Download Report").click()
      .invoke("attr", "href")
      .then((href) => {
        cy.request(href as string).then((response) => {
          expect(response.status).to.eq(200);
          expect(response.headers["content-type"]).to.include("pdf");
        });
      });
  });
});
