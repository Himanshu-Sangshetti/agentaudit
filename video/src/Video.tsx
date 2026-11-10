import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {loadFont as loadSans} from '@remotion/google-fonts/Manrope';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import DATA from './data.json';

const {fontFamily: SANS} = loadSans('normal', {weights: ['400', '500', '600', '700', '800'], subsets: ['latin']});
const {fontFamily: MONO} = loadMono('normal', {weights: ['400', '500', '700'], subsets: ['latin']});

// dark pastel (matches the Catppuccin Mocha terminal in the recording)
const C = {
  bg: '#14121b', bg2: '#1a1723', panel: 'rgba(36,32,50,0.72)', line: '#332e43', ink: '#efebf7', ink2: '#aaa3bd', ink3: '#6f6884',
  lav: '#b9a8ff', peach: '#ffb3a1', mint: '#9fe3c8', butter: '#f3d68f', sky: '#a3cbff', pink: '#f5bde6',
};
const FAMILY: Record<string, string> = {clocked: C.peach, agentaudit: C.lav, baseline: C.mint};

const SCENES = [
  {id: 'intro', len: 180}, {id: 'arch', len: 420}, {id: 'walk', len: 1500},
  {id: 'roc', len: 240}, {id: 'forest', len: 270}, {id: 'skills', len: 210}, {id: 'gov', len: 240}, {id: 'jev', len: 180}, {id: 'end', len: 150},
];
export const TOTAL = SCENES.reduce((a, s) => a + s.len, 0);

const ease = Easing.bezier(0.22, 1, 0.36, 1);
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const p = (f: number, a: number, d = 18) => interpolate(f, [a, a + d], [0, 1], {...cl, easing: ease});

