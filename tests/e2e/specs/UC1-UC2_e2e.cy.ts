//user initate the the scan by entering a domain ,and view a breif hisotry
describe("Initiate scan and view report",() => {
    it("submits a domain, waits for the scan, and views the report",()=> {
        cy.visit("/");
        //frontend component domain input
        cy.get('input[aria-label="Domain input"]')
        .type("jeandre.com")
        .should("have.value","jeandre.com");
            //scan regex find the scans te=xt
        cy.contains("button",/^SCAN$/)
        .should("not.be.disabled")
        .click();

        //scan wait in the background for 150 000ms around 2.5 min
        cy.contains("button",/^VIEW REPORT$/,{timeout:150_000})
        //press the report when it ready
        .should("have.attr","data-ready","true").click();

});
});