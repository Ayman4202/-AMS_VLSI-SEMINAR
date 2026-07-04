"""
=============================================================================
  COMPONENT 06 — Toggle Detector
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  What it does:
    Monitors CLKIN and detects when it stops toggling (clock failure).
    The BBPD cannot detect this — if CLKIN stops, there are no edges
    to compare. The toggle detector catches this within 1.5 CLKIN cycles.

  Internal circuit (paper Fig. 8):
    FF1: D=1 (tied high), CLK=CLKIN  → set every CLKIN rising edge
    ED:  Edge detector on CLKREF     → clears FF1 on every CLKREF edge
    FF2: D=FF1.Q, CLK=CLKIN          → samples FF1

    Normal:  CLKIN toggles → FF1 set then cleared → FF2 never captures 1
             → toggling = 1  (OK)

    Failure: CLKIN stops  → FF1 stays set → FF2 captures 1
             → toggling = 0  (FAIL)

  Detection latency: < 1.5 CLKIN cycles

  Usage:
    python3 06_toggle_detector.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
F_CLKIN       = 1.0e9
N_DIV         = 4
FAILURE_AT_NS = 6.0
RECOVER_AT_NS = 10.0
SIM_NS        = 16.0

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
C_CLKIN  = 'black'
C_CLKREF = 'blue'
C_FF1    = 'blue'
C_FF2    = 'red'
C_TOG_OK = '#228B22'
C_TOG_FL = 'red'
C_FAIL   = 'red'
C_RECOV  = '#228B22'


# ─────────────────────────────────────────────────────────────────────────────
# TOGGLE DETECTOR CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ToggleDetector:
    """
    Behavioral model of the toggle detector circuit.
    FF1: set by CLKIN, cleared by CLKREF edge.
    FF2: samples FF1 on CLKIN rising edge.
    toggling = 1 (OK) when CLKIN is active, 0 (FAIL) when stalled.
    """
    def __init__(self):
        self.ff1 = self.ff2 = 0
        self.toggling = 1

    def reset(self):
        self.ff1 = self.ff2 = 0
        self.toggling = 1

    def sample(self, clk_active: bool, clkref_edge: bool) -> int:
        if clk_active:
            self.ff1 = 1
            if clkref_edge:
                self.ff1 = 0
            self.ff2      = 0
            self.toggling = 1
        else:
            self.ff2      = self.ff1
            self.toggling = 0 if self.ff2 == 1 else 1
        return self.toggling


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation():
    T_clkin_ns = 1.0 / (F_CLKIN / 1e9)
    T_ref_ns   = T_clkin_ns * N_DIV
    dt         = T_clkin_ns / 20
    t_arr      = np.arange(0, SIM_NS, dt)

    clkin_arr  = np.zeros(len(t_arr))
    clkref_arr = np.zeros(len(t_arr))
    ff1_arr    = np.zeros(len(t_arr))
    ff2_arr    = np.zeros(len(t_arr))
    tog_arr    = np.ones(len(t_arr))

    det = ToggleDetector()

    for i, t in enumerate(t_arr):
        clk_active = not (FAILURE_AT_NS <= t < RECOVER_AT_NS)

        if clk_active:
            ph = (t % T_clkin_ns) / T_clkin_ns
            clkin_arr[i] = 1.0 if ph < 0.5 else 0.0
        else:
            clkin_arr[i] = 0.0

        ph_ref = (t % T_ref_ns) / T_ref_ns
        clkref_arr[i] = 1.0 if ph_ref < 0.5 else 0.0

        clkref_edge = False
        if i > 0:
            clkref_edge = (clkref_arr[i] > 0.5 and
                           clkref_arr[i-1] <= 0.5)

        tog = det.sample(clk_active, clkref_edge)
        ff1_arr[i] = det.ff1
        ff2_arr[i] = det.ff2
        tog_arr[i] = tog

    return t_arr, clkin_arr, clkref_arr, ff1_arr, ff2_arr, tog_arr


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    T_ns = 1.0 / (F_CLKIN / 1e9)
    print()
    print('=' * 50)
    print('  Toggle Detector')
    print(f'  f_CLKIN        = {F_CLKIN/1e9:.3f} GHz')
    print(f'  T_CLKIN        = {T_ns:.3f} ns')
    print(f'  Detection time < 1.5 × T_CLKIN = {1.5*T_ns:.3f} ns')
    print(f'  Failure at     = {FAILURE_AT_NS} ns')
    print(f'  Recovery at    = {RECOVER_AT_NS} ns')
    print('=' * 50)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all():
    t, clkin, clkref, ff1, ff2, tog = run_simulation()
    T_ns = 1.0 / (F_CLKIN / 1e9)

    fig = plt.figure(figsize=(13, 11))
    fig.suptitle(
        f'Toggle Detector  —  '
        f'$f_{{CLKIN}}$ = {F_CLKIN/1e9:.2f} GHz,  '
        f'Failure @ {FAILURE_AT_NS} ns,  '
        f'Recovery @ {RECOVER_AT_NS} ns',
        fontsize=10, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        4, 2, figure=fig,
        height_ratios=[0.85, 1.0, 1.0, 1.0],
        hspace=0.52, wspace=0.30,
        left=0.08, right=0.96,
        top=0.94, bottom=0.06,
    )

    def add_failure_markers(ax):
        """Shade failure window and add vertical markers."""
        ax.axvspan(FAILURE_AT_NS, RECOVER_AT_NS,
                   color=C_FAIL, alpha=0.06, zorder=0)
        ax.axvline(FAILURE_AT_NS, color=C_FAIL,  linewidth=1.0,
                   linestyle='--', alpha=0.8)
        ax.axvline(RECOVER_AT_NS, color=C_RECOV, linewidth=1.0,
                   linestyle='--', alpha=0.8)

    # ── (a) BLOCK DIAGRAM ────────────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.set_xlim(0, 16)
    ax_a.set_ylim(0, 3)
    ax_a.axis('off')
    ax_a.set_title('(a)  Toggle Detector Circuit  (paper Fig. 8)',
                   loc='left', fontsize=9, fontweight='bold')

    def box(ax, x, y, w, h, lbl, sub, col):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle='square,pad=0.0',
            facecolor='white', edgecolor=col,
            linewidth=1.3, zorder=3))
        ax.text(x+w/2, y+h*0.65, lbl, ha='center', va='center',
                fontsize=9, fontweight='bold', color=col, zorder=4)
        ax.text(x+w/2, y+h*0.25, sub, ha='center', va='center',
                fontsize=6.5, color='gray', zorder=4)

    box(ax_a, 0.3,  1.0, 1.8, 1.0, 'FF1', 'D=1 / CLK=CLKIN',  C_FF1)
    box(ax_a, 3.0,  1.0, 1.8, 1.0, 'ED',  'Edge Det / CLKREF', 'darkorange')
    box(ax_a, 5.8,  1.0, 1.8, 1.0, 'FF2', 'D=FF1 / CLK=CLKIN', C_FF2)
    box(ax_a, 9.0,  1.0, 1.8, 1.0, 'INV', 'Inverter',           'gray')

    # Arrows between blocks
    for x1, x2, col, lbl in [
        (2.1,  3.0,  C_FF1,        'FF1.Q'),
        (4.8,  5.8,  'darkorange', 'clear'),
        (7.6,  9.0,  C_FF2,        'FF2.Q'),
        (10.8, 12.2, C_TOG_OK,     'toggling'),
    ]:
        ax_a.annotate('', xy=(x2, 1.5), xytext=(x1, 1.5),
                      arrowprops=dict(arrowstyle='->', color=col,
                                      lw=1.2, mutation_scale=10))
        ax_a.text((x1+x2)/2, 1.72, lbl, ha='center',
                  fontsize=7, color=col)

    # Input arrows
    ax_a.text(1.2, 2.3, 'CLKIN', ha='center', fontsize=8,
              fontweight='bold', color=C_FF1)
    ax_a.annotate('', xy=(1.2, 2.0), xytext=(1.2, 2.25),
                  arrowprops=dict(arrowstyle='->', color=C_FF1,
                                  lw=1.0, mutation_scale=9))
    ax_a.text(3.9, 2.3, 'CLKREF', ha='center', fontsize=8,
              fontweight='bold', color='darkorange')
    ax_a.annotate('', xy=(3.9, 2.0), xytext=(3.9, 2.25),
                  arrowprops=dict(arrowstyle='->', color='darkorange',
                                  lw=1.0, mutation_scale=9))

    # Output label
    ax_a.text(12.4, 1.5, 'toggling\n1 = OK\n0 = FAIL',
              ha='left', va='center', fontsize=8,
              fontweight='bold', color=C_TOG_OK)

    # Logic description box
    ax_a.text(8.0, 2.75,
              'Normal: CLKIN toggles → FF1 cleared → toggling = 1  |  '
              'Failure: CLKIN stops → FF2 captures 1 → toggling = 0',
              ha='center', va='center', fontsize=7.5,
              bbox=dict(boxstyle='round,pad=0.3', fc='#f5f5f5',
                        ec='black', lw=0.7))

    # ── (b) CLKIN ────────────────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1, :])
    add_failure_markers(ax_b)

    ax_b.plot(t, clkin, color=C_CLKIN, linewidth=1.5)
    ax_b.fill_between(t, 0, clkin, color=C_CLKIN, alpha=0.08)

    ax_b.set_yticks([0, 1])
    ax_b.set_yticklabels(['0', '1'])
    ax_b.set_ylim(-0.25, 1.5)
    ax_b.set_xlim(0, SIM_NS)
    ax_b.set_ylabel('CLKIN')
    ax_b.set_title('(b)  CLKIN  (stops at failure, resumes at recovery)',
                   loc='left', fontsize=9, fontweight='bold')
    ax_b.text(FAILURE_AT_NS + 0.1, 1.3, 'Clock STOPPED',
              fontsize=8, color=C_FAIL, fontweight='bold')
    ax_b.text(RECOVER_AT_NS + 0.1, 1.3, 'Clock RESUMED',
              fontsize=8, color=C_RECOV, fontweight='bold')

    # ── (c) FF1 and FF2 ──────────────────────────────────────────────────────
    ax_c = fig.add_subplot(gs[2, :])
    add_failure_markers(ax_c)

    ax_c.plot(t, ff1 + 1.3, color=C_FF1, linewidth=1.5, label='FF1')
    ax_c.plot(t, ff2,       color=C_FF2, linewidth=1.5, label='FF2')
    ax_c.fill_between(t, 1.3, ff1 + 1.3, color=C_FF1, alpha=0.12)
    ax_c.fill_between(t, 0,   ff2,        color=C_FF2, alpha=0.12)

    ax_c.set_yticks([0.5, 1.8])
    ax_c.set_yticklabels(['FF2', 'FF1'])
    ax_c.set_ylim(-0.25, 2.65)
    ax_c.set_xlim(0, SIM_NS)
    ax_c.set_ylabel('Logic')
    ax_c.legend(loc='upper right', fontsize=8)
    ax_c.set_title('(c)  FF1 (blue) and FF2 (red) — internal registers',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (d) TOGGLING OUTPUT ──────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[3, :])
    add_failure_markers(ax_d)

    ax_d.plot(t, tog, color=C_TOG_OK, linewidth=2.0)
    ax_d.fill_between(t, 0, tog,
                      where=(tog > 0.5), color=C_TOG_OK, alpha=0.18)
    ax_d.fill_between(t, 0, 1,
                      where=(tog < 0.5), color=C_TOG_FL, alpha=0.12)

    ax_d.set_yticks([0, 1])
    ax_d.set_yticklabels(['0  (FAIL)', '1  (OK)'])
    ax_d.set_ylim(-0.3, 1.6)
    ax_d.set_xlim(0, SIM_NS)
    ax_d.set_xlabel('Time (ns)')
    ax_d.set_ylabel('toggling')
    ax_d.set_title('(d)  toggling Output  (1 = OK,  0 = FAIL)',
                   loc='left', fontsize=9, fontweight='bold')

    # Detection latency annotation
    fail_detect = FAILURE_AT_NS + 1.5 * T_ns
    ax_d.annotate('', xy=(fail_detect, 0.08),
                  xytext=(FAILURE_AT_NS, 0.08),
                  arrowprops=dict(arrowstyle='<->',
                                  color='black', lw=1.2,
                                  mutation_scale=9))
    ax_d.text((FAILURE_AT_NS + fail_detect) / 2, 0.20,
              f'$< 1.5 \\times T_{{CLKIN}}$ = {1.5*T_ns:.2f} ns',
              ha='center', fontsize=8, color='black')

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_summary()
    fig = plot_all()
    fig.canvas.manager.set_window_title('Component 06 — Toggle Detector')
    plt.show()


if __name__ == '__main__':
    main()
