# DLL Behavioral Simulator

> Sub-section of **AMS_VLSI-SEMINAR** repository
> Based on: Wainstein et al., IEEE OJ-SSCS 2025

---

## 📌 What Is This?

This is a **top-level behavioral simulator** of the full DLL system described in the paper. Each component of the DLL is implemented as a standalone Python module, and then integrated into a full closed-loop simulation.

The simulator is written in **pure Python** (NumPy + Matplotlib) — no special tools needed.

---

## 🏗️ DLL Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              VCDL (04)                  │
  CLKIN ───────────►│  DE0 → DE1 → ... → DE8 → DE9(dummy)   ├──► CLKOUT[7:0]
                    │       │                  │              │
                    └───────┼──────────────────┼──────────────┘
                         CLKREF             CLKFB
                            │                  │
                            ▼                  ▼
                    ┌───────────────────────────┐
                    │       BBPD (01)           │
                    │  Bang-Bang Phase Detector │
                    └──────────┬────────────────┘
                               │ PD_ER (+1 / -1)
                               ▼
                    ┌───────────────────────────┐
          CLKCTRL   │     BS-FSM (02)           │
         ◄──────────┤  Binary Search Controller │
          ÷N (05)   │  code[9:0], step[8:0]    │
                    └──────────┬────────────────┘
          toggling             │ code[9:0]
         ◄──────────           ▼
          Toggle    ┌───────────────────────────┐
          Det. (06) │       DAC (03)            │
                    │   10-bit Digital → Analog │
                    └──────────┬────────────────┘
                               │ V_CTRL
                               ▼
                         back to VCDL ↑