// ------------------------------------------------------------------ shared visual components
const GridBg: React.FC<{accent?: string}> = ({accent = C.lav}) => {
  const f = useCurrentFrame();
  const off = (f * 0.4) % 64;
  return (
    <AbsoluteFill>
      <svg width="100%" height="100%" style={{position: 'absolute', inset: 0}}>
        <defs>
          <pattern id="g" width="64" height="64" patternUnits="userSpaceOnUse" patternTransform={`translate(${off} ${off})`}>
            <path d="M64 0H0V64" fill="none" stroke="#ffffff" strokeOpacity="0.045" />
          </pattern>
          <radialGradient id="m" cx="50%" cy="45%" r="60%">
            <stop offset="0" stopColor="#fff" stopOpacity="1" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <mask id="mk"><rect width="100%" height="100%" fill="url(#m)" /></mask>
        </defs>
        <rect width="100%" height="100%" fill="url(#g)" mask="url(#mk)" />
      </svg>
      <div style={{position: 'absolute', left: `${30 + 10 * Math.sin(f / 70)}%`, top: '-20%', width: 1100, height: 900, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${accent}22, transparent)`, filter: 'blur(40px)'}} />
    </AbsoluteFill>
  );
};

// card with a rotating conic "border beam"
const BeamCard: React.FC<{w: number; h: number; children: React.ReactNode; color?: string; style?: React.CSSProperties; speed?: number}> =
  ({w, h, children, color = C.lav, style, speed = 3}) => {
    const f = useCurrentFrame();
    return (
      <div style={{position: 'relative', width: w, height: h, borderRadius: 24, padding: 1.5, overflow: 'hidden', ...style}}>
        <div style={{position: 'absolute', left: '50%', top: '50%', width: w * 2, height: w * 2, marginLeft: -w, marginTop: -w,
          background: `conic-gradient(from ${f * speed}deg, transparent 0deg, ${color} 40deg, transparent 90deg, transparent 360deg)`}} />
        <div style={{position: 'relative', width: '100%', height: '100%', borderRadius: 23, background: '#1b1825',
          boxShadow: `inset 0 0 0 1px ${C.line}`}}>{children}</div>
      </div>
    );
  };

const Kicker: React.FC<{children: React.ReactNode; at?: number; color?: string}> = ({children, at = 0, color = C.lav}) => {
  const f = useCurrentFrame();
  return <div style={{fontSize: 24, fontWeight: 700, letterSpacing: 4, textTransform: 'uppercase', color, opacity: p(f, at)}}>{children}</div>;
};
const Title: React.FC<{children: React.ReactNode; at?: number; size?: number}> = ({children, at = 4, size = 58}) => {
  const f = useCurrentFrame();
  return <div style={{fontSize: size, fontWeight: 800, letterSpacing: -1.8, lineHeight: 1.1, marginTop: 14, opacity: p(f, at),
    transform: `translateY(${(1 - p(f, at)) * 18}px)`}}>{children}</div>;
};

const Scene: React.FC<{len: number; children: React.ReactNode}> = ({len, children}) => {
  const f = useCurrentFrame();
  const o = Math.min(p(f, 0, 14), interpolate(f, [len - 14, len], [1, 0], cl));
  const z = interpolate(f, [len - 14, len], [1, 0.985], cl);
  return <AbsoluteFill style={{opacity: o, transform: `scale(${z})`, fontFamily: SANS, color: C.ink}}>{children}</AbsoluteFill>;
};

// ------------------------------------------------------------------ 1 · 3D intro
const Panels: React.FC = () => {
  const f = useCurrentFrame();
  const panels = useMemo(() => Array.from({length: 70}).map((_, i) => {
    const r = (n: number) => Math.abs(Math.sin(i * 12.9898 + n * 78.233) * 43758.5453) % 1;
    return {x: (r(1) - 0.5) * 26, y: (r(2) - 0.5) * 14, z: -r(3) * 60, rot: (r(4) - 0.5) * 0.6, bad: i === 11 || i === 37};
  }), []);
  const camZ = interpolate(f, [0, 180], [12, -18], {...cl, easing: Easing.inOut(Easing.cubic)});
  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 4, camZ + 4]} intensity={60} color={C.lav} />
      <group position={[0, 0, -camZ]}>
        {panels.map((pn, i) => {
          const bob = Math.sin(f / 30 + i) * 0.15;
          const hot = pn.bad && f > 70;
          return (
            <mesh key={i} position={[pn.x, pn.y + bob, pn.z]} rotation={[0, pn.rot + f / 400, 0]}>
              <boxGeometry args={[2.6, 1.6, 0.06]} />
              <meshStandardMaterial color={hot ? C.peach : '#3a3452'} emissive={hot ? C.peach : C.lav}
                emissiveIntensity={hot ? 0.9 + 0.4 * Math.sin(f / 5) : 0.12} transparent opacity={0.85} roughness={0.35} metalness={0.2} />
            </mesh>
          );
        })}
      </group>
    </>
  );
};

const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const s = spring({frame: f - 96, fps, config: {damping: 200}});
  return (
    <AbsoluteFill>
      <ThreeCanvas width={width} height={height} camera={{position: [0, 0, 8], fov: 50}}>
        <color attach="background" args={[C.bg]} />
        <fog attach="fog" args={[C.bg, 8, 40]} />
        <Panels />
      </ThreeCanvas>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at center, transparent 30%, ${C.bg} 85%)`}} />
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
        <div style={{fontSize: 40, fontWeight: 700, color: C.ink2, opacity: p(f, 10) * (1 - p(f, 84, 12))}}>
          Every agent reads text no one reviews.
        </div>
        <div style={{position: 'absolute', opacity: s, transform: `scale(${0.94 + 0.06 * s})`}}>
          <div style={{fontSize: 156, fontWeight: 800, letterSpacing: -6}}>Agent<span style={{color: C.lav}}>Audit</span></div>
          <div style={{fontSize: 34, color: C.ink2, marginTop: 6}}>a pre-deployment gate for AI agents, built on Clocked</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 2 · architecture with animated beams
const Beam: React.FC<{id: string; d: string; from: string; to: string; at: number; period?: number; reverse?: boolean; w?: number}> =
  ({id, d, from, to, at, period = 70, reverse, w = 2.4}) => {
    const f = useCurrentFrame();
    const vis = p(f, at, 20);
    const t = (((f - at) % period) + period) % period / period;
    const pos = reverse ? 1 - t : t;
    return (
      <g opacity={vis}>
        <path d={d} fill="none" stroke="#ffffff" strokeOpacity={0.07} strokeWidth={w} />
        <defs>
          <linearGradient id={id} gradientUnits="objectBoundingBox" x1={pos - 0.25} x2={pos + 0.05} y1="0" y2="0">
            <stop offset="0" stopColor={from} stopOpacity="0" />
            <stop offset="0.6" stopColor={from} />
            <stop offset="1" stopColor={to} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={d} fill="none" stroke={`url(#${id})`} strokeWidth={w + 0.6} strokeLinecap="round" />
      </g>
    );
  };

const NodeChip: React.FC<{x: number; y: number; w: number; label: string; sub?: string; color: string; at: number; big?: boolean}> =
  ({x, y, w, label, sub, color, at, big}) => {
    const f = useCurrentFrame();
    const t = p(f, at, 16);
    return (
      <div style={{position: 'absolute', left: x, top: y, width: w, height: big ? 78 : 70, borderRadius: 16, background: C.panel,
        border: `1.5px solid ${t > 0.5 ? color + 'aa' : C.line}`, backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', gap: 14,
        padding: '0 18px', opacity: t, transform: `scale(${0.92 + 0.08 * t})`, boxShadow: `0 0 32px ${color}22`}}>
        <div style={{width: 11, height: 11, borderRadius: 6, background: color, boxShadow: `0 0 12px ${color}`}} />
        <div>
          <div style={{fontSize: big ? 30 : 26, fontWeight: 800}}>{label}</div>
          {sub && <div style={{fontSize: 18, color: C.ink2, fontFamily: MONO, marginTop: 2}}>{sub}</div>}
        </div>
      </div>
    );
  };

const EPS = [
  {n: 'Guard', s: 'injection p · spans', c: C.peach}, {n: 'Inspect', s: 'malicious p · lines', c: C.peach},
  {n: 'Protect', s: 'secret spans', c: C.peach}, {n: 'Extract', s: 'verbatim targets', c: C.sky},
  {n: 'Decide', s: 'yes/no · choice · score', c: C.sky}, {n: 'Fill', s: 'registry record', c: C.sky},
  {n: 'Verify', s: 'claim contradicted p', c: C.mint}, {n: 'Compare', s: 'same / overlapping', c: C.mint},
  {n: 'Rerank', s: 'use / skip', c: C.mint},
];
const ARTS = ['tool descriptions', 'system prompt', 'scripts · hooks', 'skills · README', 'registry'];

const Arch: React.FC = () => {
  const f = useCurrentFrame();
  const coreX = 640, coreY = 420, coreW = 440, coreH = 250;
  const epX = 1300, epY = (i: number) => 140 + i * 96;
  const artY = (i: number) => 250 + i * 120;
  const cxL = coreX, cxR = coreX + coreW, cy = coreY + coreH / 2;
  return (
    <AbsoluteFill>
      <GridBg />
      <div style={{position: 'absolute', left: 110, top: 70}}>
        <Kicker>Architecture</Kicker>
      </div>
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
        {ARTS.map((_, i) => (
          <Beam key={i} id={`a${i}`} at={20 + i * 6} from={C.ink2} to={C.lav}
            d={`M410,${artY(i) + 35} C520,${artY(i) + 35} 540,${cy} ${cxL},${cy}`} />
        ))}
        {EPS.map((e, i) => (
          <React.Fragment key={e.n}>
            <Beam id={`o${i}`} at={70 + i * 8} from={C.lav} to={e.c} period={60}
              d={`M${cxR},${cy - 30} C${cxR + 90},${cy - 30} ${epX - 110},${epY(i) + 22} ${epX},${epY(i) + 26}`} />
            <Beam id={`r${i}`} at={110 + i * 8} from={e.c} to={C.lav} period={60} reverse w={1.6}
              d={`M${cxR},${cy + 30} C${cxR + 90},${cy + 30} ${epX - 110},${epY(i) + 38} ${epX},${epY(i) + 44}`} />
          </React.Fragment>
        ))}
        <Beam id="v" at={230} from={C.lav} to={C.pink} d={`M${coreX + coreW / 2},${coreY + coreH} L${coreX + coreW / 2},${850}`} period={50} />
      </svg>
      {ARTS.map((a, i) => <NodeChip key={a} x={110} y={artY(i)} w={300} label={a} color={C.ink2} at={10 + i * 6} />)}
      <div style={{position: 'absolute', left: 110, top: artY(5) + 10, fontSize: 20, color: C.ink3, opacity: p(f, 50)}}>read as text, never executed</div>
      <div style={{position: 'absolute', left: coreX, top: coreY, opacity: p(f, 36, 20), transform: `scale(${0.9 + 0.1 * p(f, 36, 20)})`}}>
        <BeamCard w={coreW} h={coreH}>
          <div style={{padding: '30px 34px'}}>
            <div style={{fontSize: 46, fontWeight: 800}}>Agent<span style={{color: C.lav}}>Audit</span></div>
            {['what to ask each endpoint', 'what context to send', 'how to combine the answers'].map((t, i) => (
              <div key={t} style={{fontSize: 24, color: C.ink2, marginTop: i ? 8 : 16, opacity: p(f, 60 + i * 10)}}>{t}</div>
            ))}
          </div>
        </BeamCard>
      </div>
      <div style={{position: 'absolute', left: epX - 4, top: 92, fontSize: 20, color: C.sky, fontWeight: 700, letterSpacing: 2, opacity: p(f, 66)}}>
        CLOCKED · 9 TYPED DECISION ENDPOINTS
      </div>
      {EPS.map((e, i) => <NodeChip key={e.n} x={epX} y={epY(i)} w={400} label={e.n} sub={e.s} color={e.c} at={74 + i * 8} />)}
      <div style={{position: 'absolute', left: coreX - 110, top: 850, width: coreW + 220, opacity: p(f, 236, 20)}}>
        <BeamCard w={coreW + 220} h={130} color={C.pink} speed={4}>
          <div style={{padding: '20px 28px'}}>
            <div style={{fontSize: 19, color: C.ink2, fontFamily: MONO}}>policy rules in code → verdict</div>
            <div style={{display: 'flex', gap: 26, marginTop: 12, fontSize: 26, fontWeight: 800, whiteSpace: 'nowrap'}}>
              {[['approve', C.mint], ['needs owner', C.butter], ['reuse', C.sky], ['quarantine', C.peach]].map(([v, c], i) => (
                <span key={v} style={{color: c, opacity: p(f, 250 + i * 8)}}>{v}</span>
              ))}
            </div>
          </div>
        </BeamCard>
      </div>
      <div style={{position: 'absolute', left: 110, top: 128, fontSize: 32, fontWeight: 700, opacity: p(f, 300, 20)}}>
        AgentAudit asks. Clocked decides. Policy sets authority.
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 3 · real walkthrough
// timings measured from the recording (seconds)
const T = {estimate: 5.5, scan1: 10.25, report1: 17.5, clear: 23.5, scan2: 30.5, report2: 39.5, exit: 47};
const SRC_W = 1640, SCALE = 0.86, VIEW_H = 940;

const Step: React.FC<{n: string; title: string; lines: React.ReactNode[]; on: number; off: number; color?: string}> = ({n, title, lines, on, off, color = C.lav}) => {
  const f = useCurrentFrame();
  const a = on * 30, b = off * 30;
  const vis = Math.min(p(f, a, 14), 1 - p(f, b - 10, 10));
  if (vis <= 0) return null;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, opacity: vis, transform: `translateY(${(1 - p(f, a, 14)) * 20}px)`}}>
      <div style={{fontSize: 20, fontWeight: 700, letterSpacing: 3, color}}>{n}</div>
      <div style={{fontSize: 34, fontWeight: 800, marginTop: 8, letterSpacing: -1}}>{title}</div>
      <div style={{marginTop: 20}}>
        {lines.map((l, i) => (
          <div key={i} style={{fontSize: 20, color: C.ink2, lineHeight: 1.45, marginTop: 12, opacity: p(f, a + 12 + i * 14)}}>{l}</div>
        ))}
      </div>
    </div>
  );
};

