// SPDX-License-Identifier: Apache-2.0
//
// Tests for the edi-schema episode questionnaire (self-serve capture instrument).
//
// The questionnaire page (web/questionnaire/index.html) is one self-contained
// file. To test the pure validation / serialization logic without a browser,
// this file extracts the page's inline <script> and evaluates it in a node:vm
// sandbox with no document/window (so main() never runs), then exercises the
// pure functions directly.
//
// The defect vectors below MUST mirror the ones in
// tests/test_questionnaire_parity.py: the same seeded defect must produce the
// same code on the Python side (validate_episode) and here (validateEpisode).
// That is the mutation-test / validator-parity discipline.
//
// Run: node web/questionnaire/validate.test.mjs   (Node 18+, no deps)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const pagePath = join(here, "index.html");
const html = readFileSync(pagePath, "utf8");

let passed = 0;
let failed = 0;
function ok(cond, message) {
  if (cond) { passed++; } else { failed++; console.error("  FAIL: " + message); }
}

function extractScripts(source) {
  const bodies = [];
  const re = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(source)) !== null) bodies.push(m[1]);
  return bodies;
}

function makeSandbox() {
  // No window, no document: main() must stay inert and the pure functions are
  // the only thing to reach for.
  return vm.createContext({ console, Date, Blob: undefined, URL: undefined });
}

const sandbox = vm.createContext({ console, Date });
for (const src of extractScripts(html)) vm.runInContext(src, sandbox, { filename: "questionnaire-inline.js" });

ok(typeof sandbox.validateEpisode === "function", "validateEpisode is defined");
ok(typeof sandbox.buildEpisode === "function", "buildEpisode is defined");
ok(typeof sandbox.wrapCroissant === "function", "wrapCroissant is defined");
ok(typeof sandbox.softWarnings === "function", "softWarnings is defined");

// ---------------------------------------------------------------------------
// Validator parity: the same seeded defects fail with the same codes.
// (Mirror of tests/test_questionnaire_parity.py.)
// ---------------------------------------------------------------------------

// A valid retrospective episode, minus the x_capture extension (so it is the
// schema-shaped base record the questionnaire builds toward).
function validDoc() {
  return {
    $schema: "https://postoaklabs.github.io/engineering-decision-schema/episode.schema.json",
    episode_id: "EP-Q-001",
    provenance: "retrospective",
    design: { name: "example block", pdk: "28nm" },
    prior_state: { stage: "post-cts", metrics: { wns_ns: "-0.4" } },
    observation: { metric: "wns_ns", value: "-0.4", target: "0", severity: "degrading" },
    hypothesis: "a constraint is missing",
    candidates_considered: [
      { intervention: "upsize a path", rejected_because: "schedule" },
      { intervention: "fix the constraint", rejected_because: null },
    ],
    chosen_intervention: { parameter: "set_input_delay", before: "0.5", after: "0.8" },
    post_state: { stage: "post-route", metrics: { wns_ns: "-0.1" } },
    expert_assessment: "acceptable",
    rationale: "the missing constraint was the cheap, correct fix",
    confidence: 0.8,
    failure_class: "FAIL_TIMING",
  };
}

function codes(doc) { return sandbox.validateEpisode(doc).map((e) => e.code); }

// Defect 1: missing required field (rationale) -> schema:required.
{
  const doc = validDoc();
  delete doc.rationale;
  const c = codes(doc);
  ok(c.includes("schema:required"), "missing field -> schema:required (got " + JSON.stringify(c) + ")");
}

// Defect 2: two candidates marked chosen -> E_CANDIDATES_MULTIPLE_CHOSEN.
{
  const doc = validDoc();
  doc.candidates_considered.forEach((cand) => { cand.rejected_because = null; });
  const c = codes(doc);
  ok(c.includes("E_CANDIDATES_MULTIPLE_CHOSEN"), "two chosen -> E_CANDIDATES_MULTIPLE_CHOSEN (got " + JSON.stringify(c) + ")");
}

