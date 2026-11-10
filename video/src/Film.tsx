import React from 'react';
import {AbsoluteFill, Easing, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Opening, OPENING_LEN, C, HEAD, HAND, MONO, Note, p, cl, io} from './Opening';
import DATA from './data.json';

const LIGHT_BLUE = '#6ea4ff';
const paperBg = `radial-gradient(1400px 900px at 50% 45%, ${C.paper2} 0%, ${C.paper} 60%, #dcdce0 100%)`;
const darkBg = `radial-gradient(1400px 900px at 50% 45%, #1d1e24 0%, ${C.dark} 70%)`;

// ---------------------------------------------------------------- shared bits
const Smear: React.FC<{at: number}> = ({at}) => {
  const f = useCurrentFrame();
  if (f < at - 8 || f > at + 12) return null;
  const sm = interpolate(f, [at - 8, at + 10], [-0.4, 1.3], cl);
  return <div style={{position: 'absolute', top: -100, bottom: -100, left: `${sm * 100 - 30}%`, width: '45%', background: C.blue,
    filter: 'blur(40px)', transform: 'skewX(-12deg)', zIndex: 50}} />;
};

const Kicker: React.FC<{n: string; t: string; dark?: boolean}> = ({n, t, dark}) => {
  const f = useCurrentFrame();
  return (
    <div style={{position: 'absolute', left: 90, top: 56, display: 'flex', gap: 18, alignItems: 'baseline', opacity: p(f, 4)}}>
      <span style={{fontFamily: HEAD, fontSize: 30, color: C.blue}}>{n}</span>
      <span style={{fontFamily: HEAD, fontSize: 30, letterSpacing: 2, color: dark ? '#9a9ca3' : '#55575f'}}>{t}</span>
    </div>
  );
};

