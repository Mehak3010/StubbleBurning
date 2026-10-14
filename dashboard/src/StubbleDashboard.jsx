import React, { useState, useMemo } from 'react';
import { BarChart, Bar, LineChart, Line, Area, ComposedChart, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Label, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { Flame, Wind, Activity, TrendingUp, AlertTriangle, Radio, Map, BrainCircuit, ClipboardList, Gauge } from 'lucide-react';
import { DAILY, GRID } from './data';
import { STATES } from './geo';

// Fire -> PM2.5 lag correlations (Phase 1 method, corrected data; from stubble_pm25_model.py)
const LAG_CORR = [
  { lag: 0, corr: 0.3741 }, { lag: 1, corr: 0.3542 }, { lag: 2, corr: 0.3001 }, { lag: 3, corr: 0.2542 },
  { lag: 4, corr: 0.2028 }, { lag: 5, corr: 0.1747 }, { lag: 6, corr: 0.1760 }, { lag: 7, corr: 0.2065 },
];

// Phase 2 results (from stubble_pm25_phase2_v2.py and _v3.py, leave-one-season-out, mean R2)
const ABLATION = [
  { name: 'Calendar only', r2: 0.276 },
  { name: '+ fires', r2: 0.275 },
  { name: '+ weather', r2: 0.179 },
  { name: '+ fires + weather', r2: 0.257 },
];
const ANOMALY = [
  { name: 'Fires only', r2: -0.030 },
  { name: 'Weather only', r2: 0.133 },
  { name: 'Fires + weather', r2: 0.139 },
];

const COLORS = {
  canvas: '#12141A', panel: '#1B1F27', panel2: '#222834', hair: '#2E3440',
  ember: '#FF6A3D', emberDeep: '#C43E1C', emberDim: 'rgba(255,106,61,0.18)',
  haze: '#5FA8C4', hazeDim: 'rgba(95,168,196,0.18)',
  text: '#EDE9E0', textMute: '#8A8F99', textDim: '#5C616B',
  good: '#7FBF6F', moderate: '#F2C94C', poor: '#F2994A', severe: '#EB5757', hazardous: '#8C2F26',
};
const SEASON_COLORS = { 2022: COLORS.ember, 2023: COLORS.moderate, 2024: COLORS.haze, 2025: COLORS.good };

const mono = "'SF Mono', 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace";
const sans = "'Inter', ui-sans-serif, -apple-system, BlinkMacSystemFont, sans-serif";

const WEATHER_VARS = [
  { key: 'align', label: 'Wind from Punjab/Haryana (m/s, + = toward Delhi)' },
  { key: 'wind', label: 'Wind speed (m/s)' },
  { key: 'temp', label: 'Temperature (\u00b0C)' },
  { key: 'rh', label: 'Humidity (%)' },
  { key: 'blh', label: 'Boundary layer height (m)' },
].filter(v => DAILY.some(d => d[v.key] != null));

const SEASONS = [2022, 2023, 2024, 2025];
const DELHI = { name: 'Delhi', lon: 77.21, lat: 28.61 };
const BOX = { lon0: 74.5, lon1: 76.0, lat0: 29.0, lat1: 31.5 };
const MAP = { lon0: 73.8, lon1: 77.6, lat0: 28.3, lat1: 32.0 };
const MAP_K = 150;                                        // px per degree of latitude
const MAP_KX = Math.cos((30 * Math.PI) / 180) * MAP_K;    // aspect-corrected px per degree of longitude
const mapX = (lon) => (lon - MAP.lon0) * MAP_KX;
const mapY = (lat) => (MAP.lat1 - lat) * MAP_K;
const MAP_W = (MAP.lon1 - MAP.lon0) * MAP_KX;
const MAP_H = (MAP.lat1 - MAP.lat0) * MAP_K;
const ringPath = (ring) => ring.map(([lon, lat], i) => `${i ? 'L' : 'M'}${mapX(lon).toFixed(1)},${mapY(lat).toFixed(1)}`).join('') + 'Z';
const statePath = (s) => s.rings.map(ringPath).join('');
const STATE_LABELS = [
  { t: 'PUNJAB', lon: 76.08, lat: 31.2, focus: true },
  { t: 'HARYANA', lon: 76.25, lat: 29.3, focus: true },
  { t: 'RAJASTHAN', lon: 73.85, lat: 28.6, focus: false },
  { t: 'HIMACHAL', lon: 76.7, lat: 31.9, focus: false },
  { t: 'PAKISTAN', lon: 73.85, lat: 31.3, focus: false },
];
const CITIES = [
  { name: 'Ferozepur', lon: 74.61, lat: 30.92, inside: true },
  { name: 'Bathinda', lon: 74.95, lat: 30.21, inside: true },
  { name: 'Ludhiana', lon: 75.85, lat: 30.90, inside: true },
  { name: 'Sangrur', lon: 75.84, lat: 30.25, inside: true },
  { name: 'Sirsa', lon: 75.02, lat: 29.53, inside: true },
  { name: 'Hisar', lon: 75.72, lat: 29.15, inside: true },
  { name: 'Amritsar', lon: 74.87, lat: 31.63, inside: false },
  { name: 'Chandigarh', lon: 76.78, lat: 30.73, inside: false },
  { name: 'Karnal', lon: 76.99, lat: 29.69, inside: false },
];

function MapLabel({ x, y, children, fill, size = 11, anchor = 'start', weight = 400 }) {
  const common = { x, y, fontSize: size, fontFamily: mono, fontWeight: weight, textAnchor: anchor };
  return (
    <g>
      <text {...common} fill="none" stroke={COLORS.canvas} strokeWidth="3.5" strokeLinejoin="round">{children}</text>
      <text {...common} fill={fill}>{children}</text>
    </g>
  );
}
const mean = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0);