const LiveCalls: React.FC<{on: number; off: number; calls: number; eps: string[]}> = ({on, off, calls, eps}) => {
  const f = useCurrentFrame();
  const a = on * 30, b = off * 30;
  if (f < a - 5 || f > b + 20) return null;
  const t = interpolate(f, [a, b], [0, 1], cl);
  const n = Math.round(calls * t);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 250, opacity: Math.min(p(f, a, 10), 1 - p(f, b + 6, 12))}}>
      <div style={{display: 'flex', alignItems: 'baseline', gap: 14}}>
        <div style={{width: 12, height: 12, borderRadius: 6, background: C.mint, opacity: 0.5 + 0.5 * Math.sin(f / 4)}} />
        <span style={{fontSize: 20, color: C.mint, fontWeight: 700, letterSpacing: 2}}>LIVE · CLOCKED API</span>
        <span style={{marginLeft: 'auto', fontFamily: MONO, fontSize: 44, fontWeight: 700}}>{n}<span style={{color: C.ink3, fontSize: 24}}> / {calls} calls</span></span>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 22}}>
        {eps.map((e, i) => {
          const lit = t > (i + 0.5) / eps.length;
          return <div key={e} style={{padding: '12px 14px', borderRadius: 12, border: `1.5px solid ${lit ? C.lav : C.line}`, background: lit ? '#2a2440' : 'transparent',
            fontSize: 19, fontWeight: 700, color: lit ? C.ink : C.ink3, textAlign: 'center'}}>{e}</div>;
        })}
      </div>
    </div>
  );
};

