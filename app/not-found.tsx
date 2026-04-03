import Link from "next/link";

import { EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="space-y-6">
      <EmptyState
        title="That artifact view does not exist"
        description="The requested page or detail route could not be matched to the generated Week 7 artifacts."
      />
      <Link
        className="inline-flex rounded-full border border-[var(--line)] bg-white/80 px-4 py-2 text-sm font-medium text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
        href="/"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
