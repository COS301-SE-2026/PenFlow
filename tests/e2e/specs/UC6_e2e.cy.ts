//Download PDF Report

describe("User log in and Download pdf report",()=>{
    beforeEach(()=>{
        cy.login("1234","1234")
        cy.getCookie("logged_in").should("have.property","value","1")
    })
    it("Download Pdf report",()=>{
        cy.get('nav a[href="/history"]').click(); 
        cy.url().should("include","/history");
        cy.get("table tbody tr").first().click();
        cy.contains("button","VIEW REPORT").should("be.visible").click();
        cy.url().should("include","/report/")
        
        //verify link wired up for natively download
        cy.contains("a","DOWNLOAD FULL REPORT")
        .should("have.attr","href")
        .and("include","/pdf");

        cy.contains("a","DOWNLOAD FULL REPORT")
        .should("have.attr","download");

        //click download
        cy.contains("a","DOWNLOAD FULL REPORT").click();

    });
});