//validate domain lib
export type DomainValidationResult =
    | { valid: true; domain: string }
    | { valid: false; error: string };

  function sanitizeDomain(raw: string): string {
    let v = raw.trim().toLowerCase();
    v = v.replace(/^https?:\/\//i, "");   // strip protocol
    v = v.split("/")[0];                   // strip path
    v = v.split(":")[0];                   // strip port
    v = v.replace(/^\.{1,253}/, "").replace(/\.{1,253}$/, "");     // strip leading/trailing dots .Alternation |  with + can cause backtracking  + add range check for domain of 253
    return v;
  }
  //regex 
  //checks The very first character of the segment must be a letter or a number.
  //allow optional subdomains
  //If there is more than one character, the middle section can contain letters, numbers, and hyphens. It can be between 0 and 61 characters long
  //domain max is  63 characters maximum  +1 start and end char
  //TLD must be at least 2 characters long
  const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$/;  

  export function validateDomain(raw: string): DomainValidationResult {
    const domain = sanitizeDomain(raw);

    if (!domain) return { valid: false, error: "Please enter a domain" };
    if (/[<>"';&]/.test(domain)) return { valid: false, error: "Domain contains invalid characters" };
    if (domain.length > 253) return { valid: false, error: "Domain name is too long" };
    if (!DOMAIN_REGEX.test(domain)) return { valid: false, error: "Invalid domain format (e.g. example.com)" };

    return { valid: true, domain };
  }