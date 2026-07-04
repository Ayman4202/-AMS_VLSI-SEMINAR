"""
=============================================================================
  COMPONENT 02 — Binary Search FSM (DLC)
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  What it does:
    Implements the Binary Search locking algorithm.
    Starts at code=0, jumps to midpoint, then each CLKCTRL cycle:
      1. Read PD_ER from BBPD
      2. Move code up or down by step
      3. Halve the step (right shift)
      4. Repeat B times → locked in exactly B+1 = 11 cycles

  Registers:
    code[9:0]    — current DAC code  (0 → 1023)
    codepre[9:0] — previous DAC code (backup for failure recovery)
    step[8:0]    — step size         (512 → 256 → ... → 1)
    locked       — flag when step == 1
    stall_event  — flag when clock failure detected

  Usage:
    Set LOCK_CODE and INJECT_FAILURE below.
    Run:  python3 02_binary_search_fsm.py
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
DAC_BITS        = 10
DAC_CODES       = 2**DAC_BITS      # 1024
LOCK_CODE       = 724
INJECT_FAILURE  = True
FAILURE_AT_STEP = 4
TRACK_CYCLES    = 8

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
C_CODE    = 'blue'
C_PRE     = 'black'
C_STEP    = 'red'
C_LOCK    = '#228B22'       # dashed green — locked indicator
C_FAIL    = 'red'
C_RECOVER = 'darkorange'
C_PDER_UP = '#008000'
C_PDER_DN = 'red'
C_TRACK   = 'gray'

STATE_COLORS = {
    'IDLE'    : 'gray',
    'INIT'    : 'blue',
    'BS_RUN'  : 'darkorange',
    'LOCKED'  : '#228B22',
    'FAIL'    : 'red',
    'RECOVERY': 'darkorange',
    'ERROR'   : 'darkred',
}


# ─────────────────────────────────────────────────────────────────────────────
# IDEAL BBPD
# ─────────────────────────────────────────────────────────────────────────────

def bbpd(code: int, lock_code: int) -> int:
    if code > lock_code:
        return 1
    elif code < lock_code:
        return -1
    else:
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# BINARY SEARCH FSM CLASS
# ─────────────────────────────────────────────────────────────────────────────

class BinarySearchFSM:
    def __init__(self, dac_bits: int = DAC_BITS):
        self.B       = dac_bits
        self.CODES   = 2**dac_bits
        self.code    = 0
        self.codepre = 0
        self.step    = self.CODES // 2
        self.locked  = False
        self.stall   = 0
        self.state   = 'IDLE'
        self.log     = []

    def _record(self, cycle, pd_er, action):
        self.log.append({
            'cycle'  : cycle,
            'code'   : self.code,
            'codepre': self.codepre,
            'step'   : self.step,
            'pd_er'  : pd_er,
            'action' : action,
            'state'  : self.state,
            'locked' : self.locked,
            'stall'  : self.stall,
        })

    def reset(self):
        self.state   = 'INIT'
        self.code    = 0
        self.codepre = 0
        self.step    = self.CODES // 2
        self.locked  = False
        self.stall   = 0
        self._record(0, 0, 'RESET — code=0, step=512')

    def run_step(self, cycle: int, pd_er: int, clock_ok: bool = True):
        if not clock_ok:
            self.stall += 1
            self.state  = 'FAIL'
            saved_pre   = self.codepre
            self.step   = max(self.step >> 1, 1)
            self.code   = saved_pre
            self._record(cycle, pd_er,
                         f'FAIL — revert to codepre={saved_pre}, step={self.step}')
            self.state = 'RECOVERY'
            self._record(cycle, pd_er,
                         f'RECOVERY — resume from code={self.code}')
            return

        self.stall = 0
        self.state = 'BS_RUN'
        self.codepre = self.code

        if pd_er == 1:
            new_code = max(self.code - self.step, 0)
            action   = f'{self.code} - {self.step} = {new_code}'
        else:
            new_code = min(self.code + self.step, self.CODES - 1)
            action   = f'{self.code} + {self.step} = {new_code}'

        self.code = new_code
        self.step = max(self.step >> 1, 1)

        if self.step == 1 and not self.locked:
            self.locked = True
            self.state  = 'LOCKED'

        self._record(cycle, pd_er, action)

    def track(self, cycle: int, pd_er: int):
        self.state   = 'LOCKED'
        self.codepre = self.code
        self.code    = int(np.clip(self.code + pd_er, 0, self.CODES - 1))
        self._record(cycle, pd_er,
                     f'TRACK dither {self.codepre} → {self.code}')


# ─────────────────────────────────────────────────────────────────────────────
# RUN SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(lock_code=LOCK_CODE, inject_failure=INJECT_FAILURE,
                   failure_at_step=FAILURE_AT_STEP,
                   track_cycles=TRACK_CYCLES) -> BinarySearchFSM:
    fsm = BinarySearchFSM()
    fsm.reset()

    cycle = 1
    pd = bbpd(fsm.code, lock_code)
    fsm.run_step(cycle, pd, clock_ok=True)
    cycle += 1

    for i in range(2, DAC_BITS + 2):
        clk_ok = not (inject_failure and i == failure_at_step)
        pd     = bbpd(fsm.code, lock_code)
        fsm.run_step(cycle, pd, clock_ok=clk_ok)
        cycle += 1

    for _ in range(track_cycles):
        pd = bbpd(fsm.code, lock_code)
        fsm.track(cycle, pd)
        cycle += 1

    return fsm


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(fsm: BinarySearchFSM):
    print()
    print('=' * 68)
    print('  Binary Search FSM — Step-by-Step Walkthrough')
    print(f'  DAC bits = {fsm.B}  |  Lock code = {LOCK_CODE}  |  '
          f'Failure injection = {INJECT_FAILURE}')
    print('=' * 68)
    print(f"  {'Cycle':>6}  {'Code':>6}  {'codepre':>8}  "
          f"{'Step':>6}  {'PD_ER':>6}  {'State':<10}  Action")
    print('  ' + '-' * 64)
    for r in fsm.log:
        pd_str = f'{r["pd_er"]:+d}' if r['pd_er'] != 0 else ' —'
        print(f"  {r['cycle']:>6}  {r['code']:>6}  {r['codepre']:>8}  "
              f"{r['step']:>6}  {pd_str:>6}  {r['state']:<10}  {r['action']}")
    print('=' * 68)
    lock_entry = next((r for r in fsm.log if r['state'] == 'LOCKED'), None)
    if lock_entry:
        print(f'  Locked at cycle {lock_entry["cycle"]}  '
              f'code = {lock_entry["code"]}')
    print('=' * 68)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(fsm: BinarySearchFSM):
    log    = fsm.log
    cycles = [r['cycle']   for r in log]
    codes  = [r['code']    for r in log]
    pres   = [r['codepre'] for r in log]
    steps  = [r['step']    for r in log]
    pders  = [r['pd_er']   for r in log]
    states = [r['state']   for r in log]

    lock_cycle  = next((r['cycle'] for r in log if r['state'] == 'LOCKED'), None)
    fail_cycles = [r['cycle'] for r in log if r['state'] == 'FAIL']

    fig = plt.figure(figsize=(14, 11))
    fig.suptitle(
        f'Binary Search FSM (DLC)  —  Lock code = {LOCK_CODE},  '
        f'$B$ = {DAC_BITS} bits,  $B$+1 = {DAC_BITS+1} cycles,  '
        f'Failure injection = {INJECT_FAILURE} (step {FAILURE_AT_STEP})',
        fontsize=10, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        2, 3, figure=fig,
        height_ratios=[1.0, 1.0],
        hspace=0.52, wspace=0.38,
        left=0.08, right=0.97,
        top=0.94, bottom=0.07,
    )

    def add_lock_fail(ax):
        """Add locked and failure vertical markers."""
        if lock_cycle:
            ax.axvline(lock_cycle, color=C_LOCK, linewidth=1.2,
                       linestyle='--', label=f'Locked (cycle {lock_cycle})')
        for fc in fail_cycles:
            ax.axvline(fc, color=C_FAIL, linewidth=1.0,
                       linestyle=':', alpha=0.7)

    # ── (a) STATE DIAGRAM ────────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[0, 0])
    ax_b.set_xlim(0, 10)
    ax_b.set_ylim(0, 6)
    ax_b.axis('off')
    ax_b.set_title('(a)  FSM States', loc='left',
                   fontsize=9, fontweight='bold')

    def sbox(ax, x, y, label, color, w=2.2, h=0.75):
        ax.add_patch(FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle='square,pad=0.0',
            facecolor='white', edgecolor=color,
            linewidth=1.5, zorder=3))
        ax.text(x, y, label, ha='center', va='center',
                fontsize=8, fontweight='bold', color=color, zorder=4)

    def sarrow(ax, x1, y1, x2, y2, lbl='', color='black', rad=0.0):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.0,
                                    mutation_scale=10,
                                    connectionstyle=f'arc3,rad={rad}'))
        if lbl:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.15, lbl, ha='center', fontsize=6,
                    color=color)

    sbox(ax_b, 1.2, 5.0, 'IDLE',     STATE_COLORS['IDLE'])
    sbox(ax_b, 1.2, 3.5, 'INIT',     STATE_COLORS['INIT'])
    sbox(ax_b, 1.2, 2.0, 'BS_RUN',   STATE_COLORS['BS_RUN'])
    sbox(ax_b, 1.2, 0.6, 'LOCKED',   STATE_COLORS['LOCKED'])
    sbox(ax_b, 5.5, 2.0, 'FAIL',     STATE_COLORS['FAIL'])
    sbox(ax_b, 5.5, 0.6, 'RECOVERY', STATE_COLORS['RECOVERY'])
    sbox(ax_b, 8.8, 0.6, 'ERROR',    STATE_COLORS['ERROR'])

    sarrow(ax_b, 1.2, 4.62, 1.2, 3.88, 'enable',      STATE_COLORS['INIT'])
    sarrow(ax_b, 1.2, 3.12, 1.2, 2.38, 'reset=0',     STATE_COLORS['BS_RUN'])
    sarrow(ax_b, 1.2, 1.62, 1.2, 0.98, 'step = 1',    STATE_COLORS['LOCKED'])
    sarrow(ax_b, 2.3, 2.0,  4.4, 2.0,  'toggling=0',  C_FAIL)
    sarrow(ax_b, 5.5, 1.62, 5.5, 0.98, '',            C_RECOVER)
    sarrow(ax_b, 6.6, 0.6,  7.7, 0.6,  'stall×2',     C_FAIL)
    sarrow(ax_b, 4.4, 2.0,  2.3, 2.38, 'resume',      C_RECOVER, rad=0.3)

    # self-loop on BS_RUN
    ax_b.annotate('', xy=(0.1, 2.38), xytext=(0.1, 1.62),
                  arrowprops=dict(arrowstyle='->', color=STATE_COLORS['BS_RUN'],
                                  lw=1.0, mutation_scale=10,
                                  connectionstyle='arc3,rad=0.7'))
    ax_b.text(-0.5, 2.0, '×B', ha='center', fontsize=7,
              color=STATE_COLORS['BS_RUN'])

    # ── (b) PD_ER ────────────────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[0, 1])
    add_lock_fail(ax_d)

    pd_arr  = np.array(pders, dtype=float)
    cyc_arr = np.array(cycles, dtype=float)

    # Build continuous spans: for each run of same PD_ER value,
    # fill symmetrically above/below 0 so color is continuous across runs
    i = 0
    while i < len(cyc_arr):
        val = pd_arr[i]
        j   = i + 1
        while j < len(cyc_arr) and pd_arr[j] == val:
            j += 1
        x_start = cyc_arr[i] - 0.5
        x_end   = cyc_arr[j - 1] + 0.5
        clr     = C_PDER_UP if val > 0 else C_PDER_DN
        # fill from 0 to +1 (UP) or 0 to -1 (DOWN) — symmetric around zero
        ax_d.axvspan(x_start, x_end, ymin=0.5, ymax=0.81 if val > 0 else 0.5,
                     color=clr, alpha=0.30)
        ax_d.axvspan(x_start, x_end, ymin=0.19 if val < 0 else 0.5, ymax=0.5,
                     color=clr, alpha=0.30)
        i = j

    # Step line on top
    ax_d.step(cyc_arr, pd_arr, where='mid', color='black', linewidth=1.8)
    ax_d.axhline(0, color='black', linewidth=0.5)

    # Legend patches
    import matplotlib.patches as mpatches
    up_patch   = mpatches.Patch(color=C_PDER_UP, alpha=0.5,
                                label='$PD_{ER}$ = +1 (UP)')
    down_patch = mpatches.Patch(color=C_PDER_DN, alpha=0.5,
                                label='$PD_{ER}$ = $-$1 (DOWN)')
    ax_d.legend(handles=[up_patch, down_patch], loc='upper right', fontsize=7.5)

    ax_d.set_yticks([-1, 0, 1])
    ax_d.set_yticklabels(['$-$1', '0', '+1'])
    ax_d.set_ylim(-1.6, 1.6)
    ax_d.set_xlim(0, max(cycles) + 1)
    ax_d.set_xlabel('$CLKCTRL$ Cycle')
    ax_d.set_ylabel('$PD_{ER}$')
    ax_d.set_title('(b)  Phase Detector Output', loc='left',
                   fontsize=9, fontweight='bold')

    # ── (c) STATE SEQUENCE ───────────────────────────────────────────────────
    ax_e = fig.add_subplot(gs[0, 2])
    add_lock_fail(ax_e)

    state_map = {'IDLE': 0, 'INIT': 1, 'BS_RUN': 2,
                 'LOCKED': 3, 'FAIL': 4, 'RECOVERY': 5, 'ERROR': 6}
    state_nums = [state_map.get(s, 0) for s in states]
    pt_colors  = [STATE_COLORS.get(s, 'gray') for s in states]

    ax_e.step(cycles, state_nums, where='post', color='black',
              linewidth=1.0, alpha=0.4)
    ax_e.scatter(cycles, state_nums, c=pt_colors, s=40, zorder=4)

    ax_e.set_yticks(list(state_map.values()))
    ax_e.set_yticklabels(list(state_map.keys()), fontsize=7)
    ax_e.set_xlim(0, max(cycles) + 1)
    ax_e.set_ylim(-0.5, 6.5)
    ax_e.set_xlabel('$CLKCTRL$ Cycle')
    ax_e.set_ylabel('FSM State')
    ax_e.set_title('(c)  State Sequence', loc='left',
                   fontsize=9, fontweight='bold')

    # ── (d) CODE + STEP COMBINED (twin axis) ─────────────────────────────────
    ax_f  = fig.add_subplot(gs[1, :])
    add_lock_fail(ax_f)

    ax_f.plot(cycles, codes, 'o-', color=C_CODE, linewidth=2.0,
              markersize=6, label='code[9:0]', zorder=4)
    ax_f.axhline(LOCK_CODE, color=C_LOCK, linewidth=1.0,
                 linestyle=':', label=f'Target = {LOCK_CODE}')

    # Shade failure windows
    for r in log:
        if r['state'] in ('FAIL', 'RECOVERY'):
            ax_f.axvspan(r['cycle'] - 0.45, r['cycle'] + 0.45,
                         alpha=0.10, color=C_FAIL)

    # Annotate code values — offset lock cycle label to avoid overlap
    for i in range(min(len(cycles), DAC_BITS + 3)):
        y_offset = 55 if lock_cycle and cycles[i] == lock_cycle else 28
        ax_f.text(cycles[i], codes[i] + y_offset, str(codes[i]),
                  ha='center', fontsize=7, color='black')

    # Twin axis for step
    ax_f2 = ax_f.twinx()
    ax_f2.semilogy(cycles, steps, 's--', color=C_STEP,
                   linewidth=1.4, markersize=5, alpha=0.85,
                   label='step[8:0]')
    ax_f2.set_ylabel('Step Size (log scale)', color=C_STEP, fontsize=9)
    ax_f2.tick_params(axis='y', colors=C_STEP, direction='in')
    ax_f2.set_ylim(0.5, DAC_CODES * 2)

    ax_f.set_xlabel('$CLKCTRL$ Cycle')
    ax_f.set_ylabel('DAC Code')
    ax_f.set_xlim(0, max(cycles) + 1)
    ax_f.set_ylim(-40, DAC_CODES + 80)

    lines1, lbl1 = ax_f.get_legend_handles_labels()
    lines2, lbl2 = ax_f2.get_legend_handles_labels()
    ax_f.legend(lines1 + lines2, lbl1 + lbl2,
                loc='lower right', fontsize=8)
    ax_f.set_title('(d)  Code Convergence + Step Halving',
                   loc='left', fontsize=9, fontweight='bold')

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    fsm = run_simulation(
        lock_code       = LOCK_CODE,
        inject_failure  = INJECT_FAILURE,
        failure_at_step = FAILURE_AT_STEP,
        track_cycles    = TRACK_CYCLES,
    )
    print_summary(fsm)

    fig = plot_all(fsm)
    fig.canvas.manager.set_window_title(
        f'Component 02 — Binary Search FSM  |  Lock code = {LOCK_CODE}')
    plt.show()


if __name__ == '__main__':
    main()