const Walk: React.FC = () => {
  const f = useCurrentFrame();
  const s = f / 30;
  // camera: pan the tall terminal recording (source px)
  const panSrc = interpolate(s, [0, T.report1, T.report1 + 1, T.clear - 0.6, T.clear, T.report2, T.report2 + 1, T.exit, 50],
    [0, 0, 0, 560, 0, 0, 0, 760, 760], {...cl, easing: Easing.inOut(Easing.cubic)});
  const zoom = interpolate(s, [0, 1.4, T.estimate + 3, T.scan1, T.report1, T.clear, T.scan2, T.report2],
    [1.18, 1.18, 1.18, 1.0, 1.0, 1.0, 1.06, 1.0], {...cl, easing: Easing.inOut(Easing.cubic)});
  const tilt = 1 - p(f, 0, 40);
  return (
    <AbsoluteFill>
      <GridBg accent={C.sky} />
      <div style={{position: 'absolute', left: 60, top: 56}}><Kicker>Real walkthrough · live API</Kicker></div>
      <div style={{position: 'absolute', left: 60, top: 100, width: SRC_W * SCALE, height: VIEW_H, perspective: 1800}}>
        <div style={{width: '100%', height: '100%', borderRadius: 18, overflow: 'hidden', boxShadow: '0 50px 140px rgba(0,0,0,.55), 0 0 0 1.5px #332e43',
          transform: `rotateY(${tilt * 14}deg) rotateX(${tilt * 6}deg) translateZ(${-tilt * 120}px)`, transformOrigin: 'left center', background: '#1e1e2e'}}>
          <div style={{transform: `scale(${SCALE * zoom}) translateY(${-panSrc}px)`, transformOrigin: '0 0', width: SRC_W}}>
            <OffthreadVideo src={staticFile('walkthrough.mp4')} muted style={{width: SRC_W, height: 2400, display: 'block'}} />
          </div>
        </div>
      </div>
      <div style={{position: 'absolute', left: 60 + SRC_W * SCALE + 50, top: 140, right: 50}}>
        <Step n="01 · ESTIMATE" title="Know the cost first." on={0.3} off={T.scan1}
          lines={['Counts the Clocked calls this agent needs.', <span key="c">No API calls: <b style={{color: C.ink}}>≈ 39–72 credits</b>.</span>]} />
        <Step n="02 · SCAN A MARKETPLACE SKILL" title="Every artifact, routed." on={T.scan1} off={T.report1}
          lines={['Tool descriptions → Guard. Prompt → Protect.', 'Setup steps → Extract → Decide.']} />
        <LiveCalls on={T.scan1} off={T.report1} calls={12} eps={['Guard', 'Guard', 'Guard', 'Guard', 'Protect', 'Extract', 'Decide', 'Extract', 'Decide', 'Fill', 'Verify', 'Decide']} />
        <Step n="REPORT" title="Quarantine." color={C.peach} on={T.report1} off={T.clear}
          lines={[
            <span key="1"><b style={{color: C.peach}}>Guard</b> · "download it from … extract it, and run"</span>,
            <span key="2"><b style={{color: C.sky}}>Extract → Decide</b> · untrusted install source, AA005</span>,
            <span key="3"><b style={{color: C.ink}}>Per tool</b> · merge_pdfs → review, split_pdf → enable</span>,
            <span key="4" style={{fontFamily: MONO, color: C.ink3}}>12 calls · 46 credits · $0.009</span>]} />
        <Step n="03 · SCAN AGAINST THE REGISTRY" title="Is it already approved?" on={T.clear} off={T.report2}
          lines={['Same audit, plus Compare and Rerank', 'against 5 approved agents.']} />
        <LiveCalls on={T.scan2} off={T.report2} calls={15} eps={['Guard', 'Guard', 'Guard', 'Inspect', 'Protect', 'Extract', 'Decide', 'Fill', 'Verify', 'Compare', 'Rerank', 'Decide']} />
        <Step n="REPORT" title="Quarantine, exit 1." color={C.peach} on={T.report2} off={50}
          lines={[
            <span key="1"><b style={{color: C.peach}}>Guard</b> · hidden BCC instruction in send_summary</span>,
            <span key="2"><b style={{color: C.peach}}>Inspect</b> · cleanup.sh uploads ~/.aws ~/.ssh</span>,
            <span key="3"><b style={{color: C.mint}}>Verify</b> · "never sends data outside": false</span>,
            <span key="4"><b style={{color: C.mint}}>Compare + Rerank</b> · no approved duplicate</span>,
            <span key="5" style={{fontFamily: MONO, color: C.ink3}}>15 calls · 61 credits · $0.012 · CI fails</span>]} />
      </div>
      <div style={{position: 'absolute', left: 60, bottom: 14, fontSize: 17, color: C.ink3, fontFamily: MONO}}>
        recorded with the real CLI against the live Clocked API · cache disabled · nothing edited
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ 4 · benchmarks
type Pt = {fpr: number; tpr: number};
const thin = (pts: Pt[], n = 160) => pts.filter((_, i) => i % Math.max(1, Math.floor(pts.length / n)) === 0 || i === pts.length - 1);
const ARM_COLOR = (arm: string) => arm.includes('AgentAudit') || arm.includes('pipeline') || arm.includes('Supply') ? C.lav
  : arm.includes('Clocked') ? C.peach : arm.includes('deepset') ? C.mint : C.sky;

const RocPlot: React.FC<{x: number; y: number; size: number; curves: {arm: string; auroc: number; points: Pt[]}[]; at: number; title: string;
  ops?: {from: Pt; to: Pt; at: number}}> = ({x, y, size, curves, at, title, ops}) => {
  const f = useCurrentFrame();
  const sx = (v: number) => x + v * size, sy = (v: number) => y + size - v * size;
  return (
    <g>
      <text x={x} y={y - 22} fill={C.ink} fontSize={26} fontWeight={800} fontFamily={SANS}>{title}</text>
      <rect x={x} y={y} width={size} height={size} fill="#191622" stroke={C.line} />
      {[0.25, 0.5, 0.75].map((v) => (
        <g key={v}>
          <line x1={sx(v)} x2={sx(v)} y1={y} y2={y + size} stroke="#ffffff" strokeOpacity={0.05} />
          <line y1={sy(v)} y2={sy(v)} x1={x} x2={x + size} stroke="#ffffff" strokeOpacity={0.05} />
        </g>
      ))}
      <line x1={sx(0)} y1={sy(0)} x2={sx(1)} y2={sy(1)} stroke={C.ink3} strokeDasharray="5 6" />
      {[0, 0.5, 1].map((v) => (
        <g key={v}>
          <text x={sx(v)} y={y + size + 26} fill={C.ink3} fontSize={17} textAnchor="middle" fontFamily={MONO}>{v}</text>
          <text x={x - 12} y={sy(v) + 6} fill={C.ink3} fontSize={17} textAnchor="end" fontFamily={MONO}>{v}</text>
        </g>
      ))}
      <text x={x + size / 2} y={y + size + 54} fill={C.ink2} fontSize={18} textAnchor="middle" fontFamily={SANS}>false-positive rate</text>
      <text x={x - 54} y={y + size / 2} fill={C.ink2} fontSize={18} textAnchor="middle" fontFamily={SANS} transform={`rotate(-90 ${x - 54} ${y + size / 2})`}>true-positive rate</text>
      {curves.map((c, i) => {
        const d = 'M' + thin(c.points).map((q) => `${sx(q.fpr).toFixed(1)},${sy(q.tpr).toFixed(1)}`).join(' L');
        const t = p(f, at + i * 14, 40);
        const col = ARM_COLOR(c.arm);
        return (
          <g key={c.arm}>
            <path d={d} fill="none" stroke={col} strokeWidth={c.arm.includes('AgentAudit') || c.arm.includes('pipeline') ? 4 : 2.6}
              pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - t} strokeLinejoin="round" />
            <g opacity={p(f, at + i * 14 + 30)}>
              <rect x={x + (i % 2) * (size / 2 + 10)} y={y + size + 84 + Math.floor(i / 2) * 34} width={22} height={5} rx={2} fill={col} />
              <text x={x + 32 + (i % 2) * (size / 2 + 10)} y={y + size + 92 + Math.floor(i / 2) * 34} fill={C.ink} fontSize={19} fontFamily={SANS} fontWeight={600}>{c.arm.replace(' (default)', '')} <tspan fill={C.ink3} fontFamily={MONO} fontSize={16}>{c.auroc.toFixed(3)}</tspan></text>
            </g>
          </g>
        );
      })}
      {ops && (() => {
        const t = p(f, ops.at, 40);
        const cur = {fpr: ops.from.fpr + (ops.to.fpr - ops.from.fpr) * t, tpr: ops.from.tpr + (ops.to.tpr - ops.from.tpr) * t};
        return (
          <g opacity={p(f, ops.at - 20)}>
            <circle cx={sx(ops.from.fpr)} cy={sy(ops.from.tpr)} r={9} fill="none" stroke={C.peach} strokeWidth={2.5} />
            <circle cx={sx(cur.fpr)} cy={sy(cur.tpr)} r={10} fill={t > 0.98 ? C.lav : C.peach} stroke="#fff" strokeWidth={2} />
            <line x1={sx(ops.from.fpr)} y1={sy(ops.from.tpr) + 10} x2={x + size * 0.45} y2={y + size * 0.55} stroke={C.ink3} strokeDasharray="3 4" />
            <rect x={x + size * 0.45} y={y + size * 0.55} width={size * 0.52} height={96} rx={12} fill="#14121b" stroke={C.line} />
            <text x={x + size * 0.45 + 18} y={y + size * 0.55 + 32} fill={C.ink2} fontSize={17} fontFamily={SANS} fontWeight={700}>operating point (deployed)</text>
            <text x={x + size * 0.45 + 18} y={y + size * 0.55 + 60} fill={C.peach} fontSize={18} fontFamily={MONO}>as shipped  FPR {(ops.from.fpr * 100).toFixed(1)}%</text>
            <text x={x + size * 0.45 + 18} y={y + size * 0.55 + 84} fill={C.lav} fontSize={18} fontFamily={MONO} opacity={p(f, ops.at + 30)}>AgentAudit  FPR {(ops.to.fpr * 100).toFixed(1)}%</text>
          </g>
        );
      })()}
    </g>
  );
};

const BenchFrame: React.FC<{k: string; title: string; note: string; children: React.ReactNode}> = ({k, title, note, children}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <GridBg />
      <div style={{position: 'absolute', left: 110, top: 64}}><Kicker>{k}</Kicker><Title size={50}>{title}</Title></div>
      <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>{children}</svg>
      <div style={{position: 'absolute', left: 110, bottom: 40, fontSize: 19, color: C.ink3, fontFamily: MONO, opacity: p(f, 30)}}>{note}</div>
    </AbsoluteFill>
  );
};

