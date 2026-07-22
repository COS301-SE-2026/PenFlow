//Download PDF Report

describe("User log in and Download pdf report",()=>{
    beforeEach(()=>{
        cy.login("1234","1234")
        cy.getCookie("logged_in").should("have.property","value","1")
    })
    it("Download Pdf report",()=>{
        cy.contains("a","HISTORY").click();   
        cy.url().should("include","/history");
        cy.get("table tbody tr").first().click();
        cy.contains("button","VIEW REPORT").should("be.visible").click();
        cy.url().should("include","/report/")
        
        //set up the intercept capture http rquest match with **/scans/pdf
        cy.intercept("GET","**/scans/*/pdf").as("pdfDownload")   

        //checks if it have the downlaod full report options
        cy.contains("a","DOWNLOAD FULL REPORT")
        .should("have.attr","href")
        .and("include","/pdf")
        //click the link
        cy.contains("a","DOWNLOAD FULL REPORT").click();

        //verify the intercetpt request was succesfull 
        cy.wait("@pdfDownload").its("response.statusCode")
        .should("eq",200); //http status success
        cy.get("@pdfDownload").its("response.headers.content-type")
        .should("include","application/pdf");
});
});