// Defect 3: no candidate marked chosen -> E_CANDIDATES_NO_CHOSEN.
{
  const doc = validDoc();
  doc.candidates_considered.forEach((cand) => { cand.rejected_because = "cost"; });
  const c = codes(doc);
  ok(c.includes("E_CANDIDATES_NO_CHOSEN"), "no chosen -> E_CANDIDATES_NO_CHOSEN (got " + JSON.stringify(c) + ")");
}

// Defect 4: invalid severity -> schema:enum.
{
  const doc = validDoc();
  doc.observation.severity = "fatal";
  const c = codes(doc);
  ok(c.includes("schema:enum"), "bad severity -> schema:enum (got " + JSON.stringify(c) + ")");
}

// Defect 5: reproduced without environment -> E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT.
{
  const doc = validDoc();
  doc.provenance = "reproduced";
  const c = codes(doc);
  ok(c.includes("E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT"), "reproduced no env -> that code (got " + JSON.stringify(c) + ")");
}

// The valid base produces NO errors (the schema-shaped record is clean).
{
  const doc = validDoc();
  ok(sandbox.validateEpisode(doc).length === 0, "valid base -> 0 errors");
}

// ---------------------------------------------------------------------------
// buildEpisode: provenance retrospective + x_capture self_reported.
// ---------------------------------------------------------------------------
{
  const form = {
    "episode_id": "EP-Q-002",
    "design-name": "datapath", "design-pdk": "7nm", "design-scale": "medium",
    "observation": { "obs-severity": "" }, "failure-class": "FAIL_CTS",
    candidates: [
      { intervention: "a", rejected: false, rejected_because: "risk" },
      { intervention: "b", rejected: true, rejected_because: "" },
    ],
    confidence: "0.7",
    captured_at: "2026-09-01T00:00:00Z",
  };
  const doc = sandbox.buildEpisode(form);
  ok(doc.provenance === "retrospective", "provenance is retrospective");
  ok(doc.x_capture && doc.x_capture.self_reported === true, "x_capture.self_reported true");
  ok(doc.x_capture.instrument === "episode-questionnaire", "instrument named");
  ok(doc.candidates_considered[1].rejected_because === null, "the taken candidate has rejected_because null");
}

// ---------------------------------------------------------------------------
// wrapCroissant: a hand-mirror of the Croissant 1.1 context.
// ---------------------------------------------------------------------------
{
  const doc = validDoc();
  const wrapped = sandbox.wrapCroissant(doc);
  ok(wrapped.conformsTo === "http://mlcommons.org/croissant/1.1", "croissant conformsTo 1.1");
  ok(wrapped.version === "1.1", "croissant version 1.1");
  ok(Array.isArray(wrapped.recordSet) && wrapped.recordSet[0].data.includes.length === 1, "one row included");
  ok(wrapped.recordSet[0].data.includes[0].episode_id === "EP-Q-001", "row carries the episode_id");
}

// ---------------------------------------------------------------------------
// Zero network, no storage, self-contained (grep-style like the probe page).
// ---------------------------------------------------------------------------
function check(source) {
  const forbidden = ["fetch(", "XMLHttpRequest", "WebSocket(", "navigator.sendBeacon", "EventSource",
    "localStorage", "sessionStorage", "indexedDB", "document.cookie", "<script src", "<link href=\"http", "<img src=\"http", "@import", "url(http"];
  const hits = forbidden.filter((t) => source.includes(t));
  return hits.length ? (hits.join(", ")) : null;
}
ok(check(html) === null, "zero network / no storage / self-contained: " + (check(html) || "clean"));
const scripts = extractScripts(html);
ok(scripts.length === 1, "exactly one inline script (got " + scripts.length + ")");
ok(html.includes("<style>") && !/<link[^>]*rel=["']stylesheet["']/i.test(html), "CSS is inline, no external stylesheet");

console.log("\nvalidate.test.mjs: " + passed + " passed, " + failed + " failed");
if (failed > 0) process.exit(1);