const Roc: React.FC = () => {
  const op = (DATA as any).roc.test.operating_points;
  return (
    <BenchFrame k="Benchmark 1 · tool poisoning" title="Same Guard model. Its operating point moves from 26% to 2% false alarms."
      note="Held-out MCPTox test, n = 253 (split by server) · real-tools set n = 249, never used in design · baselines' thresholds tuned on dev">
      <RocPlot x={230} y={290} size={500} curves={(DATA as any).roc.test.curves} at={20} title="MCPTox held-out test"
        ops={{from: op['Clocked default verdict'], to: op['AgentAudit frozen (consensus)'], at: 110}} />
      <RocPlot x={1140} y={290} size={500} curves={(DATA as any).roc.external.curves} at={60} title="Real MCP tools + published attacks" />
    </BenchFrame>
  );
};

const Forest: React.FC = () => {
  const f = useCurrentFrame();
  const rows = (DATA as any).forest as {suite: string; arm: string; group: string; bacc: number; bacc_ci: number[]}[];
  const suites = Array.from(new Set(rows.map((r) => r.suite)));
  const pos = [[110, 250], [1000, 250], [110, 660], [1000, 660]];
  return (
    <BenchFrame k="Benchmark 2 · every arm, every suite" title="AgentAudit vs Clocked as shipped vs open-source detectors."
      note="Balanced accuracy, 95% stratified bootstrap CIs · peach: Clocked as shipped · lavender: AgentAudit · mint: open-source, thresholds tuned on dev">
      {suites.map((su, k) => {
        const [px, py] = pos[k];
        const rs = rows.filter((r) => r.suite === su);
        const x0 = px + 330, x1 = px + 780, lo = 50, hi = 100;
        const sx = (v: number) => x0 + (v - lo) / (hi - lo) * (x1 - x0);
        const rh = rs.length > 4 ? 40 : 52;
        return (
          <g key={su} opacity={p(f, 8 + k * 20)}>
            <text x={px} y={py} fill={C.lav} fontSize={24} fontWeight={800} fontFamily={SANS}>{su}</text>
            {[50, 75, 100].map((v) => (
              <g key={v}><line x1={sx(v)} x2={sx(v)} y1={py + 18} y2={py + 24 + rs.length * rh} stroke="#fff" strokeOpacity={0.07} />
                <text x={sx(v)} y={py + 46 + rs.length * rh} fill={C.ink3} fontSize={16} textAnchor="middle" fontFamily={MONO}>{v}</text></g>
            ))}
            {rs.map((r, i) => {
              const t = p(f, 16 + k * 20 + i * 6, 26), col = FAMILY[r.group], y = py + 44 + i * rh;
              const aa = r.group === 'agentaudit';
              return (
                <g key={r.arm} opacity={p(f, 12 + k * 20 + i * 6)}>
                  <text x={x0 - 18} y={y + 6} fill={aa ? C.ink : C.ink2} fontSize={19} textAnchor="end" fontFamily={SANS} fontWeight={aa ? 800 : 500}>{r.arm}</text>
                  <line x1={sx(r.bacc_ci[0])} x2={sx(r.bacc_ci[0] + (r.bacc_ci[1] - r.bacc_ci[0]) * t)} y1={y} y2={y} stroke={col} strokeWidth={aa ? 5 : 3.5} strokeLinecap="round" />
                  <circle cx={sx(r.bacc)} cy={y} r={aa ? 8 : 6.5} fill={col} stroke="#14121b" strokeWidth={2} />
                  <text x={Math.min(sx(r.bacc_ci[1]) + 12, x1 + 14)} y={y + 6} fill={aa ? C.lav : C.ink} fontSize={18} fontFamily={MONO} fontWeight={aa ? 700 : 400}>{r.bacc.toFixed(1)}</text>
                </g>
              );
            })}
          </g>
        );
      })}
    </BenchFrame>
  );
};

