# Daily refresh playbook

The steps a scheduled run follows to update the SF apartment hunt. Keep it gentle: one run a day, few page loads, stop at the first block.

## Where things live

- Private page and database: https://claude.ai/artifact/SRXUgtG4zNVL5jfXmSYEgk (ArtifactData tool, collections below)
- Public site: this repo, deployed by GitHub Pages from `main` / root
- Build tools: `tools/page_template.html`, `tools/build_all.py`, `tools/mapbits.json`, `tools/hood_rings.json`

Database collections:

| Collection | What it holds |
|---|---|
| `listings` | One doc per listing. Fields below. |
| `status` | One doc per listing the user tracks: `want`, `sent`, `pass`, `sentOn`, `passOn`, `notes[{d,t}]`. Only the user changes these (through chat). Never edit them during a refresh. |
| `runs` | One doc per refresh: `at` (ISO UTC), `approx` (false), `title`, `summary`, `newCount`, `goneCount`, `sources[{n, st, d}]` where `st` is ok, partial, blocked, failed or skipped. |
| `meta/run` | `lastRun`, `summary` (legacy, keep updating). |

Listing fields: `a` address or title, `h` neighborhood label, `t` tier (1 top, 2 also good or farther out, 3 SoMa/Rincon/South Beach/Mission Bay), `bd`, `ba`, `sf` (number or null), `r` rent (number or null), `l` laundry (`unit`, `bldg`, `?`), `p` parking text, `pk` boolean, `av` availability as the listing says it, `ad` ISO move-in date (`""` if unknown; "now" means today), `src`, `u` URL, `n` short note in plain sentences, `f` flags (`verify`, `edge`), `img` photo URL, `lat`, `lng`, `mh` map neighborhood, `posted`, `updated` (ISO dates when the source shows them), `updNote`, `firstSeen`, `lastSeen`, `gone`.

Write only facts seen on the page. No em dashes, no emojis.

## Criteria

- Move-in Dec 15, 2026 to Feb 1, 2027 is the window. Record listings with no date too (the page groups them). Skip anything clearly starting before Dec 15 unless it's a watchlist building.
- 1BR or bigger (2BR is a bonus), 600+ sq ft, laundry in unit or building, rent up to $6,000.
- Included areas: North Beach, Telegraph Hill, Russian Hill, Marina, Cow Hollow, Pacific Heights, Lower Pac Heights, Nob Hill north of Bush, Hayes Valley west of Gough, NoPa, Alamo Square, Japantown, Presidio Heights, Laurel Heights, Lower Haight, Cole Valley, Duboce Triangle, Castro, Noe Valley, Dolores Heights, Mission west of Valencia, Potrero Hill, Dogpatch, Inner Richmond, Inner Sunset, Bernal Heights, Glen Park, and (lower priority) SoMa south of Folsom, Rincon Hill, South Beach, Mission Bay.
- Excluded: Tenderloin, Civic Center, Mid-Market, 6th St, Tendernob (south of Bush, east of Larkin), Hayes Valley east of Gough, 16th St and 24th St BART plazas, Mission St corridor, Union Square, FiDi, Chinatown, Haight St strip, outer neighborhoods, anything outside SF (Craigslist often labels Mill Valley and Oakland posts as SF areas). Watchlist buildings are the exception.
- Likely scams: rent far under market (a 1BR under about $3,000 in a tier 1 area), form links on suspiciously cheap units. Leave them out.

## Being polite to sites

- Use the Claude app's browser on the user's computer (`mcp__remote-devices__Claude_Browser__*`) for Craigslist, Zumper, Apartments.com and SightMap. Fetch with `fetch()` from a page on the same site.
- Wait 3 to 5 seconds between page loads. Craigslist: at most 6 search pages and 40 posting pages a day. Apartments.com: at most 15 pages. Zumper: at most 12.
- Stop using a site at its first block (403, 429, "Your request has been blocked", a CAPTCHA or "Access denied" page). Log it as `blocked` and move on. Never try to get around a block or solve a CAPTCHA.
- If the computer can't be reached, skip the browser sources, log them as `skipped` with "computer offline", and still do what WebFetch can (building sites, AppFolio pages).

## Steps

1. Read the current data: `listings`, `status`, `runs` (ArtifactData list with `out_dir`). Build a set of known URLs and Craigslist post ids.
2. Craigslist: search `https://sfbay.craigslist.org/search/sfc/apa?max_price=6000&min_bedrooms=1` (plus `&minSqft=600` and laundry filters, and queries like `january`, `december`). Parse `li.cl-static-search-result`. Open only new posts in included areas. From each post read the attributes line (beds, baths, ft2, "available <date>", laundry, parking), `.mapaddress`, the posted and updated times (`time.date`, `.postinginfo`), and the first photo URL.
3. Recheck known listings: every in-window or no-date listing daily, everything else on Mondays and Thursdays. A 404 or 410, or a "deleted" or "expired" page, means `gone: true`. Otherwise set `lastSeen` to today and fix rent or date if they changed.
4. Watchlist buildings (always check):
   - Chorus, 30 Otis St: open `https://sightmap.com/embed/0n9w6r13w71`, find the `/app/api/v1/.../sightmaps/<id>` request in `performance.getEntriesByType('resource')`, fetch it, and read `data.units` (`unit_number`, `area`, `display_price`, `available_on`) with bedrooms from `data.floor_plans`.
   - The Brady, 1 Brady St: `https://thebradysf.com/floorplans/` (plans, prices, units left; no dates on the page).
   - Mission Bay: Avalon at Mission Bay (255 King St), Channel Mission Bay (185 Channel St), and other Mission Bay buildings the user names. Use each building's own leasing page; if it embeds SightMap, use the method above.
   - For each building keep one listing doc (`src` "Building site (watchlist)") whose note lists the best-fitting units and the latest start date seen. If a unit fits the criteria and starts Dec 15 to Feb 1, also add it as its own listing.
5. Zumper neighborhood pages for the included areas, newest first, for listings with an available date in the window.
6. Apartments.com only if the last run wasn't blocked there: the watchlist buildings' pages first.
7. New listings: geocode with `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=<address>, San Francisco, CA` (one request per second), then set `mh` by point-in-polygon against `tools/hood_rings.json`.
8. Write all changes with ArtifactData batch (50 writes max per batch, pin `if_version` on existing docs). Write the run doc with every source's status and a one-line detail, and update `meta/run`.
9. Build and deploy:
   - Dump `listings`, `status`, `runs` and `meta` with ArtifactData list `out_dir`.
   - `python3 -I tools/build_all.py tools/page_template.html tools/mapbits.json <scratch>/sf-apartment-hunt.html . <dump>/listings <dump>/meta/run.json <dump>/status <dump>/runs`
   - Read the artifact (`Artifact` action read with the URL above), then publish `<scratch>/sf-apartment-hunt.html` with that `url`. Don't pass `capabilities`.
   - Commit and push to `main`.
10. Final message: if any new listing starts Dec 15 to Feb 1, begin with "New Dec 15 to Feb 1 move-in:" and list address, neighborhood, beds, sq ft, rent, date and link. Otherwise one line: how many new, how many gone, which sources were blocked.