const BigHead: React.FC<{text: string; at?: number; size?: number; x?: number; y?: number; color?: string}> = ({text, at = 6, size = 92, x = 90, y = 110, color = C.ink}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{position: 'absolute', left: x, top: y, fontFamily: HEAD, fontSize: size, lineHeight: 1, color, whiteSpace: 'nowrap', letterSpacing: 1}}>
      {text.split('').map((ch, i) => {
        const s = spring({frame: f - at - i * 0.9, fps, config: {damping: 12, stiffness: 150, mass: 0.7}});
        return <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - s) * -40}px)`, opacity: Math.min(1, s * 2),
          filter: `blur(${Math.max(0, (1 - s) * 10)}px)`, minWidth: ch === ' ' ? size * 0.22 : undefined}}>{ch}</span>;
      })}
    </div>
  );
};

// ---------------------------------------------------------------- 2 · where it sits (paper, line drawing)
const Sits: React.FC = () => {
  const f = useCurrentFrame();
  const Y = 470;
  const box = (x: number, w: number, at: number, title: string, sub: string, accent = false) => {
    const t = p(f, at, 16);
    return (
      <div style={{position: 'absolute', left: x, top: Y - 90, width: w, height: 180, opacity: t, transform: `translateY(${(1 - t) * 20}px)`}}>
        <svg width={w} height={180} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          <rect x={2} y={2} width={w - 4} height={176} rx={18} fill={accent ? '#fff' : C.paper} stroke={accent ? C.blue : C.ink} strokeWidth={accent ? 4 : 2.5}
            pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p(f, at, 24)} />
        </svg>
        <div style={{position: 'absolute', left: 0, right: 0, top: 36, textAlign: 'center', fontFamily: HEAD, fontSize: 58, color: accent ? C.blue : C.ink}}>{title}</div>
        <div style={{position: 'absolute', left: 0, right: 0, top: 116, textAlign: 'center', fontFamily: HAND, fontWeight: 700, fontSize: 34, color: '#55575f'}}>{sub}</div>
      </div>
    );
  };
  const dots = [0, 1, 2, 3, 4].map((i) => {
    const st = 70 + i * 18, bad = i === 2;
    const t = interpolate(f, [st, st + 60], [0, 1], {...cl, easing: io});
    const x = bad ? 600 + (790 - 600) * Math.min(1, t * 1.6) : 600 + (1330 - 600) * t;
    const shake = bad && t > 0.62 ? Math.sin(f * 2) * Math.max(0, 1 - (t - 0.62) * 4) * 8 : 0;
    return {x: x + shake, bad, show: f > st && (bad || t < 1)};
  });
  const eps = ['Guard', 'Inspect', 'Protect', 'Extract', 'Decide', 'Fill', 'Verify', 'Compare', 'Rerank'];
  return (
    <AbsoluteFill style={{background: paperBg}}>
      <Kicker n="01" t="WHERE IT SITS" />
      <BigHead text="A GATE BEFORE AN AGENT RUNS" y={110} />
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
        {[[570, 750], [1170, 1350]].map(([a, b], i) => (
          <line key={i} x1={a} x2={b} y1={Y} y2={Y} stroke={C.ink} strokeWidth={2.5} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p(f, 40 + i * 14, 16)} />
        ))}
        <line x1={960} x2={960} y1={Y + 90} y2={720} stroke={C.blue} strokeWidth={2.5} strokeDasharray="6 8" opacity={p(f, 60)} />
        {dots.map((d, i) => d.show && <circle key={i} cx={d.x} cy={Y} r={16} fill={d.bad ? C.red : C.blue} />)}
      </svg>
      {box(150, 420, 14, 'BUILD', 'Agentic Studio · MCP repos · skills')}
      {box(750, 420, 30, 'AGENTAUDIT', 'collect · route · decide', true)}
      {box(1350, 420, 46, 'PRODUCTION', 'approved registry')}
      <div style={{position: 'absolute', left: 330, right: 330, top: 730, display: 'flex', justifyContent: 'space-between', opacity: p(f, 66)}}>
        {eps.map((e, i) => (
          <div key={e} style={{textAlign: 'center', opacity: p(f, 66 + i * 3, 10)}}>
            <div style={{width: 14, height: 14, transform: 'rotate(45deg)', background: C.blue, margin: '0 auto 10px'}} />
            <div style={{fontFamily: HEAD, fontSize: 30, color: C.ink}}>{e.toUpperCase()}</div>
          </div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 830, textAlign: 'center', fontFamily: HEAD, fontSize: 30, letterSpacing: 2, color: '#55575f', opacity: p(f, 90)}}>
        CLOCKED · NINE TYPED DECISION ENDPOINTS
      </div>
      <Note text="stopped before it ever runs" x={620} y={600} at={130} color={C.red} size={46} arrow="M150,-10 C170,-50 175,-70 172,-96" />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 3 · real walkthrough
const SRCW = 3280, SRCH = 4300;
const VW = 1760, VH = 900, VX = 80, VY = 120, S0 = VW / SRCW;
type Seg = {from: number; len: number; src: number; rate: number};
const SEGS: Seg[] = [
  {from: 0, len: 150, src: 0.2, rate: 1},      // type the command
  {from: 150, len: 110, src: 4.7, rate: 1.4},  // live scan
  {from: 260, len: 600, src: 9.75, rate: 0.05}, // the report (static)
  {from: 860, len: 90, src: 11.0, rate: 0.4},  // exit code
];
export const WALK_LEN = 950;
const CAM: [number, number, number, number][] = [
  [0, 1500, 430, 1.55], [150, 1500, 450, 1.5], [260, 1500, 460, 1.45], [300, 1500, 460, 1.5], [375, 1500, 1530, 1.4],
  [485, 1500, 1690, 1.4], [595, 1500, 2140, 1.4], [705, 1500, 2590, 1.4], [815, 1500, 2620, 1.4], [860, 1500, 3760, 1.5], [950, 1500, 3790, 1.55],
];
const cam = (f: number) => {
  const xs = CAM.map((k) => k[0]);
  const at = (i: number) => interpolate(f, xs, CAM.map((k) => k[i]), {...cl, easing: io});
  const z = at(3);
  return {cx: Math.min(at(1), VW / (2 * S0 * z) + 8), cy: at(2), z};
};
type Mark = {a: number; b: number; y0: number; y1: number; x0?: number; x1?: number; note: string; sub?: string; color?: string; dim?: number};
const MARKS: Mark[] = [
  {a: 60, b: 150, y0: 160, y1: 206, x0: 60, x1: 2120, note: 'one command · nothing from the agent is executed', sub: 'AGENTAUDIT CLI'},
  {a: 272, b: 368, y0: 424, y1: 472, x0: 60, x1: 2200, note: 'blocked before it ever runs', sub: 'CLOCKED DECIDE · GOVERNED VERDICT', color: C.red},
  {a: 382, b: 478, y0: 1452, y1: 1584, x0: 60, x1: 2600, note: 'a hidden line BCCs every payslip to an outsider', sub: 'CLOCKED GUARD · TOOL DESCRIPTION', color: C.red},
  {a: 492, b: 588, y0: 1616, y1: 1744, x0: 60, x1: 1960, note: 'its cleanup script uploads your cloud and SSH keys', sub: 'CLOCKED INSPECT · SCRIPT', color: C.red},
  {a: 602, b: 698, y0: 2096, y1: 2176, x0: 60, x1: 1700, note: "the README says it never sends data out. it does.", sub: 'CLOCKED VERIFY · README CLAIM', color: C.red},
  {a: 712, b: 852, y0: 2524, y1: 2660, x0: 60, x1: 2240, note: 'so the risky tool stays switched off', sub: 'POLICY · PER-TOOL DECISION'},
  {a: 866, b: 950, y0: 3800, y1: 3850, x0: 60, x1: 300, note: 'exit code 1: CI blocks the merge', sub: 'SAME CHECK AS A GITHUB ACTION', color: C.red, dim: 0.9},
];

const Walk: React.FC = () => {
  const f = useCurrentFrame();
  const {cx, cy, z} = cam(f);
  const s = S0 * z;
  const toScreen = (x: number, y: number) => ({x: VX + VW / 2 + (x - cx) * s, y: VY + VH / 2 + (y - cy) * s});
  const live = f >= 150 && f < 260;
  const enter = p(f, 0, 30);
  return (
    <AbsoluteFill style={{background: darkBg}}>
      <Kicker n="02" t="THE REAL PRODUCT · RECORDED, LIVE API" dark />
      <div style={{position: 'absolute', left: VX, top: VY, width: VW, height: VH, borderRadius: 20, overflow: 'hidden', background: '#1e1e2e',
        boxShadow: '0 40px 120px rgba(0,0,0,.5)', transform: `scale(${0.94 + 0.06 * enter})`, opacity: enter}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: SRCW, height: SRCH, transformOrigin: '0 0',
          transform: `translate(${VW / 2}px, ${VH / 2}px) scale(${s}) translate(${-cx}px, ${-cy}px)`}}>
          {SEGS.map((g) => (
            <Sequence key={g.from} from={g.from} durationInFrames={g.len} layout="none">
              <OffthreadVideo src={staticFile('walkthrough.mp4')} startFrom={Math.round(g.src * 30)} playbackRate={g.rate} muted
                style={{width: SRCW, height: SRCH, display: 'block'}} />
            </Sequence>
          ))}
        </div>
      </div>
      {/* highlights + notes, mapped through the camera */}
      {MARKS.map((m, i) => {
        if (f < m.a || f > m.b + 8) return null;
        const t = p(f, m.a, 12), o = 1 - p(f, m.b, 8);
        const tl = toScreen(m.x0 ?? 30, m.y0), br = toScreen(m.x1 ?? 1600, m.y1);
        const col = m.color ?? LIGHT_BLUE;
        const left = Math.max(VX + 10, tl.x - 14), top = tl.y - 8, w = Math.min(VX + VW - 10, br.x + 14) - left, h = br.y - tl.y + 16;
        const noteY = top + h + 18 + 120 > VY + VH ? top - 132 : top + h + 16;
        return (
          <div key={i} style={{position: 'absolute', inset: 0, opacity: o}}>
            <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
              <defs><mask id={`mk${i}`}><rect x={0} y={0} width={1920} height={1080} fill="#fff" />
                <rect x={left} y={top} width={w} height={h} rx={12} fill="#000" /></mask></defs>
              <rect x={VX} y={VY} width={VW} height={VH} rx={20} fill="#0b0c10" opacity={t * (m.dim ?? 0.6)} mask={`url(#mk${i})`} />
              <rect x={left} y={top} width={w} height={h} rx={12} fill={`${col}14`} stroke={col} strokeWidth={3.5}
                pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
            </svg>
            <div style={{position: 'absolute', left: Math.min(left + 10, 1300), top: noteY, fontFamily: HAND, fontWeight: 700, fontSize: 50, color: col,
              transform: `rotate(-2deg) translateY(${(1 - t) * 10}px)`, opacity: t, whiteSpace: 'nowrap',
              background: '#121318f2', padding: '6px 22px 10px', borderRadius: 14, boxShadow: '0 10px 30px rgba(0,0,0,.5)', fontSize: 60}}>
              {m.note}
              {m.sub && <div style={{fontFamily: HEAD, fontSize: 24, letterSpacing: 2, color: '#9a9ca3', marginTop: -2, transform: 'rotate(2deg)'}}>{m.sub}</div>}
            </div>
          </div>
        );
      })}
      {live && (
        <div style={{position: 'absolute', right: 110, top: 150, display: 'flex', alignItems: 'center', gap: 14, padding: '12px 22px', borderRadius: 999,
          background: '#0e0f13dd', border: `1.5px solid ${C.blue}`}}>
          <div style={{width: 14, height: 14, borderRadius: 7, background: C.red, opacity: 0.5 + 0.5 * Math.sin(f / 3)}} />
          <span style={{fontFamily: HEAD, fontSize: 30, color: '#fff', letterSpacing: 2}}>LIVE · CALLING CLOCKED</span>
          <span style={{fontFamily: MONO, fontSize: 22, color: '#9a9ca3'}}>{Math.round(15 * Math.min(1, (f - 150) / 105))} / 15 calls</span>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 4 · benchmarks, drawn on paper
type Pt = {fpr: number; tpr: number};
const thin = (pts: Pt[], n = 180) => pts.filter((_, i) => i % Math.max(1, Math.floor(pts.length / n)) === 0 || i === pts.length - 1);

const Axes: React.FC<{x: number; y: number; w: number; h: number; xl: string; yl: string; at: number; ticks?: number[]}> = ({x, y, w, h, xl, yl, at, ticks = [0, 0.5, 1]}) => {
  const f = useCurrentFrame();
  const t = p(f, at, 20);
  return (
    <g>
      {[0.25, 0.5, 0.75].map((v) => <line key={v} x1={x + v * w} x2={x + v * w} y1={y} y2={y + h} stroke={C.ink} strokeOpacity={0.07 * t} />)}
      {[0.25, 0.5, 0.75].map((v) => <line key={'h' + v} x1={x} x2={x + w} y1={y + h - v * h} y2={y + h - v * h} stroke={C.ink} strokeOpacity={0.07 * t} />)}
      <path d={`M${x},${y} L${x},${y + h} L${x + w},${y + h}`} fill="none" stroke={C.ink} strokeWidth={2.5} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} />
      {ticks.map((v) => (
        <g key={v} opacity={t}>
          <text x={x + v * w} y={y + h + 34} fontFamily={MONO} fontSize={20} fill="#55575f" textAnchor="middle">{v}</text>
          <text x={x - 16} y={y + h - v * h + 7} fontFamily={MONO} fontSize={20} fill="#55575f" textAnchor="end">{v}</text>
        </g>
      ))}
      <text x={x + w} y={y + h + 70} fontFamily={HAND} fontWeight={700} fontSize={34} fill="#55575f" textAnchor="end" opacity={t}>{xl}</text>
      <text x={x - 10} y={y - 20} fontFamily={HAND} fontWeight={700} fontSize={34} fill="#55575f" opacity={t}>{yl}</text>
    </g>
  );
};

const Roc: React.FC = () => {
  const f = useCurrentFrame();
  const roc = (DATA as any).roc.test;
  const op = roc.operating_points;
  const X = 230, Y = 300, W = 640, H = 600;
  const sx = (v: number) => X + v * W, sy = (v: number) => Y + H - v * H;
  const styleOf = (arm: string) => arm.includes('AgentAudit') ? {c: C.blue, w: 5, d: ''} : arm.includes('Clocked') ? {c: C.ink, w: 3, d: ''} : {c: '#a5a7ae', w: 2.5, d: '8 8'};
  const from = op['Clocked default verdict'], to = op['AgentAudit frozen (consensus)'];
  const mv = interpolate(f, [110, 150], [0, 1], {...cl, easing: io});
  const cur = {fpr: from.fpr + (to.fpr - from.fpr) * mv, tpr: from.tpr + (to.tpr - from.tpr) * mv};
  return (
    <AbsoluteFill style={{background: paperBg}}>
      <Kicker n="03" t="BENCHMARKS · HELD-OUT DATA" />
      <BigHead text="SAME GUARD MODEL. 12× FEWER FALSE ALARMS." size={78} />
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
        <Axes x={X} y={Y} w={W} h={H} xl="false alarms →" yl="attacks caught" at={8} />
        {roc.curves.map((c: any, i: number) => {
          const st = styleOf(c.arm);
          const d = 'M' + thin(c.points).map((q: Pt) => `${sx(q.fpr).toFixed(1)},${sy(q.tpr).toFixed(1)}`).join(' L');
          const t = p(f, 20 + i * 10, 36);
          return <path key={c.arm} d={d} fill="none" stroke={st.c} strokeWidth={st.w} strokeDasharray={st.d || '1 1'} pathLength={st.d ? undefined : 1}
            strokeDashoffset={st.d ? 0 : 1 - t} opacity={st.d ? t : 1} strokeLinejoin="round" />;
        })}
        <circle cx={sx(from.fpr)} cy={sy(from.tpr)} r={16} fill="none" stroke={C.red} strokeWidth={3} opacity={p(f, 90)} />
        {f > 95 && <circle cx={sx(cur.fpr)} cy={sy(cur.tpr)} r={15} fill={C.blue} />}
        {f > 110 && f < 150 && [6, 4, 2].map((g) => {
          const m2 = interpolate(f - g, [110, 150], [0, 1], {...cl, easing: io});
          return <circle key={g} cx={sx(from.fpr + (to.fpr - from.fpr) * m2)} cy={sy(from.tpr + (to.tpr - from.tpr) * m2)} r={15} fill="none" stroke={C.blue} strokeWidth={2} opacity={0.5} />;
        })}
      </svg>
      <Note text="Clocked Guard as shipped" x={sx(0.36)} y={sy(0.86)} at={40} color={C.ink} size={36} />
      <Note text="free DeBERTa classifiers" x={sx(0.4)} y={sy(0.62)} at={56} color="#8a8c94" size={34} />
      <Note text="as shipped: 25.9% false alarms" x={1010} y={420} at={92} color={C.red} size={56} strike={150} />
      <Note text="with AgentAudit: 2.2% ✓" x={1010} y={520} at={150} color={C.blue} size={70} />
      <Note text="attacks caught: 95.6% → 97.4%" x={1010} y={640} at={168} color="#55575f" size={44} />
      <div style={{position: 'absolute', left: 1010, top: 760, width: 800, fontFamily: MONO, fontSize: 22, color: '#55575f', lineHeight: 1.6, opacity: p(f, 175)}}>
        MCPTox tool poisoning · held-out test n = 253, split by server<br />same rows for every arm · McNemar p = 1.9 × 10⁻⁷
      </div>
    </AbsoluteFill>
  );
};

const Skills: React.FC = () => {
  const f = useCurrentFrame();
  const arms: [string, number, number, number, boolean][] = [
    ['Guard, as shipped', 55.2, 52.3, 58.6, false], ['Inspect, as shipped', 72.9, 67.4, 78.6, false],
    ['Extract → Decide check', 88.2, 83.6, 92.5, true], ['AgentAudit pipeline', 88.6, 84.4, 93.0, true],
  ];
  const x0 = 760, x1 = 1760, sx = (v: number) => x0 + (v - 50) / 50 * (x1 - x0);
  return (
    <AbsoluteFill style={{background: paperBg}}>
      <Kicker n="03" t="BENCHMARKS · REAL MALWARE CAMPAIGN" />
      <BigHead text="MALWARE WRITTEN AS PROSE, CAUGHT." size={84} />
      <div style={{position: 'absolute', left: 90, top: 300, fontFamily: HEAD, lineHeight: 1}}>
        <div style={{fontSize: 60, color: '#8a8c94'}}>MALICIOUS SKILLS CAUGHT</div>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 30, marginTop: 20}}>
          <span style={{position: 'relative', fontSize: 170, color: '#8a8c94'}}>48%
            <span style={{position: 'absolute', left: -8, top: '52%', height: 9, background: C.red, width: `${p(f, 70, 10) * 108}%`, borderRadius: 4}} /></span>
          <span style={{fontSize: 230, color: C.blue, opacity: p(f, 78)}}>{Math.round(48 + 33 * p(f, 78, 26))}%</span>
        </div>
      </div>
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
        {[50, 75, 100].map((v) => (
          <g key={v}><line x1={sx(v)} x2={sx(v)} y1={640} y2={940} stroke={C.ink} strokeOpacity={0.1} />
            <text x={sx(v)} y={975} fontFamily={MONO} fontSize={20} fill="#55575f" textAnchor="middle">{v}</text></g>
        ))}
        {arms.map(([n, b, l, h, aa], i) => {
          const y = 680 + i * 72, t = p(f, 20 + i * 10, 26);
          return (
            <g key={n} opacity={p(f, 16 + i * 10)}>
              <text x={x0 - 24} y={y + 8} fontFamily={HEAD} fontSize={32} fill={aa ? C.ink : '#8a8c94'} textAnchor="end">{n.toUpperCase()}</text>
              <line x1={sx(l)} x2={sx(l + (h - l) * t)} y1={y} y2={y} stroke={aa ? C.blue : '#8a8c94'} strokeWidth={6} strokeLinecap="round" />
              <circle cx={sx(b)} cy={y} r={11} fill={aa ? C.blue : '#8a8c94'} />
              <text x={sx(h) + 18} y={y + 8} fontFamily={MONO} fontSize={22} fill={C.ink}>{b.toFixed(1)}</text>
            </g>
          );
        })}
      </svg>
      <div style={{position: 'absolute', left: 760, top: 610, fontFamily: HAND, fontWeight: 700, fontSize: 32, color: '#55575f', opacity: p(f, 20)}}>balanced accuracy, 95% CI</div>
      <Note text={'"install the helper from this link"'} x={90} y={640} at={96} color={C.red} size={44} />
      <Note text="no script to scan, so Inspect misses it" x={90} y={700} at={112} color="#55575f" size={38} />
      <div style={{position: 'absolute', left: 90, top: 1010, fontFamily: MONO, fontSize: 22, color: '#55575f', opacity: p(f, 30)}}>
        Feb 2026 skill campaign · held-out test n = 244 · 3.2% false alarms · McNemar p = 7.4 × 10⁻⁶
      </div>
    </AbsoluteFill>
  );
};