const SEASON_STATS = SEASONS.map((y) => {
  const d = DAILY.filter(r => r.season === y);
  const pm = d.filter(r => r.avg_pm25 != null).map(r => r.avg_pm25);
  const total = d.reduce((s, r) => s + r.fire_count, 0);
  return { season: String(y), total, perDay: Math.round(total / Math.max(d.length, 1)), meanPm: Math.round(mean(pm) * 10) / 10 };
});

function aqiColor(pm25) {
  if (pm25 <= 60) return COLORS.good;
  if (pm25 <= 90) return COLORS.moderate;
  if (pm25 <= 120) return COLORS.poor;
  if (pm25 <= 250) return COLORS.severe;
  return COLORS.hazardous;
}
function aqiLabel(pm25) {
  if (pm25 <= 60) return 'Satisfactory';
  if (pm25 <= 90) return 'Moderate';
  if (pm25 <= 120) return 'Poor';
  if (pm25 <= 250) return 'Very poor';
  return 'Severe';
}

function Bracket({ children }) {
  const c = `2px solid ${COLORS.ember}`;
  const corner = (pos) => <div style={{ position: 'absolute', width: 18, height: 18, ...pos }} />;
  return (
    <div style={{ position: 'relative', padding: '18px 20px' }}>
      {corner({ top: 0, left: 0, borderTop: c, borderLeft: c })}
      {corner({ top: 0, right: 0, borderTop: c, borderRight: c })}
      {corner({ bottom: 0, left: 0, borderBottom: c, borderLeft: c })}
      {corner({ bottom: 0, right: 0, borderBottom: c, borderRight: c })}
      {children}
    </div>
  );
}

