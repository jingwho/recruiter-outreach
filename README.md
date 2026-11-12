# Product Recruiter Outreach

A portable agent skill for building an evidence-backed recruiter shortlist and preparing human-reviewed outreach. Use existing employer lists and people databases instead of rebuilding a job board.

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

Installed copies do not update automatically. Review releases/commits, then pull your clean checkout or replace the installed folder with the reviewed version. Keep private configuration outside the install folder so updating does not overwrite it. No automatic monitoring, sending, or scheduled updates are included.

## Release status

Initial release: local helpers tested; live discovery quality varies by source and access. Validate the discovery workflow on a small sample and report checked versus unverified leads before scaling. Do not interpret sample results as exhaustive coverage or a guaranteed path to interviews.

See [SKILL.md](SKILL.md), [discovery](references/discovery.md), [records](references/records.md), and [outreach](references/outreach.md).