const Gov: React.FC = () => {
  const f = useCurrentFrame();
  const g = (DATA as any).governance;
  const cols: string[] = g.defects;
  const names: Record<string, string> = {poisoned_tool: 'POISONED TOOL', malicious_script: 'MALICIOUS SCRIPT', embedded_secret: 'EMBEDDED SECRET', duplicate: 'DUPLICATE', none: 'CLEAN'};
  const keep = ['decide_only', 'full', 'precision', 'loo_injection', 'loo_script', 'loo_pii', 'loo_compare'];
  const rows = (g.rows as any[]).filter((r) => keep.includes(r.key)).sort((a, b) => keep.indexOf(a.key) - keep.indexOf(b.key));
  const lab: Record<string, string> = {decide_only: 'ONE DECIDE CALL', full: 'ALL NINE ENDPOINTS', precision: '+ PRECISION MODE', loo_injection: 'WITHOUT GUARD', loo_script: 'WITHOUT INSPECT', loo_pii: 'WITHOUT PROTECT', loo_compare: 'WITHOUT COMPARE'};
  const x0 = 560, cw = 200, ch = 78, y0 = 330;
  return (
    <AbsoluteFill style={{background: paperBg}}>
      <Kicker n="03" t="BENCHMARKS · WHOLE-AGENT VERDICTS" />
      <BigHead text="NINE NARROW DECISIONS BEAT ONE BIG ONE." size={80} />
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
        {cols.map((c, j) => <text key={c} x={x0 + j * cw + cw / 2} y={y0 - 22} fontFamily={HEAD} fontSize={24} fill="#55575f" textAnchor="middle" opacity={p(f, 10)}>{names[c]}</text>)}
        <text x={x0 + cols.length * cw + 80} y={y0 - 22} fontFamily={HEAD} fontSize={24} fill="#55575f" textAnchor="middle" opacity={p(f, 10)}>CORRECT</text>
        {rows.map((r, i) => {
          const key = r.key === 'full' || r.key === 'precision';
          return (
            <g key={r.key} opacity={p(f, 14 + i * 7)}>
              <text x={x0 - 28} y={y0 + i * ch + 48} fontFamily={HEAD} fontSize={32} fill={key ? C.ink : '#8a8c94'} textAnchor="end">{lab[r.key]}</text>
              {cols.map((c, j) => {
                const [a, b] = r.cells[c]; const v = a / b, zero = a === 0;
                return (
                  <g key={c}>
                    <rect x={x0 + j * cw + 6} y={y0 + i * ch + 6} width={cw - 12} height={ch - 12} rx={10}
                      fill={zero ? 'none' : C.blue} fillOpacity={0.12 + 0.8 * v} stroke={zero ? C.red : 'none'} strokeWidth={4} />
                    <text x={x0 + j * cw + cw / 2} y={y0 + i * ch + 48} fontFamily={MONO} fontSize={24} fontWeight={700}
                      fill={zero ? C.red : v > 0.55 ? '#fff' : C.ink} textAnchor="middle">{a}/{b}</text>
                  </g>
                );
              })}
              <text x={x0 + cols.length * cw + 80} y={y0 + i * ch + 50} fontFamily={HEAD} fontSize={38} fill={key ? C.blue : '#8a8c94'} textAnchor="middle">{r.acc.toFixed(1)}%</text>
            </g>
          );
        })}
      </svg>
      <Note text="remove one endpoint, its defect gets through" x={1080} y={y0 + 7 * ch + 18} at={80} color={C.red} size={42} arrow="M-20,-6 C-90,-30 -260,-70 -350,-120" />
      <div style={{position: 'absolute', left: 90, top: 1010, fontFamily: MONO, fontSize: 22, color: '#55575f', opacity: p(f, 30)}}>
        38 held-out agents built from real MCP servers · cells: correct verdicts / agents with that defect
      </div>
    </AbsoluteFill>
  );
};

