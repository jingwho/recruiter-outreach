# Product Recruiter Outreach

A portable agent skill for building an evidence-backed recruiter shortlist and preparing outreach or carrying out explicitly authorized blank-invitation runs. Use existing employer lists and people databases instead of rebuilding a job board.

## What it does

- Searches broadly for company recruiting employees, product specialists and agency recruiters.
- Separates first-line management from Senior/Principal individual-contributor scope.
- Keeps general company contacts even when PM ownership is unknown.
- Preserves sources, uncertainty, duplicate checks and prior outreach.
- Prepares email/LinkedIn approaches without default sending automation.

This is a skill plus small local utilities, not a hosted application, LinkedIn scraper, contact database or email service. An agent needs authorized web/search tools or supplied exports for discovery. No paid provider is required; account-specific capabilities vary. The example companies and people are synthetic.

## Install

Download this repository and place its folder in the skill directory supported by your agent. For Codex, copy the folder to `~/.codex/skills/product-recruiter-outreach/` (or `$CODEX_HOME/skills/`). Do not overwrite an existing customized install without reviewing it. Other agents that support `SKILL.md` may use different paths; follow their documentation.

Example invocation:

> Use product-recruiter-outreach to find recruiters for first-line product-management roles in Austin. Start from my existing employer list, include general in-house contacts and agencies, and return a sourced shortlist. Do not send messages.

## Run the local helpers

Python 3.10+; standard library only. Run from the repository root:

```sh
python3 scripts/recruiter_list.py queries --config examples/austin.json --output /tmp/recruiter-queries.csv
python3 scripts/recruiter_list.py export --input examples/recruiters.jsonl --output /tmp/recruiter-shortlist.csv
python3 scripts/recruiter_list.py coverage --input /tmp/recruiter-queries.csv --output /tmp/recruiter-coverage.json
python3 -m unittest discover -s tests -v
```

Outputs must use new paths. The script makes no network calls. Query output is a research plan, not completed research. Update each query’s execution status and use the coverage command to distinguish planned, attempted and completed work. Records separately assess current employer, PM experience, management scope and vacancy status. Export preserves source records and makes conflicting identities/affiliations reviewable; it never verifies employment or authorizes outreach.

## Privacy and publication

Keep private run data outside this repository. Do not commit CVs, recruiter lists, correspondence, addresses, API keys or approvals. `.gitignore` offers additional protection for common local-data paths, but is not a substitute for reviewing staged files.

## Updates from an assistant conversation

Ask your assistant to update this repository, describing the behavior to change. It should fetch/read the current version, preserve unrelated work, edit, test and provide a commit or pull-request link when publishing is authorized. GitHub access is configured in the host assistant, not in this skill.

Installed copies do not update automatically. Review releases/commits, then pull your clean checkout or replace the installed folder with the reviewed version. Keep private configuration outside the install folder so updating does not overwrite it. The package contains no live sending or scheduler integration. Explicitly authorized runs can use the host’s supported UI and durable scheduler; unavailable capabilities must be reported, not promised.

## Release status

Initial release: local helpers tested; live discovery quality varies by source and access. Validate the discovery workflow on a small sample and report checked versus unverified leads before scaling. Do not interpret sample results as exhaustive coverage or a guaranteed path to interviews.

See [SKILL.md](SKILL.md), [discovery](references/discovery.md), [records](references/records.md), and [outreach](references/outreach.md).

## Optional authorized invitation run

With explicit owner authorization for a defined batch, the agent interleaves discovery and sending: immediately after verifying each eligible recruiter, it sends a blank LinkedIn invitation before researching the next candidate. There is no end-of-run queue or wait for a batch, new opening, Apollo enrichment, arbitrary pause or extra generic confirmation within the authorized scope. It checks existing connections, pending invitations, prior contact, exclusions and pauses first. No mass bot or unauthorized platform automation is included.

The 72-hour delay applies only to checking acceptance, never to sending invitations. Each confirmed send gets one acceptance check due exactly 72 hours later through a supported durable scheduler. Batch within a run without changing individual due times; deduplicate scheduling and verify setup. If scheduling or LinkedIn access is unavailable, the agent reports that limit. The local `invitation_plan.py` helper computes plans only and makes no network calls.

The check updates the same tracker to Connected, Invitation pending or Connection unknown while preserving user edits and history. It sends no messages or emails. Cold-message text stays blank until separately requested. Standalone use remains read-only unless the owner authorizes invitations.

## One continuing list

Each run updates and presents the existing list, not a new list every time. Reconcile new people and evidence into the current sheet or file, preserve user edits and previous outreach statuses, and return the same link/location with a short change summary. Create a separate list only when explicitly requested. Private exports and audit files are staging artifacts, not replacement lists.

### Profile buttons in an existing Excel tracker

Optional dependency: `python -m pip install -r requirements.txt`.

```bash
python scripts/profile_buttons.py --input /private/tracker.xlsx --output /private/tracker-staged.xlsx --sheet Recruiters --verified-profiles /private/verified-profiles.json
```

The private JSON file is an array of identity-verified direct LinkedIn `/in/` URLs. Matching cells become blue **Open profile** native hyperlinks; their actual destination remains available for deduplication and future reads. Search results and unverified profiles are not buttons. Statuses, notes and other sheets are preserved. Reopen and verify the staged workbook, then update the same tracker/Library item rather than creating a second list. CSV continues to use raw URLs. The helper neither contacts anyone nor opens a browser.

## Required location check before outreach

Each recruiter must be checked on their **full LinkedIn personal profile on every run**, not just in search results. Personal location must match the owner's configured geography. US market coverage, a US employer or a US vacancy cannot qualify a recruiter living abroad. Unknown or inaccessible locations fail closed. Keep location qualification separate from PM recruiting remit and preserve existing outreach history.

The Austin example uses `target_geography.country_codes = ["US"]`, an empty `localities` restriction (US-wide), and Austin as a preference. For a city-only scope, supply the approved normalized city values in `localities`; do not silently widen them. Preferred cities only affect prioritization, not eligibility.

Both `eligible_for_invite` and `next_candidate_action` require `target_geography`, a nonempty `current_run`, and the private `linkedin_location_check` evidence described in references/records.md. Old callers without the new inputs cannot approve an invite. Checks must be from the current run and no more than 24 hours old; the host reopens/rechecks immediately before action. A current-run label is not a substitute for that real profile inspection. These pure helpers neither browse nor send.
