import type { ReactNode } from "react";
import Link from "next/link";

import { cn } from "@/lib/utils";

type Tone = "danger" | "warning" | "success" | "info" | "neutral";

const toneClasses: Record<Tone, string> = {
  danger: "border-[var(--danger-soft)] bg-[var(--danger-bg)] text-[var(--danger)]",
  warning: "border-[var(--warning-soft)] bg-[var(--warning-bg)] text-[var(--warning)]",
  success: "border-[var(--success-soft)] bg-[var(--success-bg)] text-[var(--success)]",
  info: "border-[var(--info-soft)] bg-[var(--info-bg)] text-[var(--info)]",
  neutral: "border-[var(--line)] bg-[rgba(248,251,255,0.9)] text-[var(--ink)]/80",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
        toneClasses[tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {children}
    </span>
  );
}

export function SurfaceCard({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[30px] border border-[var(--line)] bg-[var(--card)] p-6 shadow-[0_24px_70px_var(--shadow)] backdrop-blur-xl",
        className,
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(22,98,196,0.58),transparent)]" />
      {children}
    </section>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  tone = "neutral",
  href,
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: Tone;
  href?: string;
}) {
  const body = (
    <SurfaceCard className="h-full p-5 transition-transform duration-200 hover:-translate-y-1 hover:shadow-[0_28px_80px_var(--shadow)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
          {label}
        </p>
        <Badge tone={tone}>{tone}</Badge>
      </div>
      <div className="space-y-2">
        <div className="text-3xl font-semibold tracking-tight text-[var(--ink)]">{value}</div>
        {detail ? <p className="text-sm leading-6 text-[var(--muted)]">{detail}</p> : null}
      </div>
    </SurfaceCard>
  );

  if (!href) {
    return body;
  }

  return (
    <Link className="block transition-transform duration-150 hover:-translate-y-0.5" href={href}>
      {body}
    </Link>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  aside,
}: {
  eyebrow: string;
  title: string;
  description: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--accent)]">
          {eyebrow}
        </p>
        <h1 className="font-display text-4xl leading-tight text-[var(--ink)] sm:text-5xl">
          {title}
        </h1>
        <div className="max-w-3xl text-base leading-7 text-[var(--muted)]">{description}</div>
      </div>
      {aside ? <div className="w-full max-w-md">{aside}</div> : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  expectedFile,
}: {
  title: string;
  description: string;
  expectedFile?: string;
}) {
  return (
    <SurfaceCard className="border-dashed bg-[var(--paper)]/80">
      <div className="space-y-3">
        <Badge tone="neutral">Missing data</Badge>
        <h2 className="font-display text-2xl text-[var(--ink)]">{title}</h2>
        <p className="max-w-2xl text-sm leading-7 text-[var(--muted)]">{description}</p>
        {expectedFile ? (
          <div className="rounded-2xl border border-[var(--line)] bg-white/70 px-4 py-3 font-mono text-sm text-[var(--ink)]">
            Expected file: {expectedFile}
          </div>
        ) : null}
      </div>
    </SurfaceCard>
  );
}

export function SectionLabel({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h2 className="font-display text-2xl text-[var(--ink)]">{title}</h2>
      {subtitle ? <p className="text-sm leading-6 text-[var(--muted)]">{subtitle}</p> : null}
    </div>
  );
}

export function InlinePath({ children }: { children: ReactNode }) {
  return (
    <code className="rounded-full border border-[var(--line)] bg-white/80 px-3 py-1 font-mono text-[12px] text-[var(--ink)]">
      {children}
    </code>
  );
}
