//send scan report via email
//don't  send to hit an email ,input  and example and the system will display sent after send.
describe("send scan report to inputted email",()=>{
    beforeEach(()=>{
        cy.login("1234","1234");
        cy.getCookie("logged_in").should("have.property","value","1");
    });
    it("send scan report to inputted email",()=>{
        cy.contains("a","HISTORY").click();  
        cy.url().should("include","/history");
        cy.get("table tbody tr").first().click();
        cy.contains("button","VIEW REPORT").should("be.visible").click();
        cy.url().should("include","/report/")
    
        //intercept email endpoint 
        cy.intercept("POST","**/scans/*/email-report").as("emailReport");
        
        cy.get('input[type="email"]').type("test@example.com");
        cy.contains("button","SEND REPORT").click();

        cy.wait("@emailReport").its("response.statusCode").should("eq",200);
        cy.contains("button","SENT ✓").should("be.visible");
        cy.contains("button","SENT ✓").should("be.disabled");
    });
});
