# AMS_VLSI-SEMINAR

> **Course:** AMS VLSI Seminar — 00490037
> **Institution:** Technion — Israel Institute of Technology
> **Authors:** Ayman Atiea & Maysam Simaan

---

## 📖 About This Repository

This repository documents the full work completed for the **AMS VLSI Seminar** course at the Technion. The course covers the fundamentals and advanced topics of **Analog/Mixed-Signal (AMS) VLSI design**, with a focus on high-speed wireline communication systems.

### Course Topics Covered

| # | Topic |
|---|---|
| 1 | Channels and Transmitters |
| 2 | TX and Receivers |
| 3 | Receivers and Equalization |
| 4 | Clocking Architecture and Jitter |
| 5 | Deskew Circuits and High-Speed Data Converters |

---

## 🎯 Final Project — Paper Implementation

As the final project, we selected and implemented the following IEEE paper:

> **"Fast-Locking and High-Resolution DLL With Binary Search and Clock Failure Detection for Wide Frequency Ranges in 3-nm FinFET CMOS"**
> Nicolás Wainstein, Eran Avitay, Eugene Avner
> *IEEE Open Journal of the Solid-State Circuits Society (OJ-SSCS), Vol. 5, 2025*
> DOI: [10.1109/OJSSCS.2025.3597909](https://doi.org/10.1109/OJSSCS.2025.3597909)

### Why This Paper?

The paper presents a **DAC-Based Digital DLL (DB-DLL)** that simultaneously achieves:
- ⚡ **Fast locking** — B+1 = 11 CLKCTRL cycles (binary search)
- 🎯 **Sub-picosecond resolution** — 0.73 ps (no TDC needed)
- 🔒 **Clock failure detection** — Toggle Detector, < 1.5 CLKIN cycles
- 📡 **Wide frequency range** — 533 MHz to 4.26 GHz (8× ratio)
- 🏭 **3-nm FinFET CMOS** process

---

## 🗂️ Repository Structure

```
AMS_VLSI-SEMINAR/
│
├── README.md                        ← You are here
│
├── simulator/                       ← Top-level behavioral simulator
│   ├── README_SIMULATOR.md          ← How to run the simulator
│   ├── 01_phase_detector.py         ← Component 01: BBPD
│   ├── 02_binary_search_fsm.py      ← Component 02: Binary Search FSM
│   ├── 03_dac.py                    ← Component 03: 10-bit DAC
│   ├── 04_vcdl.py                   ← Component 04: VCDL
│   ├── 05_divider.py                ← Component 05: ÷N Clock Divider
│   ├── 06_toggle_detector.py        ← Component 06: Toggle Detector
│   └── 07_full_system.py            ← Component 07: Full DLL System
│
├── verilog-a/                       ← Verilog-A implementations
│   └── bbpd.vams                    ← BBPD Verilog-A model + testbench
│
├── report/                          ← Project report (coming soon)
│
└── docs/                            ← Figures, paper, references
```

---

## 🚀 Quick Start — Running the Simulator

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/AMS_VLSI-SEMINAR.git
cd AMS_VLSI-SEMINAR
```

### 2. Install dependencies
```bash
pip install numpy matplotlib
```

### 3. Run any component
```bash
# Run individual components
python3 simulator/01_phase_detector.py
python3 simulator/02_binary_search_fsm.py
python3 simulator/03_dac.py
python3 simulator/04_vcdl.py
python3 simulator/05_divider.py
python3 simulator/06_toggle_detector.py

# Run the full integrated system
python3 simulator/07_full_system.py
```

> 📖 See [`simulator/README_SIMULATOR.md`](simulator/README_SIMULATOR.md) for full details.

---

## 🔮 Coming Soon

- [ ] Full project report (PDF)
- [ ] Verilog-A models for all components
- [ ] MATLAB comparison plots
- [ ] Measured silicon results vs. simulation

---

## 📄 License

This repository is for academic purposes only.
All circuit implementations are based on the cited IEEE paper.