function KpiCard({ icon: Icon, label, value, sub, accent }) {
  return (
    <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.hair}`, borderRadius: 4, padding: '16px 18px', flex: '1 1 200px', minWidth: 180 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
        <Icon size={12} color={accent || COLORS.textMute} />
        <span style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.07em', color: COLORS.textMute, textTransform: 'uppercase' }}>{label}</span>
      </div>
      <div style={{ fontFamily: mono, fontSize: 28, fontWeight: 600, color: COLORS.text, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontFamily: sans, fontSize: 11, color: COLORS.textDim, marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function SectionLabel({ eyebrow, title }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontFamily: mono, fontSize: 11, letterSpacing: '0.1em', color: COLORS.ember, textTransform: 'uppercase', marginBottom: 4 }}>{eyebrow}</div>
      <div style={{ fontFamily: sans, fontSize: 18, fontWeight: 600, color: COLORS.text }}>{title}</div>
    </div>
  );
}

function Note({ children }) {
  return <div style={{ fontFamily: sans, fontSize: 13, color: COLORS.textMute, marginTop: 10, lineHeight: 1.5 }}>{children}</div>;
}

function CustomTooltip({ active, payload, label, formatter }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{ background: COLORS.panel2, border: `1px solid ${COLORS.hair}`, borderRadius: 4, padding: '8px 12px', fontFamily: mono, fontSize: 12 }}>
      <div style={{ color: COLORS.textMute, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || COLORS.text }}>
          {p.name}: {formatter ? formatter(p.value, p.name) : p.value}
        </div>
      ))}
    </div>
  );
}

function SeasonButtons({ season, setSeason }) {
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {['all', ...SEASONS].map(s => {
        const on = season === String(s);
        return (
          <button key={s} onClick={() => setSeason(String(s))}
            style={{
              fontFamily: mono, fontSize: 12, padding: '6px 14px', borderRadius: 4, cursor: 'pointer',
              background: on ? COLORS.ember : 'transparent', color: on ? '#1A0D08' : COLORS.textMute,
              border: `1px solid ${on ? COLORS.ember : COLORS.hair}`, fontWeight: on ? 600 : 400,
            }}>
            {s === 'all' ? 'ALL' : s}
          </button>
        );
      })}
    </div>
  );
}

const panel = { background: COLORS.panel, border: `1px solid ${COLORS.hair}`, borderRadius: 4, padding: '18px 20px' };
const axisTick = { fill: COLORS.textMute, fontSize: 11, fontFamily: mono };

const CARDS = [
  { id: 'signal', label: 'Signal', icon: Radio, eyebrow: 'Fire vs smog', title: 'How fire activity and PM2.5 line up over time' },
  { id: 'trends', label: 'Trends', icon: Activity, eyebrow: 'Season explorer', title: 'Fire activity, PM2.5 and weather' },
  { id: 'seasons', label: 'Seasons', icon: TrendingUp, eyebrow: 'Season comparison', title: 'Fewer fires, not less smog' },
  { id: 'geo', label: 'Geography', icon: Map, eyebrow: 'Where the fires are', title: 'Fire hotspots in the study box' },
  { id: 'models', label: 'Models', icon: BrainCircuit, eyebrow: 'What predicts what', title: 'What fire counts add beyond season and weather' },
  { id: 'scatter', label: 'Explorer', icon: Gauge, eyebrow: 'Day by day', title: 'Fire count vs PM2.5, every day' },
];

export default function StubbleDashboard() {
  const [season, setSeason] = useState('all');
  const [cardIdx, setCardIdx] = useState(0);
  const [weatherKey, setWeatherKey] = useState(WEATHER_VARS.length ? WEATHER_VARS[0].key : null);
  const activeCard = CARDS[cardIdx];

  const seasonData = useMemo(
    () => (season === 'all' ? DAILY : DAILY.filter(d => d.season === Number(season))),
    [season]
  );
  const gridCells = useMemo(() => {
    // plain object, not Map: 'Map' is the lucide icon imported at the top of this file
    const acc = {};
    for (const [yr, lon, lat, n] of GRID) {
      if (season !== 'all' && yr !== Number(season)) continue;
      const k = `${lon}|${lat}`;
      acc[k] = (acc[k] || 0) + n;
    }
    return Object.entries(acc).map(([k, n]) => {
      const [lon, lat] = k.split('|').map(Number);
      return { lon, lat, n };
    });
  }, [season]);
  const gridMax = useMemo(() => Math.max(1, ...gridCells.map(c => c.n)), [gridCells]);
  const gridTotal = useMemo(() => gridCells.reduce((s, c) => s + c.n, 0), [gridCells]);
  const scatterBySeason = useMemo(
    () => SEASONS.map(y => ({
      year: y,
      points: DAILY.filter(d => d.season === y && d.avg_pm25 != null)
        .map(d => ({ date: d.date, fires: d.fire_count, x: d.fire_count + 1, y: d.avg_pm25 })),
    })),
    []
  );

  const totalFires = useMemo(() => DAILY.reduce((s, d) => s + d.fire_count, 0), []);
  const peakDay = useMemo(() => {
    const valid = DAILY.filter(d => d.avg_pm25 != null);
    return valid.reduce((a, b) => (b.avg_pm25 > a.avg_pm25 ? b : a), valid[0]);
  }, []);
  const s22 = SEASON_STATS.find(s => s.season === '2022');
  const s25 = SEASON_STATS.find(s => s.season === '2025');
  const fireDrop = s22 && s25 && s22.total > 0 ? Math.round((1 - s25.total / s22.total) * 100) : null;
  const weatherMeta = WEATHER_VARS.find(v => v.key === weatherKey);

  return (
    <div style={{ background: COLORS.canvas, minHeight: '100vh', padding: '32px 24px 64px', fontFamily: sans, color: COLORS.text }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 28, borderBottom: `1px solid ${COLORS.hair}`, paddingBottom: 20 }}>
          <div>
            <div style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.1em', color: COLORS.haze, textTransform: 'uppercase', marginBottom: 4 }}>
              NASA FIRMS VIIRS &middot; OPENAQ PM2.5 &middot; OPEN-METEO &middot; STUDY BOX 74.5&ndash;76.0&deg;E, 29.0&ndash;31.5&deg;N &rarr; DELHI-NCR
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>Stubble burning &rarr; Delhi smog</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: mono, fontSize: 10, color: COLORS.good, border: `1px solid ${COLORS.hair}`, borderRadius: 4, padding: '4px 10px' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: COLORS.good, display: 'inline-block' }} />
            4 SEASONS &middot; OCT&ndash;NOV 2022&ndash;2025
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
          <KpiCard icon={Flame} label="Fires detected" value={totalFires.toLocaleString()} sub="NOAA-20 detections in study box, Oct-Nov" accent={COLORS.ember} />
          <KpiCard icon={AlertTriangle} label="Peak PM2.5 day" value={`${Math.round(peakDay.avg_pm25)}`} sub={`${peakDay.date} \u00b7 ${aqiLabel(peakDay.avg_pm25)}`} accent={aqiColor(peakDay.avg_pm25)} />
          <KpiCard icon={Wind} label="Same-day correlation" value={LAG_CORR[0].corr.toFixed(2)} sub="Fire count vs Delhi PM2.5" accent={COLORS.haze} />
          <KpiCard icon={TrendingUp} label="2025 vs 2022 fires" value={fireDrop == null ? 'n/a' : `\u2212${fireDrop}%`} sub="Delhi's smog did not fall with it" accent={COLORS.ember} />
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
          {CARDS.map((c, i) => {
            const Icon = c.icon;
            const active = i === cardIdx;
            return (
              <button key={c.id} onClick={() => setCardIdx(i)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7, fontFamily: mono, fontSize: 12,
                  padding: '8px 14px', borderRadius: 4, cursor: 'pointer',
                  background: active ? COLORS.ember : COLORS.panel, color: active ? '#1A0D08' : COLORS.textMute,
                  border: `1px solid ${active ? COLORS.ember : COLORS.hair}`, fontWeight: active ? 600 : 400,
                }}>
                <Icon size={13} />
                {c.label}
              </button>
            );
          })}
        </div>

        {/* Signal */}
        {activeCard.id === 'signal' && (
          <div style={{ marginBottom: 14 }}>
            <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
            <Bracket>
              <div style={{ fontFamily: mono, fontSize: 12, color: COLORS.textMute, marginBottom: 4 }}>CORRELATION BETWEEN FIRE ACTIVITY AND DELHI PM2.5, BY DAYS OF LAG</div>
              <div style={{ fontFamily: sans, fontSize: 11, color: COLORS.textDim, marginBottom: 8 }}>
                Each bar correlates fire activity on a given day with Delhi's PM2.5 that many days later. Taller = stronger link.
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={LAG_CORR} margin={{ top: 10, right: 10, left: 10, bottom: 22 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                  <XAxis dataKey="lag" tickFormatter={v => (v === 0 ? 'Same day' : `+${v}d`)} tick={axisTick} axisLine={{ stroke: COLORS.hair }} tickLine={false}>
                    <Label value="DAYS AFTER THE FIRE" position="bottom" offset={4} style={{ fill: COLORS.textDim, fontFamily: mono, fontSize: 10, letterSpacing: '0.06em' }} />
                  </XAxis>
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} domain={[0, 0.6]}>
                    <Label value="CORRELATION" angle={-90} position="insideLeft" offset={10} style={{ fill: COLORS.textDim, fontFamily: mono, fontSize: 10, textAnchor: 'middle' }} />
                  </YAxis>
                  <Tooltip content={<CustomTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Bar dataKey="corr" name="Correlation" radius={[3, 3, 0, 0]}>
                    {LAG_CORR.map((d, i) => <Cell key={i} fill={i === 0 ? COLORS.ember : COLORS.emberDim} stroke={i === 0 ? COLORS.ember : 'transparent'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <Note>
                Fire activity and PM2.5 are positively correlated, strongest same-day and decaying over about a week. Daily data cannot resolve a specific smoke-transport time, and part of this link reflects both series rising through the Oct&ndash;Nov season. The Models tab separates the two.
              </Note>
            </Bracket>
          </div>
        )}

        {/* Trends */}
        {activeCard.id === 'trends' && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
              <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
              <SeasonButtons season={season} setSeason={setSeason} />
            </div>
            <div style={panel}>
              <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 8 }}>FIRE COUNT (LEFT AXIS) &middot; PM2.5 (RIGHT AXIS)</div>
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={seasonData} margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="fireGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={COLORS.ember} stopOpacity={0.45} />
                      <stop offset="100%" stopColor={COLORS.ember} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: COLORS.textMute, fontSize: 9, fontFamily: mono }} axisLine={{ stroke: COLORS.hair }} tickLine={false}
                    interval={Math.max(Math.floor(seasonData.length / 8), 0)} />
                  <YAxis yAxisId="fire" tick={{ fill: COLORS.ember, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} width={36} />
                  <YAxis yAxisId="pm25" orientation="right" tick={{ fill: COLORS.haze, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} width={36} />
                  <ReferenceLine yAxisId="pm25" y={250} stroke={COLORS.hazardous} strokeDasharray="3 3" strokeOpacity={0.6} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area yAxisId="fire" type="monotone" dataKey="fire_count" name="Fires" stroke={COLORS.ember} fill="url(#fireGrad)" strokeWidth={1.5} />
                  <Line yAxisId="pm25" type="monotone" dataKey="avg_pm25" name="PM2.5" stroke={COLORS.haze} strokeWidth={2} dot={false} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
              <div style={{ fontFamily: sans, fontSize: 11, color: COLORS.textDim, marginTop: 6 }}>
                Dashed line: CPCB &ldquo;severe&rdquo; PM2.5 threshold (250 &micro;g/m&sup3;). Axes are scaled independently, so compare shapes, not heights.
              </div>

              {WEATHER_VARS.length > 0 && (
                <div style={{ marginTop: 20, borderTop: `1px solid ${COLORS.hair}`, paddingTop: 14 }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                    {WEATHER_VARS.map(v => {
                      const on = v.key === weatherKey;
                      return (
                        <button key={v.key} onClick={() => setWeatherKey(v.key)}
                          style={{ fontFamily: mono, fontSize: 11, padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
                            background: on ? COLORS.haze : 'transparent', color: on ? '#0B1A20' : COLORS.textMute,
                            border: `1px solid ${on ? COLORS.haze : COLORS.hair}` }}>
                          {v.label.split(' (')[0]}
                        </button>
                      );
                    })}
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 6 }}>{weatherMeta ? weatherMeta.label.toUpperCase() : ''} &middot; DELHI, DAILY MEAN</div>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={seasonData} margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                      <XAxis dataKey="date" tick={{ fill: COLORS.textMute, fontSize: 9, fontFamily: mono }} axisLine={{ stroke: COLORS.hair }} tickLine={false}
                        interval={Math.max(Math.floor(seasonData.length / 8), 0)} />
                      <YAxis tick={axisTick} axisLine={false} tickLine={false} width={36} />
                      {weatherKey === 'align' && <ReferenceLine y={0} stroke={COLORS.hair} />}
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey={weatherKey} name={weatherMeta ? weatherMeta.label.split(' (')[0] : ''} stroke={COLORS.haze} strokeWidth={1.8} dot={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Seasons */}
        {activeCard.id === 'seasons' && (
          <div style={{ marginBottom: 14 }}>
            <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
            <div style={panel}>
              <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 8 }}>AVERAGE FIRES PER DAY (BARS) &middot; MEAN DELHI PM2.5 (LINE)</div>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={SEASON_STATS} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                  <XAxis dataKey="season" tick={axisTick} axisLine={{ stroke: COLORS.hair }} tickLine={false} />
                  <YAxis yAxisId="fire" tick={{ fill: COLORS.ember, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} width={40} />
                  <YAxis yAxisId="pm" orientation="right" domain={[0, 250]} tick={{ fill: COLORS.haze, fontSize: 10, fontFamily: mono }} axisLine={false} tickLine={false} width={36} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Bar yAxisId="fire" dataKey="perDay" name="Fires/day" fill={COLORS.emberDim} stroke={COLORS.ember} radius={[3, 3, 0, 0]} />
                  <Line yAxisId="pm" type="linear" dataKey="meanPm" name="Mean PM2.5" stroke={COLORS.haze} strokeWidth={2.5} dot={{ r: 5, fill: COLORS.haze }} />
                </ComposedChart>
              </ResponsiveContainer>
              <div style={{ overflowX: 'auto', marginTop: 14 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: mono, fontSize: 12 }}>
                  <thead>
                    <tr style={{ color: COLORS.textMute, textAlign: 'right' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 400 }}>SEASON</th>
                      <th style={{ padding: '6px 8px', fontWeight: 400 }}>TOTAL FIRES</th>
                      <th style={{ padding: '6px 8px', fontWeight: 400 }}>FIRES / DAY</th>
                      <th style={{ padding: '6px 8px', fontWeight: 400 }}>MEAN PM2.5</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SEASON_STATS.map(s => (
                      <tr key={s.season} style={{ borderTop: `1px solid ${COLORS.hair}`, textAlign: 'right' }}>
                        <td style={{ textAlign: 'left', padding: '6px 8px', color: COLORS.text }}>{s.season}</td>
                        <td style={{ padding: '6px 8px', color: COLORS.ember }}>{Math.round(s.total).toLocaleString()}</td>
                        <td style={{ padding: '6px 8px', color: COLORS.ember }}>{s.perDay.toLocaleString()}</td>
                        <td style={{ padding: '6px 8px', color: COLORS.haze }}>{s.meanPm}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Note>
                Fire counts in the study box fell sharply from 2022 to 2025, but Delhi's season-average PM2.5 did not follow. Four seasons is a small sample, and this does not show that fires don't matter, only that fire volume alone doesn't set how bad a season is. Weather, local emissions and Diwali all play a part.
              </Note>
            </div>
          </div>
        )}

        {/* Geography */}
        {activeCard.id === 'geo' && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
              <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
              <SeasonButtons season={season} setSeason={setSeason} />
            </div>
            <div style={{ ...panel, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 28, alignItems: 'center' }}>
              <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} role="img" aria-label="Density map of fire detections in the study box"
                style={{ width: '100%', maxWidth: 520, height: 'auto', margin: '0 auto', display: 'block', background: COLORS.canvas, border: `1px solid ${COLORS.hair}`, borderRadius: 4 }}>
                {STATES.filter(s => s.kind === 'context').map(s => (
                  <path key={s.name} d={statePath(s)} fill={COLORS.panel} stroke={COLORS.hair} strokeWidth="1" />
                ))}
                {STATES.filter(s => s.kind === 'focus').map(s => (
                  <path key={s.name} d={statePath(s)} fill={COLORS.panel2} stroke={COLORS.textDim} strokeWidth="1.2" />
                ))}
                {[75, 76, 77].map(l => (
                  <g key={`lon${l}`}>
                    <line x1={mapX(l)} x2={mapX(l)} y1={0} y2={MAP_H} stroke={COLORS.hair} strokeDasharray="2 5" />
                    <text x={mapX(l) + 4} y={MAP_H - 6} fontSize="11" fontFamily={mono} fill={COLORS.textDim}>{l}&deg;E</text>
                  </g>
                ))}
                {[29, 30, 31].map(l => (
                  <g key={`lat${l}`}>
                    <line x1={0} x2={MAP_W} y1={mapY(l)} y2={mapY(l)} stroke={COLORS.hair} strokeDasharray="2 5" />
                    <text x={6} y={mapY(l) - 5} fontSize="11" fontFamily={mono} fill={COLORS.textDim}>{l}&deg;N</text>
                  </g>
                ))}
                {gridCells.map(c => {
                  const t = Math.sqrt(c.n / gridMax);
                  return (
                    <rect key={`${c.lon}|${c.lat}`} x={mapX(c.lon)} y={mapY(c.lat + 0.1)} width={MAP_KX * 0.1 + 0.4} height={MAP_K * 0.1 + 0.4}
                      fill={COLORS.ember} fillOpacity={0.1 + 0.9 * t}>
                      <title>{`${c.n.toLocaleString()} detections`}</title>
                    </rect>
                  );
                })}
                <rect x={mapX(BOX.lon0)} y={mapY(BOX.lat1)} width={mapX(BOX.lon1) - mapX(BOX.lon0)} height={mapY(BOX.lat0) - mapY(BOX.lat1)}
                  fill="none" stroke={COLORS.ember} strokeWidth="1.5" strokeDasharray="6 4" />
                <text x={mapX(BOX.lon0)} y={mapY(BOX.lat1) - 8} fontSize="11" fontFamily={mono} fill={COLORS.ember} letterSpacing="1">STUDY BOX</text>
                {STATE_LABELS.map(l => (
                  <MapLabel key={l.t} x={mapX(l.lon)} y={mapY(l.lat)} size={12} weight={600} fill={l.focus ? COLORS.textMute : COLORS.textDim}>{l.t}</MapLabel>
                ))}
                {CITIES.map(c => (
                  <g key={c.name}>
                    <circle cx={mapX(c.lon)} cy={mapY(c.lat)} r="3.5" fill={c.inside ? COLORS.text : COLORS.textMute} fillOpacity={c.inside ? 1 : 0.6} stroke={COLORS.canvas} strokeWidth="1" />
                    <MapLabel x={mapX(c.lon) + 7} y={mapY(c.lat) + 4} fill={c.inside ? COLORS.text : COLORS.textMute}>{c.name}</MapLabel>
                  </g>
                ))}
                <circle cx={mapX(DELHI.lon)} cy={mapY(DELHI.lat)} r="6" fill={COLORS.haze} stroke={COLORS.canvas} strokeWidth="1.5" />
                <MapLabel x={mapX(DELHI.lon) - 10} y={mapY(DELHI.lat) + 4} anchor="end" size={12} weight={700} fill={COLORS.haze}>Delhi</MapLabel>
              </svg>

              <div>
                <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, letterSpacing: '0.06em', marginBottom: 8 }}>NOAA-20 DETECTIONS PER 0.1&deg; CELL (ABOUT 10 KM)</div>
                <div style={{ height: 10, borderRadius: 2, background: `linear-gradient(to right, rgba(255,106,61,0.1), ${COLORS.ember})`, border: `1px solid ${COLORS.hair}` }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 10, color: COLORS.textDim, marginTop: 4 }}>
                  <span>0</span><span>{gridMax.toLocaleString()}</span>
                </div>
                <div style={{ fontFamily: sans, fontSize: 11, color: COLORS.textDim, marginTop: 6 }}>Colour is scaled to the busiest cell in the selected season(s).</div>
                <div style={{ marginTop: 20, fontFamily: mono, fontSize: 12, color: COLORS.textMute, lineHeight: 1.9 }}>
                  <div><span style={{ color: COLORS.ember }}>BOX</span> 74.5&ndash;76.0&deg;E, 29.0&ndash;31.5&deg;N</div>
                  <div><span style={{ color: COLORS.ember }}>SHOWN</span> {gridTotal.toLocaleString()} detections</div>
                </div>
                <Note>By area, the study box is roughly two-thirds Punjab, a quarter Haryana and about 9% north-west Rajasthan. Northern Punjab (Amritsar) and eastern Haryana (Karnal) lie outside it, so counts understate regional burning. Bright city labels are inside the box, dim ones outside. State outlines: Natural Earth.</Note>
              </div>
            </div>
          </div>
        )}

        {/* Models */}
        {activeCard.id === 'models' && (
          <div style={{ marginBottom: 14 }}>
            <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
              <div style={panel}>
                <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 8 }}>PREDICTING PM2.5, HOLDING OUT ONE SEASON (MEAN R&sup2;)</div>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={ABLATION} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: COLORS.textMute, fontSize: 10, fontFamily: mono }} axisLine={{ stroke: COLORS.hair }} tickLine={false} interval={0} />
                    <YAxis tick={axisTick} axisLine={false} tickLine={false} domain={[-0.1, 0.4]} ticks={[-0.1, 0, 0.1, 0.2, 0.3, 0.4]} tickFormatter={(v) => v.toFixed(1)} width={44} />
                    <ReferenceLine y={0} stroke={COLORS.hair} />
                    <Tooltip content={<CustomTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="r2" name="R²" radius={[3, 3, 0, 0]}>
                      {ABLATION.map((d, i) => <Cell key={i} fill={i === 0 ? COLORS.textDim : COLORS.ember} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <Note>Calendar baseline = day of season, Diwali window, weekend. Adding fire counts does not improve on it.</Note>
              </div>
              <div style={panel}>
                <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 8 }}>DAY-TO-DAY SWINGS WITHIN A SEASON (MEAN R&sup2;)</div>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={ANOMALY} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: COLORS.textMute, fontSize: 10, fontFamily: mono }} axisLine={{ stroke: COLORS.hair }} tickLine={false} interval={0} />
                    <YAxis tick={axisTick} axisLine={false} tickLine={false} domain={[-0.1, 0.2]} ticks={[-0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2]} tickFormatter={(v) => v.toFixed(2)} width={44} />
                    <ReferenceLine y={0} stroke={COLORS.hair} />
                    <Tooltip content={<CustomTooltip formatter={(v) => v.toFixed(3)} />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <Bar dataKey="r2" name="R²" radius={[3, 3, 0, 0]}>
                      {ANOMALY.map((d, i) => <Cell key={i} fill={i === 0 ? COLORS.ember : COLORS.haze} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <Note>After removing each season's Oct&ndash;Nov ramp, weather explains more of the day-to-day swings than fire counts do.</Note>
              </div>
            </div>
            <div style={{ ...panel, marginTop: 20 }}>
              <div style={{ fontFamily: sans, fontSize: 13, color: COLORS.textMute, lineHeight: 1.6 }}>
                <strong style={{ color: COLORS.text }}>Reading this carefully.</strong> Same-day fire anomalies correlate with PM2.5 anomalies at about r&nbsp;=&nbsp;0.31 (95% block-bootstrap interval 0.13&ndash;0.47); 3-day and 7-day versions are weaker and their intervals include zero. This does not show that stubble burning doesn't matter. Daily satellite fire counts are a crude proxy for smoke reaching Delhi: they ignore where fires are, how big they are, which way the wind blows, and the time of day of the satellite pass. The study box covers only part of the burning region, and four seasons is a small sample. Full details are in <code>PHASE2_FINDINGS.md</code>.
              </div>
            </div>
          </div>
        )}

        {/* Explorer */}
        {activeCard.id === 'scatter' && (
          <div style={{ marginBottom: 14 }}>
            <SectionLabel eyebrow={activeCard.eyebrow} title={activeCard.title} />
            <div style={panel}>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontFamily: mono, fontSize: 11, color: COLORS.textMute, marginBottom: 8 }}>
                {SEASONS.map(y => (
                  <span key={y}><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: SEASON_COLORS[y], marginRight: 6 }} />{y}</span>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 10, right: 24, left: 8, bottom: 26 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={COLORS.hair} />
                  <XAxis type="number" dataKey="x" scale="log" domain={[1, 4001]} ticks={[1, 11, 101, 1001]} tickFormatter={(v) => Math.round(v - 1).toLocaleString()}
                    tick={axisTick} axisLine={{ stroke: COLORS.hair }} tickLine={false} allowDataOverflow>
                    <Label value="FIRES THAT DAY (LOG SCALE)" position="bottom" offset={6} style={{ fill: COLORS.textDim, fontFamily: mono, fontSize: 10, letterSpacing: '0.06em' }} />
                  </XAxis>
                  <YAxis type="number" dataKey="y" tick={axisTick} axisLine={false} tickLine={false} width={44}>
                    <Label value="PM2.5" angle={-90} position="insideLeft" style={{ fill: COLORS.textDim, fontFamily: mono, fontSize: 10, textAnchor: 'middle' }} />
                  </YAxis>
                  <Tooltip cursor={{ strokeDasharray: '3 3', stroke: COLORS.hair }}
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const p = payload[0].payload;
                      return (
                        <div style={{ background: COLORS.panel2, border: `1px solid ${COLORS.hair}`, borderRadius: 4, padding: '8px 12px', fontFamily: mono, fontSize: 12 }}>
                          <div style={{ color: COLORS.textMute, marginBottom: 4 }}>{p.date}</div>
                          <div style={{ color: COLORS.ember }}>Fires: {Math.round(p.fires).toLocaleString()}</div>
                          <div style={{ color: COLORS.haze }}>PM2.5: {Math.round(p.y)}</div>
                        </div>
                      );
                    }} />
                  {scatterBySeason.map(s => (
                    <Scatter key={s.year} name={String(s.year)} data={s.points} fill={SEASON_COLORS[s.year]} fillOpacity={0.7} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
              <Note>
                Each dot is one day. Fires and smog do rise together on average, but each season sits in a different fire range: 2022 days with 1,000+ fires reach about the same PM2.5 as 2025 days with a few dozen. Fire count helps track a season's ups and downs but does not set how bad the season is.</Note>
            </div>
          </div>
        )}

        {/* Data log: page footer, shown under every tab */}
        <div style={{ marginTop: 40, borderTop: `1px solid ${COLORS.hair}`, paddingTop: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
            <ClipboardList size={12} color={COLORS.ember} />
            <span style={{ fontFamily: mono, fontSize: 11, letterSpacing: '0.1em', color: COLORS.ember, textTransform: 'uppercase' }}>Data log &middot; methodology</span>
          </div>
          <div style={{ fontFamily: mono, fontSize: 11, color: COLORS.textDim, lineHeight: 2, wordBreak: 'break-word' }}>
            <div><span style={{ color: COLORS.ember }}>[dedup]</span> fire_archive_J1V-C2_785706 / 785707 (2024) were identical &mdash; de-duplicated to one copy (7,997 detections).</div>
            <div><span style={{ color: COLORS.ember }}>[area]</span> detections cover a box of 74.5&ndash;76.0&deg;E, 29.0&ndash;31.5&deg;N (approximately central/western Punjab and part of north-west Haryana). Northern Punjab and eastern Haryana are not covered, so counts understate regional burning.</div>
            <div><span style={{ color: COLORS.ember }}>[source]</span> NOAA-20 (J1V) only, all four seasons, so counts are comparable year to year.</div>
            <div><span style={{ color: COLORS.ember }}>[verified]</span> 2025 fires (3,430) are 57% below 2024 &mdash; in line with the ~54% drop in Punjab stubble fire cases reported by PPCB.</div>
            <div><span style={{ color: COLORS.ember }}>[weather]</span> Open-Meteo daily means for Delhi, plus upwind points at Karnal and Ludhiana.</div>
            <div><span style={{ color: COLORS.ember }}>[method]</span> models evaluated leave-one-season-out; see PHASE1_FINDINGS.md and PHASE2_FINDINGS.md in the repository.</div>
            <div><span style={{ color: COLORS.ember }}>[caveat]</span> PM2.5 is an average across Delhi-NCR sensors; daily fire counts are a rough proxy for smoke exposure.</div>
          </div>
        </div>

      </div>
    </div>
  );
}