const Jev: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: paperBg, alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
      <Kicker n="03" t="BENCHMARKS · HARNESS CHECK" />
      <div style={{fontFamily: HEAD, fontSize: 260, lineHeight: 1, color: C.ink, opacity: p(f, 4), transform: `scale(${0.96 + 0.04 * p(f, 4)})`}}>
        {Math.round(507 * p(f, 4, 30))}<span style={{color: '#8a8c94'}}> / 868</span>
      </div>
      <div style={{fontFamily: HAND, fontWeight: 700, fontSize: 56, color: C.blue, marginTop: 10, opacity: p(f, 30)}}>our harness reproduces Clocked's own benchmark, exactly</div>
      <div style={{fontFamily: MONO, fontSize: 22, color: '#55575f', marginTop: 30, opacity: p(f, 40)}}>jev-benchmark · 868 engineering decisions · Jev 1.13: 508</div>
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const word = 'AGENTAUDIT';
  const dot = spring({frame: f - 24, fps, config: {damping: 9, stiffness: 150, mass: 0.7}});
  return (
    <AbsoluteFill style={{background: paperBg, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'flex-end', fontFamily: HEAD, fontSize: 260, lineHeight: 1, color: C.ink, letterSpacing: 2}}>
        {word.split('').map((ch, i) => {
          const s = spring({frame: f - 2 - i * 1.4, fps, config: {damping: 12, stiffness: 150, mass: 0.7}});
          return <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - s) * -60}px)`, opacity: Math.min(1, s * 2),
            filter: `blur(${Math.max(0, (1 - s) * 12)}px)`}}>{ch}</span>;
        })}
        <span style={{display: 'inline-block', width: 64, height: 64, borderRadius: 32, background: C.blue, marginLeft: 14, marginBottom: 22,
          transform: `scale(${dot}) translateY(${(1 - Math.min(1, dot)) * -200}px)`}} />
      </div>
      <div style={{fontFamily: HAND, fontWeight: 700, fontSize: 50, color: '#55575f', marginTop: 30, opacity: p(f, 30)}}>a gate for AI agents, built on all nine Clocked endpoints</div>
      <div style={{fontFamily: MONO, fontSize: 30, color: C.ink, marginTop: 24, opacity: p(f, 40)}}>github.com/Himanshu-Sangshetti/agentaudit</div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- assembly
const PARTS: {c: React.FC; len: number}[] = [
  {c: Opening, len: OPENING_LEN}, {c: Sits, len: 210}, {c: Walk, len: WALK_LEN},
  {c: Roc, len: 240}, {c: Skills, len: 180}, {c: Gov, len: 210}, {c: Jev, len: 100}, {c: End, len: 150},
];
export const FILM_LEN = PARTS.reduce((a, x) => a + x.len, 0);

export const Film: React.FC = () => {
  let from = 0;
  const starts: number[] = [];
  return (
    <AbsoluteFill style={{background: C.dark}}>
      {PARTS.map((part, i) => {
        starts.push(from);
        const el = (
          <Sequence key={i} from={from} durationInFrames={part.len}>
            <part.c />
          </Sequence>
        );
        from += part.len;
        return el;
      })}
      {/* smear on every light/dark change */}
      <Smear at={starts[1]} /><Smear at={starts[2]} /><Smear at={starts[3]} />
    </AbsoluteFill>
  );
};
