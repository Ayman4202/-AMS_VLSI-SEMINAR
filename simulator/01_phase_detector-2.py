"""
=============================================================================
  COMPONENT 01 — Bang-Bang Phase Detector (BBPD)
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  What it does:
    Compares the rising edge of CLKREF against CLKFB.
    Outputs PD_ER = +1 (UP)   if CLKFB is LATE  (delay > period)
            PD_ER = -1 (DOWN) if CLKFB is EARLY (delay < period)

  Inputs  : f_clkin (any frequency), delta_t in ps
  Output  : PD_ER = +1 or -1

  Usage:
    Set F_CLKIN_HZ below to any frequency.
    Run:  python3 01_phase_detector.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  —  change to any frequency
# ─────────────────────────────────────────────────────────────────────────────
F_CLKIN_HZ       = 1.0e9     # Hz  — try 533e6, 800e6, 1e9, 4.26e9
DELTA_T_EARLY_PS = -200.0    # ps  — CLKFB leads CLKREF (early)
DELTA_T_LATE_PS  = +200.0    # ps  — CLKFB lags  CLKREF (late)

# ─────────────────────────────────────────────────────────────────────────────
# IEEE / MATLAB STYLE  —  white background, inward ticks, no grid
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
    'xtick.minor.size':   2,
    'ytick.minor.size':   2,
    'xtick.top':          True,
    'ytick.right':        True,
    'legend.frameon':     False,
    'legend.fontsize':    8,
    'axes.titlesize':     9,
    'axes.labelsize':     9,
    'lines.linewidth':    1.5,
})

# Color palette — matches IEEE paper convention
C_REF   = 'black'       # CLKREF
C_FB    = 'blue'        # CLKFB
C_UP    = '#008000'     # UP / +1
C_DOWN  = 'red'         # DOWN / -1
C_LOCK  = '#228B22'     # locked indicator (dashed green)


# ─────────────────────────────────────────────────────────────────────────────
# BBPD CLASS
# ─────────────────────────────────────────────────────────────────────────────

class BBPD:
    """
    Ideal Bang-Bang Phase Detector.
    No jitter, no analog effects — pure digital decision.

    Rule:
        delta_t >= 0  →  CLKFB late  →  PD_ER = +1  (UP)
        delta_t <  0  →  CLKFB early →  PD_ER = -1  (DOWN)
    """
    def __init__(self, f_clkin_hz: float):
        self.f_clkin = f_clkin_hz
        self.T_ps    = 1e12 / f_clkin_hz
        self.pd_er   = 0

    def compare(self, delta_t_ps: float) -> int:
        self.pd_er = 1 if delta_t_ps >= 0 else -1
        return self.pd_er


# ─────────────────────────────────────────────────────────────────────────────
# CLOCK WAVEFORM HELPER
# ─────────────────────────────────────────────────────────────────────────────

def make_square_wave(t_ps, period_ps, delay_ps=0.0):
    rise_ps   = period_ps * 0.03
    rise_norm = rise_ps / period_ps
    phase     = ((t_ps - delay_ps) % period_ps) / period_ps
    wave      = np.zeros_like(t_ps)
    for i, ph in enumerate(phase):
        if ph < rise_norm:
            wave[i] = ph / rise_norm
        elif ph < 0.5:
            wave[i] = 1.0
        elif ph < 0.5 + rise_norm:
            wave[i] = 1.0 - (ph - 0.5) / rise_norm
        else:
            wave[i] = 0.0
    return wave


def rising_edges(wave, t_ps):
    above = wave >= 0.5
    idx   = np.where(~above[:-1] & above[1:])[0]
    return t_ps[idx]


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(bbpd: BBPD):
    cases = [('Early',   DELTA_T_EARLY_PS),
             ('Aligned', 0.0),
             ('Late',    DELTA_T_LATE_PS)]
    print()
    print('=' * 52)
    print('  BBPD — Bang-Bang Phase Detector')
    print(f'  f_clkin = {bbpd.f_clkin/1e9:.3f} GHz  |  T = {bbpd.T_ps:.1f} ps')
    print('=' * 52)
    print(f"  {'Case':<10}  {'ΔT (ps)':>10}  {'PD_ER':>7}  Decision")
    print('  ' + '-' * 46)
    for lbl, dt in cases:
        pd  = bbpd.compare(dt)
        dec = 'UP   (+1)' if pd == 1 else 'DOWN (-1)'
        print(f'  {lbl:<10}  {dt:>10.1f}  {pd:>7}  {dec}')
    print('=' * 52)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(f_clkin_hz: float):
    """
    IEEE-style figure — three panels:
      (a) Bang-Bang transfer characteristic  PD_ER vs ΔT
      (b) Waveforms — Early / Aligned / Late cases
      (c) Block diagram — signal flow
    """
    T_ps     = 1e12 / f_clkin_hz
    bbpd_obj = BBPD(f_clkin_hz)
    t_ps     = np.linspace(0, 2.5 * T_ps, 3000)

    cases = [
        ('Early',   DELTA_T_EARLY_PS, C_DOWN),
        ('Aligned', 0.0,              C_UP),
        ('Late',    DELTA_T_LATE_PS,  C_FB),
    ]

    fig = plt.figure(figsize=(12, 9))
    fig.suptitle(
        f'Bang-Bang Phase Detector (BBPD)  —  '
        f'$f_{{clkin}}$ = {f_clkin_hz/1e9:.3f} GHz,  '
        f'$T$ = {T_ps:.1f} ps',
        fontsize=10, fontweight='bold', y=0.98
    )

    gs = gridspec.GridSpec(
        2, 3, figure=fig,
        height_ratios=[1.1, 1.0],
        hspace=0.45, wspace=0.38,
        left=0.08, right=0.97,
        top=0.93, bottom=0.08,
    )

    # ── (a) BANG-BANG CHARACTERISTIC ─────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :2])

    dt_sweep = np.linspace(-T_ps, T_ps, 4000)
    pd_out   = np.array([bbpd_obj.compare(dt) for dt in dt_sweep])

    # shaded regions
    ax_a.fill_between(dt_sweep[dt_sweep < 0],  -1, pd_out[dt_sweep < 0],
                      color=C_DOWN, alpha=0.08)
    ax_a.fill_between(dt_sweep[dt_sweep >= 0], 0,  pd_out[dt_sweep >= 0],
                      color=C_UP,   alpha=0.08)

    # step lines
    ax_a.plot(dt_sweep[dt_sweep < 0],  pd_out[dt_sweep < 0],
              color=C_DOWN, linewidth=2.0, label='$PD_{ER}$ = −1  (DOWN)')
    ax_a.plot(dt_sweep[dt_sweep >= 0], pd_out[dt_sweep >= 0],
              color=C_UP,   linewidth=2.0, label='$PD_{ER}$ = +1  (UP)')

    # zero lines
    ax_a.axvline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
    ax_a.axhline(0, color='black', linewidth=0.5, alpha=0.4)

    # operating points
    markers = [('o', C_DOWN, 'Early',   DELTA_T_EARLY_PS),
               ('s', C_UP,   'Aligned', 0.0),
               ('^', C_FB,   'Late',    DELTA_T_LATE_PS)]
    for mk, clr, lbl, dt in markers:
        pv = bbpd_obj.compare(dt)
        ax_a.plot(dt, pv, mk, color=clr, markersize=7,
                  markerfacecolor=clr, zorder=5, label=f'{lbl} ($\\Delta T$={dt:+.0f} ps)')

    ax_a.set_xlabel('$\\Delta T$ (ps)  =  VCDL delay $-$ $T_{clkin}$')
    ax_a.set_ylabel('$PD_{ER}$')
    ax_a.set_yticks([-1, 0, 1])
    ax_a.set_yticklabels(['$-$1 (DOWN)', '0', '+1 (UP)'])
    ax_a.set_ylim(-1.6, 1.6)
    ax_a.set_xlim(-T_ps * 1.05, T_ps * 1.05)
    ax_a.legend(loc='center right', fontsize=7.5)
    ax_a.set_title('(a)  Bang-Bang Transfer Characteristic',
                   loc='left', fontsize=9, fontweight='bold')

    # region labels
    ax_a.text(-T_ps * 0.52, -1.35, 'CLKFB early\n→ need more delay',
              ha='center', fontsize=7.5, color=C_DOWN)
    ax_a.text(+T_ps * 0.52, +1.22, 'CLKFB late\n→ need less delay',
              ha='center', fontsize=7.5, color=C_UP)

    # ── (b) BLOCK DIAGRAM ────────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[0, 2])
    ax_b.set_xlim(0, 10)
    ax_b.set_ylim(0, 6)
    ax_b.axis('off')
    ax_b.set_title('(b)  Signal Flow', loc='left',
                   fontsize=9, fontweight='bold')

    # BBPD box
    from matplotlib.patches import FancyBboxPatch, Rectangle
    bbpd_box = FancyBboxPatch((3.5, 1.8), 3.0, 2.4,
                               boxstyle='square,pad=0.0',
                               facecolor='white', edgecolor='black',
                               linewidth=1.2, zorder=3)
    ax_b.add_patch(bbpd_box)
    ax_b.text(5.0, 3.35, 'BBPD', ha='center', va='center',
              fontsize=11, fontweight='bold', color='black', zorder=4)
    ax_b.text(5.0, 2.65, 'Bang-Bang\nPhase Detector',
              ha='center', va='center', fontsize=7, color='gray', zorder=4)

    # CLKREF arrow
    ax_b.annotate('', xy=(3.5, 3.5), xytext=(1.2, 3.5),
                  arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
    ax_b.text(1.1, 3.5, '$CLKREF$', ha='right', va='center',
              fontsize=8, fontweight='bold')
    ax_b.text(2.35, 3.72, 'from DE1', ha='center', fontsize=6.5, color='gray')

    # CLKFB arrow
    ax_b.annotate('', xy=(3.5, 2.5), xytext=(1.2, 2.5),
                  arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
    ax_b.text(1.1, 2.5, '$CLKFB$', ha='right', va='center',
              fontsize=8, fontweight='bold')
    ax_b.text(2.35, 2.72, 'from DE9', ha='center', fontsize=6.5, color='gray')

    # PD_ER output arrow
    ax_b.annotate('', xy=(8.8, 3.0), xytext=(6.5, 3.0),
                  arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
    ax_b.text(9.0, 3.0, '$PD_{ER}$', ha='left', va='center',
              fontsize=8, fontweight='bold')
    ax_b.text(9.0, 3.55, '+1 (UP)',   ha='left', fontsize=7, color=C_UP)
    ax_b.text(9.0, 2.45, '$-$1 (DOWN)', ha='left', fontsize=7, color=C_DOWN)

    # Decision rule
    ax_b.text(5.0, 1.3,
              '$\\Delta T \\geq 0$ → +1 (UP)\n$\\Delta T < 0$  → $-$1 (DOWN)',
              ha='center', va='center', fontsize=7, color='black',
              bbox=dict(boxstyle='round,pad=0.3', fc='#f5f5f5',
                        ec='black', alpha=1.0, lw=0.7))

    # ── (c) WAVEFORMS — 3 sub-panels ─────────────────────────────────────────
    wave_labels = ['(c)  CLKFB Early', '(d)  CLKFB Aligned', '(e)  CLKFB Late']
    for col, (case_lbl, dt_ps, clr) in enumerate(cases):
        pd_val = bbpd_obj.compare(dt_ps)
        pd_clr = C_DOWN if pd_val == -1 else C_UP

        ax = fig.add_subplot(gs[1, col])

        clkref = make_square_wave(t_ps, T_ps, delay_ps=0.0)
        clkfb  = make_square_wave(t_ps, T_ps, delay_ps=dt_ps)

        # offsets: CLKREF top, CLKFB middle, PD_ER bottom
        REF_OFF  = 2.8
        FB_OFF   = 1.4
        PD_BOT   = 0.0
        PD_TOP   = 0.8

        ax.plot(t_ps, clkref + REF_OFF, color=C_REF, linewidth=1.4,
                label='$CLKREF$')
        ax.plot(t_ps, clkfb  + FB_OFF,  color=C_FB,  linewidth=1.4,
                label='$CLKFB$')

        # PD_ER bar
        ax.fill_between(t_ps, PD_BOT, PD_TOP,
                        color=pd_clr, alpha=0.35, step='pre')
        ax.plot([t_ps[0], t_ps[-1]], [PD_TOP, PD_TOP],
                color=pd_clr, linewidth=0.8, linestyle='-')
        ax.plot([t_ps[0], t_ps[-1]], [PD_BOT, PD_BOT],
                color='black', linewidth=0.5)

        # PD_ER label inside bar
        ax.text(t_ps[-1] * 0.05, (PD_BOT + PD_TOP) / 2,
                f'$PD_{{ER}}$ = {pd_val:+d}',
                color=pd_clr, fontsize=7.5, fontweight='bold', va='center')

        # dashed edge markers — scoped to each signal's zone
        ref_e = rising_edges(clkref, t_ps)
        fb_e  = rising_edges(clkfb,  t_ps)
        for re in ref_e[:2]:
            ax.plot([re, re], [REF_OFF, REF_OFF + 1.05],
                    color=C_REF, lw=0.7, ls='--', alpha=0.6)
        for fe in fb_e[:2]:
            ax.plot([fe, fe], [FB_OFF, FB_OFF + 1.05],
                    color=C_FB, lw=0.7, ls='--', alpha=0.6)

        # ΔT arrow between first rising edges
        if len(ref_e) > 0 and len(fb_e) > 0:
            re0, fe0 = ref_e[0], fb_e[0]
            y_arr = REF_OFF + 1.25
            ax.annotate('', xy=(fe0, y_arr), xytext=(re0, y_arr),
                        arrowprops=dict(arrowstyle='<->', color='black',
                                        lw=1.0, mutation_scale=8))
            sign = '+' if dt_ps >= 0 else ''
            ax.text((re0 + fe0) / 2, y_arr + 0.12,
                    f'$\\Delta T$ = {sign}{dt_ps:.0f} ps',
                    ha='center', va='bottom', fontsize=7.5, color='black')

        # y-axis labels
        ax.set_yticks([(PD_BOT + PD_TOP)/2, FB_OFF + 0.5, REF_OFF + 0.5])
        ax.set_yticklabels(['$PD_{ER}$', '$CLKFB$', '$CLKREF$'], fontsize=7)
        ax.set_ylim(-0.3, REF_OFF + 1.7)
        ax.set_xlim(t_ps[0], t_ps[-1])
        ax.set_xlabel('Time (ps)', fontsize=8)
        ax.set_title(wave_labels[col], loc='left',
                     fontsize=9, fontweight='bold')

        if col == 0:
            ax.legend(loc='upper right', fontsize=6.5,
                      handlelength=1.5, handletextpad=0.4)

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    bbpd = BBPD(F_CLKIN_HZ)
    print_summary(bbpd)
    fig = plot_all(F_CLKIN_HZ)
    fig.canvas.manager.set_window_title('Component 01 — BBPD Phase Detector')
    plt.show()


if __name__ == '__main__':
    main()
