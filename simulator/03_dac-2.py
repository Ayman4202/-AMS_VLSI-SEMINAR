"""
=============================================================================
  COMPONENT 03 — 10-bit DAC (Digital-to-Analog Converter)
  Based on: Wainstein et al., IEEE OJ-SSCS 2025

  What it does:
    Converts a 10-bit digital code (0 → 1023) into an analog
    voltage V_CTRL that controls the VCDL delay.

  Formula:
    V_CTRL = (code / 2^B) × V_ref

  Parameters:
    B     = 10 bits  →  1024 codes
    V_ref = 0.375 V  (paper value, configurable)
    ΔV_LSB = V_ref / 1024 ≈ 0.366 mV  (smallest voltage step)

  Usage:
    Set V_REF below to any value.
    Run:  python3 03_dac.py
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DAC_BITS  = 10
DAC_CODES = 2**DAC_BITS        # 1024
V_REF     = 0.375              # V — reference voltage (paper: 0.375 V)

# BS code sequence from FSM (lock code = 724, same as paper Fig. 5b)
BS_SEQUENCE = [0, 512, 768, 640, 704, 736, 720, 728, 724, 726, 725, 724,
               724, 725, 724, 725, 724, 725, 724]

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
C_TRANSFER = 'blue'
C_LOCK     = '#228B22'
C_VCTRL    = 'black'
C_CODE     = 'blue'
C_VREF     = 'red'
C_LSB      = 'red'
C_DNL      = '#008000'
C_INL      = 'blue'
C_LIMIT    = 'darkorange'


# ─────────────────────────────────────────────────────────────────────────────
# DAC CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DAC:
    """
    Ideal 10-bit DAC.
    Transfer function:  V_CTRL = (code / 2^B) × V_ref
    No nonlinearity, no DNL/INL — ideal model.
    """
    def __init__(self, v_ref: float = V_REF, bits: int = DAC_BITS):
        self.v_ref  = v_ref
        self.bits   = bits
        self.codes  = 2**bits
        self.dv_lsb = v_ref / self.codes

    def convert(self, code: int) -> float:
        code = int(np.clip(code, 0, self.codes - 1))
        return (code / self.codes) * self.v_ref

    def code_from_voltage(self, v: float) -> int:
        return int(np.clip(round(v / self.v_ref * self.codes),
                           0, self.codes - 1))

    def convert_sequence(self, codes) -> np.ndarray:
        return np.array([self.convert(c) for c in codes])


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(dac: DAC):
    print()
    print('=' * 48)
    print('  DAC — 10-bit Digital-to-Analog Converter')
    print(f'  V_ref   = {dac.v_ref:.3f} V')
    print(f'  B       = {dac.bits} bits  →  {dac.codes} codes')
    print(f'  ΔV_LSB  = {dac.dv_lsb*1e3:.3f} mV  (smallest step)')
    print('=' * 48)
    print(f"  {'Code':>6}    {'V_CTRL (mV)':>12}    {'% of V_ref':>10}")
    print('  ' + '-' * 40)
    for code in [0, 256, 512, 724, 768, 1023]:
        v   = dac.convert(code)
        pct = v / dac.v_ref * 100
        print(f'  {code:>6}    {v*1e3:>12.3f}    {pct:>9.1f}%')
    print('=' * 48)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE — IEEE STYLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_all(dac: DAC):
    """
    Four panels — IEEE style:
      (a) Block diagram
      (b) Transfer curve  V_CTRL vs code
      (c) DNL / INL       (ideal = 0)
      (d) Transient       V_CTRL vs CLKCTRL cycle
    """
    codes_arr = np.arange(dac.codes)
    v_arr     = dac.convert_sequence(codes_arr) * 1e3   # mV

    cycles   = np.arange(len(BS_SEQUENCE))
    v_seq    = dac.convert_sequence(BS_SEQUENCE) * 1e3
    code_seq = np.array(BS_SEQUENCE)
    v_lock   = dac.convert(724) * 1e3

    fig = plt.figure(figsize=(13, 10))
    fig.suptitle(
        f'10-bit DAC  —  $V_{{ref}}$ = {dac.v_ref:.3f} V,  '
        f'$\\Delta V_{{LSB}}$ = {dac.dv_lsb*1e3:.3f} mV,  '
        f'Codes = {dac.codes}',
        fontsize=10, fontweight='bold', y=0.99
    )

    gs = gridspec.GridSpec(
        2, 2, figure=fig,
        height_ratios=[1.0, 1.1],
        hspace=0.45, wspace=0.35,
        left=0.08, right=0.97,
        top=0.94, bottom=0.08,
    )


    # ── (a) BLOCK DIAGRAM ────────────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, 0])
    ax_a.set_xlim(0, 10)
    ax_a.set_ylim(0, 5)
    ax_a.axis('off')
    ax_a.set_title('(a)  Signal Flow', loc='left',
                   fontsize=9, fontweight='bold')

    # DAC box
    ax_a.add_patch(FancyBboxPatch(
        (3.5, 1.5), 3.0, 2.0,
        boxstyle='square,pad=0.0',
        facecolor='white', edgecolor='black',
        linewidth=1.2, zorder=3))
    ax_a.text(5.0, 2.8, 'DAC', ha='center', va='center',
              fontsize=13, fontweight='bold', color='black', zorder=4)
    ax_a.text(5.0, 2.1, '10-bit\nDigital → Analog',
              ha='center', va='center', fontsize=7.5,
              color='gray', zorder=4)

    # code input
    ax_a.annotate('', xy=(3.5, 3.0), xytext=(1.2, 3.0),
                  arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
    ax_a.text(1.1, 3.0, 'code[9:0]', ha='right', va='center',
              fontsize=8, fontweight='bold')
    ax_a.text(2.35, 3.22, 'from BS-FSM', ha='center',
              fontsize=6.5, color='gray')

    # V_ref input
    ax_a.annotate('', xy=(5.0, 1.5), xytext=(5.0, 0.7),
                  arrowprops=dict(arrowstyle='->', color=C_VREF, lw=1.2))
    ax_a.text(5.0, 0.5, f'$V_{{ref}}$ = {dac.v_ref:.3f} V',
              ha='center', va='center', fontsize=8,
              fontweight='bold', color=C_VREF)

    # V_CTRL output
    ax_a.annotate('', xy=(8.8, 2.5), xytext=(6.5, 2.5),
                  arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
    ax_a.text(9.0, 2.5, '$V_{CTRL}$', ha='left', va='center',
              fontsize=8, fontweight='bold')
    ax_a.text(9.0, 2.1, '→ VCDL', ha='left',
              fontsize=7, color='gray')

    # Formula
    ax_a.text(5.0, 4.5,
              r'$V_{CTRL} = \frac{code}{2^{10}} \times V_{ref}$'
              f'          $\\Delta V_{{LSB}}$ = {dac.dv_lsb*1e3:.3f} mV',
              ha='center', va='center', fontsize=8.5,
              bbox=dict(boxstyle='round,pad=0.3', fc='#f5f5f5',
                        ec='black', lw=0.7))

    # ── (b) TRANSFER CURVE ───────────────────────────────────────────────────
    ax_b = fig.add_subplot(gs[0, 1])

    ax_b.plot(codes_arr, v_arr, color=C_TRANSFER, linewidth=1.8,
              label=r'$V_{CTRL} = \frac{code}{1024} \times V_{ref}$')

    # Key operating points
    key_pts = [
        (0,    C_VREF,   'below'),
        (512,  'black',  'below'),
        (724,  C_LOCK,   'above'),
        (1023, C_VREF,   'below'),
    ]
    for code_k, col, pos in key_pts:
        v_k = dac.convert(code_k) * 1e3
        ax_b.plot(code_k, v_k, 'o', color=col, markersize=6, zorder=5)
        y_off = 8 if pos == 'above' else -14
        ax_b.annotate(
            f'{code_k}\n({v_k:.1f} mV)',
            xy=(code_k, v_k),
            xytext=(code_k + 55, v_k + y_off),
            fontsize=7, color=col,
            arrowprops=dict(arrowstyle='->', color=col, lw=0.7))

    # LSB inset
    ax_ins = ax_b.inset_axes([0.55, 0.06, 0.40, 0.32])
    ax_ins.tick_params(direction='in', labelsize=6)
    ax_ins.spines[:].set_color('black')
    zoom_codes = np.arange(510, 516)
    zoom_v     = dac.convert_sequence(zoom_codes) * 1e3
    ax_ins.step(zoom_codes, zoom_v, where='post',
                color=C_TRANSFER, linewidth=1.2)
    ax_ins.plot(zoom_codes, zoom_v, 'o', color=C_TRANSFER, markersize=3)
    ax_ins.annotate('', xy=(511, zoom_v[1]), xytext=(511, zoom_v[0]),
                    arrowprops=dict(arrowstyle='<->', color=C_LSB,
                                    lw=1.0, mutation_scale=7))
    ax_ins.text(511.4, (zoom_v[0]+zoom_v[1])/2,
                f'$\\Delta V_{{LSB}}$\n{dac.dv_lsb*1e3:.3f} mV',
                fontsize=5.5, color=C_LSB, va='center')
    ax_ins.set_title('LSB zoom', fontsize=6, pad=2)

    ax_b.set_xlabel('DAC Code')
    ax_b.set_ylabel('$V_{CTRL}$ (mV)')
    ax_b.set_xlim(-20, dac.codes + 20)
    ax_b.set_ylim(-5, dac.v_ref * 1e3 + 15)
    ax_b.set_yticks(np.arange(0, dac.v_ref * 1e3 + 1, 50))
    ax_b.legend(loc='upper left', fontsize=7.5)
    ax_b.set_title('(b)  Transfer Curve', loc='left',
                   fontsize=9, fontweight='bold')

    # ── (c) TRANSIENT ────────────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[1, :])

    # V_CTRL step function
    ax_d.step(cycles, v_seq, where='post', color=C_VCTRL,
              linewidth=1.8, label='$V_{CTRL}$ (mV)', zorder=3)
    ax_d.fill_between(cycles, 0, v_seq, step='post',
                      color=C_VCTRL, alpha=0.07)

    # Lock voltage reference
    ax_d.axhline(v_lock, color=C_LOCK, linewidth=1.0,
                 linestyle='--',
                 label=f'Target = {v_lock:.1f} mV  (code 724)')

    # Lock cycle marker
    lock_idx = 11
    ax_d.axvline(lock_idx, color=C_LOCK, linewidth=1.0,
                 linestyle='--', alpha=0.7)
    ax_d.text(lock_idx + 0.15, v_lock + 8,
              f'Locked\ncycle {lock_idx}',
              fontsize=7, color=C_LOCK)

    # Annotate code values — place label at centre of each held step
    for i, (cy, code_v, v_v) in enumerate(zip(cycles, code_seq, v_seq)):
        if i < 12:
            # label sits above the step it belongs to, centred between
            # this cycle and the next
            x_mid = cy + 0.45
            # alternate above/below to avoid overlap on close values
            y_off = 12 if i % 2 == 0 else -16
            ax_d.text(x_mid, v_v + y_off, str(code_v),
                      ha='center', fontsize=7, color='black')

    # Twin axis — DAC code
    ax_d2 = ax_d.twinx()
    ax_d2.step(cycles, code_seq, where='post', color=C_CODE,
               linewidth=1.2, linestyle=':', alpha=0.7,
               label='code[9:0]')
    ax_d2.set_ylabel('DAC Code', color=C_CODE, fontsize=9)
    ax_d2.tick_params(axis='y', colors=C_CODE, direction='in')
    ax_d2.set_ylim(-30, DAC_CODES + 30)

    ax_d.set_xlabel('$CLKCTRL$ Cycle')
    ax_d.set_ylabel('$V_{CTRL}$ (mV)')
    ax_d.set_xlim(-0.5, len(BS_SEQUENCE) - 0.5)
    ax_d.set_ylim(-5, dac.v_ref * 1e3 + 20)
    ax_d.set_xticks(cycles)

    lines1, lbl1 = ax_d.get_legend_handles_labels()
    lines2, lbl2 = ax_d2.get_legend_handles_labels()
    ax_d.legend(lines1 + lines2, lbl1 + lbl2,
                loc='upper left', fontsize=7.5)
    ax_d.set_title('(c)  Transient — $V_{CTRL}$ vs $CLKCTRL$ Cycle',
                   loc='left', fontsize=9, fontweight='bold')

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    dac = DAC(v_ref=V_REF, bits=DAC_BITS)
    print_summary(dac)
    fig = plot_all(dac)
    fig.canvas.manager.set_window_title(
        f'Component 03 — DAC  |  V_ref = {V_REF} V  |  {DAC_BITS}-bit')
    plt.show()


if __name__ == '__main__':
    main()
