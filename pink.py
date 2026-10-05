import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from scipy.io.wavfile import write
import sounddevice as sd

# --- Audio Generation Core (US Patent 5213562) ---
def generate_phased_pink_audio(carrier_left=275.0, carrier_right=279.0, duration_seconds=8.0):
    samples_per_second = 10466.5  # Patent sample rate
    cutoff = 200.0                # Low-pass cutoff frequency
    total_samples = int(duration_seconds * samples_per_second)
    maxdelay = 80

    st_entries = 8192
    theta = np.linspace(0, 2 * np.pi, st_entries, endpoint=False)
    w_table = np.round(32767 * np.sin(theta)).astype(np.int16)

    phase = 0x8000
    fa = 0.0
    fc = (1.0 - np.exp(-2.0 * np.pi * cutoff / samples_per_second)) * 65536.0

    noise_buffer = np.zeros(total_samples + maxdelay, dtype=np.int32)

    def noise_gen():
        nonlocal phase, fa, fc
        phase = (phase << 1) & 0xFFFF
        if phase & 0x10000:
            phase ^= 0x1D87
        
        x = w_table[phase >> 3]
        y = int((fc * x - fa) / 65536.0) if isinstance(fc, float) else int((fc * x - fa) >> 16)
        fa += (x >> 4) - y
        return np.int32(y << 4)

    for i in range(maxdelay):
        noise_buffer[i] = noise_gen()

    pink_output = np.zeros(total_samples, dtype=np.int16)
    offset = 153
    scale_f = 0x245
    gain_ns = 585
    gain_fs = 439

    np_idx = maxdelay
    for i in range(total_samples):
        if i < total_samples - maxdelay:
            noise_buffer[np_idx] = noise_gen()
            current_noise = noise_buffer[np_idx]
        else:
            current_noise = noise_buffer[i % maxdelay]
            
        flange_sample = current_noise
        xx = (int(current_noise) * gain_ns + int(flange_sample) * gain_fs) >> 10
        val = ((xx + offset) * scale_f) >> 16
        pink_output[i] = np.clip(val, -32768, 32767)
        np_idx += 1

    t = np.linspace(0, duration_seconds, total_samples, endpoint=False)
    left_channel = np.sin(2 * np.pi * carrier_left * t) * (1.0 + 0.1 * (pink_output / 32767.0))
    right_channel = np.sin(2 * np.pi * carrier_right * t) * (1.0 + 0.1 * (pink_output / 32767.0))

    stereo_data = np.vstack((left_channel, right_channel)).T
    stereo_data = np.int16(stereo_data / np.max(np.abs(stereo_data)) * 32767)
    
    return int(samples_per_second), stereo_data


# --- GUI Implementation ---
class PhasedPinkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Phased Pink Sound Generator (US Patent 5,213,562)")
        self.geometry("450x420")
        self.resizable(False, False)

        self.is_playing = False
        self.playback_thread = None

        style = ttk.Style()
        style.theme_use("clam")

        # --- Parameters Frame ---
        param_frame = ttk.LabelFrame(self, text=" Audio Parameters ", padding=15)
        param_frame.pack(fill="x", padx=15, pady=10)

        ttk.Label(param_frame, text="Left Carrier (Hz):").grid(row=0, column=0, sticky="w", pady=5)
        self.left_carrier_var = tk.DoubleVar(value=275.0)
        ttk.Entry(param_frame, textvariable=self.left_carrier_var, width=10).grid(row=0, column=1, sticky="e")

        ttk.Label(param_frame, text="Right Carrier (Hz):").grid(row=1, column=0, sticky="w", pady=5)
        self.right_carrier_var = tk.DoubleVar(value=279.0)
        ttk.Entry(param_frame, textvariable=self.right_carrier_var, width=10).grid(row=1, column=1, sticky="e")

        ttk.Label(param_frame, text="Duration (Seconds):").grid(row=2, column=0, sticky="w", pady=5)
        self.duration_var = tk.DoubleVar(value=8.0)
        ttk.Entry(param_frame, textvariable=self.duration_var, width=10).grid(row=2, column=1, sticky="e")

        # --- Output Selection Frame ---
        output_frame = ttk.LabelFrame(self, text=" Output Destination ", padding=15)
        output_frame.pack(fill="x", padx=15, pady=5)

        self.output_choice = tk.StringVar(value="speakers")

        ttk.Radiobutton(
            output_frame, 
            text="Play to Speakers (Real-time)", 
            variable=self.output_choice, 
            value="speakers"
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            output_frame, 
            text="Save to WAV File", 
            variable=self.output_choice, 
            value="wav"
        ).pack(anchor="w", pady=2)

        # --- Action Buttons Frame ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        self.run_btn = ttk.Button(btn_frame, text="Generate & Play", command=self.process_audio)
        self.run_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop Playback", command=self.stop_audio, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var, font=("Helvetica", 9, "italic"))
        self.status_label.pack()

    def process_audio(self):
        try:
            left_f = self.left_carrier_var.get()
            right_f = self.right_carrier_var.get()
            dur = self.duration_var.get()

            if dur <= 0:
                messagebox.showerror("Error", "Duration must be greater than 0.")
                return

            destination = self.output_choice.get()

            if destination == "speakers":
                self.run_btn.config(state="disabled")
                self.stop_btn.config(state="normal")
                self.status_var.set("Synthesizing audio...")
                
                # Run synthesis & playback in a non-blocking background thread
                self.playback_thread = threading.Thread(
                    target=self._play_background, 
                    args=(left_f, right_f, dur), 
                    daemon=True
                )
                self.playback_thread.start()

            elif destination == "wav":
                self.status_var.set("Synthesizing audio signal...")
                self.update_idletasks()
                sample_rate, stereo_data = generate_phased_pink_audio(left_f, right_f, dur)
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".wav",
                    filetypes=[("WAV Audio", "*.wav")],
                    initialfile="monroe_phased_pink.wav",
                    title="Save Audio Output"
                )
                if file_path:
                    write(file_path, sample_rate, stereo_data)
                    self.status_var.set(f"Saved to {os.path.basename(file_path)}")
                    messagebox.showinfo("Success", f"File saved successfully to:\n{file_path}")
                else:
                    self.status_var.set("Save canceled.")

        except Exception as e:
            messagebox.showerror("Execution Error", str(e))
            self.status_var.set("Error occurred.")
            self._reset_ui_state()

    def _play_background(self, left_f, right_f, dur):
        try:
            sample_rate, stereo_data = generate_phased_pink_audio(left_f, right_f, dur)
            float_data = stereo_data.astype(np.float32) / 32767.0
            
            self.is_playing = True
            self.status_var.set("Playing through speakers...")
            
            sd.play(float_data, samplerate=sample_rate)
            sd.wait()
            
            if self.is_playing:
                self.status_var.set("Playback complete.")
        except Exception as e:
            self.status_var.set("Playback error.")
        finally:
            self.is_playing = False
            self.after(0, self._reset_ui_state)

    def stop_audio(self):
        if self.is_playing:
            sd.stop()
            self.is_playing = False
            self.status_var.set("Playback stopped.")
            self._reset_ui_state()

    def _reset_ui_state(self):
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


if __name__ == "__main__":
    app = PhasedPinkApp()
    app.mainloop()