const Skills: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <BenchFrame k="Benchmark 3 · malicious skills" title="Extract → Decide finds malware written as prose."
      note="Real February 2026 skill campaign (agent-skill-malware), held-out test n = 244 · pipeline vs Inspect: McNemar p = 7.4e-6">
      <RocPlot x={230} y={280} size={520} curves={(DATA as any).skills_roc} at={16} title="ROC, held-out test" />
      {[['Guard, as shipped', 10.3, 0.0, C.peach], ['Inspect, as shipped', 48.3, 2.5, C.peach], ['Supply-chain check alone', 77.0, 0.6, C.lav], ['AgentAudit pipeline', 80.5, 3.2, C.lav]].map(([n, r, fp, c], i) => {
        const t = p(f, 90 + i * 14, 30);
        return (
          <g key={n as string} opacity={p(f, 84 + i * 14)}>
            <text x={1220} y={560 + i * 96} fill={C.ink} fontSize={24} fontWeight={700} fontFamily={SANS}>{n as string}</text>
            <rect x={1220} y={576 + i * 96} width={440} height={16} rx={8} fill="#221e2e" />
            <rect x={1220} y={576 + i * 96} width={440 * (r as number) / 100 * t} height={16} rx={8} fill={c as string} />
            <text x={1680} y={592 + i * 96} fill={c as string} fontSize={26} fontWeight={800} fontFamily={SANS}>{((r as number) * t).toFixed(1)}%</text>
            <text x={1220} y={620 + i * 96} fill={C.ink3} fontSize={16} fontFamily={MONO}>recall · FPR {(fp as number).toFixed(1)}%</text>
          </g>
        );
      })}
    </BenchFrame>
  );
};

