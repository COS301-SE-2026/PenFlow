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


 });

 