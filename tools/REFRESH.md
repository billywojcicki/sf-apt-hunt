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

Listing fields: `a` address or title, `h` neighborhood label, `t` tier (1 top, 2 also good or farther out, 3 SoMa/Rincon/South Beach/Mission Bay), `bd`, `ba`, `sf` (number or null), `r` rent (number or null), `l` laundry (`unit`, `bldg`, `?`), `p` parking text, `pk` boolean, `av` availability as the listing says it, `ad` ISO move-in date (`""` if unknown; "now" means today), `src`, `u` URL, `n` short note in plain sentences, `f` flags (`verify`, `edge`), `img` photo URL, `lat`, `lng`, `mh` map neighborhood, `posted`, `updated` (ISO dates when the source shows them), `updNote`, `firstSeen`, `lastSeen`, `gone`, `back` (`{on, was, why}` when a passed or taken-down listing returns; see step 3).

Write only facts seen on the page. No em dashes, no emojis.

## Criteria

- Move-in Dec 15, 2026 to Feb 1, 2027 is the window. Record listings with no date too (the page groups them). Skip anything clearly starting before Dec 15 unless it's a watchlist building.
- 1BR or bigger (2BR is a bonus), 600+ sq ft, laundry in unit or building, rent up to $6,000.
- Included areas: North Beach, Telegraph Hill, Russian Hill, Marina, Cow Hollow, Pacific Heights, Lower Pac Heights, Nob Hill north of Bush, Hayes Valley west of Gough, NoPa, Alamo Square, Japantown, Presidio Heights, Laurel Heights, Lower Haight, Cole Valley, Duboce Triangle, Castro, Noe Valley, Dolores Heights, Mission west of Valencia, Potrero Hill, Dogpatch, Inner Richmond, Inner Sunset, Bernal Heights, Glen Park, and (lower priority) SoMa south of Folsom, Rincon Hill, South Beach, Mission Bay.
- Excluded: Tenderloin, Civic Center, Mid-Market, 6th St, Tendernob (south of Bush, east of Larkin), Hayes Valley east of Gough, 16th St and 24th St BART plazas, Mission St corridor, Union Square, FiDi, Chinatown, Haight St strip, outer neighborhoods, anything outside SF (Craigslist often labels Mill Valley and Oakland posts as SF areas). Watchlist buildings are the exception.
- Likely scams: rent far under market (a 1BR under about $3,000 in a tier 1 area), form links on suspiciously cheap units. Leave them out.

## Being polite to sites

- If the Claude app's browser on the user's computer is reachable (`mcp__remote-devices__Claude_Browser__*` tools present and answering), use it for Craigslist, Zumper, Apartments.com and SightMap, fetching with `fetch()` from a page on the same site. The scheduled run usually happens in the cloud while the computer sleeps; then use WebFetch for everything, and for SightMap pages that need scripts, log them as `partial`.
- Wait 3 to 5 seconds between page loads. Craigslist: at most 6 search pages and 40 posting pages a day. Apartments.com: at most 15 pages. Zumper: at most 12.
- Stop using a site at its first block (403, 429, "Your request has been blocked", a CAPTCHA or "Access denied" page). Log it as `blocked` and move on. Never try to get around a block or solve a CAPTCHA.
- If a source only works in the browser and the computer can't be reached, log it as `skipped` with "computer asleep" and carry on.

## Steps

