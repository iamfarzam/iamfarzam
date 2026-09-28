// Match credential formats without including any real credential values.
export const credentialRules = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
  /\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b/,
  /\bAIza[A-Za-z0-9_-]{35}\b/,
  /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/,
];

export function isExampleEmail(email) {
  const domain = email.slice(email.lastIndexOf("@") + 1).toLowerCase();
  return ["example.com", "example.org", "example.net", "localhost", "test", "invalid"].includes(domain)
    || domain.endsWith(".test") || domain.endsWith(".invalid");
}

export function isPlaceholderValue(value) {
  return /^(?:replace[-_]|change[-_]|fictional[-_]|isolated[-_]|test[-_]|example|REDACTED_|<|\$\{|process\.env|config\()/i.test(value);
}

export function containsPrivateContent(content, personalPatterns = []) {
  const normalized = content.toLowerCase();
  if (personalPatterns.some((value) => value && normalized.includes(value.toLowerCase()))) {
    return true;
  }
  if (credentialRules.some((rule) => rule.test(content))) {
    return true;
  }
  const emails = content.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) || [];
  if (emails.some((email) => !isExampleEmail(email))) return true;
  const assignments = content.matchAll(/\b(?:DJANGO_SECRET_KEY|SECRET_KEY|EMAIL_HOST_PASSWORD|AWS_SECRET_ACCESS_KEY|S3_SECRET_KEY|POSTGRES_PASSWORD|DATABASE_PASSWORD|API_KEY|AUTH_TOKEN|ACCESS_TOKEN)\s*[:=]\s*(?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s"'#]+))/g);
  for (const match of assignments) {
    const value = match[1] || match[2] || match[3];
    if (value.length >= 16 && !isPlaceholderValue(value) && !/[()+]/.test(value)) return true;
  }
  const connections = content.matchAll(/\b(?:postgres(?:ql)?|mysql|redis|amqp):\/\/[^:\s/'"]+:([^@\s'"/]+)@/g);
  return [...connections].some((match) => !isPlaceholderValue(match[1]));
}
