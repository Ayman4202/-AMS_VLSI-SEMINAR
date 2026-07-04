"""
=============================================================================
  COMPONENT 05 — ÷N Clock Divider
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  What it does:
    Divides CLKIN by N to produce CLKCTRL.
    CLKCTRL is the slow clock that drives the BS-FSM.
    Running the FSM at lower frequency gives the DAC time to settle.

  Formula:
    f_CLKCTRL = f_CLKIN / N
    T_CLKCTRL = N × T_CLKIN

  N values from paper:
    N=1  at 533 MHz and 800 MHz
    N=4  at 4.26 GHz

  Usage:
    python3 05_divider.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
F_CLKIN  = 1.0e9    # Hz — input clock (configurable)
N_DIV    = 4        # division ratio (1, 2, 4, 6, 8 supported by paper)

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
C_CLKIN   = 'black'
C_CLKCTRL = 'blue'
C_ACTIVE  = '#228B22'
C_BAR     = 'black'
C_BAR2    = 'red'


# ─────────────────────────────────────────────────────────────────────────────
# DIVIDER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ClockDivider:
    """
    Integer clock divider.
    Divides CLKIN by N to produce CLKCTRL.
    CLKCTRL toggles every N/2 CLKIN cycles (50% duty cycle).
    """
    def __init__(self, f_clkin: float = F_CLKIN, n: int = N_DIV):
        self.f_clkin   = f_clkin
        self.n         = n
        self.T_clkin   = 1e12 / f_clkin
        self.f_clkctrl = f_clkin / n
        self.T_clkctrl = self.T_clkin * n

    def clkin_wave(self, t_ps):
        return self._square(t_ps, self.T_clkin)

    def clkctrl_wave(self, t_ps):
        return self._square(t_ps, self.T_clkctrl)

    def _square(self, t_ps, period_ps, rise=0.02):
        ph = (t_ps % period_ps) / period_ps
        w  = np.zeros_like(t_ps)
        for i, p in enumerate(ph):
            if   p < rise:       w[i] = p / rise
            elif p < 0.5:        w[i] = 1.0
            elif p < 0.5 + rise: w[i] = 1.0 - (p - 0.5) / rise
        return w


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(div: ClockDivider):
    print()
    print('=' * 50)
    print('  ÷N Clock Divider')
    print(f'  f_CLKIN    = {div.f_clkin/1e9:.3f} GHz')
    print(f'  N          = {div.n}')
    print(f'  f_CLKCTRL  = {div.f_clkctrl/1e6:.3f} MHz')
    print(f'  T_CLKIN    = {div.T_clkin:.1f} ps')
    print(f'  T_CLKCTRL  = {div.T_clkctrl:.1f} ps')
    print('=' * 50)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(div: ClockDivider):
    """
    Four panels — IEEE style:
      (a) Block diagram
      (b) CLKIN vs CLKCTRL waveforms
      (c) f_CLKCTRL vs N  (bar chart)
      (d) T_CLKCTRL vs N  (bar chart)
    """
    fig = plt.figure(figsize=(13, 10))
    fig.suptitle(
        f'$\\div N$ Clock Divider  —  '
        f'$f_{{CLKIN}}$ = {div.f_clkin/1e9:.3f} GHz,  '
        f'$N$ = {div.n},  '
        f'$f_{{CLKCTRL}}$ = {div.f_clkctrl/1e6:.1f} MHz',
        fontsize=10, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        3, 2, figure=fig,
        height_ratios=[0.85, 1.3, 1.1],
        hspace=0.50, wspace=0.32,
        left=0.08, right=0.96,
        top=0.94, bottom=0.07,
    )

    # ── (a) BLOCK DIAGRAM ────────────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.set_xlim(0, 14)
    ax_a.set_ylim(0, 3)
    ax_a.axis('off')
    ax_a.set_title('(a)  Signal Flow', loc='left',
                   fontsize=9, fontweight='bold')

    # Divider box
    ax_a.add_patch(FancyBboxPatch(
        (4.5, 0.7), 3.2, 1.6,
        boxstyle='square,pad=0.0',
        facecolor='white', edgecolor='black',
        linewidth=1.2, zorder=3))
    ax_a.text(6.1, 1.72, f'$\\div${div.n}',
              ha='center', va='center', fontsize=18,
              fontweight='bold', color='black', zorder=4)
    ax_a.text(6.1, 1.08, 'Clock Divider',
              ha='center', va='center', fontsize=8.5,
              color='gray', zorder=4)

    # CLKIN input
    ax_a.annotate('', xy=(4.5, 1.5), xytext=(2.0, 1.5),
                  arrowprops=dict(arrowstyle='->', color='black',
                                  lw=1.2, mutation_scale=10))
    ax_a.text(1.9, 1.5, 'CLKIN', ha='right', va='center',
              fontsize=9, fontweight='bold')
    ax_a.text(3.25, 1.72,
              f'{div.f_clkin/1e9:.2f} GHz\n$T$ = {div.T_clkin:.0f} ps',
              ha='center', fontsize=7.5, color='gray')

    # CLKCTRL output
    ax_a.annotate('', xy=(10.0, 1.5), xytext=(7.7, 1.5),
                  arrowprops=dict(arrowstyle='->', color='black',
                                  lw=1.2, mutation_scale=10))
    ax_a.text(10.15, 1.5, 'CLKCTRL', ha='left', va='center',
              fontsize=9, fontweight='bold')
    ax_a.text(10.15, 1.08, '→ to BS-FSM',
              ha='left', fontsize=7.5, color='gray')
    ax_a.text(8.85, 1.72,
              f'{div.f_clkctrl/1e6:.1f} MHz\n$T$ = {div.T_clkctrl:.0f} ps',
              ha='center', fontsize=7.5, color='gray')

    # Formula box
    ax_a.text(6.1, 2.75,
              f'$f_{{CLKCTRL}} = f_{{CLKIN}} / N = '
              f'{div.f_clkin/1e9:.2f}$ GHz $/ {div.n} = '
              f'{div.f_clkctrl/1e6:.1f}$ MHz',
              ha='center', va='center', fontsize=8.5,
              bbox=dict(boxstyle='round,pad=0.3', fc='#f5f5f5',
                        ec='black', lw=0.7))

    # ── (b) WAVEFORMS ────────────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1, :])

    t_ps   = np.linspace(0, 4 * div.T_clkctrl, 4000)
    clkin  = div.clkin_wave(t_ps)
    clkctl = div.clkctrl_wave(t_ps)

    # CLKIN top lane, CLKCTRL bottom lane
    ax_b.plot(t_ps, clkin  + 1.3, color=C_CLKIN,   linewidth=1.6,
              label=f'CLKIN  ({div.f_clkin/1e9:.2f} GHz)')
    ax_b.plot(t_ps, clkctl,       color=C_CLKCTRL, linewidth=2.0,
              label=f'CLKCTRL  ({div.f_clkctrl/1e6:.1f} MHz)')

    # CLKIN edge markers (dotted)
    for k in range(4 * div.n + 1):
        t_edge = k * div.T_clkin
        if t_edge <= t_ps[-1]:
            ax_b.axvline(t_edge, color=C_CLKIN, linewidth=0.5,
                         linestyle=':', alpha=0.35)

    # CLKCTRL edge markers (dashed)
    for k in range(5):
        t_edge = k * div.T_clkctrl
        if t_edge <= t_ps[-1]:
            ax_b.axvline(t_edge, color=C_CLKCTRL, linewidth=0.8,
                         linestyle='--', alpha=0.5)

    # Brace: N × T_CLKIN = T_CLKCTRL
    y_brace = 2.55
    ax_b.annotate('', xy=(div.T_clkctrl, y_brace),
                  xytext=(0, y_brace),
                  arrowprops=dict(arrowstyle='<->',
                                  color='black', lw=1.2,
                                  mutation_scale=10))
    ax_b.text(div.T_clkctrl / 2, y_brace + 0.08,
              f'$N \\times T_{{CLKIN}}$ = $T_{{CLKCTRL}}$  '
              f'({div.n} × {div.T_clkin:.0f} ps = {div.T_clkctrl:.0f} ps)',
              ha='center', va='bottom', fontsize=8.5, color='black')

    # Lane labels
    ax_b.text(-t_ps[-1]*0.01, 1.8,  'CLKIN',   ha='right',
              fontsize=8, color=C_CLKIN,   fontweight='bold')
    ax_b.text(-t_ps[-1]*0.01, 0.5,  'CLKCTRL', ha='right',
              fontsize=8, color=C_CLKCTRL, fontweight='bold')

    ax_b.set_xlim(-t_ps[-1]*0.02, t_ps[-1]*1.02)
    ax_b.set_ylim(-0.2, 2.9)
    ax_b.set_yticks([])
    ax_b.set_xlabel('Time (ps)')
    ax_b.legend(loc='upper right', fontsize=8.5)
    ax_b.set_title('(b)  CLKIN vs CLKCTRL Waveforms',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (c) f_CLKCTRL vs N ───────────────────────────────────────────────────
    ax_c = fig.add_subplot(gs[2, 0])

    n_vals = [1, 2, 4, 6, 8]
    f_vals = [div.f_clkin / n / 1e6 for n in n_vals]
    bar_colors = [C_ACTIVE if n == div.n else C_BAR for n in n_vals]

    bars = ax_c.bar(range(len(n_vals)), f_vals,
                    color=bar_colors, width=0.55, zorder=3)

    for bar, fv, n in zip(bars, f_vals, n_vals):
        ax_c.text(bar.get_x() + bar.get_width()/2,
                  fv + max(f_vals)*0.02,
                  f'{fv:.0f}', ha='center', fontsize=8, color='black')

    ax_c.set_xticks(range(len(n_vals)))
    ax_c.set_xticklabels([f'$N$={n}' for n in n_vals])
    ax_c.set_xlabel('Division Ratio $N$')
    ax_c.set_ylabel('$f_{CLKCTRL}$ (MHz)')
    ax_c.set_ylim(0, max(f_vals) * 1.18)

    # Legend patch
    import matplotlib.patches as mpatches
    active_patch = mpatches.Patch(color=C_ACTIVE,
                                  label=f'Current $N$={div.n}')
    ax_c.legend(handles=[active_patch], loc='upper right', fontsize=8)
    ax_c.set_title('(c)  $f_{CLKCTRL}$ vs $N$',
                   loc='left', fontsize=9, fontweight='bold')

    # ── (d) T_CLKCTRL vs N ───────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[2, 1])

    t_vals     = [div.T_clkin * n for n in n_vals]
    bar_colors2 = [C_ACTIVE if n == div.n else C_BAR2 for n in n_vals]

    bars2 = ax_d.bar(range(len(n_vals)), t_vals,
                     color=bar_colors2, width=0.55, zorder=3,
                     alpha=0.85)

    for bar, tv in zip(bars2, t_vals):
        ax_d.text(bar.get_x() + bar.get_width()/2,
                  tv + max(t_vals)*0.02,
                  f'{tv:.0f}', ha='center', fontsize=8, color='black')

    ax_d.set_xticks(range(len(n_vals)))
    ax_d.set_xticklabels([f'$N$={n}' for n in n_vals])
    ax_d.set_xlabel('Division Ratio $N$')
    ax_d.set_ylabel('$T_{CLKCTRL}$ (ps)')
    ax_d.set_ylim(0, max(t_vals) * 1.18)

    active_patch2 = mpatches.Patch(color=C_ACTIVE,
                                   label=f'Current $N$={div.n}')
    ax_d.legend(handles=[active_patch2], loc='upper left', fontsize=8)
    ax_d.set_title('(d)  $T_{CLKCTRL}$ vs $N$',
                   loc='left', fontsize=9, fontweight='bold')

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    div = ClockDivider(F_CLKIN, N_DIV)
    print_summary(div)
    fig = plot_all(div)
    fig.canvas.manager.set_window_title(
        f'Component 05 — ÷N Divider  |  N={N_DIV}  |  '
        f'f_CLKIN={F_CLKIN/1e9:.2f}GHz')
    plt.show()


if __name__ == '__main__':
    main()
