# Discovery sources and sequence

## Inputs before crawling

Prefer an existing application tracker, target-employer list, or authorized export/search results from a job platform. Normalize company labels while preserving source names and known aliases. Historical applications establish interest, not current hiring. Include companies without a current vacancy when the user wants relationship-building. Do not require named recruiters on postings.

For each run, record scope, source access, date and a query/time budget. Stop at the user's requested coverage or budget; report remaining work. Expand queries when results are thin, not by silently loosening the career level or location.

## First: people search at target employers

Use an authorized people-search interface, search-engine index, or user-supplied export. Search current company plus recruiting titles: recruiter, technical recruiter, talent acquisition, talent partner, sourcer. Run locally and without recruiter-location restrictions. Someone outside the city can cover its roles.

Example public-index queries (replace the example values):
- site:linkedin.com/in "Example Software" "recruiter" "Austin"
- site:linkedin.com/in "Example Software" "talent acquisition"
- site:linkedin.com/in "Example Software" "talent partner"

Keep broad company recruiting contacts. Product, design, engineering and R&D coverage can raise priority; explicit sales-only or executive-only remits may lower it or exclude it according to the user's targets. Do not assume technical recruiting includes product management.

## Second: specialist searches across companies

- site:linkedin.com/in "product management" "recruiter" "Austin"
- site:linkedin.com/in "product recruiting" "Texas"
- site:linkedin.com/posts "product manager" "Austin" "hiring"

Follow the original author, not a reposter. A general technical recruiter may have actual PM-hiring evidence even without product in their title. A past hiring post establishes experience, not a currently open mandate.

## Third: agency directories and team pages

Useful starting points, not exhaustive or guaranteed-current databases:
- Relancer: https://relancer.com/product-management-recruiters-in-austin-texas
- US product directory: https://relancer.com/product-management-recruiters-in-united-states
- i-Recruit specialty directory: https://www.i-recruit.com/speciality/product-management-recruiters

Directories may target employers buying recruiting services. “Available” can mean a recruiter accepts client work, not that they have vacancies for candidates. Use firm entries to discover named consultants through their official team pages. Check levels served; do not bias a first-line manager search toward executive-only firms.

## Optional scale and contact tools

Apollo people search supports company/title/location filters; it can discover recruiting employees and enrich qualified contacts. LinkedIn Sales Navigator supports saved people/company searches. These are optional, potentially paid adapters, not required dependencies. Do not wait for Apollo/enrichment or a new vacancy before sending an already authorized blank invitation to a verified eligible recruiter. Verify current account access, limits, cost and export/API permissions before use. Never promise a paid feature from a free account.

- Apollo filters: https://knowledge.apollo.io/hc/en-us/articles/4412665755661-Use-Search-Filters-to-Find-Prospects
- Apollo pricing: https://www.apollo.io/pricing
- Sales Navigator: https://business.linkedin.com/sell/sales-navigator/compare-plans

## Verification and practical limits

For each person separately check identity, current employer, recruiting function, market coverage, product relevance and career-level relevance. Save a short supporting excerpt and source/date for each important claim. “No evidence found” is different from “does not recruit product.”

Search indexes are incomplete and stale. Operators may not constrain results perfectly. Relative dates in snippets are unreliable, and old roles can match current queries. If direct profile access is blocked, do not bypass it or label the record live-verified. Preserve indexed evidence and leave the necessary check open.

Respect access restrictions, platform terms and rate limits. Use authorized search/API access or manual review. LinkedIn rules prohibit unauthorized scraping and automated activity:
- https://www.linkedin.com/legal/user-agreement
- https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions

Prefer a small pilot before scaling: compare distinct relevant people, ambiguous records and checking effort for each source. Treat any observed yield as a result for that sample, not an exhaustive coverage claim.


## Manage the verification bottleneck

Generate a reusable query plan, but execute a small diverse batch before expanding every company/title combination. Record each query's execution status using the ledger in records.md. For authorized invitation runs, verify and immediately invite each eligible person before researching the next; never accumulate verified eligible people into a later send queue. If a search surfaces more leads than can be checked within the budget, retain only the unverified backlog, clearly labeled incomplete, and process it one person at a time. Research-only runs can retain a verification backlog without sending. Report which verification dimensions remain unknown; a completed search is not a verified shortlist.
