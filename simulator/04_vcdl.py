"""
=============================================================================
  COMPONENT 04 — VCDL (Voltage-Controlled Delay Line)
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  Physical model:
    - 8 active Delay Elements (DE1 → DE8) between CLKREF and CLKFB
    - DE0 output = CLKREF (reference tap)
    - DE8 output = CLKFB  (feedback tap)
    - Each DE: current-starved inverter
    - delay_per_DE = KC / (V_DD - V_CTRLP - V_th)
    - total_delay  = N_DE × delay_per_DE
    - KC calibrated so total_delay(code=724) = T_clkin exactly

  Curve direction (matches paper Fig. 4):
    code ↑ → V_DAC ↑ → V_CTRLP ↑ → pMOS V_SG ↓ → less current → delay ↑
    At code=0:    ΔT < 0  (CLKFB early)
    At code=724:  ΔT = 0  (locked)
    At code=1023: ΔT > 0  (CLKFB late)

  Usage:
    python3 04_vcdl.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
F_CLKIN   = 1.0e9
V_DD      = 0.75
V_TH      = 0.25
V_REF     = 0.375
DAC_BITS  = 10
DAC_CODES = 2**DAC_BITS
N_DE      = 8
LOCK_CODE = 724

BS_CODES  = [0, 512, 768, 640, 704, 736, 720, 728, 724, 726, 725, 724]

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
C_CURVE   = 'black'
C_LOCK    = '#228B22'
C_EARLY   = 'blue'
C_LATE    = 'red'
C_BS      = 'darkorange'
C_DE      = 'red'
C_REF     = 'black'
C_FB      = 'blue'


# ─────────────────────────────────────────────────────────────────────────────
# VCDL CLASS
# ─────────────────────────────────────────────────────────────────────────────

class VCDL:
    """
    Nonlinear VCDL — 8 active delay elements.
    delay_per_DE(code) = KC / (V_DD - V_DAC(code) - V_th)
    total_delay(code)  = N_DE × delay_per_DE(code)
    delta_t(code)      = total_delay(code) - T_clkin
    KC calibrated so delta_t(LOCK_CODE) = 0.
    """
    def __init__(self):
        self.T_ps   = 1e12 / F_CLKIN
        v_lock      = (LOCK_CODE / DAC_CODES) * V_REF
        denom_l     = V_DD - v_lock - V_TH
        self.KC     = (self.T_ps / N_DE) * denom_l

    def v_dac(self, code):
        code = int(np.clip(code, 0, DAC_CODES - 1))
        return (code / DAC_CODES) * V_REF

    def delay_per_de(self, code):
        v   = self.v_dac(code)
        den = max(V_DD - v - V_TH, 1e-9)
        return self.KC / den

    def total_delay(self, code):
        return N_DE * self.delay_per_de(code)

    def delta_t(self, code):
        return self.total_delay(code) - self.T_ps

    def delay_curve(self):
        codes  = np.arange(DAC_CODES)
        delays = np.array([self.total_delay(c) for c in codes])
        deltas = delays - self.T_ps
        return codes, delays, deltas


# ─────────────────────────────────────────────────────────────────────────────
# SQUARE WAVE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def square_wave(t_ps, period_ps, delay_ps=0.0):
    rise = 0.03
    ph   = ((t_ps - delay_ps) % period_ps) / period_ps
    w    = np.zeros_like(t_ps)
    for i, p in enumerate(ph):
        if   p < rise:       w[i] = p / rise
        elif p < 0.5:        w[i] = 1.0
        elif p < 0.5 + rise: w[i] = 1.0 - (p - 0.5) / rise
    return w


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(vcdl: VCDL):
    print()
    print('=' * 58)
    print('  VCDL — Voltage-Controlled Delay Line')
    print(f'  f_clkin={F_CLKIN/1e9:.2f} GHz  T={vcdl.T_ps:.1f} ps  '
          f'N_DE={N_DE}  Lock code={LOCK_CODE}')
    print('=' * 58)
    print(f"  {'Code':>6}  {'V_DAC(mV)':>10}  "
          f"{'Delay/DE(ps)':>13}  {'Total(ps)':>10}  {'ΔT(ps)':>8}")
    print('  ' + '-' * 54)
    for c in [0, 256, 512, LOCK_CODE, 768, 1023]:
        vd = vcdl.v_dac(c) * 1e3
        dp = vcdl.delay_per_de(c)
        td = vcdl.total_delay(c)
        dt = vcdl.delta_t(c)
        print(f'  {c:>6}  {vd:>10.2f}  {dp:>13.2f}  '
              f'{td:>10.2f}  {dt:>+8.2f}')
    print('=' * 58)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(vcdl: VCDL):
    T_ps             = vcdl.T_ps
    codes, _, deltas = vcdl.delay_curve()

    fig = plt.figure(figsize=(14, 11))
    fig.suptitle(
        f'VCDL  —  $f_{{clkin}}$ = {F_CLKIN/1e9:.2f} GHz,  '
        f'$T$ = {T_ps:.0f} ps,  $N_{{DE}}$ = {N_DE},  '
        f'Lock code = {LOCK_CODE}',
        fontsize=10, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        3, 2, figure=fig,
        height_ratios=[0.85, 1.2, 1.1],
        hspace=0.50, wspace=0.32,
        left=0.08, right=0.96,
        top=0.94, bottom=0.07,
    )

    # ── (a) BLOCK DIAGRAM ────────────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, :])
    ax_a.set_xlim(0, 18)
    ax_a.set_ylim(0, 3.2)
    ax_a.axis('off')
    ax_a.set_title('(a)  VCDL Structure — 8 Active DEs + Reference + Dummy',
                   loc='left', fontsize=9, fontweight='bold')

    labels = ['DE0\n(ref)', 'DE1', 'DE2', 'DE3', 'DE4',
              'DE5', 'DE6', 'DE7', 'DE8', 'DE9\ndummy']
    de_colors = ['red'] + ['blue']*8 + ['gray']
    xs    = [1.0 + i * 1.72 for i in range(10)]
    y0    = 1.8

    # CLKIN arrow
    ax_a.annotate('', xy=(0.38, y0 + 0.12), xytext=(0.05, y0 + 0.12),
                  arrowprops=dict(arrowstyle='->', color='black',
                                  lw=1.2, mutation_scale=10))
    ax_a.text(-0.05, y0 + 0.12, 'CLKIN', ha='right', va='center',
              fontsize=8, fontweight='bold')

    for i, (lbl, col, x) in enumerate(zip(labels, de_colors, xs)):
        ax_a.add_patch(FancyBboxPatch(
            (x - 0.6, y0 - 0.28), 1.2, 0.80,
            boxstyle='square,pad=0.0',
            facecolor='white', edgecolor=col,
            linewidth=1.3, zorder=3))
        ax_a.text(x, y0 + 0.10, lbl, ha='center', va='center',
                  fontsize=7, fontweight='bold', color=col, zorder=4)

        if i < 9:
            ax_a.annotate('', xy=(xs[i+1] - 0.6, y0 + 0.10),
                          xytext=(x + 0.6, y0 + 0.10),
                          arrowprops=dict(arrowstyle='->', color='black',
                                          lw=0.8, mutation_scale=8))
        # CLKREF tap
        if i == 0:
            ax_a.annotate('', xy=(x, y0 - 0.28), xytext=(x, y0 - 0.72),
                          arrowprops=dict(arrowstyle='->', color='red',
                                          lw=1.2, mutation_scale=9))
            ax_a.text(x, y0 - 0.82, 'CLKREF', ha='center', va='top',
                      fontsize=7.5, fontweight='bold', color='red')

        # CLKFB tap
        if i == 8:
            ax_a.annotate('', xy=(x, y0 - 0.28), xytext=(x, y0 - 0.72),
                          arrowprops=dict(arrowstyle='->', color='blue',
                                          lw=1.2, mutation_scale=9))
            ax_a.text(x, y0 - 0.82, 'CLKFB', ha='center', va='top',
                      fontsize=7.5, fontweight='bold', color='blue')

    # V_CTRL rail
    mid_x = (xs[1] + xs[8]) / 2
    ax_a.plot([xs[1] - 0.5, xs[8] + 0.5], [y0 - 0.52, y0 - 0.52],
              color='darkorange', linewidth=1.2, linestyle='--')
    ax_a.text(mid_x, y0 - 0.62, '$V_{CTRL}$ — same to all 8 active DEs',
              ha='center', va='top', fontsize=7.5, color='darkorange')

    # 8 DE brace
    ax_a.annotate('', xy=(xs[8] + 0.6, y0 + 0.65),
                  xytext=(xs[1] - 0.6, y0 + 0.65),
                  arrowprops=dict(arrowstyle='<->', color='black',
                                  lw=1.0, mutation_scale=8))
    ax_a.text(mid_x, y0 + 0.75,
              '8 active DEs — total delay = $T_{clkin}$ at lock',
              ha='center', va='bottom', fontsize=7.5, color='black')

    # ── (b) ΔT vs DAC CODE ───────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[1, 0])

    ax_b.plot(codes, deltas, color=C_CURVE, linewidth=2.0,
              label='$\\Delta T$ = total delay $-$ $T_{clkin}$')

    # Shaded regions
    ax_b.fill_between(codes, deltas, 0, where=(deltas < 0),
                      color=C_EARLY, alpha=0.08,
                      label='CLKFB early  ($\\Delta T$ < 0)')
    ax_b.fill_between(codes, deltas, 0, where=(deltas > 0),
                      color=C_LATE,  alpha=0.08,
                      label='CLKFB late   ($\\Delta T$ > 0)')

    # Lock lines
    ax_b.axhline(0, color=C_LOCK, linewidth=1.2, linestyle='--',
                 label='$\\Delta T$ = 0  (lock)')
    ax_b.axvline(LOCK_CODE, color=C_LOCK, linewidth=0.8,
                 linestyle=':', alpha=0.7)

    # BS search path — connecting line
    bs_dt = [vcdl.delta_t(c) for c in BS_CODES]
    ax_b.plot(BS_CODES, bs_dt, color=C_BS, linewidth=1.0,
              linestyle='--', alpha=0.6, zorder=3)

    # BS dots
    for i, (c, dt) in enumerate(zip(BS_CODES, bs_dt)):
        is_lock = (i == len(BS_CODES) - 1)
        col  = C_LOCK if is_lock else C_BS
        size = 8 if is_lock else 5
        ax_b.plot(c, dt, 'o', color=col, markersize=size, zorder=5)

    # Labels — only sparse steps
    for i in [0, 2, 4, len(BS_CODES)-1]:
        c, dt   = BS_CODES[i], bs_dt[i]
        is_lock = (i == len(BS_CODES) - 1)
        col     = C_LOCK if is_lock else C_BS
        y_off   = 18 if i % 4 == 0 else -22
        lbl     = f'Lock ({c})' if is_lock else f'step {i} ({c})'
        ax_b.text(c + 12, dt + y_off, lbl,
                  fontsize=7, color=col,
                  va='bottom' if y_off > 0 else 'top')

    ax_b.set_xlabel('DAC Code')
    ax_b.set_ylabel('$\\Delta T$  (ps)')
    ax_b.set_xlim(-20, DAC_CODES + 20)
    ax_b.legend(loc='upper left', fontsize=7.5)
    ax_b.set_title('(b)  $\\Delta T$ vs DAC Code',
                   loc='left', fontsize=9, fontweight='bold')

    # Region labels
    ax_b.text(250, min(deltas)*0.55, 'CLKFB early\n→ increase code',
              ha='center', fontsize=7.5, color=C_EARLY)
    ax_b.text(850, max(deltas)*0.55, 'CLKFB late\n→ decrease code',
              ha='center', fontsize=7.5, color=C_LATE)

    # ── (c) DE DELAY vs V_CTRL ───────────────────────────────────────────────
    ax_c = fig.add_subplot(gs[1, 1])

    v_range  = np.linspace(0, V_REF * 0.97, 500)
    de_delay = np.array([vcdl.KC / max(V_DD - v - V_TH, 1e-9)
                         for v in v_range])

    ax_c.plot(v_range * 1e3, de_delay, color=C_CURVE, linewidth=2.0,
              label=r'$t_{DE} = K_C\,/\,(V_{DD} - V_{CTRL} - V_{th})$')

    # Operating points
    for code_m, lbl, col in [
        (0,         'code=0',          C_LATE),
        (512,       'code=512',        'black'),
        (LOCK_CODE, f'code={LOCK_CODE}\n(lock)', C_LOCK),
    ]:
        v_m = vcdl.v_dac(code_m)
        d_m = vcdl.delay_per_de(code_m)
        ax_c.plot(v_m * 1e3, d_m, 'o', color=col, markersize=6, zorder=5)
        ax_c.annotate(lbl, xy=(v_m * 1e3, d_m),
                      xytext=(10, 5), textcoords='offset points',
                      fontsize=7.5, color=col,
                      arrowprops=dict(arrowstyle='->', color=col, lw=0.7))

    ax_c.set_xlabel('$V_{CTRL}$  (mV)')
    ax_c.set_ylabel('Delay per DE  (ps)')
    ax_c.set_xlim(-5, V_REF * 1e3 + 5)
    ax_c.legend(loc='upper left', fontsize=7.5)
    ax_c.set_title('(c)  Single DE Delay vs $V_{CTRL}$  (hyperbolic)',
                   loc='left', fontsize=9, fontweight='bold')

    # Equation annotation
    ax_c.text(0.97, 0.97,
              f'$V_{{DD}}$={V_DD} V,  $V_{{th}}$={V_TH} V,  '
              f'$V_{{ref}}$={V_REF} V',
              ha='right', va='top', fontsize=7.5, color='gray',
              transform=ax_c.transAxes)

    # ── (d) CLOCK WAVEFORMS ──────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[2, :])

    t_ps = np.linspace(0, 3 * T_ps, 3000)

    snapshots = [
        (BS_CODES[0],  0.0, 'Step 0   code=0',           C_LATE),
        (BS_CODES[4],  3.2, 'Step 4   code=704',          'darkorange'),
        (LOCK_CODE,    6.4, f'Locked   code={LOCK_CODE}', C_LOCK),
    ]

    for code_s, offset, lbl, col in snapshots:
        dt_val = vcdl.delta_t(code_s)
        clkref = square_wave(t_ps, T_ps, delay_ps=0.0)
        clkfb  = square_wave(t_ps, T_ps, delay_ps=dt_val)

        ax_d.plot(t_ps, clkref * 0.85 + offset + 1.1,
                  color=C_REF, linewidth=1.4, alpha=0.85)
        ax_d.plot(t_ps, clkfb  * 0.85 + offset,
                  color=col,   linewidth=1.6)

        # Signal labels
        ax_d.text(t_ps[-1] * 1.005, offset + 1.55, 'CLKREF',
                  va='center', fontsize=6.5, color=C_REF)
        ax_d.text(t_ps[-1] * 1.005, offset + 0.42, 'CLKFB',
                  va='center', fontsize=6.5, color=col)

        # Step info
        ax_d.text(t_ps[-1] * 1.22, offset + 0.9,
                  f'{lbl}\n$\\Delta T$ = {dt_val:+.1f} ps',
                  va='center', ha='center', fontsize=7.5, color=col)

    ax_d.set_xlim(-T_ps * 0.05, t_ps[-1] * 1.38)
    ax_d.set_ylim(-0.3, 8.8)
    ax_d.set_yticks([])
    ax_d.set_xlabel('Time (ps)')
    ax_d.set_title(
        '(d)  Clock Waveforms — CLKREF vs CLKFB at 3 BS steps',
        loc='left', fontsize=9, fontweight='bold')

    # Row separators
    for sep in [3.0, 6.2]:
        ax_d.axhline(sep, color='black', linewidth=0.5,
                     linestyle='--', alpha=0.3)

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    vcdl = VCDL()
    print_summary(vcdl)
    fig = plot_all(vcdl)
    fig.canvas.manager.set_window_title(
        f'Component 04 — VCDL  |  '
        f'f_clkin={F_CLKIN/1e9:.2f}GHz  Lock code={LOCK_CODE}')
    plt.show()


if __name__ == '__main__':
    main()
