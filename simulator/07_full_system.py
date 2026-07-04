"""
=============================================================================
  COMPONENT 07 — Full DLL System (Integrated)
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  Integrates all 6 components:
    01. BBPD          — Bang-Bang Phase Detector
    02. BS-FSM        — Binary Search Controller
    03. DAC           — 10-bit Digital-to-Analog Converter
    04. VCDL          — Voltage-Controlled Delay Line
    05. ÷N Divider    — Clock Divider
    06. Toggle Det.   — Clock Failure Detector

  Signal flow each CLKCTRL cycle:
    VCDL → ΔT → BBPD → PD_ER → FSM → code → DAC → V_CTRL → VCDL

  Usage:
    python3 07_full_system.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
F_CLKIN         = 1.0e9
N_DIV           = 4
V_DD            = 0.75
V_TH            = 0.25
V_REF           = 0.375
DAC_BITS        = 10
DAC_CODES       = 2**DAC_BITS
LOCK_CODE       = 724
FAILURE_PROB    = True
FORCE_FAIL_STEP = 3
FAIL_THRESHOLD  = 128
FAIL_RATE       = 0.10
TRACK_CYCLES    = 12

np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# IEEE / MATLAB STYLE
# ─────────────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.sans-serif':    ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size':          9,
    'axes.linewidth':     0.8,
    'axes.edgecolor':     'black',
    'axes.facecolor':     'white',
    'figure.facecolor':   'white',
    'xtick.direction':    'in',
    'ytick.direction':    'in',
    'xtick.major.size':   4,
    'ytick.major.size':   4,
    'xtick.top':          True,
    'ytick.right':        True,
    'legend.frameon':     False,
    'legend.fontsize':    8,
    'axes.titlesize':     9,
    'axes.labelsize':     9,
    'lines.linewidth':    1.5,
})

# IEEE color palette
C_DT     = 'blue'
C_LOCK   = '#228B22'
C_FAIL   = 'red'
C_RECOV  = '#228B22'
C_CODE   = 'blue'
C_VCTRL  = 'red'
C_STEP   = 'red'
C_TOG_OK = '#228B22'
C_TOG_FL = 'red'
C_PDUP   = '#008000'
C_PDDN   = 'red'
C_REF    = 'black'
C_FB     = 'blue'

STATE_COL = {
    'INIT'    : 'blue',
    'BS_RUN'  : 'darkorange',
    'LOCKED'  : '#228B22',
    'FAIL'    : 'red',
    'RECOVERY': 'darkorange',
}


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENT MODELS
# ─────────────────────────────────────────────────────────────────────────────

class DAC:
    def convert(self, code):
        return (int(np.clip(code, 0, DAC_CODES-1)) / DAC_CODES) * V_REF

class VCDL:
    def __init__(self):
        self.T_ps = 1e12 / F_CLKIN
        v_lock    = (LOCK_CODE / DAC_CODES) * V_REF
        self.KC   = (self.T_ps / 8) * (V_DD - v_lock - V_TH)

    def delta_t(self, code):
        v   = (int(np.clip(code, 0, DAC_CODES-1)) / DAC_CODES) * V_REF
        den = max(V_DD - v - V_TH, 1e-9)
        return 8 * self.KC / den - self.T_ps

class BBPD:
    def compare(self, delta_t):
        return 1 if delta_t >= 0 else -1

class ToggleDetector:
    def sample(self, clk_ok):
        return clk_ok

class BSFSM:
    def __init__(self):
        self.code = 0; self.codepre = 0
        self.step = DAC_CODES // 2
        self.locked = False; self.stall = 0

    def init(self):
        self.code    = 0
        self.codepre = 0
        self.step    = DAC_CODES // 2
        self.locked  = False
        self.stall   = 0

    def run(self, pd_er, toggling):
        if not toggling:
            self.stall += 1
            self.code   = self.codepre
            return self.code, 'FAIL'
        self.stall   = 0
        self.codepre = self.code
        if pd_er == 1:
            self.code = max(self.code - self.step, 0)
        else:
            self.code = min(self.code + self.step, DAC_CODES - 1)
        self.step = max(self.step >> 1, 1)
        if self.step == 1 and not self.locked:
            self.locked = True
        state = 'LOCKED' if self.locked else 'BS_RUN'
        return self.code, state

    def track(self, pd_er):
        self.codepre = self.code
        self.code    = int(np.clip(self.code - pd_er, 0, DAC_CODES - 1))
        return self.code, 'LOCKED'


# ─────────────────────────────────────────────────────────────────────────────
# FULL SYSTEM SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def run_system():
    dac  = DAC()
    vcdl = VCDL()
    bbpd = BBPD()
    togd = ToggleDetector()
    fsm  = BSFSM()

    T_ctrl_ns = 1e9 / (F_CLKIN / N_DIV)
    log       = []

    def record(cyc, t, code, step, dt, pd, v, tog, state):
        log.append(dict(cycle=cyc, time_ns=t, code=code,
                        step=step, delta_t=dt, pd_er=pd,
                        v_ctrl=v, toggling=tog, state=state))

    fsm.init()
    t_ns    = 0.0
    v       = dac.convert(fsm.code)
    dt      = vcdl.delta_t(fsm.code)
    pd_init = bbpd.compare(dt)
    record(0, t_ns, fsm.code, fsm.step, dt, pd_init, v, True, 'INIT')
    t_ns   += T_ctrl_ns
    lock_time = None

    for i in range(1, DAC_BITS + 6):
        if FAILURE_PROB:
            if i == FORCE_FAIL_STEP:
                clk_ok = False
            elif fsm.step >= FAIL_THRESHOLD:
                clk_ok = np.random.random() > FAIL_RATE
            else:
                clk_ok = True
        else:
            clk_ok = True

        tog    = togd.sample(clk_ok)
        dt_cur = vcdl.delta_t(fsm.code)
        pd     = bbpd.compare(dt_cur)
        code, state = fsm.run(pd, tog)
        v      = dac.convert(code)
        dt_new = vcdl.delta_t(code)
        record(i, t_ns, code, fsm.step, dt_new, pd, v, tog, state)

        if fsm.locked and lock_time is None:
            lock_time = t_ns
        t_ns += T_ctrl_ns

    if lock_time is None:
        lock_time = t_ns

    for j in range(TRACK_CYCLES):
        dt_cur = vcdl.delta_t(fsm.code)
        pd     = bbpd.compare(dt_cur)
        code, state = fsm.track(pd)
        v      = dac.convert(code)
        dt_new = vcdl.delta_t(code)
        record(DAC_BITS + 2 + j, t_ns, code, 1, dt_new, pd, v, True, state)
        t_ns += T_ctrl_ns

    return log, lock_time, T_ctrl_ns


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(log, lock_time, T_ctrl_ns):
    print()
    print('=' * 60)
    print('  Full DLL System — Binary Search Locking')
    print(f'  f_CLKIN={F_CLKIN/1e9:.2f}GHz  N={N_DIV}  '
          f'Lock code={LOCK_CODE}')
    print(f'  Lock time = {lock_time:.1f} ns  '
          f'({DAC_BITS+1} CLKCTRL cycles × {T_ctrl_ns:.1f} ns)')
    print('=' * 60)
    print(f"  {'Cyc':>4}  {'Code':>5}  {'Step':>5}  "
          f"{'ΔT(ps)':>8}  {'PD_ER':>6}  {'State'}")
    print('  ' + '-' * 48)
    for r in log:
        if r['state'] in ('INIT','BS_RUN','FAIL','RECOVERY','LOCKED') \
                and r['cycle'] <= DAC_BITS + 3:
            print(f"  {r['cycle']:>4}  {r['code']:>5}  "
                  f"{r['step']:>5}  {r['delta_t']:>+8.1f}  "
                  f"{r['pd_er']:>+6}  {r['state']}")
    print('=' * 60)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(log, lock_time):
    cycles  = [r['cycle']    for r in log]
    times   = [r['time_ns']  for r in log]
    codes   = [r['code']     for r in log]
    steps   = [r['step']     for r in log]
    deltas  = [r['delta_t']  for r in log]
    pders   = [r['pd_er']    for r in log]
    vctrl   = [r['v_ctrl']   for r in log]
    togs    = [r['toggling'] for r in log]
    states  = [r['state']    for r in log]
    pt_col  = [STATE_COL.get(s, 'gray') for s in states]

    x_max   = max(times) * 1.05

    fig = plt.figure(figsize=(15, 18))
    fig.suptitle(
        f'Full DLL System  —  All Components Integrated\n'
        f'$f_{{CLKIN}}$ = {F_CLKIN/1e9:.2f} GHz,  $N$ = {N_DIV},  '
        f'Lock code = {LOCK_CODE},  Lock time = {lock_time:.1f} ns',
        fontsize=11, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        5, 2, figure=fig,
        height_ratios=[0.9, 1.1, 1.1, 1.1, 1.2],
        hspace=0.52, wspace=0.32,
        left=0.08, right=0.96,
        top=0.95, bottom=0.04,
    )

    def add_markers(ax):
        """Lock line + failure shading on every plot."""
        ax.axvline(lock_time, color=C_LOCK, linewidth=1.0,
                   linestyle='--', label=f'Locked @ {lock_time:.1f} ns')
        for i, (tog, t) in enumerate(zip(togs, times)):
            if not tog and i < len(times) - 1:
                ax.axvspan(t, times[i+1], color=C_FAIL,
                           alpha=0.08, zorder=0)

    # ── (a) SYSTEM BLOCK DIAGRAM ─────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.set_xlim(0, 20)
    ax_a.set_ylim(0, 4.0)
    ax_a.axis('off')
    ax_a.set_title('(a)  System Block Diagram  (paper Fig. 2a)',
                   loc='left', fontsize=9, fontweight='bold')

    def bd_box(x, y, w, h, lbl, sub, col):
        ax_a.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle='square,pad=0.0',
            facecolor='white', edgecolor=col,
            linewidth=1.3, zorder=3))
        ax_a.text(x+w/2, y+h*0.65, lbl, ha='center', va='center',
                  fontsize=9, fontweight='bold', color=col, zorder=4)
        ax_a.text(x+w/2, y+h*0.25, sub, ha='center', va='center',
                  fontsize=6.5, color='gray', zorder=4)

    def bd_arrow(x1, y1, x2, y2, lbl='', col='black', rad=0.0):
        ax_a.annotate('', xy=(x2, y2), xytext=(x1, y1),
                      arrowprops=dict(arrowstyle='->', color=col,
                                      lw=1.2, mutation_scale=10,
                                      connectionstyle=f'arc3,rad={rad}'))
        if lbl:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax_a.text(mx, my+0.14, lbl, ha='center', va='bottom',
                      fontsize=7, color=col,
                      bbox=dict(boxstyle='round,pad=0.15',
                                fc='white', ec='none', alpha=0.85))

    bd_box(1.0,  1.8, 2.8, 1.4, 'VCDL',       'Voltage-Controlled\nDelay Line', 'blue')
    bd_box(5.2,  2.2, 2.2, 1.0, 'BBPD',        'Bang-Bang PD',                  '#008000')
    bd_box(5.2,  0.9, 2.2, 0.9, '$\\div N$',   'Divider',                       'darkorange')
    bd_box(1.0,  0.3, 2.8, 0.8, 'Toggle Det.', 'Clock Failure',                 'red')
    bd_box(9.0,  1.5, 2.8, 1.4, 'BS Control',  'FSM  code[9:0]',                'darkorange')
    bd_box(13.2, 1.5, 2.2, 1.4, 'DAC',         '10-bit D→A',                    'blue')
    bd_box(13.2, 3.2, 2.2, 0.6, 'Replica',     '$V_{CTRLP/N}$',                 'gray')

    # CLKIN input
    ax_a.text(-0.1, 2.6, 'CLKIN', ha='right', va='center',
              fontsize=8, fontweight='bold')
    bd_arrow(0.1, 2.6, 1.0, 2.6, '', 'black')

    # CLKOUT
    ax_a.text(3.9, 3.75, 'CLKOUT[7:0]', ha='center', va='center',
              fontsize=7.5, fontweight='bold', color='#008000',
              bbox=dict(boxstyle='round,pad=0.2', fc='white',
                        ec='#008000', lw=0.8))
    bd_arrow(2.4, 3.2, 2.4, 3.55, '', '#008000')

    # Signal arrows
    bd_arrow(3.8, 2.8, 5.2, 2.8,  'CLKREF',    'red')
    bd_arrow(3.8, 2.3, 5.2, 2.3,  'CLKFB',     'blue')
    bd_arrow(3.8, 1.9, 5.2, 1.55, 'CLKIN',     'darkorange')
    bd_arrow(2.4, 1.8, 2.4, 1.1,  'CLKREF',    'red')
    bd_arrow(7.4, 2.7, 9.0, 2.4,  '$PD_{ER}$', '#008000')
    bd_arrow(7.4, 1.35,9.0, 1.9,  'CLKCTRL',   'darkorange')
    bd_arrow(3.8, 0.7, 9.0, 1.7,  'toggling',  'red', rad=-0.2)
    bd_arrow(11.8,2.2, 13.2,2.2,  'code[9:0]', 'blue')
    bd_arrow(14.3,2.9, 14.3,3.2,  '',          'gray')

    # Feedback: Replica → VCDL
    ax_a.annotate('', xy=(2.4, 3.2), xytext=(13.2, 3.5),
                  arrowprops=dict(arrowstyle='->', color='darkorange',
                                  lw=1.2, mutation_scale=10,
                                  connectionstyle='arc3,rad=0.0'))
    ax_a.text(8.5, 3.65, '$V_{CTRLP}$ / $V_{CTRLN}$',
              ha='center', fontsize=7.5, color='darkorange')

    # ── (b) ΔT vs TIME ───────────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1, 0])
    add_markers(ax_b)

    ax_b.plot(times, deltas, 'o-', color=C_DT,
              linewidth=1.8, markersize=4, label='$\\Delta T$')
    ax_b.axhline(0, color=C_LOCK, linewidth=1.0,
                 linestyle=':', label='$\\Delta T$ = 0')

    ax_b.set_xlabel('Time (ns)')
    ax_b.set_ylabel('$\\Delta T$ (ps)')
    ax_b.set_xlim(-0.5, x_max)
    ax_b.legend(loc='upper right', fontsize=7.5)
    ax_b.set_title('(b)  VCDL Phase Error $\\Delta T$',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (c) PD_ER vs TIME ────────────────────────────────────────────────────
    ax_c = fig.add_subplot(gs[1, 1])
    add_markers(ax_c)

    pd_arr  = np.array(pders, dtype=float)
    cyc_arr = np.array(times, dtype=float)

    # Continuous span fills
    i = 0
    while i < len(cyc_arr):
        val = pd_arr[i]
        j   = i + 1
        while j < len(cyc_arr) and pd_arr[j] == val:
            j += 1
        clr = C_PDUP if val > 0 else C_PDDN
        ax_c.axvspan(cyc_arr[i] - 0.5*(cyc_arr[1]-cyc_arr[0]),
                     cyc_arr[j-1] + 0.5*(cyc_arr[1]-cyc_arr[0]),
                     ymin=0.5, ymax=0.81 if val > 0 else 0.5,
                     color=clr, alpha=0.30)
        ax_c.axvspan(cyc_arr[i] - 0.5*(cyc_arr[1]-cyc_arr[0]),
                     cyc_arr[j-1] + 0.5*(cyc_arr[1]-cyc_arr[0]),
                     ymin=0.19 if val < 0 else 0.5, ymax=0.5,
                     color=clr, alpha=0.30)
        i = j

    ax_c.step(times, pd_arr, where='mid', color='black', linewidth=1.8)
    ax_c.axhline(0, color='black', linewidth=0.5)

    up_patch   = mpatches.Patch(color=C_PDUP, alpha=0.5,
                                label='$PD_{ER}$ = +1 (UP)')
    down_patch = mpatches.Patch(color=C_PDDN, alpha=0.5,
                                label='$PD_{ER}$ = $-$1 (DOWN)')
    ax_c.legend(handles=[up_patch, down_patch],
                loc='upper right', fontsize=7.5)
    ax_c.set_yticks([-1, 0, 1])
    ax_c.set_yticklabels(['$-$1', '0', '+1'])
    ax_c.set_ylim(-1.6, 1.6)
    ax_c.set_xlim(-0.5, x_max)
    ax_c.set_xlabel('Time (ns)')
    ax_c.set_ylabel('$PD_{ER}$')
    ax_c.set_title('(c)  BBPD Phase Detector Output',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (d) DAC CODE + V_CTRL ────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[2, 0])
    add_markers(ax_d)

    ax_d.plot(times, codes, 'o-', color=C_CODE,
              linewidth=1.8, markersize=4, label='code[9:0]', zorder=4)
    ax_d.axhline(LOCK_CODE, color=C_LOCK, linewidth=1.0,
                 linestyle=':', label=f'Target = {LOCK_CODE}')

    # Shade failure windows
    for r in log:
        if r['state'] == 'FAIL':
            ax_d.axvspan(r['time_ns'] - 0.3, r['time_ns'] + 0.3,
                         alpha=0.10, color=C_FAIL)

    ax_d2 = ax_d.twinx()
    ax_d2.plot(times, [v*1e3 for v in vctrl], 's--',
               color=C_VCTRL, linewidth=1.2, markersize=3,
               alpha=0.75, label='$V_{CTRL}$ (mV)')
    ax_d2.set_ylabel('$V_{CTRL}$ (mV)', color=C_VCTRL, fontsize=9)
    ax_d2.tick_params(axis='y', colors=C_VCTRL, direction='in')
    ax_d2.set_ylim(-10, V_REF*1e3 + 20)

    ax_d.set_xlabel('Time (ns)')
    ax_d.set_ylabel('DAC Code')
    ax_d.set_xlim(-0.5, x_max)
    ax_d.set_ylim(-30, DAC_CODES + 30)

    lines1, lbl1 = ax_d.get_legend_handles_labels()
    lines2, lbl2 = ax_d2.get_legend_handles_labels()
    ax_d.legend(lines1 + lines2, lbl1 + lbl2,
                loc='lower right', fontsize=7.5)
    ax_d.set_title('(d)  DAC Code + $V_{CTRL}$',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (e) STEP SIZE ────────────────────────────────────────────────────────
    ax_e = fig.add_subplot(gs[2, 1])
    add_markers(ax_e)

    ax_e.semilogy(times, np.maximum(steps, 1), 's-',
                  color=C_STEP, linewidth=1.8, markersize=5,
                  label='step[8:0]')
    for i, (t, s) in enumerate(zip(times, steps)):
        if i < DAC_BITS + 2:
            ax_e.text(t, max(s, 1)*1.6, str(s),
                      ha='center', fontsize=6.5, color='black')

    ax_e.set_xlabel('Time (ns)')
    ax_e.set_ylabel('Step Size (log scale)')
    ax_e.set_xlim(-0.5, x_max)
    ax_e.legend(loc='upper right', fontsize=7.5)
    ax_e.set_title('(e)  BS-FSM Step Halving',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (f) TOGGLE DETECTOR ──────────────────────────────────────────────────
    ax_f = fig.add_subplot(gs[3, 0])
    add_markers(ax_f)

    tog_arr = np.array([int(tg) for tg in togs], dtype=float)
    ax_f.step(times, tog_arr, where='post',
              color='black', linewidth=1.8, zorder=4)
    ax_f.fill_between(times, 0, tog_arr, step='post',
                      where=(tog_arr > 0.5),
                      color=C_TOG_OK, alpha=0.18, label='Clock OK')
    ax_f.fill_between(times, 0, 1, step='post',
                      where=(tog_arr < 0.5),
                      color=C_TOG_FL, alpha=0.15, label='Clock STALLED')

    fail_times = [t for t, tg in zip(times, togs) if not tg]
    if fail_times:
        ax_f.annotate('Clock failure\ndetected',
                      xy=(fail_times[0], 0.05),
                      xytext=(fail_times[0] + 2.5, 0.45),
                      fontsize=7.5, color=C_FAIL,
                      arrowprops=dict(arrowstyle='->',
                                      color=C_FAIL, lw=1.0))

    ax_f.set_yticks([0, 1])
    ax_f.set_yticklabels(['0  (FAIL)', '1  (OK)'])
    ax_f.set_ylim(-0.3, 1.6)
    ax_f.set_xlim(-0.5, x_max)
    ax_f.set_xlabel('Time (ns)')
    ax_f.set_ylabel('toggling')
    ax_f.legend(loc='upper right', fontsize=7.5)
    ax_f.set_title('(f)  Toggle Detector Output',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (g) FSM STATE TIMELINE ───────────────────────────────────────────────
    ax_g = fig.add_subplot(gs[3, 1])
    add_markers(ax_g)

    state_y = {'INIT': 0, 'BS_RUN': 1, 'LOCKED': 2,
                'FAIL': 3, 'RECOVERY': 4}
    sy = [state_y.get(s, 1) for s in states]
    sc = [STATE_COL.get(s, 'gray') for s in states]

    ax_g.step(times, sy, where='post', color='black',
              linewidth=0.8, alpha=0.4)
    ax_g.scatter(times, sy, c=sc, s=40, zorder=4)

    ax_g.set_yticks(list(state_y.values()))
    ax_g.set_yticklabels(list(state_y.keys()), fontsize=8)
    ax_g.set_ylim(-0.5, 4.5)
    ax_g.set_xlim(-0.5, x_max)
    ax_g.set_xlabel('Time (ns)')
    ax_g.set_ylabel('FSM State')
    ax_g.set_title('(g)  FSM State Timeline',
                   loc='left', fontsize=9, fontweight='bold')

    # State color legend
    patches = [mpatches.Patch(color=v, label=k)
               for k, v in STATE_COL.items()]
    ax_g.legend(handles=patches, loc='upper right',
                fontsize=7, ncol=2)

    # ── (h) CLOCK WAVEFORMS ──────────────────────────────────────────────────
    ax_h = fig.add_subplot(gs[4, :])

    T_ps  = 1e12 / F_CLKIN
    t_ps  = np.linspace(0, 3 * T_ps, 3000)
    vcdl_obj = VCDL()

    def sq(t, period, delay=0.0):
        rise = 0.03
        ph   = ((t - delay) % period) / period
        w    = np.zeros_like(t)
        for i, p in enumerate(ph):
            if   p < rise:       w[i] = p / rise
            elif p < 0.5:        w[i] = 1.0
            elif p < 0.5 + rise: w[i] = 1.0 - (p - 0.5) / rise
        return w

    snaps = [
        (0,         0.0, 'Step 0   code = 0',          C_FAIL),
        (704,       3.2, 'Step 4   code = 704',         'darkorange'),
        (LOCK_CODE, 6.4, f'Locked   code = {LOCK_CODE}', C_LOCK),
    ]

    for code_s, offset, lbl, col in snaps:
        dt_val = vcdl_obj.delta_t(code_s)
        clkref = sq(t_ps, T_ps, delay=0.0)
        clkfb  = sq(t_ps, T_ps, delay=dt_val)

        ax_h.plot(t_ps, clkref * 0.85 + offset + 1.1,
                  color=C_REF, linewidth=1.4, alpha=0.85)
        ax_h.plot(t_ps, clkfb  * 0.85 + offset,
                  color=col,   linewidth=1.6)

        ax_h.text(t_ps[-1]*1.005, offset + 1.55, 'CLKREF',
                  va='center', fontsize=6.5, color=C_REF)
        ax_h.text(t_ps[-1]*1.005, offset + 0.42, 'CLKFB',
                  va='center', fontsize=6.5, color=col)
        ax_h.text(t_ps[-1]*1.22, offset + 0.9,
                  f'{lbl}\n$\\Delta T$ = {dt_val:+.1f} ps',
                  va='center', ha='center', fontsize=7.5, color=col)

        # ΔT arrow
        above  = clkref >= 0.5
        edges  = np.where(~above[:-1] & above[1:])[0]
        above2 = clkfb  >= 0.5
        edges2 = np.where(~above2[:-1] & above2[1:])[0]
        if len(edges) > 0 and len(edges2) > 0 and abs(dt_val) > 5:
            re0, fe0 = t_ps[edges[0]], t_ps[edges2[0]]
            y_arr    = offset + 2.25
            ax_h.annotate('', xy=(fe0, y_arr), xytext=(re0, y_arr),
                          arrowprops=dict(arrowstyle='<->',
                                          color=col, lw=1.2,
                                          mutation_scale=9))
            ax_h.text((re0+fe0)/2, y_arr+0.08,
                      f'{dt_val:+.0f} ps',
                      ha='center', va='bottom',
                      fontsize=7.5, color=col)

        # Row separator
        if offset > 0:
            ax_h.axhline(offset - 0.15, color='black',
                         linewidth=0.5, linestyle='--', alpha=0.25)

    ax_h.set_xlim(-T_ps*0.05, t_ps[-1]*1.38)
    ax_h.set_ylim(-0.3, 8.8)
    ax_h.set_yticks([])
    ax_h.set_xlabel('Time (ps)')
    ax_h.set_title(
        '(h)  Clock Alignment — CLKREF vs CLKFB  '
        '(Start / Mid-BS / Locked)',
        loc='left', fontsize=9, fontweight='bold')

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log, lock_time, T_ctrl_ns = run_system()
    print_summary(log, lock_time, T_ctrl_ns)
    fig = plot_all(log, lock_time)
    fig.canvas.manager.set_window_title(
        f'Component 07 — Full DLL System  |  '
        f'Lock={lock_time:.1f}ns  code={LOCK_CODE}')
    plt.show()


if __name__ == '__main__':
    main()
