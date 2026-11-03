# Data dictionary

- `cohort`: specific experiment, not a device-wide pooled test.
- `question`, `arm`, `cap`, `repeat`: local question ID, recorded method, whole-message input ceiling and generation repeat when applicable. `original` in a cross-page round is not the earlier page-local `structure` arm.
- `correctness`, `support`: final retained 0–2 dimension scores. The support field has historical application differences; read AUDIT_NOTES.
- `core_label_original`: original boolean/string/null. Null means unresolved or unavailable as documented, never a pass. Early core correctness/answering labels are not a unified completion metric.
- `dimensions`: other supplied dimensions, retained to avoid silently dropping scored fields. Null and NA are not 0 or 2. They are not combined into a total score.
- `passed`: derived only where that experiment specified a joint endpoint. `historical_joint` uses correctness=2 and support=2; supported completion also requires core completion=是. All included endpoint rows are resolved final ratings.
- `physical_job_id`: reuse identity in the ATV320 structure comparison. Logical rows are not independent calls.
- `request_sha256`: recorded digest of complete request content, not output uniqueness or immutable model weights.
- `source_record_sha256`: digest of the retained source score file, not its full contents or a public source address.
- `support_application_flag`: records the four previously identified application inconsistencies; `resolved_by_rater_correction_2026-10-21` means the designated rater supplied the final support correction. It does not assert that every historical score was revalidated.
- `support_revision`: V20 initial and final support, original and final review dates, pseudonymous rater code, correction type, source digest and reason code. Corrections apply only to the specified response identity; the original `source_record_sha256` still identifies the initial source table.
- `support_as_recorded`: current final confirmed support in the 78-response identity table. For four V20 corrections, `original_support` and `support_revision_date` retain the initial value and actual correction date.
- `original_support`, `clarification_applied`: V90 initial/final support distinction; N01-A final support is 1.
- `delivery`: recorded mechanical completeness where exported, not semantic correctness.
- `selected_unit_ids`: ordered original source-unit IDs in a V20 input. IDs encode document revision, one-based physical PDF page and unit number, but not manual text.
- `listed_packages`: OR across sufficient alternatives for each fact, AND across required facts and within each alternative package. CF uses a separate all-parent-unit endpoint.
- `stop`: first oversized candidate package. It means not admitted at this position, not unavailable in the manual or impossible to retrieve.
- `input_tokens_estimated`: historical local estimate including serialization, **not provider-reported token usage**.
- `added_count`, `lost_count`: unit occurrences relative to B0 at the same question and budget; not relevance-weighted token savings.
- `R_ACS`, `R_OTHER`: distinct designated raters with non-overlapping device assignments. No independent paired ratings are available.

Records preserve all conditions within each included cohort. Cohort selection is based on manuscript tables, not outcome. Early Stage_1/Stage_2 development rounds, automated judgments and superseded trial scores are not exported as final human outcomes.
# Language of source labels

The original Chinese string values `是` and `否` mean “yes” and “no”. Interpret them using the record's `core_semantics`; historical core correctness and later answer completion are different concepts. The Chinese literals in some parsing code are functional patterns for Chinese manuals, not instructions or output labels to translate blindly.

