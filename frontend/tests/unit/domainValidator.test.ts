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
    //xxs injection prevention
     it("rejects script tag injection", () => {
      const r = validateDomain("<script>evil()</script>");
      expect(r.valid).toBe(false);
    });
       it("rejects bare word with no TLD", () => {
      const r = validateDomain("notadomain");
      expect(r.valid).toBe(false);
    });

    it("rejects empty input", () => {
      const r = validateDomain("");
      expect(r.valid).toBe(false);
    });



 });

 