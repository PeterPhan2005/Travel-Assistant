# Offline Agent Evaluation Report

Fixture schema version: 1

Threshold status: pass

Overall: 43/43 passed; 0 failed; 10000 basis points.

The default suite is deterministic, offline, credential-free, and performs no real model request.

## Per-target metrics

| Target | Total | Passed | Failed | Pass rate (bp) |
| --- | ---: | ---: | ---: | ---: |
| router | 6 | 6 | 0 | 10000 |
| discovery | 5 | 5 | 0 | 10000 |
| narration | 5 | 5 | 0 | 10000 |
| local_culture | 5 | 5 | 0 | 10000 |
| itinerary | 5 | 5 | 0 | 10000 |
| grounding_reviewer | 5 | 5 | 0 | 10000 |
| response_composer | 5 | 5 | 0 | 10000 |
| runtime | 7 | 7 | 0 | 10000 |

## Per-check metrics

| Check | Total | Passed | Failed | Pass rate (bp) |
| --- | ---: | ---: | ---: | ---: |
| contract_valid | 43 | 43 | 0 | 10000 |
| deterministic_repeat | 43 | 43 | 0 | 10000 |
| evidence_closed | 35 | 35 | 0 | 10000 |
| expected_failure | 14 | 14 | 0 | 10000 |
| expected_intent | 6 | 6 | 0 | 10000 |
| expected_items | 34 | 34 | 0 | 10000 |
| expected_order | 13 | 13 | 0 | 10000 |
| expected_plan | 6 | 6 | 0 | 10000 |
| expected_status | 31 | 31 | 0 | 10000 |
| expected_warning | 5 | 5 | 0 | 10000 |
| no_new_fact | 31 | 31 | 0 | 10000 |
| no_overlap | 4 | 4 | 0 | 10000 |
| no_unexpected_call | 43 | 43 | 0 | 10000 |
| optional_fields_omitted | 9 | 9 | 0 | 10000 |
| privacy_safe | 43 | 43 | 0 | 10000 |
| source_union_exact | 19 | 19 | 0 | 10000 |
| time_window_exact | 4 | 4 | 0 | 10000 |
| warning_preserved | 12 | 12 | 0 | 10000 |

## Case results

| Case ID | Target | Status | Passed checks | Failed checks |
| --- | --- | --- | --- | --- |
| composer-001 | response_composer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, expected_warning, no_new_fact, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact, warning_preserved | - |
| composer-002 | response_composer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, expected_warning, no_new_fact, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact, warning_preserved | - |
| composer-003 | response_composer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, expected_warning, no_new_fact, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact, warning_preserved | - |
| composer-004 | response_composer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, expected_warning, no_new_fact, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact, warning_preserved | - |
| composer-005 | response_composer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, expected_warning, no_new_fact, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact, warning_preserved | - |
| discovery-001 | discovery | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact | - |
| discovery-002 | discovery | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact | - |
| discovery-003 | discovery | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact | - |
| discovery-004 | discovery | pass | contract_valid, deterministic_repeat, expected_failure, no_unexpected_call, privacy_safe | - |
| discovery-005 | discovery | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, expected_status, no_unexpected_call, optional_fields_omitted, privacy_safe, source_union_exact | - |
| grounding-001 | grounding_reviewer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe | - |
| grounding-002 | grounding_reviewer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe | - |
| grounding-003 | grounding_reviewer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe | - |
| grounding-004 | grounding_reviewer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe | - |
| grounding-005 | grounding_reviewer | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe | - |
| itinerary-001 | itinerary | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, no_new_fact, no_overlap, no_unexpected_call, privacy_safe, time_window_exact | - |
| itinerary-002 | itinerary | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, no_new_fact, no_overlap, no_unexpected_call, privacy_safe, time_window_exact | - |
| itinerary-003 | itinerary | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, no_new_fact, no_overlap, no_unexpected_call, privacy_safe, time_window_exact | - |
| itinerary-004 | itinerary | pass | contract_valid, deterministic_repeat, expected_failure, no_unexpected_call, privacy_safe | - |
| itinerary-005 | itinerary | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_order, no_new_fact, no_overlap, no_unexpected_call, privacy_safe, time_window_exact | - |
| local-culture-001 | local_culture | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| local-culture-002 | local_culture | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| local-culture-003 | local_culture | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| local-culture-004 | local_culture | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| local-culture-005 | local_culture | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| narration-001 | narration | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| narration-002 | narration | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| narration-003 | narration | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| narration-004 | narration | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| narration-005 | narration | pass | contract_valid, deterministic_repeat, evidence_closed, expected_items, expected_status, no_new_fact, no_unexpected_call, privacy_safe, source_union_exact | - |
| router-001 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| router-002 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| router-003 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| router-004 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| router-005 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| router-006 | router | pass | contract_valid, deterministic_repeat, expected_intent, expected_items, expected_plan, no_unexpected_call, privacy_safe | - |
| runtime-001 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-002 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-003 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-004 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-005 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-006 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
| runtime-007 | runtime | pass | contract_valid, deterministic_repeat, evidence_closed, expected_failure, expected_status, no_new_fact, no_unexpected_call, privacy_safe, warning_preserved | - |
