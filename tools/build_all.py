# Build the artifact page and the GitHub Pages copy from one template.
# usage: python3 -I build_all.py <template> <mapbits.json> <artifact_out.html> <repo_dir> <dump_listings_dir> <meta.json>
import json, glob, os, sys
tpl, bits, art, repo, dump, metaf = sys.argv[1:7]
status_dir = sys.argv[7] if len(sys.argv) > 7 else ""
runs_dir = sys.argv[8] if len(sys.argv) > 8 else ""
import datetime
BUILT = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
s = open(tpl).read(); b = json.load(open(bits))
DROP = {"Chinatown", "FiDi", "Castro", "Haight", "Presidio"}
s = s.replace("<!--__SFMAP__-->", b["svg"])
s = s.replace("/*__HOODS__*/", json.dumps(b["hoods"], separators=(",", ":")))
s = s.replace("/*__LABELS__*/", json.dumps([l for l in b["labels"] if l[0] not in DROP]))
s = s.replace("/*__PROJ__*/", json.dumps(b["proj"]))
s = s.replace("/*__BUILT__*/", BUILT)
open(art, "w").write(s)
rows = []
for f in sorted(glob.glob(os.path.join(dump, "*.json"))):
    d = json.load(open(f)); d = d.get("data", d); d["id"] = os.path.basename(f)[:-5]; rows.append(d)
os.makedirs(os.path.join(repo, "data"), exist_ok=True)
json.dump(rows, open(os.path.join(repo, "data", "listings.json"), "w"), indent=1)
m = json.load(open(metaf)); m = m.get("data", m)
json.dump({"lastRun": m.get("lastRun", ""), "summary": m.get("summary", "")}, open(os.path.join(repo, "data", "meta.json"), "w"))
st = {}
if status_dir and os.path.isdir(status_dir):
    for f in sorted(glob.glob(os.path.join(status_dir, "*.json"))):
        d = json.load(open(f)); st[os.path.basename(f)[:-5]] = d.get("data", d)
json.dump(st, open(os.path.join(repo, "data", "status.json"), "w"), indent=1)
runs = []
if runs_dir and os.path.isdir(runs_dir):
    for f in glob.glob(os.path.join(runs_dir, "*.json")):
        d = json.load(open(f)); runs.append(d.get("data", d))
runs.sort(key=lambda r: r.get("at", ""), reverse=True)
json.dump(runs, open(os.path.join(repo, "data", "runs.json"), "w"), indent=1)
i = s.index("</style>") + len("</style>")
html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="description" content="San Francisco apartments with a Dec 15 to Feb 1 move-in: 1BR+, 600+ sq ft, laundry, under $6,000.">\n'
        + s[:i] +
        '\n<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}img{max-width:100%}[hidden]{display:none!important}'
        ':root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
        '</head>\n<body>' + s[i:] + '\n</body>\n</html>\n')
open(os.path.join(repo, "index.html"), "w").write(html)
print(len(rows), "listings;", len(s), "bytes")
