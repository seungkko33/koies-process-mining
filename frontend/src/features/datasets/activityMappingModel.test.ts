import { describe, expect, it } from "vitest";

import { parseArtifact } from "../../api/datasets";
import type { ActivityCoverageRow } from "../../types/datasets";
import { filterActivityCoverageRows } from "./datasetModel";

const rows: ActivityCoverageRow[] = [
  {
    source_activity: "claimService.calculate",
    business_activity: "급여결정",
    event_count: 120,
    case_count: 100,
    mapped: true,
  },
  {
    source_activity: "paymentService.execute",
    business_activity: null,
    event_count: 20,
    case_count: 18,
    mapped: false,
  },
];

describe("Activity Mapping model", () => {
  it("filters unmapped methods without losing frequency order", () => {
    expect(filterActivityCoverageRows(rows, "unmapped", "")).toEqual([rows[1]]);
  });

  it("searches both source and business activity labels", () => {
    expect(filterActivityCoverageRows(rows, "all", "급여")).toEqual([rows[0]]);
    expect(filterActivityCoverageRows(rows, "all", "payment")).toEqual([rows[1]]);
  });
});

describe("Artifact status DTO", () => {
  it("preserves lifecycle protection flags", () => {
    expect(parseArtifact({
      artifact_id: "artifact-1",
      dataset_id: "dataset-1",
      semantic_contract_version: 2,
      mapping_version: 2,
      artifact_type: "NORMALIZED",
      path: "dataset/events-v2.parquet",
      size_bytes: 1024,
      created_at: "2026-09-01T00:00:00",
      active: true,
      pinned: false,
    })).toMatchObject({ active: true, pinned: false, artifact_type: "NORMALIZED" });
  });

  it("rejects malformed lifecycle flags", () => {
    expect(() => parseArtifact({ artifact_id: "broken" })).toThrow();
  });
});