const Gov: React.FC = () => {
  const f = useCurrentFrame();
  const g = (DATA as any).governance;
  const cols: string[] = g.defects;
  const names: Record<string, string> = {poisoned_tool: 'poisoned tool', malicious_script: 'malicious script', embedded_secret: 'embedded secret', duplicate: 'duplicate', none: 'clean'};
  const rows = g.rows as {arm: string; key: string; acc: number; cells: Record<string, number[]>}[];
  const x0 = 520, cw = 190, ch = 52, y0 = 270;
  return (
    <BenchFrame k="Benchmark 4 · whole-agent verdicts + ablation" title="Remove one endpoint and its defect type goes unseen."
      note="38 held-out agents built from real MCP servers · cells: correct verdicts / agents of that type · one Decide call over raw artifacts = 60.5%">
      {cols.map((c, j) => <text key={c} x={x0 + j * cw + cw / 2} y={y0 - 18} fill={C.ink2} fontSize={19} textAnchor="middle" fontFamily={SANS} fontWeight={700}>{names[c]}</text>)}
      <text x={x0 + cols.length * cw + 70} y={y0 - 18} fill={C.ink2} fontSize={19} textAnchor="middle" fontFamily={SANS} fontWeight={700}>accuracy</text>
      {rows.map((r, i) => {
        const t = p(f, 10 + i * 6, 16);
        const key = r.key === 'full' || r.key === 'precision';
        return (
          <g key={r.key} opacity={t}>
            <text x={x0 - 24} y={y0 + i * ch + 33} fill={key ? C.ink : C.ink2} fontSize={20} textAnchor="end" fontFamily={SANS} fontWeight={key ? 800 : 500}>{r.arm}</text>
            {cols.map((c, j) => {
              const [a, b] = r.cells[c]; const v = b ? a / b : 0;
              const col = v === 1 ? C.lav : v >= 0.7 ? '#8f80cc' : v >= 0.4 ? '#6b5d99' : v > 0 ? '#4a3f6a' : '#3a2a33';
              const zero = v === 0;
              return (
                <g key={c}>
                  <rect x={x0 + j * cw + 4} y={y0 + i * ch + 4} width={cw - 8} height={ch - 8} rx={8} fill={zero ? '#4a2a2a' : col} opacity={0.35 + 0.65 * v + (zero ? 0.5 : 0)} />
                  <text x={x0 + j * cw + cw / 2} y={y0 + i * ch + 33} fill={zero ? C.peach : C.ink} fontSize={19} textAnchor="middle" fontFamily={MONO} fontWeight={700}>{a}/{b}</text>
                </g>
              );
            })}
            <text x={x0 + cols.length * cw + 70} y={y0 + i * ch + 33} fill={key ? C.lav : C.ink2} fontSize={22} textAnchor="middle" fontFamily={MONO} fontWeight={800}>{r.acc.toFixed(1)}</text>
          </g>
        );
      })}
    </BenchFrame>
  );
};

