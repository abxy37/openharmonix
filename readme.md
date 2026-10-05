# OpenHarmonix - Phased Pink Sound Generator

A Python GUI application implementing the **Phased Pink Sound** audio synthesis algorithms based on **U.S. Patent 5,213,562** (Robert A. Monroe / The Monroe Institute). 

This tool synthesizes amplitude-modulated phased pink noise overlaid with dual carrier frequencies to generate binaural beats, enabling acoustic entrainment research and experimentation.

---

## Features

* **Patent-Compliant Audio Engine:** Simulates digital filtering, density noise generation, and comb-filter flanging techniques as outlined in U.S. Patent 5,213,562.
* **Dual Carrier Frequency Synthesis:** Custom left and right carrier adjustments (defaulting to 275 Hz / 279 Hz) to produce configurable binaural beat frequencies (e.g., 4 Hz Delta/Theta entrainment).
* **Flexible Output Options:**
  * **Real-time Speaker Playback:** Non-blocking multi-threaded audio output with an immediate **Stop Playback** button.
  * **WAV Export:** Direct export of 16-bit PCM stereo WAV files for offline listening or further processing.

---

## Installation

### 1. Prerequisites

Ensure you have **Python 3.8+** installed.

#### Linux Users (Debian/Ubuntu/Arch)
`tkinter` is included by default with standard Python installers on Windows and macOS. On Linux systems, install `tkinter` via your package manager if it is missing:

```bash
# Debian / Ubuntu
sudo apt-get install python3-tk

# Arch Linux
sudo pacman -S tk