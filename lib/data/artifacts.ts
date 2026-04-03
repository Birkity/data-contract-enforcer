import { cache } from "react";
import fs from "fs/promises";
import path from "path";

import YAML from "yaml";

import { humanizeSlug, normalizeFilePath, toArray } from "@/lib/utils";

type JsonRecord = Record<string, unknown>;

export type RegistrySubscription = {
  contract_id: string;
  subscriber_id: string;
  fields_consumed?: string[];
  breaking_fields?: Array<{ field?: string; reason?: string }>;
  validation_mode?: string;
  registered_at?: string;
  contact?: {
    owner?: string;
    role?: string;
    email?: string;
  };
};

export type ContractField = {
  name: string;
  type: string;
  description: string;
  required: boolean;
  format?: string;
  minimum?: number | null;
  maximum?: number | null;
  enumValues: string[];
  sampleValues: string[];
  observedMin?: number | null;
  observedMax?: number | null;
  isRisky: boolean;
};

export type ContractArtifact = {
  id: string;
  title: string;
  description: string;
  filePath: string;
  dbtPath?: string;
  sourceDataset: string;
  clauseCount: number;
  riskyFields: string[];
  fields: ContractField[];
  registrySubscribers: RegistrySubscription[];
  lineageNotes: string[];
  implementationModel?: {
    enforcement_boundary?: string;
    blast_radius_primary_source?: string;
    lineage_role?: string;
    trust_boundary_tier?: string;
  };
};

export type ValidationResult = {
  check_id: string;
  column_name?: string;
  check_type?: string;
  status?: string;
  actual_value?: string;
  expected?: string;
  severity?: string;
  records_failing?: number;
  sample_failing?: string[];
  message?: string;
  records_total?: number;
  failing_fraction?: number;
  failing_percent?: number;
  validation_mode?: string;
  action?: string;
  blocking?: boolean;
};

export type ValidationReport = {
  slug: string;
  fileName: string;
  filePath: string;
  report_id: string;
  contract_id: string;
  run_timestamp?: string;
  validation_mode?: string;
  decision?: string;
  blocking?: boolean;
  total_checks: number;
  passed: number;
  failed: number;
  warned: number;
  errored: number;
  blocked?: number;
  profiled_row_count?: number;
  results: ValidationResult[];
  failingChecks: ValidationResult[];
  sourceLabel: string;
};

export type ViolationEntry = {
  id: string;
  report_id: string;
  contract_id: string;
  field?: string;
  check_type?: string;
  status?: string;
  severity?: string;
  action?: string;
  blocking?: boolean;
  message?: string;
  validation_mode?: string;
  sample_values?: string[];
  records_failing?: number;
  records_total?: number;
  failing_percent?: number;
  check_id?: string;
  sourceKind: "Injected test" | "Real finding" | "Unknown";
  reportSlug?: string;
};

export type AttributionEntry = {
  violation_id: string;
  check_id: string;
  field?: string;
  producer_system?: string;
  dataset_path?: string;
  severity?: string;
  message?: string;
  records_failing?: number;
  sample_failing?: string[];
  matching_violation_log_entries?: number;
  blame_chain?: Array<{
    file_path?: string;
    repo_root?: string;
    commit_hash?: string;
    author?: string;
    author_email?: string;
    commit_timestamp?: string;
    commit_message?: string;
    confidence_score?: number;
    path_relevance?: number;
    lineage_distance?: number;
    rationale?: string;
    recent_commit_count?: number;
    line_blame_hits?: number;
    rank?: number;
  }>;
  blast_radius?: {
    primary?: {
      source?: string;
      subscriber_count?: number;
      matched_on_field?: boolean;
      subscribers?: RegistrySubscription[];
      summary?: string;
      confidence?: string;
    };
    enrichment?: {
      source?: string;
      matched_nodes?: string[];
      upstream_candidates?: string[];
      downstream_nodes?: string[];
      registry_aligned_consumers?: Array<{
        subscriber_id?: string;
        snapshot_root?: string;
        matched_nodes?: string[];
        fields_consumed?: string[];
      }>;
      summary?: string;
      confidence?: string;
    };
  };
};

export type SnapshotInventory = {
  contractId: string;
  versionCount: number;
  latestPath?: string;
  versions: string[];
};

const rootPath = (...segments: string[]) =>
  path.join(/* turbopackIgnore: true */ process.cwd(), ...segments);

