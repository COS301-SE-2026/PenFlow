import { validateDomain } from "@/lib/domainValidator";

describe("validateDomain", () => {
    it("accepts a plain domain", () => {
      const r = validateDomain("example.com");
      expect(r.valid).toBe(true);
      if (r.valid) expect(r.domain).toBe("example.com");
    });

   it("strips https protocol and path", () => {
      const r = validateDomain("https://example.com/some/path");
      expect(r.valid).toBe(true);
      if (r.valid) expect(r.domain).toBe("example.com");
    });
     it("strips port number", () => {
      const r = validateDomain("example.com:8080");
      expect(r.valid).toBe(true);
      if (r.valid) expect(r.domain).toBe("example.com");
    });



 });

 