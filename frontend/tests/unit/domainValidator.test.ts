import { validateDomain } from "@/lib/domainValidator";


//reduce code repetition by using it.each split 7 identical test to 2 
//test 1 validate domain test (4case) strip protocol,path,port and accepts subdomains
describe("validateDomain", () => {
      it.each([
          ["accepts a plain domain", "example.com", "example.com"],
          ["strips https protocol and path", "https://example.com/some/path", "example.com"],
          ["strips port number", "example.com:8080", "example.com"],
          ["accepts subdomain", "sub.example.co.za", "sub.example.co.za"],
      ])("%s", (_desc, input, expected) => {
          const r = validateDomain(input);
          expect(r.valid).toBe(true);
          if (r.valid) expect(r.domain).toBe(expected);
      });
      //bad input rejects , no tld ,xxs injection , empty string
      it.each([
          ["rejects script tag injection", "<script>evil()</script>"],
          ["rejects bare word with no TLD", "notadomain"],
          ["rejects empty input", ""],
      ])("%s", (_desc, input) => {
          const r = validateDomain(input);
          expect(r.valid).toBe(false);
      });
  });

 