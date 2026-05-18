//validate domain lib
export type DomainValidationResult =
    | { valid: true; domain: string }
    | { valid: false; error: string };

  function sanitizeDomain(raw: string): string {
    let v = raw.trim().toLowerCase();
    v = v.replace(/^https?:\/\//i, "");   // strip protocol
    v = v.split("/")[0];                   // strip path
    v = v.split(":")[0];                   // strip port
    v = v.replace(/^\.+|\.+$/g, "");      // strip leading/trailing dots
    return v;
  }

  const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$/;

  export function validateDomain(raw: string): DomainValidationResult {
    const domain = sanitizeDomain(raw);

    if (!domain) return { valid: false, error: "Please enter a domain" };
    if (/[<>"';&]/.test(domain)) return { valid: false, error: "Domain contains invalid characters" };
    if (domain.length > 253) return { valid: false, error: "Domain name is too long" };
    if (!DOMAIN_REGEX.test(domain)) return { valid: false, error: "Invalid domain format (e.g. example.com)" };

    return { valid: true, domain };
  }