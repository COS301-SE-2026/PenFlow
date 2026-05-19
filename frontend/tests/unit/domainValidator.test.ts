import { validateDomain } from "@/lib/domainValidator";

describe("validateDomain", () => {
    it("accepts a plain domain", () => {
      const r = validateDomain("example.com");
      expect(r.valid).toBe(true);
      if (r.valid) expect(r.domain).toBe("example.com");
    });

 });
