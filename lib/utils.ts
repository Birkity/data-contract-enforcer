export function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function humanizeSlug(value: string) {
  return value
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatDate(value?: string | null) {
  if (!value) {
    return "Not available";
  }

  try {
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value?: number | null, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }

  return `${value.toFixed(digits)}%`;
}

export function shortHash(value?: string | null, size = 8) {
  if (!value) {
    return "—";
  }

  return value.length <= size ? value : value.slice(0, size);
}

export function severityTone(value?: string | null) {
  const normalized = (value ?? "").toUpperCase();

  if (normalized === "CRITICAL" || normalized === "FAIL" || normalized === "BLOCK") {
    return "danger";
  }

  if (normalized === "HIGH" || normalized === "WARN") {
    return "warning";
  }

  if (normalized === "MEDIUM" || normalized === "AUDIT") {
    return "info";
  }

  if (normalized === "LOW" || normalized === "PASS" || normalized === "ALLOW_WITH_AUDIT_TRAIL") {
    return "success";
  }

  return "neutral";
}

export function decisionTone(value?: string | null) {
  return severityTone(value);
}

export function truncateMiddle(value: string, keep = 18) {
  if (!value || value.length <= keep) {
    return value;
  }

  const edge = Math.max(4, Math.floor((keep - 3) / 2));
  return `${value.slice(0, edge)}...${value.slice(-edge)}`;
}

export function normalizeFilePath(value?: string | null) {
  if (!value) {
    return "";
  }

  return value.replace(/\\/g, "/");
}

export function toArray<T>(value: T | T[] | undefined | null) {
  if (value === undefined || value === null) {
    return [];
  }

  return Array.isArray(value) ? value : [value];
}