async function readTextSafe(relativePath: string) {
  try {
    const text = await fs.readFile(rootPath(relativePath), "utf8");
    return text.replace(/^\uFEFF/, "");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return null;
    }

    throw error;
  }
}

async function readDirSafe(relativePath: string) {
  try {
    return await fs.readdir(rootPath(relativePath), { withFileTypes: true });
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return [];
    }

    throw error;
  }
}

async function readJsonSafe<T>(relativePath: string): Promise<T | null> {
  const text = await readTextSafe(relativePath);
  if (!text) {
    return null;
  }

  return JSON.parse(text) as T;
}

async function readYamlSafe<T>(relativePath: string): Promise<T | null> {
  const text = await readTextSafe(relativePath);
  if (!text) {
    return null;
  }

  return YAML.parse(text) as T;
}

function parseJsonl<T>(text: string): T[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as T);
}

function toStringArray(value: unknown) {
  return toArray(value as string[]).map((item) => String(item));
}

function normalizeContractField(name: string, rawField: JsonRecord): ContractField {
  const enumValues = toStringArray(rawField.enum);
  const sampleValues = toStringArray((rawField.profile as JsonRecord | undefined)?.sample_values);
  const minimum = typeof rawField.minimum === "number" ? rawField.minimum : null;
  const maximum = typeof rawField.maximum === "number" ? rawField.maximum : null;
  const observedMin = typeof (rawField.profile as JsonRecord | undefined)?.observed_min === "number"
    ? ((rawField.profile as JsonRecord).observed_min as number)
    : null;
  const observedMax = typeof (rawField.profile as JsonRecord | undefined)?.observed_max === "number"
    ? ((rawField.profile as JsonRecord).observed_max as number)
    : null;

  return {
    name,
    type: String(rawField.type ?? "unknown"),
    description: String(rawField.description ?? "No description captured in the generated contract."),
    required: Boolean(rawField.required),
    format: rawField.format ? String(rawField.format) : undefined,
    minimum,
    maximum,
    enumValues,
    sampleValues,
    observedMin,
    observedMax,
    isRisky:
      /confidence|sequence|run_type|source_hash|schema_version/i.test(name) ||
      minimum !== null ||
      maximum !== null ||
      enumValues.length > 0,
  };
}

async function listSnapshotInventories() {
  const contractDirs = await readDirSafe("schema_snapshots/contracts");
  const inventories: SnapshotInventory[] = [];

  for (const entry of contractDirs) {
    if (!entry.isDirectory()) {
      continue;
    }

    const versionEntries = await readDirSafe(path.join("schema_snapshots/contracts", entry.name));
    const versions = versionEntries
      .filter((item) => item.isFile() && /\.(yaml|yml)$/i.test(item.name))
      .map((item) =>
        normalizeFilePath(path.join("schema_snapshots/contracts", entry.name, item.name)),
      )
      .sort();

    inventories.push({
      contractId: entry.name,
      versionCount: versions.length,
      latestPath: versions.find((version) => version.endsWith("latest.yaml") || version.endsWith("latest.yml")),
      versions,
    });
  }

  return inventories.sort((left, right) => left.contractId.localeCompare(right.contractId));
}

export const loadRegistry = cache(async () => {
  const registry = await readYamlSafe<{ subscriptions?: RegistrySubscription[] }>(
    "contract_registry/subscriptions.yaml",
  );

  return {
    filePath: "contract_registry/subscriptions.yaml",
    subscriptions: registry?.subscriptions ?? [],
  };
});