```

---

## 📦 Components

| File | Component | What It Simulates |
|---|---|---|
| `01_phase_detector.py` | **BBPD** | Compares CLKREF vs CLKFB → outputs ±1 |
| `02_binary_search_fsm.py` | **BS-FSM** | Binary search locking algorithm |
| `03_dac.py` | **DAC** | 10-bit code → analog V_CTRL voltage |
| `04_vcdl.py` | **VCDL** | V_CTRL → delay → ΔT phase error |
| `05_divider.py` | **÷N Divider** | CLKIN → CLKCTRL (slow FSM clock) |
| `06_toggle_detector.py` | **Toggle Detector** | Detects stalled/dead clock |
| `07_full_system.py` | **Full DLL** | All components integrated |

---

## ⚙️ Requirements

| Package | Version | Install |
|---|---|---|
| Python | ≥ 3.8 | [python.org](https://python.org) |
| NumPy | ≥ 1.21 | `pip install numpy` |
| Matplotlib | ≥ 3.5 | `pip install matplotlib` |

### One-line install
```bash
pip install numpy matplotlib
```

---

## 🚀 How to Run

### Step 1 — Navigate to the simulator folder
```bash
cd AMS_VLSI-SEMINAR/simulator
```

### Step 2 — Run individual components
```bash
python3 01_phase_detector.py
python3 02_binary_search_fsm.py
python3 03_dac.py
python3 04_vcdl.py
python3 05_divider.py
python3 06_toggle_detector.py
```

### Step 3 — Run the full integrated system
```bash
python3 07_full_system.py
```

Each script will:
1. Print a **terminal summary** with key values
2. Open a **matplotlib figure** with IEEE-style plots

---

## 🔧 Configuration

Every file has a **CONFIGURATION block** at the top — you can change parameters without touching any other code:

### `01_phase_detector.py`
```python
F_CLKIN_HZ       = 1.0e9     # Hz — try 533e6, 800e6, 4.26e9
DELTA_T_EARLY_PS = -200.0    # ps — CLKFB leads CLKREF
DELTA_T_LATE_PS  = +200.0    # ps — CLKFB lags  CLKREF
```

### `02_binary_search_fsm.py`
```python
LOCK_CODE       = 724    # target DAC code (0–1023)
INJECT_FAILURE  = True   # simulate clock stall mid-search
FAILURE_AT_STEP = 4      # which BS step triggers the failure
```

### `03_dac.py`
```python
V_REF    = 0.375    # V — DAC reference voltage (paper value)
DAC_BITS = 10       # bits → 1024 codes
```

### `04_vcdl.py`
```python
F_CLKIN   = 1.0e9   # Hz — input clock frequency
LOCK_CODE = 724     # code where ΔT = 0 (calibrated)
```

### `05_divider.py`
```python
F_CLKIN = 1.0e9   # Hz
N_DIV   = 4       # division ratio (1, 2, 4, 6, 8)
```

### `06_toggle_detector.py`
```python
FAILURE_AT_NS = 6.0    # ns — when clock failure is injected
RECOVER_AT_NS = 10.0   # ns — when clock recovers
SIM_NS        = 16.0   # ns — total simulation time
```

### `07_full_system.py`
```python
F_CLKIN         = 1.0e9   # Hz
LOCK_CODE       = 724
FORCE_FAIL_STEP = 3        # inject failure at step 3
TRACK_CYCLES    = 12       # dither cycles after lock
```

---

## 📊 What Each Plot Shows

### Component 01 — BBPD
- **(a)** Signal flow block diagram
- **(b)** Transfer characteristic — PD_ER vs ΔT
- **(c/d/e)** Waveforms for Early / Aligned / Late cases

### Component 02 — Binary Search FSM
- **(a)** FSM state diagram
- **(b)** PD_ER output — continuous color fills
- **(c)** FSM state sequence over time
- **(d)** Code convergence + step halving (twin axis)

### Component 03 — DAC
- **(a)** Signal flow block diagram
- **(b)** Transfer curve V_CTRL vs code + LSB zoom inset
- **(c)** Transient V_CTRL vs CLKCTRL cycle

### Component 04 — VCDL
- **(a)** VCDL chain structure (DE0–DE9)
- **(b)** ΔT vs DAC code — nonlinear curve + BS search path
- **(c)** Single DE delay vs V_CTRL — hyperbolic
- **(d)** Clock waveforms at 3 BS steps

### Component 05 — ÷N Divider
- **(a)** Signal flow block diagram
- **(b)** CLKIN vs CLKCTRL waveforms
- **(c)** f_CLKCTRL vs N — bar chart
- **(d)** T_CLKCTRL vs N — bar chart

### Component 06 — Toggle Detector
- **(a)** Circuit block diagram (FF1 → ED → FF2 → INV)
- **(b)** CLKIN waveform — stops and resumes
- **(c)** FF1 and FF2 internal states
- **(d)** toggling output + detection latency annotation

### Component 07 — Full System
- **(a)** Full system block diagram
- **(b)** ΔT vs time
- **(c)** PD_ER vs time
- **(d)** DAC code + V_CTRL twin axis
- **(e)** Step halving log scale
- **(f)** Toggle detector output
- **(g)** FSM state timeline
- **(h)** Clock waveforms — 3 snapshots

---

## 📐 Key DLL Parameters (Paper Values)

| Parameter | Value |
|---|---|
| Technology | 3-nm FinFET CMOS |
| Frequency Range | 533 MHz – 4.26 GHz |
| DAC Resolution | 10 bits (1024 codes) |
| Locking Time | B+1 = **11 CLKCTRL cycles** |
| Time Resolution ΔT_LSB | **0.73 ps** |
| Supply Voltage | 0.75 V |
| DAC Full-Scale | 0.375 V |
| Toggle Detection | < 1.5 CLKIN cycles |
| Core Area | 31.7 × 36.9 µm² |

---

## 🔑 Key Concepts

### Binary Search Locking
```
Cycle 0:  code =   0,  step = 512   ← start at 0
Cycle 1:  code = 512,  step = 256   ← jump to midpoint
Cycle 2:  code = 768,  step = 128   ← too low → go up
Cycle 3:  code = 640,  step =  64   ← too high → go down
  ...
Cycle 11: code = 724,  step =   1   ← LOCKED ✓
```
**Only 3 lines of logic:**
```python
codepre = code          # 1. save backup
code    = code ± step   # 2. jump up or down
step    = step >> 1     # 3. halve the step
```

### Toggle Detector
```
Normal:  CLKIN toggles → FF1 cleared by CLKREF → toggling = 1 (OK)
Failure: CLKIN stops   → FF2 captures 1        → toggling = 0 (FAIL)
Detection latency: < 1.5 × T_CLKIN
```

---

## 📚 Reference

```bibtex
@article{wainstein2025dll,
  author  = {Wainstein, Nicolás and Avitay, Eran and Avner, Eugene},
  title   = {Fast-Locking and High-Resolution {DLL} With Binary Search
             and Clock Failure Detection for Wide Frequency Ranges
             in 3-nm {FinFET} {CMOS}},
  journal = {IEEE Open Journal of the Solid-State Circuits Society},
  volume  = {5},
  year    = {2025},
  doi     = {10.1109/OJSSCS.2025.3597909}
}
```
