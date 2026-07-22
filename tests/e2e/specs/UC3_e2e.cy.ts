//view scan history
//test mock user 1234 


describe("View scan history",()=>{
    beforeEach(()=>{
        cy.login("1234","1234")
        cy.getCookie("logged_in").should("have.property","value","1")
    })
    it("View Scan history",()=>{
    cy.contains("a","HISTORY").click();   
      cy.url().should("include","/history");
    cy.contains("h1","SCAN HISTORY").should("be.visible")

   
});
});
