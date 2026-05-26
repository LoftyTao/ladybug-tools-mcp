# Energy Result Diagnosis

Use this when the user asks why an Energy result looks high, low, or suspicious and wants an evidence-first explanation.

## Preconditions

- Diagnose from a completed Energy run ledger, not from guesses.
- Save a baseline Garden version before making model changes.
- Treat single-run explanations as hypotheses, not proof of causality.

## MCP Route

1. Validate the Honeybee Model.
2. Create a Garden version for the baseline.
3. Confirm weather with Garden-managed EPW target.
4. Start or inspect the Energy run.
5. After completion, list outputs and read EUI or requested SQL summaries.
   For chart-style output, read the returned `time_interval`,
   `time_interval_guidance`, and any `effective_interval_minutes` before
   describing a curve as hourly, sub-hourly, monthly average, or monthly total.
6. Search Honeybee Rooms, Faces, Apertures, and compact room Energy properties.
7. Search standards or Garden library resources for construction, program, schedule, setpoint, and HVAC assumptions.
8. Explain evidence first, then propose the smallest next test.

## Evidence Checklist

- Weather target and location/source.
- EUI total and major end-use components when available.
- Room ProgramType, Setpoint, HVAC, and conditioned assumptions.
- Window ratio or aperture area and key constructions.
- Schedule/program assumptions relevant to the user question.
- Validation status and run status.
- ERR repair hints if `energyplus_read_errors` returns them. If the hint code
  is `ironbug_heating_water_coil_ua_or_flow_not_numeric`, rebuild the affected
  Ironbug hot-water coil with numeric `u_factor_times_area_value` and
  `maximum_water_flow_rate`, then rebuild the owning FCU, terminal, or plant
  graph before another Energy run.
- Result-data truncation fields: use `collection_count`,
  `returned_collection_count`, and `collections_truncated`; do not invent alias
  counts.

## Success Criteria

- The explanation cites completed-run outputs and model/resource state.
- The baseline Garden version is saved.
- Recommendations are framed as testable hypotheses, such as "rerun with WWR reduced to 0.30".

## Stop Conditions

- Do not claim a single run proves the unique cause.
- Do not overstate IdealAir or template HVAC results as real equipment reports.
- If schedule and program are ordinary, do not force them into the answer as a likely cause.
- Keep campaign evidence, EUI values, and Garden version IDs in LLM-Wiki.