export const loadContracts = cache(async (): Promise<ContractArtifact[]> => {
  const registry = await loadRegistry();
  const entries = await readDirSafe("generated_contracts");
  const contractFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".yaml") && !entry.name.endsWith("_dbt.yml"))
    .map((entry) => entry.name)
    .sort();

  const contracts = await Promise.all(
    contractFiles.map(async (fileName) => {
      const relativePath = normalizeFilePath(path.join("generated_contracts", fileName));
      const raw = (await readYamlSafe<JsonRecord>(relativePath)) ?? {};
      const schema = (raw.schema as Record<string, JsonRecord> | undefined) ?? {};
      const fields = Object.entries(schema).map(([name, field]) => normalizeContractField(name, field));
      const id = String(raw.id ?? fileName.replace(/\.yaml$/i, "").replace(/_/g, "-"));
      const title = String((raw.info as JsonRecord | undefined)?.title ?? humanizeSlug(id));
      const description = String(
        (raw.info as JsonRecord | undefined)?.description ??
          "Generated contract derived from the local Week 7 artifact set.",
      );
      const sourceDataset = String(
        ((raw.servers as JsonRecord | undefined)?.local as JsonRecord | undefined)?.path ?? "Unknown source dataset",
      );
      const lineageNotes = [
        ...toStringArray((raw.terms as JsonRecord | undefined)?.limitations),
        ...toStringArray((raw.lineage as JsonRecord | undefined)?.notes),
      ].filter(Boolean);
      const dbtCandidate = normalizeFilePath(
        path.join("generated_contracts", fileName.replace(/\.yaml$/i, "_dbt.yml")),
      );
      const hasDbt = Boolean(await readTextSafe(dbtCandidate));
      const registrySubscribers = registry.subscriptions.filter(
        (subscription) => subscription.contract_id === id,
      );

      return {
        id,
        title,
        description,
        filePath: relativePath,
        dbtPath: hasDbt ? dbtCandidate : undefined,
        sourceDataset,
        clauseCount: fields.length,
        riskyFields: fields.filter((field) => field.isRisky).map((field) => field.name),
        fields,
        registrySubscribers,
        lineageNotes,
        implementationModel: (raw.implementation_model as ContractArtifact["implementationModel"]) ?? undefined,
      } satisfies ContractArtifact;
    }),
  );

  return contracts.sort((left, right) => left.id.localeCompare(right.id));
});

export const loadValidationReports = cache(async (): Promise<ValidationReport[]> => {
  const entries = await readDirSafe("validation_reports");
  const reportFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => entry.name)
    .sort();

  const reports = await Promise.all(
    reportFiles.map(async (fileName) => {
      const filePath = normalizeFilePath(path.join("validation_reports", fileName));
      const raw = (await readJsonSafe<JsonRecord>(filePath)) ?? {};
      const results = ((raw.results as JsonRecord[] | undefined) ?? []).map((result) => ({
        check_id: String(result.check_id ?? "unknown.check"),
        column_name: result.column_name ? String(result.column_name) : undefined,
        check_type: result.check_type ? String(result.check_type) : undefined,
        status: result.status ? String(result.status) : undefined,
        actual_value: result.actual_value ? String(result.actual_value) : undefined,
        expected: result.expected ? String(result.expected) : undefined,
        severity: result.severity ? String(result.severity) : undefined,
        records_failing:
          typeof result.records_failing === "number" ? result.records_failing : undefined,
        sample_failing: toStringArray(result.sample_failing),
        message: result.message ? String(result.message) : undefined,
        records_total: typeof result.records_total === "number" ? result.records_total : undefined,
        failing_fraction:
          typeof result.failing_fraction === "number" ? result.failing_fraction : undefined,
        failing_percent:
          typeof result.failing_percent === "number" ? result.failing_percent : undefined,
        validation_mode: result.validation_mode ? String(result.validation_mode) : undefined,
        action: result.action ? String(result.action) : undefined,
        blocking: Boolean(result.blocking),
      }));

      return {
        slug: fileName.replace(/\.json$/i, ""),
        fileName,
        filePath,
        report_id: String(raw.report_id ?? fileName),
        contract_id: String(raw.contract_id ?? "unknown-contract"),
        run_timestamp: raw.run_timestamp ? String(raw.run_timestamp) : undefined,
        validation_mode: raw.validation_mode ? String(raw.validation_mode) : undefined,
        decision: raw.decision ? String(raw.decision) : undefined,
        blocking: Boolean(raw.blocking),
        total_checks: Number(raw.total_checks ?? 0),
        passed: Number(raw.passed ?? 0),
        failed: Number(raw.failed ?? 0),
        warned: Number(raw.warned ?? 0),
        errored: Number(raw.errored ?? 0),
        blocked: raw.blocked ? Number(raw.blocked) : undefined,
        profiled_row_count: raw.profiled_row_count ? Number(raw.profiled_row_count) : undefined,
        results,
        failingChecks: results.filter((result) => result.status && result.status !== "PASS"),
        sourceLabel: fileName.includes("injected")
          ? "Injected test"
          : fileName.includes("baseline")
            ? "Clean baseline"
            : "Validation report",
      } satisfies ValidationReport;
    }),
  );

  return reports.sort((left, right) => {
    const leftTime = left.run_timestamp ? new Date(left.run_timestamp).getTime() : 0;
    const rightTime = right.run_timestamp ? new Date(right.run_timestamp).getTime() : 0;
    return rightTime - leftTime;
  });
});

