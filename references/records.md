# Private records

Keep JSONL (one object per line) as a portable starting point. Examples contain synthetic people only. Real records, CVs, email addresses, messages, approvals and replies belong outside the published skill repository.

## Required fields

- `name`: display name, not an identity key.
- `company`: claimed current affiliation; retain uncertainty in notes.
- `profile_url`: canonical professional profile URL when known, otherwise an empty string.
- `category`: `strong_match`, `company_contact`, `needs_checking`, or `excluded`.
- `evidence`: array of objects containing `claim`, `url`, `checked_at` (ISO date), and `basis` (`live`, `indexed`, or `user_supplied`). Claims should be specific, such as current employer or prior PM hiring. Add publication date/excerpt if available.
- `outreach`: one of `none`, `drafted`, `approved`, `sent`, `uncertain`, `replied`, `closed`.
- `do_not_contact`: boolean. A true value overrides other outreach states.

Useful optional fields: `recruiter_type`, `recruiter_location`, `market_coverage`, `role_scope`, `email`, `email_source`, `email_status`, `notes`, `opportunities`, and `events`.

Contact source, identity, remit and mailbox deliverability are separate checks. Label inferred addresses. Accept-all/unknown mail verification does not confirm an individual mailbox.

## Deduplication

Prefer a stable profile URL or a confirmed platform ID. Do not automatically merge same-name records, guessed emails or normalized name/company pairs. Keep people and employment separate conceptually: the same profile at two employers is one person with conflicting or changed employment, not two contacts.

The bundled export helper collapses only matching canonical profile URLs. It preserves all evidence, makes conflicting employers or categories `needs_checking`, and conservatively preserves contact restrictions. Notes and source records remain reviewable in the export. Same-name records without matching URLs remain separate. Recheck merged records before outreach.

## Outreach history

Store immutable events with time, channel, actual recipient/address, draft version, authorization reference, outcome and source. The helper does not authorize or send messages. A status label of `approved` alone is not sufficient authorization: consult the actual user approval and scope.

Check historical messages before follow-ups. Do not contact an opt-out, repeat a known send, or retry an uncertain send before verifying the outcome. A reply stops a scheduled follow-up pending review. Keep failed, uncertain and sent outcomes distinct.

## Coverage reporting

For each run retain source/query, access method, run date, pages/records examined, distinct candidates, duplicate hits, category counts, inaccessible sources and unverified claims. Do not confuse application counts with employer counts. Deduplicate company aliases without claiming all applications were merged.


## Separate verification dimensions

For new records, populate `assessments` with four independent keys: `current_employer`, `pm_experience`, `management_scope`, and `vacancy_status`. Each has `status` (`supported`, `unknown`, `conflicting`, or `not_applicable`), a plain-language `value`, and `evidence_indices` pointing to zero-based entries in the record's evidence array. Supported/conflicting claims require evidence. Legacy records without this field remain readable, but missing assessments mean unknown, not verified.

Examples: a current employer can be supported while PM experience and management scope remain unknown. Evidence of past PM hiring does not prove first-line management recruiting. A closed vacancy can have supported status with value `closed`; `supported` describes confidence, not availability. When no vacancy is being assessed, use `not_applicable` rather than inventing an active role. Do not reject a general company contact simply because PM ownership is unknown.

Merged contradictory assessments become unknown pending review; original assessments and their evidence references remain in source records. Reconcile them before upgrading confidence.

## Query execution ledger

Query generation is not query execution. The query CSV contains a stable `query_id`, the query and stream, plus `status`, `attempted_at`, `records_examined`, and `notes`. Keep all generated rows, including unexecuted ones:
- `planned`: not attempted.
- `executed`: query ran; enter attempt date (YYYY-MM-DD) and examined record count, including zero.
- `blocked`: attempted but source/access failed; enter attempt date and reason, not a result count.
- `skipped`: deliberately not attempted; explain why.

Run `python3 scripts/recruiter_list.py coverage --input /path/to/query-ledger.csv --output /path/to/coverage.json` to summarize. Counts are search-result records examined, not distinct people or live-profile verifications. Separately report deduped people and verification dimensions. Generated, attempted, executed and blocked totals must remain distinguishable. A skipped or blocked query means the planned coverage was not completed.

## Simple user-facing tracker

Default CSV exports contain only Name, Company, LinkedIn, Email, Relevance, Status, Notes and Source. Do not expose market coverage, nested JSON, duplicate invitation/outreach columns or repetitive confirmation text. Keep audit evidence and detailed verification private in JSONL; `export --detailed` is an optional audit export, not the default deliverable.

Keep one current `status` per person (for example Not contacted, Invitation pending, Connected, Messaged, Replied, Call arranged, Previously contacted, Skipped, Excluded). Update it immediately after verified actions and reconcile legacy `outreach` fields. Use `relevance` for one short reason this person is on the list. Notes should contain only material caveats, skip reasons or a concise next action/date. Keep message text and dated contact events in the private history, not extra default tracker columns. Do not say an invitation is pending merely from a generic email-sent event. Preserve all original audit details separately.
