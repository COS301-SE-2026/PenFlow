describe("checking health mock", () => {
  it("loads the app", () => {
    cy.visit("http://localhost:3000");
    cy.contains("PenFlow");
  });
});