export const loadViolations = cache(async (): Promise<ViolationEntry[]> => {
  const text = await readTextSafe("violation_log/violations.jsonl");
  if (!text) {
    return [];
  }

  const reports = await loadValidationReports();
  const reportLookup = new Map(reports.map((report) => [report.report_id, report]));

  return parseJsonl<JsonRecord>(text).map((entry, index) => {
    const report = reportLookup.get(String(entry.report_id ?? ""));
    const sourceKind =
      report?.fileName.includes("injected")
        ? "Injected test"
        : report
          ? "Real finding"
          : "Unknown";

    return {
      id: `${entry.report_id ?? "unknown"}:${entry.check_id ?? index}`,
      report_id: String(entry.report_id ?? ""),
      contract_id: String(entry.contract_id ?? ""),
      field: entry.field ? String(entry.field) : undefined,
      check_type: entry.check_type ? String(entry.check_type) : undefined,
      status: entry.status ? String(entry.status) : undefined,
      severity: entry.severity ? String(entry.severity) : undefined,
      action: entry.action ? String(entry.action) : undefined,
      blocking: Boolean(entry.blocking),
      message: entry.message ? String(entry.message) : undefined,
      validation_mode: entry.validation_mode ? String(entry.validation_mode) : undefined,
      sample_values: toStringArray(entry.sample_values),
      records_failing:
        typeof entry.records_failing === "number" ? entry.records_failing : undefined,
      records_total: typeof entry.records_total === "number" ? entry.records_total : undefined,
      failing_percent: typeof entry.failing_percent === "number" ? entry.failing_percent : undefined,
      check_id: entry.check_id ? String(entry.check_id) : undefined,
      sourceKind,
      reportSlug: report?.slug,
    } satisfies ViolationEntry;
  });
});

export const loadAttribution = cache(async () => {
  const raw = await readJsonSafe<{
    generated_at?: string;
    architecture_mode?: Record<string, string>;
    confidence_scoring_method?: { summary?: string; components?: string[] };
    attributions?: AttributionEntry[];
  }>("violation_log/blame_chain.json");

  return raw ?? { attributions: [] };
});

export const loadSchemaEvolution = cache(async () => {
  const compatibility = await readJsonSafe<JsonRecord>("schema_snapshots/compatibility_report.json");
  const evolutionSummary = await readJsonSafe<JsonRecord>("schema_snapshots/evolution_summary.json");
  const snapshotInventory = await listSnapshotInventories();

  const previousSnapshotPath = compatibility?.previous_snapshot
    ? String(compatibility.previous_snapshot)
    : null;
  const currentSnapshotPath = compatibility?.current_snapshot
    ? String(compatibility.current_snapshot)
    : null;

  return {
    compatibility,
    evolutionSummary,
    snapshotInventory,
    previousSnapshotPath,
    currentSnapshotPath,
    previousSnapshot: previousSnapshotPath ? await readYamlSafe<JsonRecord>(previousSnapshotPath) : null,
    currentSnapshot: currentSnapshotPath ? await readYamlSafe<JsonRecord>(currentSnapshotPath) : null,
  };
});

export const loadAiMetrics = cache(async () => {
  return await readJsonSafe<JsonRecord>("enforcer_report/ai_metrics.json");
});

export const loadReportData = cache(async () => {
  return await readJsonSafe<JsonRecord>("enforcer_report/report_data.json");
});

export const loadDashboardData = cache(async () => {
  const [contracts, validations, violations, registry, attribution, schemaEvolution, aiMetrics, reportData] =
    await Promise.all([
      loadContracts(),
      loadValidationReports(),
      loadViolations(),
      loadRegistry(),
      loadAttribution(),
      loadSchemaEvolution(),
      loadAiMetrics(),
      loadReportData(),
    ]);

  const severityCounts = violations.reduce(
    (accumulator, violation) => {
      const key = (violation.severity ?? "UNKNOWN").toUpperCase();
      accumulator[key] = (accumulator[key] ?? 0) + 1;
      return accumulator;
    },
    {} as Record<string, number>,
  );

  return {
    contracts,
    validations,
    violations,
    registry,
    attribution,
    schemaEvolution,
    aiMetrics,
    reportData,
    severityCounts,
  };
});
