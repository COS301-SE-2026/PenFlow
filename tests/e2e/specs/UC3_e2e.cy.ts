//view scan history
//test mock user 1234 

describe("User Login",()=>{
    it("User login and redirect to the dashboard",()=>{
        cy.login("1234","1234")

    });

}
);

describe("View scan history",()=>{
    beforeEach(()=>{
        cy.login("1234","1234")
    })
    it("View Scan history",()=>{
    cy.visit("/history");
    cy.contains("h1","SCAN HISTORY").should("be.visible")

    //clicking row opens the modal with view report action
    cy.get("table tbody tr").first().click();
    cy.contains("button","VIEW REPORT").should("be.visible").click();

    cy.url().should("include","/report/")
});
});