const Jev: React.FC = () => {
  const f = useCurrentFrame();
  const rows = (DATA as any).jev as {task: string; n: number; ours: number; published: number; jev: number}[];
  const names: Record<string, string> = {route: 'route', triage: 'triage', score: 'size', gate: 'risk'};
  const base = 860, h = 520, bw = 64;
  return (
    <BenchFrame k="Benchmark 5 · harness check" title="Our harness reproduces Clocked's own benchmark exactly: 507 / 868."
      note="jev-benchmark (MIT), 868 decisions from n8n commits · Jev 1.13 answers as published with the benchmark · Clocked engine v66">
      {rows.map((r, i) => {
        const gx = 230 + i * 380;
        const bars: [string, number, string][] = [['Clocked published', r.published, C.peach], ['our reproduction', r.ours, C.lav], ['Jev 1.13', r.jev, C.mint]];
        return (
          <g key={r.task}>
            {bars.map(([n, v, c], j) => {
              const t = p(f, 16 + i * 10 + j * 5, 30);
              return (
                <g key={n}>
                  <rect x={gx + j * (bw + 14)} y={base - (v / 100) * h * t} width={bw} height={(v / 100) * h * t} rx={10} fill={c} opacity={0.9} />
                  <text x={gx + j * (bw + 14) + bw / 2} y={base - (v / 100) * h * t - 14} fill={C.ink} fontSize={19} textAnchor="middle" fontFamily={MONO} opacity={t}>{v.toFixed(1)}</text>
                </g>
              );
            })}
            <text x={gx + (3 * bw + 28) / 2} y={base + 40} fill={C.ink} fontSize={24} fontWeight={800} textAnchor="middle" fontFamily={SANS}>{names[r.task] ?? r.task}</text>
            <text x={gx + (3 * bw + 28) / 2} y={base + 66} fill={C.ink3} fontSize={17} textAnchor="middle" fontFamily={MONO}>n = {r.n}</text>
          </g>
        );
      })}
      {[['Clocked published', C.peach], ['our reproduction', C.lav], ['Jev 1.13', C.mint]].map(([n, c], i) => (
        <g key={n} opacity={p(f, 40)}><rect x={1250 + i * 210} y={262} width={16} height={16} rx={4} fill={c} />
          <text x={1274 + i * 210} y={277} fill={C.ink2} fontSize={18} fontFamily={SANS}>{n}</text></g>
      ))}
    </BenchFrame>
  );
};

const End: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f - 4, fps, config: {damping: 200}});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
      <GridBg />
      <div style={{fontSize: 140, fontWeight: 800, letterSpacing: -5, opacity: s, transform: `scale(${0.94 + 0.06 * s})`}}>
        Agent<span style={{color: C.lav}}>Audit</span>
      </div>
      <div style={{display: 'flex', gap: 56, marginTop: 34, fontSize: 26, color: C.ink2, opacity: p(f, 20)}}>
        <span>all 9 Clocked endpoints</span><span>CLI · GitHub Action · REST</span><span>≈ 1¢ per audit</span>
      </div>
      <div style={{fontSize: 30, color: C.ink, marginTop: 40, fontFamily: MONO, opacity: p(f, 34)}}>github.com/Himanshu-Sangshetti/agentaudit</div>
    </AbsoluteFill>
  );
};

const COMPONENTS: Record<string, React.FC> = {intro: Intro, arch: Arch, walk: Walk, roc: Roc, forest: Forest, skills: Skills, gov: Gov, jev: Jev, end: End};

export const AgentAudit: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{background: C.bg}}>
      {SCENES.map((s) => {
        const Comp = COMPONENTS[s.id];
        const el = (
          <Sequence key={s.id} from={from} durationInFrames={s.len}>
            <Scene len={s.len}><Comp /></Scene>
          </Sequence>
        );
        from += s.len;
        return el;
      })}
    </AbsoluteFill>
  );
};