1. Read the current data: `listings`, `status`, `runs` (ArtifactData list with `out_dir`). Build a set of known URLs and Craigslist post ids.
2. Craigslist: search `https://sfbay.craigslist.org/search/sfc/apa?max_price=6000&min_bedrooms=1` (plus `&minSqft=600` and laundry filters, and queries like `january`, `december`). Parse `li.cl-static-search-result`. Open only new posts in included areas. From each post read the attributes line (beds, baths, ft2, "available <date>", laundry, parking), `.mapaddress`, the posted and updated times (`time.date`, `.postinginfo`), and the first photo URL.
   - Skip post ids already in `tools/cl_seen.json`, and add every id you saw this run to it before leaving the Craigslist page (navigating away loses the page's variables).
   - Always record `posted` (the post's first `time` in `.postinginfos`, as YYYY-MM-DD) and `updated` (the last one, if different) on every new listing, and refresh both when a known listing is reposted. For other sources, record the listed date whenever the page shows one. The card shows it as "Listed <date> (N days ago)".
   - Always read the whole `#postingbody`, never a trimmed excerpt. Move-in dates are often only in the description ("Available now" in a bullet list, "Move in date: Jan 1", "ready mid-December"). Scan it for avail, move-in, ready, vacant, now, immediately, month names and dates like 1/15. If the description's date differs from the attributes line, use the description and say so in the note.
   - For J. Wavro posts, also open the linked jwavro.com rental page; it shows "Available Now" or a date even when the post doesn't.
3. Watch for comebacks. Every listing the user passed on (status `pass`) or that went `gone` stays watched, whatever its date:
   - Match each new Craigslist or site post against those listings by address, or within about 40 m by lat/lng with the same beds. Reposts get new post ids, so don't rely on the URL.
   - When one is reposted, update the existing doc instead of adding a new one: new `u`, `ad`, `av`, `r`, `posted`, `lastSeen`, `gone: false`.
   - Set `back: {on: <today>, was: <old ad or "">, why: "<short reason, e.g. Relisted on Craigslist>"}` only when it's a real comeback: the new move-in date is later than the old one, or it now falls Dec 15 to Feb 1, or a taken-down listing returns with no date. A plain repost with the same or an earlier date gets no `back`.
   - Never touch the `status` doc. The page shows it in a "Back on the market" section until the user passes on it again.
   - Put every comeback first in the run summary and the final message.
4. Recheck known listings: every in-window or no-date listing daily, everything else on Mondays and Thursdays. A 404 or 410, or a "deleted" or "expired" page, means `gone: true`. Otherwise set `lastSeen` to today and fix rent or date if they changed.
5. Watchlist buildings (always check):
   - Chorus, 30 Otis St: open `https://sightmap.com/embed/0n9w6r13w71`, find the `/app/api/v1/.../sightmaps/<id>` request in `performance.getEntriesByType('resource')`, fetch it, and read `data.units` (`unit_number`, `area`, `display_price`, `available_on`) with bedrooms from `data.floor_plans`.
   - The Brady, 1 Brady St: SightMap code `jlw0nexgp2y` (same method as Chorus; gives unit dates and prices).
   - 1598 Bay St (Marina, mostly owner-held condos at Bay and Octavia): search Craigslist for `1598 bay` and check https://sfhighrises.com/building/1598-bay/ for rentals. Keep the `1598-bay-st` doc's note and `lastSeen` current; add any real unit as its own listing.
   - Mission Bay market-rate rentals (use each building's own leasing page; if it embeds SightMap, use the method above):
     - Avalon at Mission Bay, 255 King St and 240 Berry St: https://www.avaloncommunities.com/california/san-francisco-apartments/avalon-at-mission-bay (add `?furnished=false&moveInDate=12%2F15%2F2026&leaseTerm=12` to a unit URL and read the page text for the quote)
     - Channel Mission Bay, 185 Channel St: https://www.udr.com/san-francisco-bay-area-apartments/san-francisco/channel-mission-bay/apartments-pricing/
     - Edgewater, 355 Berry St: https://www.udr.com/san-francisco-bay-area-apartments/san-francisco/edgewater/apartments-pricing/
     - Mission Bay by Windsor, 360 Berry St: https://www.windsorcommunities.com/properties/mission-bay-by-windsor/floorplans/ (page text in the browser lists units, dates and total price)
     - Strata, 1201 4th St: SightMap `dzlpodl9wg4`
     - Venue, 1155 4th St: SightMap `910pd5yyw2z`
     - MB360, 1200 4th St: from an essexapartmenthomes.com page, fetch `/api/properties/513956/availability?start_date=2026-12-15&end_date=2027-02-01&format=spa` and read `result.floorplans[].units[]` (`name`, `beds`, `sqft`, `minimum_rent`, `availability_date`)
     - Azure, 690 Long Bridge St: https://www.equityapartments.com/san-francisco-bay/mission-bay/azure-apartments
     - The Canyon at Mission Rock, 1023 3rd St, and Verde at Mission Rock, 1070 Bridgeview Way: Greystar dropped them (links redirect) as of Oct 11. Log `failed` unless a new leasing site turns up.
   - Mission Bay condo buildings have no leasing office. Catch their units through Craigslist and Zumper by address: The Beacon (250 to 260 King St), Arterra (300 to 310 Berry St), Park Terrace (325 Berry St), 235 and 255 Berry St, Radiance (330 Mission Bay Blvd N), Madrone (420 to 480 Mission Bay Blvd N), Arden (708 to 738 Long Bridge St), One Mission Bay (1000 3rd St and 110 Channel St), Glassworks (207 King St).
   - Skip income-restricted and university housing (Five 88, 1180 4th St, Edwin M. Lee, Crescent Cove, Rich Sorro, Mission Creek Senior, HomeRise, UCSF housing).
   - For each building keep one listing doc (`src` "Building site (watchlist)") whose note lists the best-fitting units and the latest start date seen. If a unit fits the criteria and starts Dec 15 to Feb 1, also add it as its own listing.
6. Greystar SF search `https://www.greystar.com/s/san-francisco-ca` and building pages (unit dates and 12-month prices). J. Wavro listings. RentSFNow `/apartments/?city=san-francisco&bedrooms=1&view=list` (Veritas units are mostly under 600 ft²).
7. Zumper neighborhood pages for the included areas, newest first, for listings with an available date in the window.
8. Apartments.com only if the last run wasn't blocked there: the watchlist buildings' pages first.
9. New listings: geocode with `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=<address>, San Francisco, CA` (one request per second, through the browser or WebFetch; the shell can't reach it), then set `mh` by point-in-polygon against `tools/hood_rings.json`.
10. Write all changes with ArtifactData batch (50 writes max per batch, pin `if_version` on existing docs). Write the run doc with every source's status and a one-line detail, and update `meta/run`.
11. Build and deploy:
   - Dump `listings`, `status`, `runs` and `meta` with ArtifactData list `out_dir`.
   - `python3 -I tools/build_all.py tools/page_template.html tools/mapbits.json <scratch>/sf-apartment-hunt.html . <dump>/listings <dump>/meta/run.json <dump>/status <dump>/runs`
   - Read the artifact (`Artifact` action read with the URL above), then publish `<scratch>/sf-apartment-hunt.html` with that `url`. Don't pass `capabilities`.
   - Commit and push to `main`.
12. Final message: start with any comebacks ("Back on the market:"). Then, if any new listing starts Dec 15 to Feb 1, "New Dec 15 to Feb 1 move-in:" and list address, neighborhood, beds, sq ft, rent, date and link. Otherwise one line: how many new, how many gone, which sources were blocked.
