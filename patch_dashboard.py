import re, shutil, sys

JSX = r"dashboard\src\StubbleDashboard.jsx"
EXP = "export_dashboard_data.py"

for f in (JSX, EXP):
    shutil.copy(f, f + ".bak")          # backups, delete later

s = open(JSX, encoding="utf-8").read()
if "GEO.lon" in s:
    sys.exit("Dashboard already patched.")

def rep(old, new):
    global s
    if s.count(old) != 1:
        sys.exit(f"Could not find expected text (found {s.count(old)}x): {old[:70]!r}")
    s = s.replace(old, new)

rep("title: 'Fewer fires, similar smog'", "title: 'Fewer fires, not less smog'")
rep('<Line yAxisId="pm" type="monotone" dataKey="meanPm"', '<Line yAxisId="pm" type="linear" dataKey="meanPm"')
rep("domain={[-0.1, 0.4]} width={36} />",
    "domain={[-0.1, 0.4]} ticks={[-0.1, 0, 0.1, 0.2, 0.3, 0.4]} tickFormatter={(v) => v.toFixed(1)} width={44} />")
rep("domain={[-0.1, 0.2]} width={36} />",
    "domain={[-0.1, 0.2]} ticks={[-0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2]} tickFormatter={(v) => v.toFixed(2)} width={44} />")
rep("const SEASONS = [2022, 2023, 2024, 2025];\n",
"""const SEASONS = [2022, 2023, 2024, 2025];
const DELHI = [{ longitude: 77.21, latitude: 28.61 }];
const _lons = [...HOTSPOTS.map(h => h.longitude), DELHI[0].longitude];
const _lats = [...HOTSPOTS.map(h => h.latitude), DELHI[0].latitude];
const GEO = {
  lon: [Math.floor(Math.min(..._lons) - 0.2), Math.ceil(Math.max(..._lons) + 0.2)],
  lat: [Math.floor(Math.min(..._lats) - 0.2), Math.ceil(Math.max(..._lats) + 0.2)],
};
""")
rep("domain={[74.3, 76.2]}", "domain={GEO.lon}")
rep("domain={[28.9, 31.6]}", "domain={GEO.lat}")
rep("""                    {hotspotFiltered.map((d, i) => <Cell key={i} fill={d.frp > 15 ? COLORS.emberDeep : COLORS.emberDim} />)}
                  </Scatter>
""", """                    {hotspotFiltered.map((d, i) => <Cell key={i} fill={d.frp > 15 ? COLORS.emberDeep : COLORS.emberDim} />)}
                  </Scatter>
                  <Scatter data={DELHI} name="Delhi" fill={COLORS.haze} />
""")
rep("High FRP means &gt; 15 MW.</Note>", "High FRP means &gt; 15 MW. The blue dot is Delhi.</Note>")
a = s.index("Each dot is one day. If fire counts alone")
b = s.index("</Note>", a)
s = s[:a] + ("Each dot is one day. Fires and smog do rise together on average, but each season sits in a different fire range: "
  "2022 days with 1,000+ fires reach about the same PM2.5 as 2025 days with a few dozen. Fire count helps track a season's ups and downs "
  "but does not set how bad the season is.") + s[b:]
open(JSX, "w", encoding="utf-8").write(s)

t = open(EXP, encoding="utf-8").read()
t = re.sub(r"^LON_RANGE.*\n", "", t, flags=re.M)
t = re.sub(r"^LAT_RANGE.*\n", "", t, flags=re.M)
t = re.sub(r'^\s*fire = fire\[fire\["longitude"\]\.between.*\n', "", t, flags=re.M)
assert "LON_RANGE" not in t and "LAT_RANGE" not in t
open(EXP, "w", encoding="utf-8").write(t)
print("Patched both files.")