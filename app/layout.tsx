import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import "@/app/globals.css";
import { loadReportData } from "@/lib/data/artifacts";

export const metadata: Metadata = {
  title: {
    default: "TRP Week 7 Data Contract Enforcer",
    template: "%s | TRP Week 7 Data Contract Enforcer",
  },
  description:
    "Read-only reviewer dashboard over the real generated artifacts of the TRP Week 7 Data Contract Enforcer.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const reportData = await loadReportData();

  return (
    <html lang="en">
      <body>
        <AppShell
          architecture={(reportData?.architecture as Parameters<typeof AppShell>[0]["architecture"]) ?? null}
          generatedAt={typeof reportData?.generated_at === "string" ? reportData.generated_at : null}
        >
          {children}
        </AppShell>
      </body>
    </html>
  );
}
