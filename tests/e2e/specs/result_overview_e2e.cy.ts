//result overview: scan result summary page risk score, category metrics, top findin
//have to already have a completed scan
describe("Result Overview", () => {
  beforeEach(() => {
    cy.login("1234", "1234");
    cy.visit("/phase2_scan");
    cy.contains("a", "View Results").first().click();
  })
  //check if risk score and summary cards are there
  it("shows the risk score and per-category summary cards", () => {
    cy.url().should("match", /\/phase2_scan\/results\/[^/]+$/);

    cy.get("[data-scan-id]").within(() => {
      cy.contains("Risk Score").should("be.visible");
      cy.contains(/\/100/ ).should("be.visible" )

    cy.contains("Findings" ).should("be.visible")
      cy.contains("Assets").should("be.visible")
      cy.contains("Services").should("be.visible")
      cy.contains("Technologies").should("be.visible")  
})
  })

    //shows findings and risk overtime
  it("shows top critical findings and top assets by findings with links out", () => {
    cy.get("[data-scan-id]").within(() => {
      cy.contains("h2", "Risk Over Time").should("be.visible");

      cy.contains("h2", "Top Critical Findings").should("be.visible");
      cy.contains("a", "View all findings")
        .should("have.attr", "href")
        .and("include", "/findings")
        cy.contains("h2", "Top Assets by Findings").should("be.visible");
      cy.contains("a", "View all assets")
        .should("have.attr", "href")
        .and("include", "/assets")
    })
  })
})


