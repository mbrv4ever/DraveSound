#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DraveSound  —  een Dravenlock product.
Een lichte, portable muziekmaker (loops + sporen, in Magix-stijl) met de
DraveMotion-huisstijl. Single-file PyQt5. Onefile-klaar (ffmpeg in de .exe).
Neemt automatisch de computertaal over (Nederlands als basis).
"""
import os
import sys
import json
import math
import time
import wave
import subprocess
import urllib.request
import urllib.parse


# --------------------------------------------------------------------------- #
#  PORTABLE INFRASTRUCTUUR  (moet vóór audio-imports staan)
# --------------------------------------------------------------------------- #
def app_dir():
    """De map waarin de app draait: naast de .exe (frozen) of naast dit script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = app_dir()
CACHE_DIR = os.path.join(APP_DIR, "cache")
PROJECTS_DIR = os.path.join(APP_DIR, "projecten")
MEDIA_DIR = os.path.join(APP_DIR, "media")
BIN_DIR = os.path.join(APP_DIR, "bin")
CONFIG_PATH = os.path.join(APP_DIR, "dravesound_config.json")

APP_VERSION = "0.33.1"
APP_NAME = "DraveSound"
AUTHOR_NAME = "Dravenlock"
WEBSITE_URL = "https://dravenlock.nl/"
DONATE_URL = "https://paypal.me/roger076"
DOWNLOAD_PAGE_URL = "https://github.com/mbrv4ever/DraveSound/releases/latest"
UPDATE_CHECK_URL = "https://dravenlock.nl/downloads/DraveSound/version.txt"
SERVICE_EMAIL = "service@dravenlock.nl"

SAMPLE_RATE = 44100
REFERENCE_BPM = 120.0          # loops worden naar dit tempo gerefereerd; BPM rekt ze mee
PROJECT_EXT = ".dravesound"

for _d in (CACHE_DIR, PROJECTS_DIR, MEDIA_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except OSError:
        pass

# Houd imageio/ffmpeg-cache binnen de app-map (portable, nooit %APPDATA%).
os.environ["IMAGEIO_USERDIR"] = CACHE_DIR
_ff_local = os.path.join(BIN_DIR, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
if os.path.exists(_ff_local):
    os.environ["IMAGEIO_FFMPEG_EXE"] = _ff_local


def resource_path(rel):
    """Pad naar een GEBUNDELDE (alleen-lezen) resource (bv. logo, ffmpeg)."""
    base = getattr(sys, "_MEIPASS", APP_DIR)
    return os.path.join(base, rel)


# Optionele afhankelijkheden ------------------------------------------------- #
try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

try:
    import soundfile as sf
    HAVE_SF = True
except Exception:
    HAVE_SF = False

try:
    import imageio_ffmpeg
    HAVE_FFMPEG = True
except Exception:
    HAVE_FFMPEG = False

try:
    import sounddevice as sd
    HAVE_SD = True
except Exception:
    HAVE_SD = False


def ffmpeg_exe():
    """Pad naar ffmpeg (in de .exe gebundeld, los in bin/, env, of imageio), of None."""
    names = ["ffmpeg.exe", "ffmpeg"] if os.name == "nt" else ["ffmpeg"]
    cand = []
    for n in names:
        cand.append(resource_path(n))
        cand.append(resource_path(os.path.join("bin", n)))
    cand.append(_ff_local)
    for c in cand:
        if c and os.path.exists(c):
            return c
    env = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if env and os.path.exists(env):
        return env
    if not HAVE_FFMPEG:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  CONFIG
# --------------------------------------------------------------------------- #
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except OSError:
        pass


BLOCKS_PATH = os.path.join(APP_DIR, "dravesound_blocks.json")


def load_blocks():
    try:
        with open(BLOCKS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_blocks(blocks):
    try:
        with open(BLOCKS_PATH, "w", encoding="utf-8") as fh:
            json.dump(blocks, fh, indent=2)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
#  TAAL  (neemt de computertaal over; Nederlands is de basis/terugval)
# --------------------------------------------------------------------------- #
SUPPORTED_LANGS = ["nl", "en"]
_CURRENT_LANG = None

TRANSLATIONS = {
    "en": {
        "een Dravenlock product": "a Dravenlock product",
        "📖 Snelgids": "📖 Quick guide", "✉️ Contact": "✉️ Contact",
        "🔄 Updates": "🔄 Updates", "ⓘ Info": "ⓘ Info", "⤓ Exporteren…": "⤓ Export…",
        "Project": "Project", "Loop-bibliotheek": "Loop library", "Spoor": "Track",
        "Nieuw": "New", "Openen…": "Open…", "Opslaan…": "Save…", "Instellingen…": "Settings…",
        "📂 Map met loops laden…": "📂 Load loop folder…", "Uit lijst verwijderen": "Remove from list",
        "+ Spoor": "+ Track", "Tempo (BPM)": "Tempo (BPM)", "Raster (magnetisch)": "Grid (magnetic)",
        "▶ Afspelen": "▶ Play", "⏸ Pauze": "⏸ Pause", "⏹ Stop": "⏹ Stop",
        "🗑 Verwijder": "🗑 Delete", "Geselecteerde clip": "Selected clip", "— geen clip —": "— no clip —",
        "✂ Knippen": "✂ Cut", "⧉ Kopiëren": "⧉ Copy", "📋 Plakken": "📋 Paste",
        "Lengte (tellen) — 0 = automatisch": "Length (beats) — 0 = automatic",
        "Effect (op deze clip)": "Effect (on this clip)", "Fade in": "Fade in", "Fade uit": "Fade out",
        "Kies een effect:": "Choose an effect:", "Sterkte (minder ↔ meer):": "Strength (less ↔ more):",
        "▶ Beluister": "▶ Preview", "🎛 Effect…": "🎛 Effect…", "🎛 Effecten…": "🎛 Effects…",
        "📋 Plak hier": "📋 Paste here", "Effecten": "Effects", "Toepassen": "Apply", "Annuleren": "Cancel",
        "⧉ Dupliceren": "⧉ Duplicate", "✎ Spoor hernoemen": "✎ Rename track", "🗑 Spoor verwijderen": "🗑 Delete track",
        "Spoor hernoemen": "Rename track", "Nieuwe naam:": "New name:", "Spoor verwijderen": "Delete track",
        "Spoor '{0}' verwijderen?": "Delete track '{0}'?", "Er staan {0} clip(s) op.": "It has {0} clip(s).",
        "Master-volume": "Master volume",
        "Niveau": "Level", "🕘 Recent…": "🕘 Recent…", "(geen recente projecten)": "(no recent projects)",
        "Bestandsnaam:": "File name:", "Formaat:": "Format:", "(MP3 vereist ffmpeg)": "(MP3 requires ffmpeg)",
        "Map kiezen…": "Choose folder…", "Map": "Folder", "Bezig met exporteren…": "Exporting…",
        "Geëxporteerd:": "Exported:", "Klaar!": "Done!", "Export mislukt.": "Export failed.",
        "'{0}' bestaat al. Overschrijven?": "'{0}' already exists. Overwrite?",
        "Blokjes (eigen combinaties)": "Blocks (your own combos)", "💾 Selectie → blokje": "💾 Selection → block",
        "Dubbelklik om op de afspeelkop te plaatsen": "Double-click to place at the playhead",
        "Blokje bewaren": "Save block", "Naam van het blokje:": "Block name:",
        "➕ Plaats op afspeelkop": "➕ Place at playhead", "✎ Hernoemen": "✎ Rename",
        "Hernoemen": "Rename", "Verwijderen": "Delete", "Blokje '{0}' verwijderen?": "Delete block '{0}'?",
        "🔔 Metronoom": "🔔 Metronome", "🔁 Lus": "🔁 Loop", "Lus begin": "Loop start", "Lus eind": "Loop end",
        "Zet het lusbegin op de afspeelkop": "Set loop start at the playhead",
        "Zet het luseind op de afspeelkop": "Set loop end at the playhead",
        "♥ Donatie": "♥ Donate", "Steun Dravenlock": "Support Dravenlock", "Donatie": "Donation",
        "Steun Dravenlock — bedankt!": "Support Dravenlock — thank you!",
        "Diepte (minder ↔ meer):": "Depth (less ↔ more):",
        "Vervorming (zachter ↔ ruwer):": "Drive (softer ↔ rougher):",
        "Lo-fi (subtiel ↔ grof):": "Lo-fi (subtle ↔ coarse):",
        "Toon (donker ↔ helder):": "Tone (dark ↔ bright):",
        "Overdrive (vervorming)": "Overdrive (distortion)", "Bitcrusher (lo-fi)": "Bitcrusher (lo-fi)",
        "Toon (donker ↔ helder)": "Tone (dark ↔ bright)",
        "Flanger": "Flanger", "Ping-pong echo": "Ping-pong echo", "Pan (links ↔ rechts)": "Pan (left ↔ right)",
        "Gater": "Gater", "Compressor": "Compressor",
        "Pan (links ↔ rechts):": "Pan (left ↔ right):", "Diepte (subtiel ↔ sterk):": "Depth (subtle ↔ strong):",
        "Gate (zwak ↔ sterk):": "Gate (weak ↔ strong):", "Compressie (zacht ↔ sterk):": "Compression (soft ↔ strong):",
        "Phaser": "Phaser", "Toonhoogte (lager ↔ hoger)": "Pitch (lower ↔ higher)",
        "Phaser (subtiel ↔ sterk):": "Phaser (subtle ↔ strong):",
        "Toonhoogte (lager ↔ hoger):": "Pitch (lower ↔ higher):",
        "Spoor (mixer)": "Track (mixer)", "Spoorvolume %": "Track volume %",
        "Mute": "Mute", "Solo": "Solo", "Effect": "Effect",
        "Startmaat / -tel": "Start bar / beat", "Volume %": "Volume %",
        "Een lichte muziekmaker met loops en sporen.":
            "A lightweight music maker with loops and tracks.",
        "📖 Open de Snelgids": "📖 Open the quick guide",
        "Nieuw hier? Laad een map met loops of sound clips en sleep ze op de sporen.":
            "New here? Load a folder of loops or sound clips and drop them onto the tracks.",
        "Taal": "Language", "Automatisch (computertaal)": "Automatic (system language)",
        "Nederlands": "Dutch", "English": "English",
        "De taal verandert nadat je DraveSound opnieuw start.":
            "The language changes after you restart DraveSound.",
        "Annuleer": "Cancel", "Toepassen": "Apply", "Sluiten": "Close", "✉️ Versturen": "✉️ Send",
        "Exporteren": "Export", "Kies een exportformaat:": "Choose an export format:",
        "Updates": "Updates", "Controleren op updates…": "Checking for updates…",
        "Contact opnemen": "Contact", "Soort bericht:": "Type of message:",
        "Vraag": "Question", "Klacht": "Complaint", "Idee": "Idea", "Bug / fout": "Bug / error",
        "Anders": "Other", "Je naam:": "Your name:", "Je bericht:": "Your message:",
        "📋 Kopieer e-mailadres": "📋 Copy e-mail address",
        "Je e-mailadres (zodat de maker je kan antwoorden):":
            "Your e-mail (so the author can reply):",
    },
}


def current_lang():
    global _CURRENT_LANG
    if _CURRENT_LANG is None:
        choice = load_config().get("language", "auto")
        if choice in SUPPORTED_LANGS:
            _CURRENT_LANG = choice
        else:
            try:
                from PyQt5.QtCore import QLocale
                _CURRENT_LANG = "nl" if QLocale.system().language() == QLocale.Dutch else "en"
            except Exception:
                _CURRENT_LANG = "nl"
    return _CURRENT_LANG


def t(s):
    lang = current_lang()
    if lang == "nl":
        return s
    return TRANSLATIONS.get(lang, {}).get(s, s)


# --------------------------------------------------------------------------- #
#  AUDIO
# --------------------------------------------------------------------------- #
def load_audio(path, sr=SAMPLE_RATE):
    """Lees een audiobestand -> (float32 array (n, 2), sr). Stereo, op SR.

    Gebruikt soundfile als dat kan; anders de stdlib 'wave' (PCM-WAV).
    """
    if not HAVE_NUMPY:
        return None
    data = None
    in_sr = sr
    if HAVE_SF:
        try:
            data, in_sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception:
            data = None
    if data is None:
        # WAV-fallback via stdlib
        try:
            with wave.open(path, "rb") as w:
                in_sr = w.getframerate()
                ch = w.getnchannels()
                sw = w.getsampwidth()
                raw = w.readframes(w.getnframes())
            if sw == 2:
                arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
            elif sw == 1:
                arr = (np.frombuffer(raw, dtype="u1").astype(np.float32) - 128.0) / 128.0
            elif sw == 4:
                arr = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
            else:
                return None
            data = arr.reshape(-1, ch) if ch > 1 else arr.reshape(-1, 1)
        except Exception:
            return None
    # naar stereo
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    # resample (eenvoudig lineair) indien nodig
    if in_sr != sr and data.shape[0] > 1:
        n_out = int(round(data.shape[0] * sr / float(in_sr)))
        if n_out > 0:
            x_old = np.linspace(0.0, 1.0, data.shape[0], endpoint=False)
            x_new = np.linspace(0.0, 1.0, n_out, endpoint=False)
            data = np.stack([np.interp(x_new, x_old, data[:, c]) for c in range(2)], axis=1)
    return data.astype(np.float32)


AUDIO_EXTS = (".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif", ".m4a")
_AUDIO_CACHE = {}


def cached_audio(path):
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return None
    if key not in _AUDIO_CACHE:
        if len(_AUDIO_CACHE) > 64:
            _AUDIO_CACHE.clear()
        _AUDIO_CACHE[key] = load_audio(path)
    return _AUDIO_CACHE[key]


def audio_seconds(path):
    a = cached_audio(path)
    if a is None or a.shape[0] == 0:
        return 0.0
    return a.shape[0] / float(SAMPLE_RATE)


def _ola_stretch(x, factor):
    """Rek/krimp audio in de tijd met behoud van toonhoogte (eenvoudige overlap-add).
    factor = uitvoerlengte / invoerlengte (2.0 = twee keer zo lang / half tempo)."""
    if x is None or x.size == 0 or not HAVE_NUMPY or abs(factor - 1.0) < 1e-3:
        return x
    n = x.shape[0]
    out_len = max(1, int(round(n * factor)))
    win = 2048
    if n < win * 2:                      # te kort om te rekken -> simpel resamplen
        idx = np.clip((np.arange(out_len) / factor).astype(np.int64), 0, n - 1)
        return x[idx].astype(np.float32)
    hop_out = win // 2
    window = np.hanning(win).astype(np.float32)[:, None]
    nwin = 1 + (out_len) // hop_out
    out = np.zeros((out_len + win, 2), np.float32)
    norm = np.zeros((out_len + win, 1), np.float32)
    for i in range(nwin):
        op = i * hop_out
        ip = int(op / factor)
        if ip + win > n:
            seg = np.zeros((win, 2), np.float32)
            avail = max(0, n - ip)
            if avail > 0:
                seg[:avail] = x[ip:ip + avail]
        else:
            seg = x[ip:ip + win]
        out[op:op + win] += seg * window
        norm[op:op + win] += window[:, :1]
    norm[norm < 1e-6] = 1.0
    return (out[:out_len] / norm[:out_len]).astype(np.float32)


_STRETCH_CACHE = {}


def stretched_audio(path, bpm):
    """Loop op het project-tempo (toonhoogte blijft gelijk). bpm==REFERENCE_BPM = ongewijzigd."""
    a = cached_audio(path)
    if a is None or a.shape[0] == 0:
        return a
    factor = REFERENCE_BPM / float(bpm) if bpm else 1.0
    if abs(factor - 1.0) < 1e-3:
        return a
    try:
        key = (path, os.path.getmtime(path), round(factor, 4))
    except OSError:
        return a
    if key not in _STRETCH_CACHE:
        if len(_STRETCH_CACHE) > 48:
            _STRETCH_CACHE.clear()
        _STRETCH_CACHE[key] = _ola_stretch(a, factor)
    return _STRETCH_CACHE[key]

EFFECTS = ["Geen", "Echo", "Galm", "Dof (laagdoorlaat)", "Helder (hoogdoorlaat)",
           "Overdrive (vervorming)", "Tremolo", "Bitcrusher (lo-fi)", "Chorus",
           "Toon (donker ↔ helder)", "Flanger", "Ping-pong echo",
           "Pan (links ↔ rechts)", "Gater", "Compressor",
           "Phaser", "Toonhoogte (lager ↔ hoger)"]

# effecten waarbij 0% niet "uit" betekent maar één uiterste (50% = neutraal)
NEUTRAL_EFFECTS = {"Toon (donker ↔ helder)", "Pan (links ↔ rechts)",
                   "Toonhoogte (lager ↔ hoger)"}

# effecten die een uitklinkende staart toevoegen (extra ruimte in de mix)
TAIL_EFFECTS = {"Echo", "Galm", "Ping-pong echo"}


def _lowpass(buf, k):
    if k <= 1:
        return buf
    ker = np.ones(k, dtype=np.float32) / k
    out = np.empty_like(buf)
    for ch in range(buf.shape[1]):
        out[:, ch] = np.convolve(buf[:, ch], ker, mode="same")
    return out


def _shift(buf, d):
    out = np.zeros_like(buf)
    if 0 < d < buf.shape[0]:
        out[d:] = buf[: buf.shape[0] - d]
    return out


def _phaser(buf, amount, sr):
    """Phaser: meerdere notch-filters die met een LFO door het spectrum vegen (STFT)."""
    n = buf.shape[0]
    N = 1024
    if n < N * 2:
        return buf
    H = N // 4
    win = np.hanning(N).astype(np.float32)
    freqs = np.fft.rfftfreq(N, 1.0 / sr).astype(np.float32)
    depth = 0.6 + 0.4 * amount
    rate = 0.3 + 0.6 * amount
    nfr = 1 + (n - N) // H
    out = np.zeros((n + N, 2), np.float32)
    norm = np.zeros(n + N, np.float32)
    for ch, phoff in ((0, 0.0), (1, 1.0)):
        x = buf[:, ch]
        for i in range(nfr):
            pos = i * H
            seg = x[pos:pos + N] * win
            S = np.fft.rfft(seg)
            tcen = (pos + N / 2.0) / sr
            lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * rate * tcen + phoff * np.pi))
            f0 = 250.0 + lfo * 1800.0
            g = np.ones_like(freqs)
            for m in range(1, 5):
                fc = f0 * m
                g = g * (1.0 - depth * np.exp(-((freqs - fc) / (0.12 * fc + 30.0)) ** 2))
            seg2 = np.fft.irfft(S * g, N).astype(np.float32) * win
            out[pos:pos + N, ch] += seg2
            if ch == 0:
                norm[pos:pos + N] += win * win
    norm[norm < 1e-6] = 1.0
    out[:, 0] /= norm; out[:, 1] /= norm
    return out[:n]


def _pitch_shift(buf, semitones):
    """Toonhoogte verschuiven zonder de lengte te veranderen (rek + herbemonstering)."""
    if buf is None or buf.size == 0 or abs(semitones) < 0.05 or not HAVE_NUMPY:
        return buf
    ratio = float(2.0 ** (semitones / 12.0))
    stretched = _ola_stretch(buf, ratio)            # zelfde toon, andere lengte
    n = buf.shape[0]; m = stretched.shape[0]
    if m < 2:
        return buf
    idx = np.linspace(0.0, m - 1.0, n).astype(np.float32)   # terug naar oorspronkelijke lengte
    i0 = np.floor(idx).astype(np.int64); frac = (idx - i0).astype(np.float32)[:, None]
    i1 = np.clip(i0 + 1, 0, m - 1); i0 = np.clip(i0, 0, m - 1)
    return (stretched[i0] * (1.0 - frac) + stretched[i1] * frac).astype(np.float32)


def apply_effect(buf, effect, bpm=120.0, amount=0.6):
    """Pas een effect toe op een stereo-buffer met sterkte 'amount' (0..1).
    Echo/Galm geven een langere buffer terug (de staart klinkt uit)."""
    if buf is None or buf.size == 0 or not effect or effect == "Geen" or not HAVE_NUMPY:
        return buf
    amount = max(0.0, min(1.0, float(amount)))
    if amount <= 0.001 and effect not in NEUTRAL_EFFECTS:
        return buf
    sr = SAMPLE_RATE
    n = buf.shape[0]
    if effect == "Echo":
        # ritmische echo op een halve tel; 'amount' = hoeveel echo (nat) je toevoegt
        d = max(int(sr * (60.0 / max(40.0, bpm)) * 0.5), int(0.12 * sr))
        g = 0.72
        ntap = 6
        tail = d * (ntap + 1)
        out = np.zeros((n + tail, 2), np.float32); out[:n] += buf
        for k in range(1, ntap + 1):
            out[k * d:k * d + n] += buf * (amount * (g ** k))
        return out
    if effect == "Galm":
        tail = int(0.9 * sr)
        out = np.zeros((n + tail, 2), np.float32); out[:n] += buf
        g = 0.7
        for k in range(1, 26):
            dl = int((0.012 * k + 0.004 * (k * k) / 25.0) * sr)
            if dl >= tail:
                break
            out[dl:dl + n] += buf * (amount * g)
            g *= 0.82
        return out
    if effect.startswith("Dof"):
        k = int(20 + 240 * amount)            # meer sterkte = doffer
        lp = _lowpass(buf, k)
        return (buf * (1.0 - amount) + lp * amount).astype(np.float32)
    if effect.startswith("Helder"):
        hp = buf - _lowpass(buf, 160)
        return (buf + hp * (1.6 * amount)).astype(np.float32)
    if effect.startswith("Overdrive"):
        # warme, rauwe vervorming (soft-clip met tanh); meer sterkte = ruwer
        drive = 1.0 + 18.0 * amount
        y = np.tanh(buf * drive)
        comp = 0.85 / max(0.3, np.tanh(drive))     # houd het niveau in toom
        return (y * comp).astype(np.float32)
    if effect == "Tremolo":
        # volume trilt op de tel; sterkte = diepte (snelheid loopt mee met het tempo)
        rate = max(0.5, (bpm / 60.0) * 2.0)         # twee pulsen per tel
        tt = np.arange(n, dtype=np.float32) / sr
        lfo = 0.5 * (1.0 + np.sin(2.0 * np.pi * rate * tt))
        env = (1.0 - amount) + amount * lfo
        return (buf * env[:, None]).astype(np.float32)
    if effect.startswith("Bitcrusher"):
        # lo-fi: minder bits + lagere samplerate; meer sterkte = grover
        bits = max(2.0, 16.0 - 13.0 * amount)
        levels = float(2 ** int(round(bits)))
        y = np.round(buf * levels) / levels
        step = 1 + int(round(amount * 24))          # sample-&-hold (samplerate omlaag)
        if step > 1:
            idx = (np.arange(n) // step) * step
            idx = np.clip(idx, 0, n - 1)
            y = y[idx]
        return y.astype(np.float32)
    if effect == "Chorus":
        # brede, rijke klank: traag gemoduleerd korte delay, links/rechts verschoven
        base = 0.018 * sr                           # ~18 ms
        depth = (0.004 + 0.006 * amount) * sr       # modulatiediepte
        rate = 0.5 + 0.8 * amount                   # Hz
        tt = np.arange(n, dtype=np.float32)
        out = np.empty_like(buf)
        for ch, ph in ((0, 0.0), (1, np.pi)):       # rechterkanaal in tegenfase = breedte
            mod = base + depth * np.sin(2.0 * np.pi * rate * tt / sr + ph)
            read = tt - mod
            i0 = np.floor(read).astype(np.int64)
            frac = (read - i0).astype(np.float32)
            i0c = np.clip(i0, 0, n - 1); i1c = np.clip(i0 + 1, 0, n - 1)
            wet = buf[i0c, ch] * (1.0 - frac) + buf[i1c, ch] * frac
            out[:, ch] = buf[:, ch] * (1.0 - 0.5 * amount) + wet * (0.5 * amount)
        return out.astype(np.float32)
    if effect.startswith("Toon ("):
        # toonregelaar: 0% = donker (laagdoorlaat), 50% = neutraal, 100% = helder
        if amount < 0.5:
            p = (0.5 - amount) * 2.0
            k = int(20 + 200 * p)
            return (buf * (1.0 - p) + _lowpass(buf, k) * p).astype(np.float32)
        p = (amount - 0.5) * 2.0
        hp = buf - _lowpass(buf, 160)
        return (buf + hp * (1.6 * p)).astype(np.float32)
    if effect == "Flanger":
        # zeer korte, gemoduleerde delay = suizende kam; sterkte = diepte/mix
        base = 0.0012 * sr
        depth = (0.0008 + 0.0030 * amount) * sr
        rate = 0.15 + 0.6 * amount
        tt = np.arange(n, dtype=np.float32)
        mod = base + depth * (0.5 * (1.0 + np.sin(2.0 * np.pi * rate * tt / sr)))
        read = tt - mod
        i0 = np.floor(read).astype(np.int64)
        frac = (read - i0).astype(np.float32)[:, None]
        i0c = np.clip(i0, 0, n - 1); i1c = np.clip(i0 + 1, 0, n - 1)
        wet = buf[i0c] * (1.0 - frac) + buf[i1c] * frac
        return (buf + wet * (0.9 * amount)).astype(np.float32)
    if effect == "Ping-pong echo":
        # echo die tussen links en rechts stuitert
        d = max(int(sr * (60.0 / max(40.0, bpm)) * 0.5), int(0.12 * sr))
        g = 0.72
        ntap = 6
        tail = d * (ntap + 1)
        out = np.zeros((n + tail, 2), np.float32); out[:n] += buf
        mono = 0.5 * (buf[:, 0] + buf[:, 1])
        for k in range(1, ntap + 1):
            ch = 0 if (k % 2 == 1) else 1
            out[k * d:k * d + n, ch] += mono * (amount * (g ** k))
        return out
    if effect.startswith("Pan"):
        # plaats het geluid: 0% = links, 50% = midden, 100% = rechts (gelijk vermogen)
        ang = amount * (np.pi / 2.0)
        lg = float(np.cos(ang)); rg = float(np.sin(ang))
        out = buf.copy()
        out[:, 0] *= lg * 1.41421356
        out[:, 1] *= rg * 1.41421356
        return out.astype(np.float32)
    if effect == "Gater":
        # hakt het geluid ritmisch in/uit op de tel; sterkte = hoe diep het dempt
        rate = max(0.5, (bpm / 60.0) * 2.0)         # twee poorten per tel
        tt = np.arange(n, dtype=np.float32) / sr
        phase = (tt * rate) % 1.0
        gate = np.where(phase < 0.5, 1.0, 1.0 - amount).astype(np.float32)
        # randjes glad maken tegen klikken
        w = max(1, int(0.004 * sr))
        gate = np.convolve(gate, np.ones(w, np.float32) / w, mode="same").astype(np.float32)
        return (buf * gate[:, None]).astype(np.float32)
    if effect == "Compressor":
        # maakt het geluid voller/gelijkmatiger; sterkte = hoeveel compressie + makeup
        win = max(1, int(0.012 * sr))
        mono = np.mean(np.abs(buf), axis=1).astype(np.float32)
        env = np.convolve(mono, np.ones(win, np.float32) / win, mode="same")
        env = np.maximum(env, 1e-4)
        thr = 0.30 * (1.0 - 0.7 * amount)
        ratio = 1.0 + 7.0 * amount
        over = np.maximum(env, thr)
        target = thr + (over - thr) / ratio
        gain = (target / over).astype(np.float32)
        gain = np.convolve(gain, np.ones(win, np.float32) / win, mode="same").astype(np.float32)
        makeup = 1.0 + 1.2 * amount
        return (buf * gain[:, None] * makeup).astype(np.float32)
    if effect == "Phaser":
        return _phaser(buf, amount, sr)
    if effect.startswith("Toonhoogte"):
        semis = (amount - 0.5) * 24.0              # 0%=-12, 50%=0, 100%=+12 halve tonen
        return _pitch_shift(buf, semis)
    return buf


def apply_fades(a, fade_in, fade_out):
    """Lineaire fade in/uit op een stereo-buffer (per clip)."""
    if a is None or a.size == 0 or not HAVE_NUMPY or (not fade_in and not fade_out):
        return a
    a = a.copy()
    n = a.shape[0]
    flen = min(int(0.6 * SAMPLE_RATE), n // 2)
    if flen < 2:
        return a
    if fade_in:
        ramp = np.linspace(0.0, 1.0, flen, dtype=np.float32)
        a[:flen] *= ramp[:, None]
    if fade_out:
        ramp = np.linspace(1.0, 0.0, flen, dtype=np.float32)
        a[n - flen:] *= ramp[:, None]
    return a


class Clip:
    """Een loop op een spoor, geplaatst op een beat-positie.

    span_beats=None -> natuurlijke lengte van de loop.
    span_beats=getal -> uitgerekt: de loop herhaalt zich om die lengte te vullen.
    """
    def __init__(self, path, start_beat=0.0, gain=1.0, name=None, span_beats=None,
                 effect="Geen", fade_in=False, fade_out=False, effect_amount=0.6):
        self.path = path
        self.start_beat = float(start_beat)
        self.gain = float(gain)
        self.name = name or os.path.basename(path)
        self.span_beats = float(span_beats) if span_beats else None
        self.effect = effect or "Geen"
        self.fade_in = bool(fade_in)
        self.fade_out = bool(fade_out)
        self.effect_amount = float(effect_amount)

    def seconds(self):
        return audio_seconds(self.path)

    def natural_length_beats(self, bpm=None):
        # lengte in beats op het REFERENTIE-tempo: blijft gelijk ongeacht het project-BPM,
        # want de loop wordt bij het mixen naar het project-tempo gerekt.
        return self.seconds() * REFERENCE_BPM / 60.0

    def length_beats(self, bpm):
        if self.span_beats and self.span_beats > 0:
            return self.span_beats
        return self.natural_length_beats(bpm)

    def to_dict(self):
        return {"path": self.path, "start_beat": self.start_beat,
                "gain": self.gain, "name": self.name, "span_beats": self.span_beats,
                "effect": self.effect, "fade_in": self.fade_in, "fade_out": self.fade_out,
                "effect_amount": self.effect_amount}

    @classmethod
    def from_dict(cls, d):
        return cls(d["path"], d.get("start_beat", 0.0), d.get("gain", 1.0),
                   d.get("name"), d.get("span_beats"), d.get("effect", "Geen"),
                   d.get("fade_in", False), d.get("fade_out", False),
                   d.get("effect_amount", 0.6))


class Track:
    def __init__(self, name="Spoor", gain=1.0, mute=False, solo=False, effect="Geen"):
        self.name = name
        self.gain = float(gain)
        self.mute = bool(mute)
        self.solo = bool(solo)
        self.effect = effect or "Geen"
        self.clips = []

    def to_dict(self):
        return {"name": self.name, "gain": self.gain, "mute": self.mute,
                "solo": self.solo, "effect": self.effect,
                "clips": [c.to_dict() for c in self.clips]}

    @classmethod
    def from_dict(cls, d):
        tr = cls(d.get("name", "Spoor"), d.get("gain", 1.0), d.get("mute", False),
                 d.get("solo", False), d.get("effect", "Geen"))
        tr.clips = [Clip.from_dict(c) for c in d.get("clips", [])]
        return tr


class Project:
    def __init__(self):
        self.bpm = 120.0
        self.beats_per_bar = 4
        self.master_gain = 1.0
        self.tracks = [Track("Spoor 1"), Track("Spoor 2"), Track("Spoor 3")]

    def end_beat(self):
        end = 0.0
        for tr in self.tracks:
            for c in tr.clips:
                end = max(end, c.start_beat + c.length_beats(self.bpm))
        return end

    def to_dict(self):
        return {"app": APP_NAME, "version": APP_VERSION, "bpm": self.bpm,
                "beats_per_bar": self.beats_per_bar, "master_gain": self.master_gain,
                "tracks": [tr.to_dict() for tr in self.tracks]}

    @classmethod
    def from_dict(cls, d):
        p = cls()
        p.bpm = float(d.get("bpm", 120.0))
        p.beats_per_bar = int(d.get("beats_per_bar", 4))
        p.master_gain = float(d.get("master_gain", 1.0))
        tr = [Track.from_dict(x) for x in d.get("tracks", [])]
        p.tracks = tr or [Track("Spoor 1")]
        return p

    # ---- mixdown ---------------------------------------------------------- #
    def mixdown(self, start_beat=0.0, progress=None):
        """Meng alle sporen (met volume/mute/solo/effect) tot één stereo float32-array.
        progress(fractie 0..1) wordt zo nu en dan aangeroepen (voor de voortgangsbalk)."""
        if not HAVE_NUMPY:
            return None
        spb = 60.0 / self.bpm                      # seconden per beat
        total_sec = max(0.0, (self.end_beat() - start_beat)) * spb
        n = int(math.ceil(total_sec * SAMPLE_RATE)) + 1
        if n <= 1:
            return np.zeros((1, 2), np.float32)
        needs_tail = any(c.effect in TAIL_EFFECTS
                         for tr in self.tracks for c in tr.clips)
        if needs_tail:
            n += int(2.5 * SAMPLE_RATE)            # ruimte voor effect-staarten (echo/galm)
        any_solo = any(tr.solo for tr in self.tracks)
        total_clips = max(1, sum(len(tr.clips) for tr in self.tracks))
        done_clips = 0
        master = np.zeros((n, 2), np.float32)
        for tr in self.tracks:
            if tr.mute or (any_solo and not tr.solo):
                done_clips += len(tr.clips)
                if progress:
                    progress(min(1.0, done_clips / total_clips))
                continue
            tbuf = np.zeros((n, 2), np.float32)
            has = False
            for c in tr.clips:
                a = stretched_audio(c.path, self.bpm)   # loop op het project-tempo
                done_clips += 1
                if progress:
                    progress(min(1.0, done_clips / total_clips))
                if a is None or a.shape[0] == 0:
                    continue
                # uitgerekt? herhaal de loop tot de gevraagde lengte
                if c.span_beats and c.span_beats > 0:
                    need = int(round(c.span_beats * spb * SAMPLE_RATE))
                    if need > a.shape[0]:
                        reps = int(math.ceil(need / a.shape[0]))
                        a = np.tile(a, (reps, 1))
                    a = a[:need]
                # eerst fades op het fragment, daarna het effect (zodat de staart uitklinkt)
                a = apply_fades(a, c.fade_in, c.fade_out)
                a = apply_effect(a, c.effect, self.bpm, c.effect_amount)
                dst = int(round((c.start_beat - start_beat) * spb * SAMPLE_RATE))
                if dst < 0:                         # clip begon vóór de startpositie
                    skip = -dst
                    if skip >= a.shape[0]:
                        continue
                    a = a[skip:]
                    dst = 0
                end = min(dst + a.shape[0], n)
                if dst >= n or end <= dst:
                    continue
                tbuf[dst:end] += a[: end - dst] * c.gain
                has = True
            if not has:
                continue
            master += tbuf * tr.gain
        peak = float(np.max(np.abs(master))) if master.size else 0.0
        if peak > 1.0:
            master /= peak                                     # interne clip-bescherming
        master *= float(getattr(self, "master_gain", 1.0))     # master-volume (echte regeling)
        np.clip(master, -1.0, 1.0, out=master)                 # eindlimiter
        return master

    def _write_wav(self, buf, path):
        if buf is None:
            return False
        if HAVE_SF:
            sf.write(path, buf, SAMPLE_RATE, subtype="PCM_16")
            return True
        ints = (np.clip(buf, -1.0, 1.0) * 32767.0).astype("<i2")
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
            w.writeframes(ints.tobytes())
        return True

    def export_wav(self, path):
        return self._write_wav(self.mixdown(0.0), path)

    def export_wav_buffer(self, buf, path):
        return self._write_wav(buf, path)

    def export_mp3(self, path):
        ff = ffmpeg_exe()
        if not ff:
            return False
        tmp = os.path.join(CACHE_DIR, "_mixdown.wav")
        if not self.export_wav(tmp):
            return False
        return self._wav_to_mp3(tmp, path)

    def export_mp3_buffer(self, buf, path):
        ff = ffmpeg_exe()
        if not ff:
            return False
        tmp = os.path.join(CACHE_DIR, "_mixdown.wav")
        if not self._write_wav(buf, tmp):
            return False
        return self._wav_to_mp3(tmp, path)

    def _wav_to_mp3(self, tmp, path):
        ff = ffmpeg_exe()
        try:
            subprocess.run([ff, "-y", "-i", tmp, "-codec:a", "libmp3lame",
                            "-q:a", "2", path],
                           capture_output=True,
                           creationflags=(0x08000000 if os.name == "nt" else 0))
            return os.path.exists(path) and os.path.getsize(path) > 0
        except Exception:
            return False


# =========================================================================== #
#  GUI
# =========================================================================== #
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QDialog, QFileDialog, QMessageBox,
    QLineEdit, QPlainTextEdit, QCheckBox, QSlider, QMenu, QInputDialog, QListWidget,
    QProgressDialog, QRadioButton, QButtonGroup, QSplashScreen,
)
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QIcon, QFont, QDrag
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QRectF, QMimeData

try:
    import winsound
    HAVE_WINSOUND = True
except Exception:
    HAVE_WINSOUND = False


def play_array(buf, sr=SAMPLE_RATE):
    """Speel een numpy-geluidsbuffer af (stopt eerst wat er speelde). True bij succes."""
    if HAVE_SD and buf is not None and getattr(buf, "size", 0) > 0:
        try:
            sd.stop(); sd.play(buf, sr); return True
        except Exception:
            return False
    return False


def stop_audio():
    if HAVE_SD:
        try:
            sd.stop()
        except Exception:
            pass
    if HAVE_WINSOUND:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


DRAVENLOCK_QSS = """
QMainWindow, QDialog, QWidget { background-color:#0e0e11; color:#d4d4d4; }
QLabel { color:#d4d4d4; }
QLabel#title { color:#f2f2f2; font-size:22px; font-weight:600; }
QLabel#subtitle { color:#9aa0a8; font-family:"Consolas","DejaVu Sans Mono",monospace; font-size:11px; }
QLabel#section { color:#a8a8b0; font-size:11px; font-weight:600; letter-spacing:1px; }
QLabel#mono { color:#8e8e96; font-family:"Consolas","DejaVu Sans Mono",monospace; }
QMessageBox QLabel, QInputDialog QLabel { font-size:14pt; }
QMessageBox QPushButton { font-size:12pt; padding:8px 22px; min-width:90px; }
#panel, #header { background-color:#16161b; border:1px solid #2a2a31; border-radius:10px; }
QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QListWidget {
    background-color:#23232a; color:#d6d6d6; border:1px solid #3a3a44; border-radius:8px; padding:8px 10px;
}
QPushButton:hover, QComboBox:hover { background-color:#2d2d36; border-color:#4a4a56; }
QPushButton:pressed { background-color:#34343f; }
QPushButton:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QListWidget:focus, QLineEdit:focus, QPlainTextEdit:focus { border:2px solid #6fa3d6; }
QPushButton#cta { background-color:#27384b; border:1px solid #6fa3d6; color:#eaf3fc; }
QPushButton#cta:hover { background-color:#2f4661; }
QPushButton:disabled, QDoubleSpinBox:disabled { color:#666; border-color:#2a2a31; }
QListWidget { background-color:#1b1b21; }
QListWidget::item:selected { background-color:#27384b; border:1px solid #6fa3d6; color:#fff; }
QTreeWidget { background-color:#1b1b21; border:1px solid #2a2a31; border-radius:8px; }
QTreeWidget::item { padding:4px; }
QTreeWidget::item:selected { background-color:#27384b; color:#fff; }
QScrollArea { border:none; }
QSlider::groove:horizontal { height:6px; background:#46464f; border-radius:3px; }
QSlider::handle:horizontal { background:#d0d0d0; width:18px; margin:-7px 0; border-radius:9px; }
QStatusBar { background-color:#121216; color:#c8c8c8; }
"""


def make_logo(size):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor("#27384b")); p.setPen(QColor("#6fa3d6"))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 8, 8)
    p.setPen(QColor("#eaf3fc"))
    f = QFont("Arial", int(size * 0.46)); f.setBold(True); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "♪")
    p.end()
    return pm


def app_icon():
    for name in ("logo.ico", "logo.png"):
        p = resource_path(name)
        if os.path.exists(p):
            ic = QIcon(p)
            if not ic.isNull():
                return ic
        p2 = os.path.join(APP_DIR, name)
        if os.path.exists(p2):
            ic = QIcon(p2)
            if not ic.isNull():
                return ic
    return QIcon(make_logo(64))


def logo_pixmap(h):
    for name in ("logo.png", "logo.ico"):
        for base in (resource_path(name), os.path.join(APP_DIR, name)):
            if os.path.exists(base):
                pm = QPixmap(base)
                if not pm.isNull():
                    return pm.scaledToHeight(h, Qt.SmoothTransformation)
    return make_logo(h)


def make_splash_pixmap():
    """Opstart-splash: logo + naam + tagline op de donkere huisstijl-achtergrond."""
    W, H = 480, 300
    pm = QPixmap(W, H); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor("#0e0e11")); p.setPen(QPen(QColor("#2a2a31"), 2))
    p.drawRoundedRect(1, 1, W - 2, H - 2, 16, 16)
    logo = logo_pixmap(110)
    p.drawPixmap((W - logo.width()) // 2, 34, logo)
    p.setPen(QColor("#f2f2f2")); f = QFont("Arial", 26); f.setBold(True); p.setFont(f)
    p.drawText(QRectF(0, 150, W, 44), Qt.AlignCenter, APP_NAME)
    p.setPen(QColor("#7fb4ff")); f2 = QFont("Arial", 13); f2.setBold(True); p.setFont(f2)
    p.drawText(QRectF(0, 198, W, 26), Qt.AlignCenter, t("Een lichte muziekmaker met loops en sporen."))
    p.setPen(QColor("#8b909a")); p.setFont(QFont("Arial", 10))
    p.drawText(QRectF(0, 236, W, 22), Qt.AlignCenter, f"een {AUTHOR_NAME} product")
    p.setPen(QColor("#5f6b78")); p.setFont(QFont("Arial", 9))
    p.drawText(QRectF(0, 262, W, 20), Qt.AlignCenter, f"v{APP_VERSION}")
    p.end()
    return pm


def section(text):
    lbl = QLabel(t(text).upper()); lbl.setObjectName("section"); return lbl


# ---- versie-controle ------------------------------------------------------ #
def parse_version(s):
    import re
    nums = re.findall(r"\d+", str(s or ""))
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(remote, local=APP_VERSION):
    return parse_version(remote) > parse_version(local)


def fetch_latest_version():
    try:
        req = urllib.request.Request(UPDATE_CHECK_URL,
                                     headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=6) as r:
            text = r.read().decode("utf-8", "replace").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return {"version": lines[0], "notes": "\n".join(lines[1:])} if lines else None
    except Exception:
        return None


class _UpdateWorker(QThread):
    done = pyqtSignal(object)

    def run(self):
        self.done.emit(fetch_latest_version())


class _ExportWorker(QThread):
    """Mixt en schrijft het bestand in een aparte thread, met voortgang."""
    progress = pyqtSignal(int)
    done = pyqtSignal(bool, str)

    def __init__(self, project, path, ext, parent=None):
        super().__init__(parent)
        self.project = project; self.path = path; self.ext = ext

    def run(self):
        try:
            self.progress.emit(3)
            buf = self.project.mixdown(0.0, progress=lambda f: self.progress.emit(int(5 + f * 65)))
            if buf is None:
                self.done.emit(False, self.path); return
            self.progress.emit(72)
            if self.ext == "wav":
                ok = self.project.export_wav_buffer(buf, self.path)
            else:
                ok = self.project.export_mp3_buffer(buf, self.path)
            self.progress.emit(100)
            self.done.emit(bool(ok), self.path)
        except Exception:
            self.done.emit(False, self.path)


class ExportDialog(QDialog):
    """Export-venster: bestandsnaam + formaat (WAV/MP3) + map kiezen."""
    def __init__(self, default_dir, mp3_ok=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Exporteren"))
        self.resize(460, 230)
        self.folder = default_dir
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Bestandsnaam:")))
        self.name = QLineEdit("mijn-mix"); lay.addWidget(self.name)
        lay.addWidget(QLabel(t("Formaat:")))
        row = QHBoxLayout()
        self.wav_rb = QRadioButton("WAV"); self.wav_rb.setChecked(True)
        self.mp3_rb = QRadioButton("MP3"); self.mp3_rb.setEnabled(mp3_ok)
        grp = QButtonGroup(self); grp.addButton(self.wav_rb); grp.addButton(self.mp3_rb)
        row.addWidget(self.wav_rb); row.addWidget(self.mp3_rb); row.addStretch(1)
        lay.addLayout(row)
        if not mp3_ok:
            lay.addWidget(QLabel(t("(MP3 vereist ffmpeg)")))
        frow = QHBoxLayout()
        self.folder_lbl = QLabel(self._short(self.folder)); frow.addWidget(self.folder_lbl, 1)
        fb = QPushButton(t("Map kiezen…")); fb.clicked.connect(self._choose_folder); frow.addWidget(fb)
        lay.addLayout(frow)
        lay.addStretch(1)
        brow = QHBoxLayout(); brow.addStretch(1)
        cancel = QPushButton(t("Annuleren")); cancel.clicked.connect(self.reject)
        ok = QPushButton(t("Exporteren")); ok.setObjectName("cta"); ok.clicked.connect(self.accept)
        brow.addWidget(cancel); brow.addWidget(ok); lay.addLayout(brow)

    def _short(self, d):
        return (t("Map") + ": …" + d[-34:]) if len(d) > 36 else (t("Map") + ": " + d)

    def _choose_folder(self):
        d = QFileDialog.getExistingDirectory(self, t("Map kiezen…"), self.folder)
        if d:
            self.folder = d; self.folder_lbl.setText(self._short(d))

    def result_path(self):
        ext = "wav" if self.wav_rb.isChecked() else "mp3"
        name = (self.name.text().strip() or "mijn-mix")
        for ch in '\\/:*?"<>|':
            name = name.replace(ch, "_")
        if name.lower().endswith("." + ext):
            name = name[: -(len(ext) + 1)]
        return os.path.join(self.folder, f"{name}.{ext}"), ext


# ---- dialogen ------------------------------------------------------------- #
class QuickGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("📖 Snelgids") + " - " + APP_NAME)
        self.resize(660, 640)
        lay = QVBoxLayout(self)
        txt = QPlainTextEdit(); txt.setReadOnly(True)
        txt.setPlainText(
            f"{APP_NAME} — {t('Een lichte muziekmaker met loops en sporen.')}\n\n"
            "── AAN DE SLAG ──\n"
            "1. Klik op 'Map met loops laden…' en kies een map met geluidsbestanden\n"
            "   (WAV/MP3/OGG/FLAC), bijvoorbeeld een soundpool of je eigen clips.\n"
            "   Klik op een map om 'm te openen; dubbelklik om 'm te sluiten.\n"
            "2. Klik op een loop om 'm te beluisteren. Kies links een spoor en\n"
            "   dubbelklik een loop om 'm op de afspeelkop te zetten, of sleep 'm\n"
            "   op de tijdlijn (slepen vanuit Windows Verkenner kan ook).\n"
            "3. Versleep clips om ze te verschuiven (ook tussen sporen). Met 'Raster\n"
            "   (magnetisch)' aan klikken ze netjes op de tel. Rek een clip uit aan\n"
            "   de rechterrand: de loop herhaalt dan tot die lengte.\n"
            "4. Stel het tempo (BPM) in: de loops worden mee versneld/vertraagd\n"
            "   (toonhoogte blijft gelijk), zodat alles op jouw tempo loopt.\n\n"
            "── AFSPELEN ──\n"
            "• Afspelen / Pauze / Stop. De rode lijn is de afspeelkop; sleep 'm op de\n"
            "  liniaal of klik om te verspringen.\n"
            "• Metronoom: tik op elke tel (accent op tel 1). Alleen bij afspelen.\n"
            "• Lus: zet 'Lus begin' en 'Lus eind' (of sleep het blauwe gebied op de\n"
            "  liniaal). Met 'Lus' aan wordt dat stuk herhaald afgespeeld.\n"
            "• Niveaumeter (links): groen/geel/rood toont het uitgangsniveau.\n"
            "• Master-volume (links) regelt het totale niveau van alles.\n\n"
            "── SPOREN & MIXER ──\n"
            "• '+ Spoor' voegt een spoor toe. Rechterklik op de mixer (links in de\n"
            "  tijdlijn) om een spoor te hernoemen of te verwijderen.\n"
            "• Per spoor: M = mute, S = solo, en het volumebalkje.\n\n"
            "── CLIPS BEWERKEN ──\n"
            "• Klik een clip om 'm rechts in te stellen (start, volume, lengte, fades).\n"
            "• Rechterklik een clip: Dupliceren, Kopiëren, Knippen, Verwijderen, Effect.\n"
            "  Sneltoetsen: Ctrl+C/X/V, Ctrl+D (dupliceren), Delete.\n"
            "• Meerdere clips: trek een kader om ze heen, of Ctrl-klik ze aan/uit.\n"
            "  Kopiëren/plakken werkt dan op de hele groep (de onderlinge plaatsing\n"
            "  blijft behouden). 'Plak hier' (rechterklik) plakt op die plek.\n\n"
            "── EFFECTEN (per clip) ──\n"
            "• Selecteer een clip en klik rechts op 'Effecten…'. Kies het effect en\n"
            "  regel de sterkte met de schuif; Beluister/Stop, dan Toepassen.\n"
            "• Beschikbaar: Echo, Galm, Dof, Helder, Overdrive, Tremolo, Bitcrusher,\n"
            "  Chorus, Toon (donker↔helder), Flanger, Ping-pong echo, Pan\n"
            "  (links↔rechts), Gater, Compressor, Phaser en Toonhoogte (lager↔hoger).\n\n"
            "── BLOKJES (eigen combinaties) ──\n"
            "• Selecteer een groep clips en klik 'Selectie → blokje' om de combinatie\n"
            "  te bewaren (met naam). Blokjes blijven bewaard tussen sessies.\n"
            "• Dubbelklik een blokje om het op de afspeelkop te plaatsen; rechterklik\n"
            "  voor plaatsen/hernoemen/verwijderen.\n\n"
            "── PROJECT & EXPORT ──\n"
            "• Nieuw / Openen / Opslaan, en 'Recent…' voor je laatste projecten.\n"
            "• Exporteren: kies een bestandsnaam en formaat (WAV/MP3) en eventueel een\n"
            "  map; een voortgangsbalk toont het mixen/converteren.\n\n"
            "Tip: zet een 'logo.png' in de programmamap voor je eigen logo overal.\n")
        lay.addWidget(txt)
        b = QPushButton(t("Sluiten")); b.setObjectName("cta"); b.clicked.connect(self.accept)
        lay.addWidget(b)


def open_quick_guide(parent=None):
    QuickGuideDialog(parent).exec_()


class ContactDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Contact opnemen") + " - " + APP_NAME)
        self.resize(560, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Soort bericht:")))
        self.kind = QComboBox()
        self.kind.addItems([t("Vraag"), t("Klacht"), t("Idee"), t("Bug / fout"), t("Anders")])
        lay.addWidget(self.kind)
        lay.addWidget(QLabel(t("Je naam:")))
        self.name = QLineEdit(); lay.addWidget(self.name)
        lay.addWidget(QLabel(t("Je e-mailadres (zodat de maker je kan antwoorden):")))
        self.email = QLineEdit(); lay.addWidget(self.email)
        lay.addWidget(QLabel(t("Je bericht:")))
        self.body = QPlainTextEdit(); self.body.setMinimumHeight(180); lay.addWidget(self.body, 1)
        lay.addWidget(QLabel(f"{SERVICE_EMAIL}"))
        row = QHBoxLayout()
        copy = QPushButton(t("📋 Kopieer e-mailadres")); copy.clicked.connect(self._copy)
        row.addWidget(copy); row.addStretch(1)
        cancel = QPushButton(t("Sluiten")); cancel.clicked.connect(self.reject); row.addWidget(cancel)
        send = QPushButton(t("✉️ Versturen")); send.setObjectName("cta"); send.clicked.connect(self._send)
        row.addWidget(send); lay.addLayout(row)

    def _copy(self):
        QApplication.clipboard().setText(SERVICE_EMAIL)

    def _send(self):
        if not self.body.toPlainText().strip():
            return
        subject = f"[{APP_NAME} v{APP_VERSION}] {self.kind.currentText()}"
        body = (f"{self.name.text().strip()} <{self.email.text().strip()}>\n\n"
                f"{self.body.toPlainText().strip()}\n")
        url = f"mailto:{SERVICE_EMAIL}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        from PyQt5.QtGui import QDesktopServices
        if QDesktopServices.openUrl(QUrl(url)):
            self.accept()
        else:
            QApplication.clipboard().setText(f"{SERVICE_EMAIL}\n{subject}\n\n{body}")


class SettingsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Instellingen…").rstrip("…") + " - " + APP_NAME)
        self.resize(360, 300)
        lay = QVBoxLayout(self)
        g = QGridLayout()
        g.addWidget(QLabel(t("Tempo (BPM)")), 0, 0)
        self.bpm = QSpinBox(); self.bpm.setRange(40, 300); self.bpm.setValue(int(project.bpm))
        g.addWidget(self.bpm, 0, 1)
        g.addWidget(QLabel("Tellen per maat"), 1, 0)
        self.bpb = QSpinBox(); self.bpb.setRange(2, 12); self.bpb.setValue(project.beats_per_bar)
        g.addWidget(self.bpb, 1, 1)
        lay.addLayout(g)
        lay.addWidget(section("Taal"))
        self.lang = QComboBox()
        self._codes = ["auto", "nl", "en"]
        self.lang.addItems([t("Automatisch (computertaal)"), t("Nederlands"), t("English")])
        cur = load_config().get("language", "auto")
        self.lang.setCurrentIndex(self._codes.index(cur) if cur in self._codes else 0)
        lay.addWidget(self.lang)
        note = QLabel(t("De taal verandert nadat je DraveSound opnieuw start."))
        note.setObjectName("mono"); note.setWordWrap(True); lay.addWidget(note)
        lay.addStretch(1)
        row = QHBoxLayout(); row.addStretch(1)
        c = QPushButton(t("Annuleer")); c.clicked.connect(self.reject); row.addWidget(c)
        ok = QPushButton(t("Toepassen")); ok.setObjectName("cta"); ok.clicked.connect(self.accept)
        row.addWidget(ok); lay.addLayout(row)

    def language(self):
        return self._codes[self.lang.currentIndex()]


class EffectDialog(QDialog):
    """Eigen venster: kies het effect, regel de sterkte, beluister, en pas toe op de clip."""

    NEUTRAL = NEUTRAL_EFFECTS                       # 50% = neutraal i.p.v. uit
    CAPTION = {"Toon (donker ↔ helder)": "Toon (donker ↔ helder):",
               "Pan (links ↔ rechts)": "Pan (links ↔ rechts):",
               "Tremolo": "Diepte (minder ↔ meer):",
               "Overdrive (vervorming)": "Vervorming (zachter ↔ ruwer):",
               "Bitcrusher (lo-fi)": "Lo-fi (subtiel ↔ grof):",
               "Flanger": "Diepte (subtiel ↔ sterk):",
               "Gater": "Gate (zwak ↔ sterk):",
               "Compressor": "Compressie (zacht ↔ sterk):",
               "Phaser": "Phaser (subtiel ↔ sterk):",
               "Toonhoogte (lager ↔ hoger)": "Toonhoogte (lager ↔ hoger):"}

    def __init__(self, clip, on_change=None, on_preview=None, on_stop=None, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.on_change = on_change
        self.on_preview = on_preview
        self.on_stop = on_stop
        self._orig = (clip.effect, clip.effect_amount)   # voor Annuleren
        self.setWindowTitle(t("Effecten") + " — " + clip.name)
        self.resize(440, 290)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Kies een effect:")))
        self.combo = QComboBox(); self.combo.addItems(EFFECTS)
        self.combo.setCurrentText(clip.effect if clip.effect in EFFECTS else "Geen")
        self.combo.currentTextChanged.connect(self._effect_changed)
        lay.addWidget(self.combo)
        self.cap_lbl = QLabel()
        lay.addWidget(self.cap_lbl)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0, 100)
        self.slider.setValue(int(clip.effect_amount * 100))
        self.slider.valueChanged.connect(self._changed)
        lay.addWidget(self.slider)
        self.amt_lbl = QLabel(); lay.addWidget(self.amt_lbl)
        lay.addStretch(1)
        row = QHBoxLayout()
        prev = QPushButton(t("▶ Beluister")); prev.clicked.connect(self._preview)
        stopb = QPushButton(t("⏹ Stop")); stopb.clicked.connect(self._stop)
        row.addWidget(prev); row.addWidget(stopb); row.addStretch(1)
        cancel = QPushButton(t("Annuleren")); cancel.clicked.connect(self.reject)
        apply = QPushButton(t("Toepassen")); apply.setObjectName("cta"); apply.clicked.connect(self._apply)
        row.addWidget(cancel); row.addWidget(apply)
        lay.addLayout(row)
        self._update_caption()
        self._changed()

    def _update_caption(self):
        fx = self.combo.currentText()
        self.cap_lbl.setText(t(self.CAPTION.get(fx, "Sterkte (minder ↔ meer):")))
        self.slider.setEnabled(fx != "Geen")

    def _effect_changed(self, fx):
        # bij wisselen naar een neutraal-effect: start op het midden
        if fx in self.NEUTRAL and self.slider.value() != 50:
            self.slider.blockSignals(True); self.slider.setValue(50); self.slider.blockSignals(False)
        self._update_caption()
        self._changed()

    def _changed(self, *_):
        self.clip.effect = self.combo.currentText()
        self.clip.effect_amount = self.slider.value() / 100.0
        self.amt_lbl.setText(f"{self.slider.value()}%")
        if self.on_change:
            self.on_change()

    def _preview(self):
        if self.on_preview:
            self.on_preview(self.clip)

    def _stop(self):
        if self.on_stop:
            self.on_stop()

    def _apply(self):
        self._stop(); self.accept()

    def reject(self):
        # zet de clip terug zoals hij was
        self.clip.effect, self.clip.effect_amount = self._orig
        if self.on_change:
            self.on_change()
        self._stop()
        super().reject()


DRAG_MIME = "application/x-dravesound"


class LoopTree(QTreeWidget):
    """Boom met de loop-bibliotheek; loops en mappen zijn naar de tijdlijn te slepen."""
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragOnly)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setExpandsOnDoubleClick(False)   # wij regelen open/dicht zelf

    def startDrag(self, actions):
        it = self.currentItem()
        if it is None:
            return
        f = it.data(0, Qt.UserRole)          # bestand
        d = it.data(0, Qt.UserRole + 1)      # map (soundpool)
        payload = ("F|" + f) if f else (("D|" + d) if d else None)
        if not payload:
            return
        md = QMimeData()
        md.setData(DRAG_MIME, payload.encode("utf-8"))
        md.setText(payload)
        drag = QDrag(self); drag.setMimeData(md)
        drag.exec_(Qt.CopyAction)


class IntroOverlay(QWidget):
    """Het introscherm dat over de lege tijdlijn ligt; geeft drops door aan de tijdlijn."""
    def __init__(self, parent, arrange):
        super().__init__(parent)
        self._arrange = arrange
        self.setAcceptDrops(True)

    def dragEnterEvent(self, ev):
        md = ev.mimeData()
        if md.hasFormat(DRAG_MIME) or md.hasText() or md.hasUrls():
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        ev.acceptProposedAction()

    def dropEvent(self, ev):
        # lege tijdlijn: zet op het eerste spoor, aan het begin
        self._arrange.apply_drop(ev.mimeData(), 0, 0.0)
        ev.acceptProposedAction()


class PreviewBar(QWidget):
    """Tijdelijke voorbeeld-balk: toont en speelt een loop af voor je 'm gebruikt."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(34)
        self.name = ""; self.dur = 0.0; self.prog = 0.0; self._start = 0.0
        self._t = QTimer(self); self._t.timeout.connect(self._step)
        self.hide()

    def start(self, name, seconds):
        self.name = name; self.dur = max(0.05, seconds); self.prog = 0.0
        self._start = time.monotonic(); self.show(); self._t.start(33)

    def stop(self):
        self._t.stop(); self.hide()

    def _step(self):
        self.prog = (time.monotonic() - self._start) / self.dur
        if self.prog >= 1.0:
            self.stop(); return
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#16161b"))
        p.setPen(QColor("#2a2a31")); p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        fillw = int((self.width() - 2) * max(0.0, min(1.0, self.prog)))
        p.fillRect(1, 1, fillw, self.height() - 2, QColor("#27384b"))
        cx = 1 + fillw
        p.setPen(QPen(QColor("#6fa3d6"), 2)); p.drawLine(cx, 1, cx, self.height() - 1)
        p.setPen(QColor("#eaf3fc")); p.setFont(QFont("Arial", 9))
        p.drawText(8, 0, self.width() - 16, self.height(), Qt.AlignVCenter,
                   "♪  " + (t("Voorbeeld") + ": " if False else "") + self.name)
        p.end()


class LevelMeter(QWidget):
    """Niveaumeter: groen → geel → rood; toont of het uitgangsniveau te hard (clipt) gaat."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(14)
        self.level = 0.0      # 0..1 (huidig niveau)
        self.peak = 0.0       # vasthoud-piek

    def set_level(self, v):
        v = max(0.0, min(1.0, float(v)))
        self.level = v
        # piek zakt langzaam, springt direct omhoog
        self.peak = v if v > self.peak else max(v, self.peak - 0.04)
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        w = self.width() - 2; h = self.height() - 2
        p.fillRect(self.rect(), QColor("#0c0c0f"))
        p.setPen(QColor("#2a2a31")); p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        # gevulde balk, per segment ingekleurd
        fill = int(w * self.level)
        for x in range(0, fill):
            frac = x / float(max(1, w))
            if frac < 0.7:
                col = QColor("#3fae5a")        # groen
            elif frac < 0.9:
                col = QColor("#d6b13a")        # geel
            else:
                col = QColor("#d6534a")        # rood
            p.fillRect(1 + x, 1, 1, h, col)
        # piek-streepje
        if self.peak > 0.01:
            px = 1 + int(w * self.peak)
            p.setPen(QPen(QColor("#eaf3fc"), 1)); p.drawLine(px, 1, px, h + 1)
        p.end()


# ---- tijdlijn (maten/beats) ----------------------------------------------- #
class ArrangeView(QWidget):
    GUTTER = 120        # linker kolom met spoornamen + mixer
    RULER = 42          # twee rijen: maten boven, seconden eronder
    LANE = 76

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.ppb = 26.0           # pixels per beat
        self.playhead = 0.0       # in beats
        self.snap = True
        self.loop_on = False
        self.loop_start = 0.0
        self.loop_end = 0.0
        self.sel = None           # (track_idx, clip) — primaire selectie (rechterpaneel)
        self.sel_clips = set()    # meervoudige selectie (clip-objecten)
        self._marquee = None      # (x0,y0,x1,y1) tijdens kader trekken
        self._marquee_anchor = None
        self.on_select = None
        self.on_change = None
        self.on_playhead = None
        self.on_audition = None
        self.on_audition_clip = None
        self.on_track = None
        self.on_context = None
        self._drag = None         # (clip, grab_offset_beats, src_track_idx)
        self._resize = None       # (clip, track_idx) tijdens uitrekken
        self._ph_drag = False     # afspeelkop verslepen
        self._loop_drag = None    # 'new' | 'start' | 'end' tijdens lus-slepen
        self._loop_anchor = 0.0
        self.on_loop = None       # callback(start, end) bij lus-slepen
        self._cur_track = 0
        self._vp_w = 0
        self._vp_h = 0
        self.setMinimumHeight(self.RULER + self.LANE * 3 + 20)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._recalc()

    def set_viewport(self, w, h):
        self._vp_w, self._vp_h = int(w), int(h)
        self._recalc(); self.update()

    def set_project(self, project):
        self.project = project; self.sel = None; self.sel_clips = set(); self._recalc(); self.update()

    def _recalc(self):
        beats = max(self.project.end_beat() + self.project.beats_per_bar * 4, 32)
        w = int(self.GUTTER + beats * self.ppb + 40)
        h = self.RULER + self.LANE * len(self.project.tracks) + 10
        w = max(w, self._vp_w)        # vul minstens de zichtbare breedte
        h = max(h, self._vp_h)        # vul minstens de zichtbare hoogte
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def set_zoom(self, ppb):
        self.ppb = max(6.0, min(120.0, ppb)); self._recalc(); self.update()

    def beat_to_x(self, b):
        return self.GUTTER + b * self.ppb

    def x_to_beat(self, x):
        return max(0.0, (x - self.GUTTER) / self.ppb)

    def _snap(self, beat):
        return round(beat) if self.snap else beat

    def _clip_at(self, x, y):
        ti = int((y - self.RULER) // self.LANE)
        if ti < 0 or ti >= len(self.project.tracks):
            return None, ti
        b = self.x_to_beat(x)
        for c in reversed(self.project.tracks[ti].clips):
            if c.start_beat <= b <= c.start_beat + c.length_beats(self.project.bpm):
                return c, ti
        return None, ti

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        # spoor-kolom (mixer): M / S / volume / spoor kiezen
        if ev.x() < self.GUTTER and ev.y() >= self.RULER:
            ti = int((ev.y() - self.RULER) // self.LANE)
            if 0 <= ti < len(self.project.tracks):
                tr = self.project.tracks[ti]
                lane_top = self.RULER + ti * self.LANE
                (mx, my, mw, mh), (sx, sy, sw, sh), (vx, vy, vw, vh) = self._ctrl_rects(lane_top)
                if mx <= ev.x() <= mx + mw and my <= ev.y() <= my + mh:
                    tr.mute = not tr.mute
                elif sx <= ev.x() <= sx + sw and sy <= ev.y() <= sy + sh:
                    tr.solo = not tr.solo
                elif vx <= ev.x() <= vx + vw and vy <= ev.y() <= vy + vh:
                    tr.gain = max(0.0, min(1.5, (ev.x() - vx) / float(vw) * 1.5))
                self._cur_track = ti
                if self.on_track:
                    self.on_track(ti)
                self.update()
            return
        # lus slepen op de liniaal (alleen als de lus aanstaat)
        if self.loop_on and ev.y() < self.RULER and ev.x() >= self.GUTTER:
            if self.loop_end > self.loop_start and abs(ev.x() - self.beat_to_x(self.loop_start)) <= 7:
                self._loop_drag = "start"
            elif self.loop_end > self.loop_start and abs(ev.x() - self.beat_to_x(self.loop_end)) <= 7:
                self._loop_drag = "end"
            else:
                self._loop_drag = "new"
                self._loop_anchor = self._snap(self.x_to_beat(ev.x()))
            return
        # afspeelkop: in de liniaal, of door de rode lijn zelf te pakken
        near_line = abs(ev.x() - self.beat_to_x(self.playhead)) <= 5
        if ev.y() < self.RULER or near_line:
            self._ph_drag = True
            self.playhead = self._snap(self.x_to_beat(ev.x()))
            if self.on_playhead: self.on_playhead()
            self.update(); return
        clip, ti = self._clip_at(ev.x(), ev.y())
        ctrl = bool(ev.modifiers() & Qt.ControlModifier)
        if clip is not None:
            if ctrl:                                 # Ctrl-klik: toevoegen/verwijderen uit selectie
                if clip in self.sel_clips:
                    self.sel_clips.discard(clip)
                else:
                    self.sel_clips.add(clip)
                self.sel = (ti, clip)
                if self.on_select:
                    self.on_select(ti, clip)
                self.update(); return
            if clip not in self.sel_clips:           # gewone klik op niet-geselecteerde clip
                self.sel_clips = {clip}
            self.sel = (ti, clip)
            right_x = self.beat_to_x(clip.start_beat + clip.length_beats(self.project.bpm))
            if abs(ev.x() - right_x) <= 6:          # rechterrand -> uitrekken
                self._resize = (clip, ti)
                if self.on_select:
                    self.on_select(ti, clip)
            else:
                self._drag = (clip, self.x_to_beat(ev.x()) - clip.start_beat, ti)
                if self.on_select:
                    self.on_select(ti, clip)
        else:
            # lege plek: begin een selectiekader (kader trekken)
            self.sel = None
            if not ctrl:
                self.sel_clips = set()
            self._marquee_anchor = (ev.x(), ev.y())
            self._marquee = (ev.x(), ev.y(), ev.x(), ev.y())
            if self.on_select:
                self.on_select(ti, None)
        self.update()

    def _apply_loop_drag(self, b):
        b = max(0.0, b)
        if self._loop_drag == "start":
            self.loop_start = max(0.0, min(b, self.loop_end - 1.0))
        elif self._loop_drag == "end":
            self.loop_end = max(b, self.loop_start + 1.0)
        else:  # new: van anker naar huidige positie
            self.loop_start = max(0.0, min(self._loop_anchor, b))
            self.loop_end = max(self._loop_anchor, b)
        self.update()
        if self.on_loop:
            self.on_loop(self.loop_start, self.loop_end)

    def mouseMoveEvent(self, ev):
        if self._loop_drag is not None:
            self._apply_loop_drag(self._snap(self.x_to_beat(ev.x()))); return
        if self._marquee is not None:
            x0, y0, _, _ = self._marquee
            self._marquee = (x0, y0, ev.x(), ev.y())
            self._select_in_marquee()
            self.update(); return
        if self._ph_drag:
            self.playhead = self._snap(self.x_to_beat(ev.x()))
            if self.on_playhead: self.on_playhead()
            self.update(); return
        if self._resize is not None:
            clip, _ti = self._resize
            span = self._snap(self.x_to_beat(ev.x()) - clip.start_beat)
            clip.span_beats = max(1.0, span)
            self._recalc(); self.update()
            if self.on_select:
                self.on_select(_ti, clip)
            if self.on_change:
                self.on_change()
            return
        if self._drag is not None:
            clip, off, src = self._drag
            # horizontaal: verschuif in de tijd
            clip.start_beat = max(0.0, self._snap(self.x_to_beat(ev.x()) - off))
            # verticaal: verplaats naar een ander spoor
            ti = int((ev.y() - self.RULER) // self.LANE)
            if 0 <= ti < len(self.project.tracks) and ti != src:
                if clip in self.project.tracks[src].clips:
                    self.project.tracks[src].clips.remove(clip)
                self.project.tracks[ti].clips.append(clip)
                self._drag = (clip, off, ti)
                self.sel = (ti, clip)
                if self.on_select:
                    self.on_select(ti, clip)
            self._recalc(); self.update()
            if self.on_change:
                self.on_change()
            return
        # cursor-hint op de rechterrand van een clip
        clip, _ti = self._clip_at(ev.x(), ev.y())
        if clip is not None:
            right_x = self.beat_to_x(clip.start_beat + clip.length_beats(self.project.bpm))
            self.setCursor(Qt.SizeHorCursor if abs(ev.x() - right_x) <= 6 else Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _select_in_marquee(self):
        if not self._marquee:
            return
        x0, y0, x1, y1 = self._marquee
        rx0, rx1 = min(x0, x1), max(x0, x1)
        ry0, ry1 = min(y0, y1), max(y0, y1)
        sel = set()
        for i, tr in enumerate(self.project.tracks):
            y = self.RULER + i * self.LANE + 6
            if y + (self.LANE - 14) < ry0 or y > ry1:    # rij buiten het kader
                continue
            for c in tr.clips:
                cx = self.beat_to_x(c.start_beat)
                cw = max(6.0, c.length_beats(self.project.bpm) * self.ppb)
                if cx + cw >= rx0 and cx <= rx1:         # clip overlapt horizontaal
                    sel.add(c)
        self.sel_clips = sel

    def mouseReleaseEvent(self, ev):
        if self._marquee is not None:
            ax, ay = self._marquee_anchor or (ev.x(), ev.y())
            moved = abs(ev.x() - ax) > 4 or abs(ev.y() - ay) > 4
            if not moved:                                # gewone klik op lege plek
                self.sel_clips = set()
                self.playhead = self._snap(self.x_to_beat(ev.x()))
                if self.on_playhead:
                    self.on_playhead()
            self._marquee = None; self._marquee_anchor = None
            self.update()
        self._drag = None
        self._resize = None
        self._ph_drag = False
        self._loop_drag = None

    def contextMenuEvent(self, ev):
        x, y = ev.pos().x(), ev.pos().y()
        if y < self.RULER:
            return
        ti = max(0, min(len(self.project.tracks) - 1, int((y - self.RULER) // self.LANE)))
        in_gutter = x < self.GUTTER
        if in_gutter:                               # rechterklik op de mixer = spoor-menu
            if self.on_context:
                self.on_context(None, ti, 0.0, ev.globalPos(), True)
            return
        clip, cti = self._clip_at(x, y)
        if clip is not None:
            ti = cti
        beat = self._snap(self.x_to_beat(x))
        if clip is not None:
            self.sel = (ti, clip)
            if clip not in self.sel_clips:          # buiten de groep geklikt -> alleen deze clip
                self.sel_clips = {clip}
            if self.on_select:
                self.on_select(ti, clip)
            self.update()
        if self.on_context:
            self.on_context(clip, ti, beat, ev.globalPos(), False)

    # ---- slepen vanuit de bibliotheek of vanuit Windows Verkenner ---- #
    def dragEnterEvent(self, ev):
        md = ev.mimeData()
        if md.hasFormat(DRAG_MIME) or md.hasText() or md.hasUrls():
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        ev.acceptProposedAction()

    def _add_path_at(self, path, ti, beat):
        """Voeg één bestand of een hele map (loops achter elkaar) toe op spoor ti vanaf beat."""
        last = None
        if os.path.isdir(path):
            b = beat
            for fn in sorted(os.listdir(path)):
                fp = os.path.join(path, fn)
                if fn.lower().endswith(AUDIO_EXTS) and os.path.isfile(fp):
                    c = Clip(fp, b); self.project.tracks[ti].clips.append(c); last = (ti, c)
                    b += max(1.0, round(c.length_beats(self.project.bpm)))
        elif os.path.isfile(path) and path.lower().endswith(AUDIO_EXTS):
            c = Clip(path, beat); self.project.tracks[ti].clips.append(c); last = (ti, c)
        return last

    def apply_drop(self, md, ti, beat):
        """Verwerk een drop (bibliotheek of Verkenner) op spoor ti vanaf beat."""
        ti = max(0, min(len(self.project.tracks) - 1, ti))
        last = None
        if md.hasFormat(DRAG_MIME) or (md.hasText() and "|" in md.text()):
            raw = (bytes(md.data(DRAG_MIME)).decode("utf-8")
                   if md.hasFormat(DRAG_MIME) else md.text())
            _kind, _, path = raw.partition("|")
            last = self._add_path_at(path, ti, beat) or last
        elif md.hasUrls():                                  # sleep vanuit Verkenner
            b = beat
            for url in md.urls():
                p = url.toLocalFile()
                if not p:
                    continue
                res = self._add_path_at(p, ti, b)
                if res:
                    last = res
                    b = res[1].start_beat + max(1.0, round(res[1].length_beats(self.project.bpm)))
        if last:
            self.sel = last
            if self.on_select:
                self.on_select(*last)
        self._recalc(); self.update()
        if self.on_change:
            self.on_change()
        return last

    def dropEvent(self, ev):
        pos = ev.pos()
        ti = int((pos.y() - self.RULER) // self.LANE)
        beat = self._snap(self.x_to_beat(pos.x()))
        self.apply_drop(ev.mimeData(), ti, beat)
        ev.acceptProposedAction()

    def add_clip(self, path, track_idx, at_beat):
        if track_idx < 0 or track_idx >= len(self.project.tracks):
            return
        c = Clip(path, self._snap(at_beat))
        self.project.tracks[track_idx].clips.append(c)
        self.sel = (track_idx, c)
        self._recalc(); self.update()
        if self.on_select:
            self.on_select(track_idx, c)
        if self.on_change:
            self.on_change()

    def delete_selected(self):
        if not self.sel:
            return
        ti, clip = self.sel
        if 0 <= ti < len(self.project.tracks) and clip in self.project.tracks[ti].clips:
            self.project.tracks[ti].clips.remove(clip)
        self.sel = None; self._recalc(); self.update()
        if self.on_change:
            self.on_change()

    def _fmt_sec(self, s):
        return f"{int(s) // 60}:{int(s) % 60:02d}"

    def _ctrl_rects(self, lane_top):
        ry = lane_top + self.LANE - 30
        return ((8, ry, 26, 22), (38, ry, 26, 22), (72, ry, self.GUTTER - 80, 22))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0e0e11"))
        W, H = self.width(), self.height()
        bpb = self.project.beats_per_bar
        any_solo = any(tr.solo for tr in self.project.tracks)
        # lanes
        cur = getattr(self, "_cur_track", 0)
        for i, tr in enumerate(self.project.tracks):
            y = self.RULER + i * self.LANE
            p.fillRect(0, y, W, self.LANE, QColor("#1a1a20" if i % 2 == 0 else "#15151a"))
            p.setPen(QColor("#33333c")); p.drawLine(0, y, W, y)
            # naam-kolom (mixer)
            p.fillRect(0, y, self.GUTTER, self.LANE,
                       QColor("#22303f") if i == cur else QColor("#16161b"))
            p.setPen(QColor("#3a3a44")); p.drawLine(self.GUTTER, y, self.GUTTER, y + self.LANE)
            if i == cur:
                p.fillRect(0, y, 4, self.LANE, QColor("#6fa3d6"))
            p.setPen(QColor("#eaeaf0") if i == cur else QColor("#cfd2d6"))
            f = QFont("Arial", 10); f.setBold(i == cur); p.setFont(f)
            p.drawText(12, y + 4, self.GUTTER - 18, 22, Qt.AlignVCenter, tr.name)
            # M / S / volume
            (mx, my, mw, mh), (sx, sy, sw, sh), (vx, vy, vw, vh) = self._ctrl_rects(y)
            muted_eff = tr.mute or (any_solo and not tr.solo)
            p.setBrush(QColor("#7a2f2f") if tr.mute else QColor("#23232a"))
            p.setPen(QColor("#b05555") if tr.mute else QColor("#3a3a44"))
            p.drawRoundedRect(mx, my, mw, mh, 4, 4)
            p.setBrush(QColor("#7a6a2f") if tr.solo else QColor("#23232a"))
            p.setPen(QColor("#c9b24f") if tr.solo else QColor("#3a3a44"))
            p.drawRoundedRect(sx, sy, sw, sh, 4, 4)
            p.setPen(QColor("#eaeaf0")); p.setFont(QFont("Arial", 9))
            p.drawText(mx, my, mw, mh, Qt.AlignCenter, "M")
            p.drawText(sx, sy, sw, sh, Qt.AlignCenter, "S")
            # volumebalk (0..150%)
            p.setBrush(QColor("#23232a")); p.setPen(QColor("#3a3a44"))
            p.drawRoundedRect(vx, vy, vw, vh, 4, 4)
            frac = max(0.0, min(1.0, tr.gain / 1.5))
            p.fillRect(vx + 2, vy + 2, int((vw - 4) * frac), vh - 4, QColor("#3a6ea5"))
            p.setPen(QColor("#cfd6de")); p.setFont(QFont("Arial", 7))
            p.drawText(vx, vy, vw, vh, Qt.AlignCenter, f"{int(tr.gain * 100)}%")
            if muted_eff:
                p.setPen(QColor("#8a8a92")); p.setFont(QFont("Arial", 7))
                p.drawText(12, y + 4, self.GUTTER - 18, 22, Qt.AlignRight | Qt.AlignVCenter, "stil")
        # onderrand laatste spoor
        p.setPen(QColor("#33333c"))
        p.drawLine(0, self.RULER + self.LANE * len(self.project.tracks),
                   W, self.RULER + self.LANE * len(self.project.tracks))
        # raster (verticale lijnen)
        beats = int((W - self.GUTTER) / self.ppb) + 2
        for b in range(beats + 1):
            x = self.beat_to_x(b)
            bar_line = (b % bpb == 0)
            p.setPen(QColor("#2f2f37") if bar_line else QColor("#1d1d23"))
            p.drawLine(int(x), self.RULER, int(x), H)
        # liniaal-balk
        p.fillRect(0, 0, W, self.RULER, QColor("#16161b"))
        p.setPen(QColor("#2a2a31")); p.drawLine(0, self.RULER, W, self.RULER)
        # lus-gebied markeren op de liniaal
        if getattr(self, "loop_on", False) and self.loop_end > self.loop_start:
            lx = self.beat_to_x(self.loop_start); rx = self.beat_to_x(self.loop_end)
            p.fillRect(QRectF(lx, 0, rx - lx, self.RULER), QColor(111, 163, 214, 60))
            p.setPen(QColor("#6fa3d6"))
            p.drawLine(int(lx), 0, int(lx), self.RULER)
            p.drawLine(int(rx), 0, int(rx), self.RULER)
        midy = 22
        p.setPen(QColor("#33333c")); p.drawLine(self.GUTTER, midy, W, midy)
        # bovenrij: maten
        for b in range(0, beats + 1, bpb):
            x = self.beat_to_x(b)
            p.setPen(QColor("#9aa0a8")); p.setFont(QFont("Arial", 8))
            p.drawText(int(x) + 3, 0, 60, midy, Qt.AlignVCenter, "Maat " + str(b // bpb + 1))
        # onderrij: seconden (interval zo dat labels niet plakken)
        spb = 60.0 / self.project.bpm
        pps = self.ppb / spb                      # pixels per seconde
        step = 1
        for cand in (1, 2, 5, 10, 15, 30, 60):
            if cand * pps >= 42:
                step = cand; break
        else:
            step = 60
        total_sec = int((W - self.GUTTER) / pps) + 2
        for s in range(0, total_sec + 1, step):
            x = self.beat_to_x(s / spb)
            if x < self.GUTTER:
                continue
            p.setPen(QColor("#5f6b78")); p.drawLine(int(x), midy, int(x), self.RULER)
            p.setPen(QColor("#7f8a96")); p.setFont(QFont("Arial", 7))
            p.drawText(int(x) + 3, midy, 50, self.RULER - midy, Qt.AlignVCenter,
                       self._fmt_sec(s))
        # clips
        for i, tr in enumerate(self.project.tracks):
            y = self.RULER + i * self.LANE + 6
            for c in tr.clips:
                x = self.beat_to_x(c.start_beat)
                w = max(6.0, c.length_beats(self.project.bpm) * self.ppb)
                rect = QRectF(x, y, w, self.LANE - 14)
                selected = (self.sel and self.sel[1] is c) or (c in self.sel_clips)
                p.setBrush(QColor("#3a78c2") if selected else QColor("#2c557f"))
                p.setPen(QPen(QColor("#9ec3ec") if selected else QColor("#4a4a56"), 2 if selected else 1))
                p.drawRoundedRect(rect, 6, 6)
                # herhaal-streepjes als de loop is uitgerekt
                nat = c.natural_length_beats(self.project.bpm)
                if c.span_beats and nat > 0:
                    p.setPen(QPen(QColor("#1c3a59"), 1))
                    k = 1
                    while k * nat < c.span_beats - 0.01:
                        tx = self.beat_to_x(c.start_beat + k * nat)
                        p.drawLine(int(tx), int(y + 3), int(tx), int(y + self.LANE - 17))
                        k += 1
                # uitrek-handvat rechts
                p.setPen(QPen(QColor("#9ec3ec") if selected else QColor("#7fa6cc"), 2))
                hx = int(x + w) - 3
                p.drawLine(hx, int(y + 5), hx, int(y + self.LANE - 19))
                p.setPen(QColor("#eaf3fc")); p.setFont(QFont("Arial", 9))
                p.drawText(rect.adjusted(6, 2, -10, -2), Qt.AlignVCenter | Qt.TextWordWrap, c.name)
        # afspeelkop
        px = self.beat_to_x(self.playhead)
        p.setPen(QPen(QColor("#e2554f"), 2)); p.drawLine(int(px), 0, int(px), H)
        # selectiekader
        if self._marquee is not None:
            x0, y0, x1, y1 = self._marquee
            r = QRectF(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            p.setPen(QPen(QColor("#9ec3ec"), 1, Qt.DashLine))
            p.setBrush(QColor(111, 163, 214, 40)); p.drawRect(r)
        p.end()


# ---- hoofdvenster --------------------------------------------------------- #
class DraveSound(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self.cur_track = 0
        self.playing = False
        self.metronome = False
        self.loop_on = False
        self.loop_start = 0.0
        self.loop_end = 0.0
        self._upd_worker = None
        self._clipboard = None
        self.blocks = load_blocks()
        self.recent = load_config().get("recent", [])
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1280, 760)
        self._build()
        self.play_timer = QTimer(self); self.play_timer.timeout.connect(self._tick)
        self._update_intro(); self._update_time(); self._refresh_track_panel()

    # ---- UI ---- #
    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.addWidget(self._header())
        body = QHBoxLayout()
        body.addWidget(self._left(), 0)
        body.addWidget(self._center(), 1)
        body.addWidget(self._right(), 0)
        outer.addLayout(body, 1)
        self.statusBar().showMessage(f"{APP_NAME} v{APP_VERSION}")
        donate = QPushButton(t("♥ Donatie")); donate.setObjectName("cta")
        donate.setToolTip(t("Steun Dravenlock"))
        donate.clicked.connect(self._donate)
        self.statusBar().addPermanentWidget(donate)

    def _donate(self):
        from PyQt5.QtGui import QDesktopServices
        if not QDesktopServices.openUrl(QUrl(DONATE_URL)):
            QMessageBox.information(self, t("Donatie"),
                                    t("Steun Dravenlock — bedankt!") + f"\n{DONATE_URL}")

    def _header(self):
        h = QWidget(); h.setObjectName("header"); lay = QHBoxLayout(h)
        logo = QLabel(); logo.setPixmap(logo_pixmap(44)); lay.addWidget(logo)
        tb = QVBoxLayout(); tb.setSpacing(0)
        title = QLabel(APP_NAME); title.setObjectName("title")
        sub = QLabel(f"v{APP_VERSION}  ·  {t('een Dravenlock product')}"); sub.setObjectName("subtitle")
        tb.addWidget(title); tb.addWidget(sub); lay.addLayout(tb); lay.addStretch(1)
        for label, fn in [("📖 Snelgids", self.open_guide), ("✉️ Contact", self.open_contact),
                          ("🔄 Updates", lambda: self.check_updates(False)), ("ⓘ Info", self.show_info)]:
            b = QPushButton(t(label)); b.clicked.connect(fn); lay.addWidget(b)
        exp = QPushButton(t("⤓ Exporteren…")); exp.setObjectName("cta")
        exp.clicked.connect(self.export_dialog); lay.addWidget(exp)
        return h

    def _left(self):
        lay = QVBoxLayout(); lay.setSpacing(6)
        lay.addWidget(section("Project"))
        for label, fn in [("Nieuw", self.new_project), ("Openen…", self.open_project),
                          ("Opslaan…", self.save_project), ("Instellingen…", self.open_settings)]:
            b = QPushButton(t(label)); b.clicked.connect(fn); lay.addWidget(b)
        self.recent_btn = QPushButton(t("🕘 Recent…")); self.recent_btn.clicked.connect(self._recent_menu)
        lay.addWidget(self.recent_btn)
        lay.addWidget(section("Loop-bibliotheek"))
        lb = QPushButton(t("📂 Map met loops laden…")); lb.clicked.connect(self.load_loop_folder)
        lay.addWidget(lb)
        self.loops = LoopTree()
        self.loops.itemDoubleClicked.connect(self._add_loop_to_track)
        self.loops.itemClicked.connect(self._preview_loop)
        self.loops.setToolTip("Klik om te beluisteren · dubbelklik of sleep naar een spoor")
        lay.addWidget(self.loops, 1)
        lay.addWidget(section("Blokjes (eigen combinaties)"))
        sb = QPushButton(t("💾 Selectie → blokje")); sb.clicked.connect(self._save_block)
        lay.addWidget(sb)
        self.blocks_list = QListWidget(); self.blocks_list.setMaximumHeight(120)
        self.blocks_list.itemDoubleClicked.connect(lambda *_: self._place_block())
        self.blocks_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.blocks_list.customContextMenuRequested.connect(self._blocks_menu)
        self.blocks_list.setToolTip(t("Dubbelklik om op de afspeelkop te plaatsen"))
        lay.addWidget(self.blocks_list)
        self._refresh_blocks_list()
        lay.addWidget(section("Spoor"))
        self.track_combo = QComboBox(); self._refresh_tracks()
        self.track_combo.currentIndexChanged.connect(self._set_track); lay.addWidget(self.track_combo)
        at = QPushButton(t("+ Spoor")); at.clicked.connect(self.add_track); lay.addWidget(at)
        bpm_row = QHBoxLayout(); bpm_row.addWidget(QLabel(t("Tempo (BPM)")))
        self.bpm_spin = QSpinBox(); self.bpm_spin.setRange(40, 300); self.bpm_spin.setValue(int(self.project.bpm))
        self.bpm_spin.valueChanged.connect(self._set_bpm); bpm_row.addWidget(self.bpm_spin)
        lay.addLayout(bpm_row)
        self.grid_chk = QCheckBox(t("Raster (magnetisch)")); self.grid_chk.setChecked(True)
        self.grid_chk.toggled.connect(lambda on: setattr(self.arrange, "snap", on))
        lay.addWidget(self.grid_chk)
        self.master_lbl = QLabel(t("Master-volume") + f"  {int(self.project.master_gain * 100)}%")
        lay.addWidget(self.master_lbl)
        self.master_slider = QSlider(Qt.Horizontal); self.master_slider.setRange(0, 150)
        self.master_slider.setValue(int(self.project.master_gain * 100))
        self.master_slider.valueChanged.connect(self._set_master)
        lay.addWidget(self.master_slider)
        lay.addWidget(QLabel(t("Niveau")))
        self.meter = LevelMeter()
        lay.addWidget(self.meter)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(lay); panel.setFixedWidth(280)
        return panel

    def _set_master(self, v):
        self.project.master_gain = v / 100.0
        self.master_lbl.setText(t("Master-volume") + f"  {v}%")

    def _master(self, buf):
        """Pas het master-volume toe op om het even welke uitvoer (algemeen)."""
        if buf is None or not HAVE_NUMPY:
            return buf
        g = float(getattr(self.project, "master_gain", 1.0))
        if abs(g - 1.0) < 1e-3:
            return buf
        return np.clip(buf * g, -1.0, 1.0).astype(np.float32)

    def _center(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.arrange = ArrangeView(self.project)
        self.arrange.on_select = self._on_select
        self.arrange.on_change = self._on_change
        self.arrange.on_playhead = self._update_time
        self.arrange.on_audition = lambda path: self._audition(path)
        self.arrange.on_audition_clip = self._audition_clip
        self.arrange.on_track = self._select_track
        self.arrange.on_context = self._on_context
        self.arrange.on_loop = self._loop_from_drag
        self.intro = IntroOverlay(w, self.arrange); self._build_intro()
        self.preview_bar = PreviewBar()
        lay.addWidget(self.preview_bar)
        sc = QScrollArea(); sc.setWidget(self.arrange); sc.setWidgetResizable(False)
        self._scroll = sc
        lay.addWidget(sc, 1)
        tr = QHBoxLayout()
        self.play_btn = QPushButton(t("▶ Afspelen")); self.play_btn.clicked.connect(self.toggle_play)
        tr.addWidget(self.play_btn)
        stop = QPushButton(t("⏹ Stop")); stop.clicked.connect(self.stop); tr.addWidget(stop)
        cut = QPushButton(t("✂ Knippen")); cut.clicked.connect(self.cut_clip); tr.addWidget(cut)
        cpy = QPushButton(t("⧉ Kopiëren")); cpy.clicked.connect(self.copy_clip); tr.addWidget(cpy)
        pst = QPushButton(t("📋 Plakken")); pst.clicked.connect(self.paste_clip); tr.addWidget(pst)
        self.dele = QPushButton(t("🗑 Verwijder")); self.dele.clicked.connect(self._delete_clip); tr.addWidget(self.dele)
        self.metro_chk = QCheckBox(t("🔔 Metronoom"))
        self.metro_chk.toggled.connect(lambda on: setattr(self, "metronome", bool(on)))
        tr.addWidget(self.metro_chk)
        self.loop_chk = QCheckBox(t("🔁 Lus"))
        self.loop_chk.toggled.connect(self._toggle_loop); tr.addWidget(self.loop_chk)
        lb = QPushButton(t("Lus begin")); lb.setToolTip(t("Zet het lusbegin op de afspeelkop"))
        lb.clicked.connect(lambda: self._set_loop_edge(True)); tr.addWidget(lb)
        le = QPushButton(t("Lus eind")); le.setToolTip(t("Zet het luseind op de afspeelkop"))
        le.clicked.connect(lambda: self._set_loop_edge(False)); tr.addWidget(le)
        self.time_lbl = QLabel("Maat 1"); self.time_lbl.setObjectName("mono"); tr.addWidget(self.time_lbl)
        tr.addStretch(1)
        zo = QPushButton("➖"); zo.setFixedWidth(40); zo.clicked.connect(lambda: self.arrange.set_zoom(self.arrange.ppb * 0.8))
        zi = QPushButton("➕"); zi.setFixedWidth(40); zi.clicked.connect(lambda: self.arrange.set_zoom(self.arrange.ppb * 1.25))
        tr.addWidget(zo); tr.addWidget(zi)
        lay.addLayout(tr)
        return w

    def _right(self):
        lay = QVBoxLayout(); lay.setSpacing(6)
        lay.addWidget(section("Geselecteerde clip"))
        self.clip_lbl = QLabel(t("— geen clip —")); self.clip_lbl.setWordWrap(True); lay.addWidget(self.clip_lbl)
        lay.addWidget(QLabel(t("Startmaat / -tel")))
        self.start_spin = QDoubleSpinBox(); self.start_spin.setRange(0, 99999); self.start_spin.setSingleStep(1)
        self.start_spin.valueChanged.connect(self._edit_start); lay.addWidget(self.start_spin)
        lay.addWidget(QLabel(t("Volume %")))
        self.gain_spin = QDoubleSpinBox(); self.gain_spin.setRange(0, 200); self.gain_spin.setSingleStep(5)
        self.gain_spin.setValue(100); self.gain_spin.valueChanged.connect(self._edit_gain); lay.addWidget(self.gain_spin)
        lay.addWidget(QLabel(t("Lengte (tellen) — 0 = automatisch")))
        self.len_spin = QDoubleSpinBox(); self.len_spin.setRange(0, 9999); self.len_spin.setSingleStep(1)
        self.len_spin.valueChanged.connect(self._edit_span); lay.addWidget(self.len_spin)
        lay.addWidget(QLabel(t("Effect (op deze clip)")))
        self.fx_lbl = QLabel("—"); self.fx_lbl.setStyleSheet("color:#9fbfe0;")
        lay.addWidget(self.fx_lbl)
        fxbtn = QPushButton(t("🎛 Effecten…"))
        fxbtn.clicked.connect(lambda: self.open_effect_dialog()); lay.addWidget(fxbtn)
        frow = QHBoxLayout()
        self.fadein_chk = QCheckBox(t("Fade in")); self.fadein_chk.toggled.connect(self._edit_fade_in)
        self.fadeout_chk = QCheckBox(t("Fade uit")); self.fadeout_chk.toggled.connect(self._edit_fade_out)
        frow.addWidget(self.fadein_chk); frow.addWidget(self.fadeout_chk); lay.addLayout(frow)

        lay.addSpacing(8)
        lay.addWidget(section("Spoor (mixer)"))
        self.track_name_lbl = QLabel("Spoor 1"); self.track_name_lbl.setWordWrap(True)
        lay.addWidget(self.track_name_lbl)
        lay.addWidget(QLabel(t("Spoorvolume %")))
        self.tvol_spin = QSpinBox(); self.tvol_spin.setRange(0, 150); self.tvol_spin.setValue(100)
        self.tvol_spin.valueChanged.connect(self._edit_track_gain); lay.addWidget(self.tvol_spin)
        row = QHBoxLayout()
        self.mute_chk = QCheckBox(t("Mute")); self.mute_chk.toggled.connect(self._edit_track_mute)
        self.solo_chk = QCheckBox(t("Solo")); self.solo_chk.toggled.connect(self._edit_track_solo)
        row.addWidget(self.mute_chk); row.addWidget(self.solo_chk); lay.addLayout(row)

        lay.addStretch(1)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(lay); panel.setFixedWidth(240)
        return panel

    def _build_intro(self):
        self.intro.setObjectName("introOverlay")
        self.intro.setStyleSheet("#introOverlay{background-color:transparent;}"
                                 "#introOverlay QLabel{background-color:transparent;border:none;}")
        v = QVBoxLayout(self.intro); v.setAlignment(Qt.AlignCenter); v.setSpacing(12)
        lg = QLabel(); lg.setAlignment(Qt.AlignCenter); lg.setPixmap(logo_pixmap(150)); v.addWidget(lg)
        ti = QLabel(APP_NAME); ti.setAlignment(Qt.AlignCenter)
        ti.setStyleSheet("color:#f2f2f2;font-size:44px;font-weight:bold;"); v.addWidget(ti)
        tg = QLabel(t("Een lichte muziekmaker met loops en sporen.")); tg.setAlignment(Qt.AlignCenter)
        tg.setStyleSheet("color:#7fb4ff;font-size:20px;font-weight:bold;"); v.addWidget(tg)
        hint = QLabel(t("Nieuw hier? Laad een map met loops of sound clips en sleep ze op de sporen."))
        hint.setAlignment(Qt.AlignCenter); hint.setWordWrap(True)
        hint.setStyleSheet("color:#c8ccd4;font-size:18px;"); v.addWidget(hint)
        g = QPushButton(t("📖 Open de Snelgids")); g.setObjectName("cta"); g.setMinimumHeight(46)
        g.setMinimumWidth(220); g.clicked.connect(self.open_guide)
        row = QHBoxLayout(); row.setAlignment(Qt.AlignCenter); row.addWidget(g); v.addLayout(row)
        self.intro.hide()

    def _place_intro(self):
        if hasattr(self, "intro") and hasattr(self, "_scroll"):
            self.intro.setGeometry(self._scroll.geometry())

    def _update_intro(self):
        empty = not any(tr.clips for tr in self.project.tracks)
        if empty:
            self._place_intro()
        self.intro.setVisible(empty and not self.playing)
        self.intro.raise_()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, "_scroll") and hasattr(self, "arrange"):
            vp = self._scroll.viewport()
            self.arrange.set_viewport(vp.width(), vp.height())
        self._place_intro()

    # ---- acties ---- #
    def _refresh_tracks(self):
        self.track_combo.blockSignals(True); self.track_combo.clear()
        self.track_combo.addItems([tr.name for tr in self.project.tracks])
        self.track_combo.setCurrentIndex(min(self.cur_track, len(self.project.tracks) - 1))
        self.track_combo.blockSignals(False)

    def _set_track(self, i):
        self.cur_track = max(0, i)
        self.arrange._cur_track = self.cur_track; self.arrange.update()
        self._refresh_track_panel()

    def _select_track(self, ti):
        self.cur_track = ti
        self.track_combo.blockSignals(True); self.track_combo.setCurrentIndex(ti); self.track_combo.blockSignals(False)
        self._refresh_track_panel()

    def _refresh_track_panel(self):
        if not (0 <= self.cur_track < len(self.project.tracks)):
            return
        tr = self.project.tracks[self.cur_track]
        self.track_name_lbl.setText(tr.name)
        for w, v in ((self.tvol_spin, int(tr.gain * 100)),):
            w.blockSignals(True); w.setValue(v); w.blockSignals(False)
        self.mute_chk.blockSignals(True); self.mute_chk.setChecked(tr.mute); self.mute_chk.blockSignals(False)
        self.solo_chk.blockSignals(True); self.solo_chk.setChecked(tr.solo); self.solo_chk.blockSignals(False)

    def _edit_track_gain(self, v):
        if 0 <= self.cur_track < len(self.project.tracks):
            self.project.tracks[self.cur_track].gain = float(v) / 100.0
            self.arrange.update()

    def _edit_track_mute(self, on):
        if 0 <= self.cur_track < len(self.project.tracks):
            self.project.tracks[self.cur_track].mute = bool(on); self.arrange.update()

    def _edit_track_solo(self, on):
        if 0 <= self.cur_track < len(self.project.tracks):
            self.project.tracks[self.cur_track].solo = bool(on); self.arrange.update()

    def _edit_fade_in(self, on):
        if self.arrange.sel:
            self.arrange.sel[1].fade_in = bool(on)

    def _edit_fade_out(self, on):
        if self.arrange.sel:
            self.arrange.sel[1].fade_out = bool(on)

    def _set_bpm(self, v):
        self.project.bpm = float(v); self.arrange._recalc(); self.arrange.update()

    def add_track(self):
        self.project.tracks.append(Track(f"Spoor {len(self.project.tracks) + 1}"))
        self._refresh_tracks(); self.arrange.set_project(self.project); self._refresh_track_panel()

    def load_loop_folder(self):
        d = QFileDialog.getExistingDirectory(self, t("📂 Map met loops laden…"), MEDIA_DIR)
        if not d:
            return
        self.loops.clear()
        self._loop_count = 0

        def add_dir(folder, parent):
            try:
                entries = sorted(os.listdir(folder))
            except OSError:
                return 0
            subdirs = [e for e in entries if os.path.isdir(os.path.join(folder, e))]
            files = [e for e in entries
                     if e.lower().endswith(AUDIO_EXTS) and os.path.isfile(os.path.join(folder, e))]
            n = 0
            for sub in subdirs:
                node = QTreeWidgetItem(parent, ["📁 " + sub])
                node.setData(0, Qt.UserRole + 1, os.path.join(folder, sub))  # sleepbare map (pool)
                node.setExpanded(False)
                n += add_dir(os.path.join(folder, sub), node)
            for f in files:
                leaf = QTreeWidgetItem(parent, ["🎵 " + f])
                leaf.setData(0, Qt.UserRole, os.path.join(folder, f))
                n += 1
            return n

        root = QTreeWidgetItem(self.loops, ["📁 " + (os.path.basename(d.rstrip("/\\")) or d)])
        root.setData(0, Qt.UserRole + 1, d)        # ook de hele map sleepbaar
        total = add_dir(d, root)
        root.setExpanded(True)
        self._loop_count = total
        self.statusBar().showMessage(f"{total} loops geladen (met submappen).")

    def _add_loop_to_track(self, item, _col=0):
        path = item.data(0, Qt.UserRole)
        if path:                                  # bestand: op het spoor zetten
            self.arrange.add_clip(path, self.cur_track, self.arrange.playhead)
            self._update_intro()
        else:                                     # map: dubbelklik = dichtklappen (incl. submappen)
            self._collapse_tree(item)

    def _collapse_tree(self, item):
        for i in range(item.childCount()):
            self._collapse_tree(item.child(i))
        item.setExpanded(False)

    def _audition(self, path, name=None):
        """Beluister een loop (elk formaat via sounddevice; WAV-terugval via winsound)."""
        if not path or not os.path.isfile(path):
            return
        if self.playing:                 # eerst het hoofd-afspelen stoppen
            self.stop()
        name = name or os.path.basename(path)
        secs = audio_seconds(path) or 1.0
        a = cached_audio(path)
        if not play_array(self._master(a)):
            if HAVE_WINSOUND and path.lower().endswith(".wav"):
                try:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
        self.preview_bar.start(name, secs)
        self.statusBar().showMessage(f"Voorbeeld: {name}")

    def _preview_loop(self, item, _col=0):
        """Klik: bestand = beluisteren; map = openen (uitklappen)."""
        path = item.data(0, Qt.UserRole)
        if path:
            self._audition(path)
        else:                                     # map: enkele klik = openen
            item.setExpanded(True)

    def _audition_clip(self, clip):
        """Beluister een clip zoals hij klinkt — uitgerekte clips spelen de herhaling."""
        if self.playing or not clip:
            return
        a = cached_audio(clip.path)
        if a is None or a.shape[0] == 0:
            return
        if clip.span_beats and clip.span_beats > 0 and HAVE_NUMPY:
            spb = 60.0 / self.project.bpm
            need = int(round(clip.span_beats * spb * SAMPLE_RATE))
            if need > a.shape[0]:
                reps = int(math.ceil(need / a.shape[0])); a = np.tile(a, (reps, 1))
            a = a[:need]
        secs = a.shape[0] / float(SAMPLE_RATE)
        if not play_array(self._master(a)):
            if HAVE_WINSOUND and clip.path.lower().endswith(".wav"):
                try:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    winsound.PlaySound(clip.path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
        self.preview_bar.start(clip.name, secs)
        self.statusBar().showMessage(f"Voorbeeld: {clip.name}")

    def _on_select(self, ti, clip):
        if clip is None:
            self.clip_lbl.setText(t("— geen clip —")); return
        self.cur_track = ti
        self.arrange._cur_track = ti
        self.track_combo.blockSignals(True); self.track_combo.setCurrentIndex(ti); self.track_combo.blockSignals(False)
        self._refresh_track_panel()
        self.clip_lbl.setText(clip.name)
        self.start_spin.blockSignals(True); self.start_spin.setValue(clip.start_beat); self.start_spin.blockSignals(False)
        self.gain_spin.blockSignals(True); self.gain_spin.setValue(clip.gain * 100); self.gain_spin.blockSignals(False)
        self.len_spin.blockSignals(True)
        self.len_spin.setValue(clip.span_beats or 0.0)
        self.len_spin.blockSignals(False)
        self._refresh_clip_fx(clip)
        self.fadein_chk.blockSignals(True); self.fadein_chk.setChecked(clip.fade_in); self.fadein_chk.blockSignals(False)
        self.fadeout_chk.blockSignals(True); self.fadeout_chk.setChecked(clip.fade_out); self.fadeout_chk.blockSignals(False)

    def _on_change(self):
        self._update_intro(); self._update_time()

    def _edit_start(self, v):
        if self.arrange.sel:
            self.arrange.sel[1].start_beat = float(v); self.arrange._recalc(); self.arrange.update()

    def _edit_gain(self, v):
        if self.arrange.sel:
            self.arrange.sel[1].gain = float(v) / 100.0

    def _edit_span(self, v):
        if self.arrange.sel:
            self.arrange.sel[1].span_beats = (float(v) if v and v > 0 else None)
            self.arrange._recalc(); self.arrange.update()

    def _selected_pairs(self):
        """Lijst (spoor-index, clip) van alle geselecteerde clips (of de primaire)."""
        pairs = []
        sel = getattr(self.arrange, "sel_clips", None) or set()
        if sel:
            for ti, tr in enumerate(self.project.tracks):
                for c in tr.clips:
                    if c in sel:
                        pairs.append((ti, c))
        elif self.arrange.sel:
            pairs.append(self.arrange.sel)
        return pairs

    def _delete_clip(self):
        pairs = self._selected_pairs()
        if not pairs:
            return
        for ti, c in pairs:
            if c in self.project.tracks[ti].clips:
                self.project.tracks[ti].clips.remove(c)
        self.arrange.sel = None; self.arrange.sel_clips = set()
        self.arrange._recalc(); self.arrange.update()
        self._on_select(self.cur_track, None); self._update_intro()
        self.statusBar().showMessage(f"{len(pairs)} clip(s) verwijderd.")

    def copy_clip(self):
        pairs = self._selected_pairs()
        if not pairs:
            self.statusBar().showMessage("Niets geselecteerd."); return
        ref_t = min(ti for ti, _ in pairs)
        ref_b = min(c.start_beat for _, c in pairs)
        self._clipboard = {"items": [{"dt": ti - ref_t, "db": c.start_beat - ref_b,
                                      "clip": c.to_dict()} for ti, c in pairs]}
        self.statusBar().showMessage(f"{len(pairs)} clip(s) gekopieerd.")

    def cut_clip(self):
        self.copy_clip()
        if getattr(self, "_clipboard", None):
            self._delete_clip()
            self.statusBar().showMessage("Geknipt.")

    def _paste_group(self, ti, beat, group=None):
        cb = group if group is not None else getattr(self, "_clipboard", None)
        if not cb or not cb.get("items"):
            self.statusBar().showMessage("Niets om te plakken."); return
        ti = max(0, min(len(self.project.tracks) - 1, ti))
        beat = max(0.0, beat)
        newsel = set(); primary = None; missing = 0
        for it in cb["items"]:
            tt = max(0, min(len(self.project.tracks) - 1, ti + int(it["dt"])))
            d = dict(it["clip"]); d["start_beat"] = max(0.0, beat + float(it["db"]))
            if d.get("path") and not os.path.isfile(d["path"]):
                missing += 1
            c = Clip.from_dict(d)
            self.project.tracks[tt].clips.append(c)
            newsel.add(c); primary = (tt, c)
        if primary is None:
            return
        self.arrange.sel_clips = newsel; self.arrange.sel = primary
        self.cur_track = primary[0]; self.arrange._cur_track = primary[0]
        self.arrange._recalc(); self.arrange.update()
        self._on_select(primary[0], primary[1]); self._update_intro()
        msg = f"{len(newsel)} clip(s) geplakt."
        if missing:
            msg += f" Let op: {missing} loop(s) niet gevonden op schijf."
        self.statusBar().showMessage(msg)

    def paste_clip(self):
        self._paste_group(self.cur_track, self.arrange.playhead)

    def paste_at(self, ti, beat):
        self._paste_group(ti, beat)

    # ---- blokjes (eigen combinaties) ---- #
    def _group_from_selection(self):
        pairs = self._selected_pairs()
        if not pairs:
            return None
        ref_t = min(ti for ti, _ in pairs)
        ref_b = min(c.start_beat for _, c in pairs)
        return [{"dt": ti - ref_t, "db": c.start_beat - ref_b, "clip": c.to_dict()}
                for ti, c in pairs]

    def _save_block(self):
        items = self._group_from_selection()
        if not items:
            self.statusBar().showMessage("Selecteer eerst een of meer clips."); return
        name, ok = QInputDialog.getText(self, t("Blokje bewaren"), t("Naam van het blokje:"),
                                        text=f"Blokje {len(self.blocks) + 1}")
        if not ok or not name.strip():
            return
        self.blocks.append({"name": name.strip(), "items": items})
        save_blocks(self.blocks); self._refresh_blocks_list()
        self.statusBar().showMessage(f"Blokje '{name.strip()}' bewaard ({len(items)} clip(s)).")

    def _refresh_blocks_list(self):
        self.blocks_list.clear()
        for b in self.blocks:
            n = len(b.get("items", []))
            self.blocks_list.addItem(f"{b.get('name', 'Blokje')}  ({n})")

    def _place_block(self, ti=None, beat=None):
        idx = self.blocks_list.currentRow()
        if idx < 0 or idx >= len(self.blocks):
            self.statusBar().showMessage("Kies eerst een blokje."); return
        block = {"items": self.blocks[idx].get("items", [])}
        self._paste_group(self.cur_track if ti is None else ti,
                          self.arrange.playhead if beat is None else beat, group=block)

    def _blocks_menu(self, pos):
        idx = self.blocks_list.indexAt(pos).row()
        if idx < 0 or idx >= len(self.blocks):
            return
        self.blocks_list.setCurrentRow(idx)
        menu = QMenu(self)
        menu.addAction(t("➕ Plaats op afspeelkop"), self._place_block)
        menu.addAction(t("✎ Hernoemen"), lambda: self._rename_block(idx))
        menu.addAction(t("🗑 Verwijderen"), lambda: self._delete_block(idx))
        menu.exec_(self.blocks_list.mapToGlobal(pos))

    def _rename_block(self, idx):
        if idx < 0 or idx >= len(self.blocks):
            return
        name, ok = QInputDialog.getText(self, t("Hernoemen"), t("Nieuwe naam:"),
                                        text=self.blocks[idx].get("name", ""))
        if ok and name.strip():
            self.blocks[idx]["name"] = name.strip()
            save_blocks(self.blocks); self._refresh_blocks_list()

    def _delete_block(self, idx):
        if idx < 0 or idx >= len(self.blocks):
            return
        nm = self.blocks[idx].get("name", "blokje")
        if QMessageBox.question(self, t("Verwijderen"), t("Blokje '{0}' verwijderen?").format(nm)) != QMessageBox.Yes:
            return
        del self.blocks[idx]
        save_blocks(self.blocks); self._refresh_blocks_list()
        self.statusBar().showMessage("Blokje verwijderd.")

    def _on_context(self, clip, ti, beat, globalpos, in_gutter=False):
        menu = QMenu(self)
        if in_gutter:
            menu.addAction(t("✎ Spoor hernoemen"), lambda: self.rename_track(ti))
            menu.addAction(t("🗑 Spoor verwijderen"), lambda: self.delete_track(ti))
        else:
            if clip is not None:
                menu.addAction(t("⧉ Dupliceren"), lambda: self.duplicate_clip(ti, clip))
                menu.addAction(t("⧉ Kopiëren"), self.copy_clip)
                menu.addAction(t("✂ Knippen"), self.cut_clip)
                menu.addAction(t("🗑 Verwijder"), self._delete_clip)
                menu.addSeparator()
                menu.addAction(t("🎛 Effect…"), lambda: self.open_effect_dialog(clip))
            if getattr(self, "_clipboard", None):
                menu.addSeparator()
                menu.addAction(t("📋 Plak hier"), lambda: self.paste_at(ti, beat))
        if not menu.isEmpty():
            menu.exec_(globalpos)

    def duplicate_clip(self, ti=None, clip=None):
        if clip is None and self.arrange.sel:
            ti, clip = self.arrange.sel
        if clip is None:
            self.statusBar().showMessage("Kies eerst een clip."); return
        ti = max(0, min(len(self.project.tracks) - 1, ti if ti is not None else self.cur_track))
        d = clip.to_dict()
        d["start_beat"] = clip.start_beat + clip.length_beats(self.project.bpm)   # net erachter
        c = Clip.from_dict(d)
        self.project.tracks[ti].clips.append(c)
        self.arrange.sel = (ti, c)
        self.arrange._recalc(); self.arrange.update()
        self._on_select(ti, c); self._update_intro()
        self.statusBar().showMessage("Clip gedupliceerd.")

    def rename_track(self, ti):
        ti = max(0, min(len(self.project.tracks) - 1, ti))
        tr = self.project.tracks[ti]
        name, ok = QInputDialog.getText(self, t("Spoor hernoemen"), t("Nieuwe naam:"), text=tr.name)
        if ok and name.strip():
            tr.name = name.strip()
            self._refresh_tracks(); self._refresh_track_panel(); self.arrange.update()
            self.statusBar().showMessage("Spoor hernoemd.")

    def delete_track(self, ti):
        ti = max(0, min(len(self.project.tracks) - 1, ti))
        if len(self.project.tracks) <= 1:
            self.statusBar().showMessage("Er moet minstens één spoor blijven."); return
        tr = self.project.tracks[ti]
        n = len(tr.clips)
        msg = t("Spoor '{0}' verwijderen?").format(tr.name)
        if n:
            msg += " " + t("Er staan {0} clip(s) op.").format(n)
        if QMessageBox.question(self, t("Spoor verwijderen"), msg) != QMessageBox.Yes:
            return
        del self.project.tracks[ti]
        self.cur_track = max(0, min(self.cur_track, len(self.project.tracks) - 1))
        self.arrange._cur_track = self.cur_track
        self.arrange.sel = None
        self._refresh_tracks(); self.arrange.set_project(self.project)
        self._refresh_track_panel(); self._on_select(self.cur_track, None)
        self._update_intro(); self._update_time()
        self.statusBar().showMessage("Spoor verwijderd.")

    def open_effect_dialog(self, clip=None):
        clip = clip or (self.arrange.sel[1] if self.arrange.sel else None)
        if clip is None:
            self.statusBar().showMessage("Kies eerst een clip."); return
        dlg = EffectDialog(clip, on_change=lambda: (self.arrange.update(), self._refresh_clip_fx(clip)),
                           on_preview=self._preview_clip, on_stop=self._stop_preview, parent=self)
        dlg.exec_()
        self._refresh_clip_fx(clip)

    def _refresh_clip_fx(self, clip):
        if self.arrange.sel and self.arrange.sel[1] is clip:
            if clip.effect and clip.effect != "Geen":
                self.fx_lbl.setText(f"{clip.effect} · {int(clip.effect_amount * 100)}%")
            else:
                self.fx_lbl.setText(t("Geen"))

    def _stop_preview(self):
        stop_audio(); self.preview_bar.stop()

    def _preview_clip(self, clip):
        """Beluister één clip mét het huidige effect (voor het effect-venster)."""
        if self.playing:
            self.stop()
        stop_audio()                     # stop eerst de vorige weergave
        a = stretched_audio(clip.path, self.project.bpm)
        if a is None or a.shape[0] == 0:
            return
        if clip.span_beats and clip.span_beats > 0:
            spb = 60.0 / self.project.bpm
            need = int(round(clip.span_beats * spb * SAMPLE_RATE))
            if need > a.shape[0]:
                a = np.tile(a, (int(math.ceil(need / a.shape[0])), 1))
            a = a[:need]
        a = apply_fades(a, clip.fade_in, clip.fade_out)
        a = apply_effect(a, clip.effect, self.project.bpm, clip.effect_amount)
        peak = float(np.max(np.abs(a))) if a.size else 0.0
        if peak > 1.0:
            a = a / peak
        a = self._master(a)              # master-volume ook op het effect-voorbeeld
        if not play_array(a):            # sounddevice; anders winsound-terugval
            tmp = os.path.join(CACHE_DIR, "_fxpreview.wav")
            self.project.export_wav_buffer(a, tmp)
            if HAVE_WINSOUND:
                try:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
        self.preview_bar.start(clip.name + " (effect)", a.shape[0] / float(SAMPLE_RATE))

    def keyPressEvent(self, ev):
        if ev.modifiers() & Qt.ControlModifier:
            if ev.key() == Qt.Key_C:
                self.copy_clip(); return
            if ev.key() == Qt.Key_X:
                self.cut_clip(); return
            if ev.key() == Qt.Key_V:
                self.paste_clip(); return
            if ev.key() == Qt.Key_D:
                self.duplicate_clip(); return
        if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self._delete_clip()

    # ---- afspelen ---- #
    def _fmt_time(self, sec):
        sec = max(0.0, sec)
        m = int(sec // 60); s = int(sec % 60)
        return f"{m}:{s:02d}"

    def _time_text(self):
        spb = 60.0 / self.project.bpm
        cur = self.arrange.playhead * spb
        total = self.project.end_beat() * spb
        bar = int(self.arrange.playhead // self.project.beats_per_bar) + 1
        return f"Maat {bar}   ·   {self._fmt_time(cur)} / {self._fmt_time(total)}"

    def _update_time(self):
        self.time_lbl.setText(self._time_text())

    # ---- lus + metronoom ---- #
    def _toggle_loop(self, on):
        self.loop_on = bool(on)
        if self.loop_on and self.loop_end <= self.loop_start:
            self.loop_start = 0.0
            self.loop_end = self.project.end_beat()    # standaard: hele stuk
        self._sync_loop_view()

    def _set_loop_edge(self, is_start):
        b = round(self.arrange.playhead)
        if is_start:
            self.loop_start = b
            if self.loop_end <= self.loop_start:
                self.loop_end = self.loop_start + self.project.beats_per_bar
        else:
            self.loop_end = b
            if self.loop_end <= self.loop_start:
                self.loop_start = max(0.0, self.loop_end - self.project.beats_per_bar)
        self._sync_loop_view()
        self.statusBar().showMessage(
            f"Lus: tel {self.loop_start:.0f} → {self.loop_end:.0f}")

    def _sync_loop_view(self):
        self.arrange.loop_on = self.loop_on
        self.arrange.loop_start = self.loop_start
        self.arrange.loop_end = self.loop_end
        self.arrange.update()

    def _loop_from_drag(self, s, e):
        self.loop_start = float(s); self.loop_end = float(e)
        self.statusBar().showMessage(f"Lus: tel {s:.0f} → {e:.0f}")

    def _click_track(self, n, start_beat):
        """Bouw een metronoom-klikspoor: accent op tel 1 van elke maat."""
        out = np.zeros((n, 2), np.float32)
        spb = 60.0 / self.project.bpm
        bpb = max(1, int(self.project.beats_per_bar))
        clen = int(0.035 * SAMPLE_RATE)
        tt = np.arange(clen, dtype=np.float32) / SAMPLE_RATE
        env = np.exp(-tt * 38.0).astype(np.float32)
        hi = (np.sin(2 * np.pi * 1500 * tt) * env * 0.5).astype(np.float32)
        lo = (np.sin(2 * np.pi * 1000 * tt) * env * 0.32).astype(np.float32)
        b = int(math.ceil(start_beat - 1e-6))
        while True:
            idx = int(round((b - start_beat) * spb * SAMPLE_RATE))
            if idx >= n:
                break
            click = hi if (b % bpb == 0) else lo
            end = min(idx + clen, n); seg = click[: end - idx]
            out[idx:end, 0] += seg; out[idx:end, 1] += seg
            b += 1
        return out

    def _play_buffer(self, buf):
        if play_array(buf):
            return
        tmp = os.path.join(CACHE_DIR, "_preview.wav")
        self.project.export_wav_buffer(buf, tmp)
        if HAVE_WINSOUND:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
                winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def toggle_play(self):
        if self.playing:
            self._pause(); return
        if self.project.end_beat() <= 0:
            self.statusBar().showMessage("Niets om af te spelen — zet eerst loops op de sporen."); return
        spb = 60.0 / self.project.bpm
        self._looping = self.loop_on and self.loop_end > self.loop_start
        if self._looping:
            start = self.loop_start
            buf = self.project.mixdown(start)
            region = int(round((self.loop_end - self.loop_start) * spb * SAMPLE_RATE))
            if buf is not None and 0 < region < buf.shape[0]:
                buf = buf[:region]
        else:
            start = self.arrange.playhead
            if start >= self.project.end_beat():
                start = 0.0; self.arrange.playhead = 0.0
            buf = self.project.mixdown(start)
        if buf is None:
            self.statusBar().showMessage("numpy ontbreekt — kan niet mixen."); return
        if self.metronome:
            buf = np.clip(buf + self._click_track(buf.shape[0], start), -1.0, 1.0).astype(np.float32)
        self._loop_buf = buf
        self._play_buffer(buf)
        self.preview_bar.stop()
        self.playing = True; self.play_btn.setText(t("⏸ Pauze")); self.intro.hide()
        self._play_t0 = time.monotonic()
        self._play_start_beat = start
        self._play_dur = buf.shape[0] / float(SAMPLE_RATE)
        self.play_timer.start(20)

    def _update_meter(self, elapsed):
        buf = getattr(self, "_loop_buf", None)
        if buf is None:
            self.meter.set_level(0.0); return
        idx = int(elapsed * SAMPLE_RATE)
        if 0 <= idx < buf.shape[0]:
            seg = buf[idx:idx + int(0.03 * SAMPLE_RATE)]
            self.meter.set_level(float(np.max(np.abs(seg))) if seg.size else 0.0)
        else:
            self.meter.set_level(0.0)

    def _tick(self):
        spb = 60.0 / self.project.bpm
        elapsed = time.monotonic() - self._play_t0
        if getattr(self, "_looping", False):
            if elapsed >= self._play_dur:                  # lus opnieuw starten
                self._play_t0 = time.monotonic(); elapsed = 0.0
                self._play_buffer(self._loop_buf)
            self.arrange.playhead = min(self.loop_start + elapsed / spb, self.loop_end)
            self.time_lbl.setText(self._time_text()); self.arrange.update()
            self._update_meter(elapsed)
            return
        self.arrange.playhead = min(self._play_start_beat + elapsed / spb,
                                    self.project.end_beat())
        self.time_lbl.setText(self._time_text())
        self.arrange.update()
        self._update_meter(elapsed)
        if elapsed >= getattr(self, "_play_dur", 0.0):
            self.stop()

    def _pause(self):
        """Pauzeer: geluid stopt, de rode lijn blijft staan."""
        self.play_timer.stop(); self.playing = False
        stop_audio()
        self.meter.set_level(0.0)
        self.play_btn.setText(t("▶ Afspelen")); self.arrange.update()

    def stop(self):
        """Stop: geluid stopt en de rode lijn keert terug naar het begin."""
        self.play_timer.stop(); self.playing = False
        stop_audio()
        self.meter.set_level(0.0)
        self.play_btn.setText(t("▶ Afspelen"))
        self.preview_bar.stop()
        self.arrange.playhead = 0.0; self.arrange.update()
        self._update_time(); self._update_intro()

    # ---- project ---- #
    def new_project(self):
        self.stop(); self.project = Project()
        self.bpm_spin.blockSignals(True); self.bpm_spin.setValue(int(self.project.bpm)); self.bpm_spin.blockSignals(False)
        self._sync_master()
        self._refresh_tracks(); self.arrange.set_project(self.project); self._update_intro(); self._update_time(); self._refresh_track_panel()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, t("Openen…"), PROJECTS_DIR,
                                              f"{APP_NAME} (*{PROJECT_EXT});;Alle (*)")
        if path:
            self._load_project(path)

    def _load_project(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self.project = Project.from_dict(json.load(fh))
        except Exception as e:
            QMessageBox.warning(self, "Openen", f"Kon niet openen:\n{e}"); return
        self.stop()
        self.bpm_spin.blockSignals(True); self.bpm_spin.setValue(int(self.project.bpm)); self.bpm_spin.blockSignals(False)
        self._sync_master()
        self._refresh_tracks(); self.arrange.set_project(self.project)
        self._update_intro(); self._update_time(); self._refresh_track_panel()
        self._add_recent(path)
        self.statusBar().showMessage(f"Geopend: {os.path.basename(path)}")

    def _add_recent(self, path):
        path = os.path.abspath(path)
        self.recent = [p for p in self.recent if p != path]
        self.recent.insert(0, path)
        self.recent = self.recent[:8]
        cfg = load_config(); cfg["recent"] = self.recent; save_config(cfg)

    def _recent_menu(self):
        # houd alleen bestaande bestanden over
        self.recent = [p for p in self.recent if os.path.isfile(p)]
        menu = QMenu(self)
        if not self.recent:
            menu.addAction(t("(geen recente projecten)")).setEnabled(False)
        else:
            for p in self.recent:
                menu.addAction(os.path.basename(p), lambda _=False, pp=p: self._load_project(pp))
        menu.exec_(self.recent_btn.mapToGlobal(self.recent_btn.rect().bottomLeft()))

    def _sync_master(self):
        self.master_slider.blockSignals(True)
        self.master_slider.setValue(int(self.project.master_gain * 100))
        self.master_slider.blockSignals(False)
        self.master_lbl.setText(t("Master-volume") + f"  {int(self.project.master_gain * 100)}%")

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, t("Opslaan…"),
                                              os.path.join(PROJECTS_DIR, "project" + PROJECT_EXT),
                                              f"{APP_NAME} (*{PROJECT_EXT})")
        if not path:
            return
        if not path.endswith(PROJECT_EXT):
            path += PROJECT_EXT
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.project.to_dict(), fh, indent=2)
            self._add_recent(path)
            self.statusBar().showMessage("Opgeslagen.")
        except Exception as e:
            QMessageBox.warning(self, "Opslaan", str(e))

    def open_settings(self):
        dlg = SettingsDialog(self.project, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.project.bpm = float(dlg.bpm.value())
        self.project.beats_per_bar = dlg.bpb.value()
        self.bpm_spin.blockSignals(True); self.bpm_spin.setValue(int(self.project.bpm)); self.bpm_spin.blockSignals(False)
        self.arrange._recalc(); self.arrange.update()
        new_lang = dlg.language(); cfg = load_config()
        if new_lang != cfg.get("language", "auto"):
            cfg["language"] = new_lang; save_config(cfg)
            QMessageBox.information(self, t("Taal"), t("De taal verandert nadat je DraveSound opnieuw start."))

    def export_dialog(self):
        if self.project.end_beat() <= 0:
            QMessageBox.information(self, t("Exporteren"), "Zet eerst loops op de sporen."); return
        dlg = ExportDialog(MEDIA_DIR, mp3_ok=bool(ffmpeg_exe()), parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        path, ext = dlg.result_path()
        if os.path.exists(path):
            if QMessageBox.question(self, t("Exporteren"),
                                    t("'{0}' bestaat al. Overschrijven?").format(os.path.basename(path))) != QMessageBox.Yes:
                return
        # voortgangsvenster + export in een aparte thread
        self._prog = QProgressDialog(t("Bezig met exporteren…"), t("Annuleren"), 0, 100, self)
        self._prog.setWindowTitle(t("Exporteren"))
        self._prog.setWindowModality(Qt.WindowModal)
        self._prog.setMinimumDuration(0); self._prog.setAutoClose(True); self._prog.setValue(0)
        self._exp_worker = _ExportWorker(self.project, path, ext, self)
        self._exp_worker.progress.connect(self._prog.setValue)
        self._exp_worker.done.connect(self._on_export_done)
        self._prog.canceled.connect(self._exp_worker.terminate)
        self._exp_worker.start()

    def _on_export_done(self, ok, path):
        if hasattr(self, "_prog") and self._prog is not None:
            self._prog.reset()
        if ok:
            self.statusBar().showMessage(t("Geëxporteerd:") + " " + os.path.basename(path))
            QMessageBox.information(self, t("Exporteren"),
                                    t("Klaar!") + f"\n{path}")
        else:
            self.statusBar().showMessage("Export mislukt.")
            QMessageBox.warning(self, t("Exporteren"), t("Export mislukt."))

    # ---- gids / contact / info / updates ---- #
    def open_guide(self):
        open_quick_guide(self)

    def open_contact(self):
        ContactDialog(self).exec_()

    def show_info(self):
        QMessageBox.information(
            self, APP_NAME,
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br>een {AUTHOR_NAME} product<br>"
            f"<a href='{WEBSITE_URL}'>{WEBSITE_URL}</a><br><br>"
            f"{t('Een lichte muziekmaker met loops en sporen.')}<br><br>"
            f"Audio: {'aan' if HAVE_NUMPY else 'uit'} · "
            f"WAV: {'aan' if (HAVE_SF or True) else 'uit'} · "
            f"MP3-export: {'aan' if ffmpeg_exe() else 'uit'}")

    def check_updates(self, silent=True):
        if self._upd_worker is not None and self._upd_worker.isRunning():
            return
        self._upd_silent = silent
        if not silent:
            self.statusBar().showMessage(t("Controleren op updates…"))
        self._upd_worker = _UpdateWorker(self)
        self._upd_worker.done.connect(self._on_update)
        self._upd_worker.start()

    def _on_update(self, latest):
        silent = getattr(self, "_upd_silent", True)
        if latest is None:
            if not silent:
                QMessageBox.information(self, t("Updates"),
                    f"Kon de versie nu niet ophalen. Kijk op {WEBSITE_URL}.")
            return
        if is_newer(latest.get("version", "")):
            notes = latest.get("notes", "").strip()
            extra = f"<br><br>{notes.replace(chr(10), '<br>')}" if notes else ""
            QMessageBox.information(self, t("Updates"),
                f"Nieuwe versie: <b>v{latest['version']}</b> (jij: v{APP_VERSION}){extra}<br><br>"
                f"{DOWNLOAD_PAGE_URL}")
        elif not silent:
            QMessageBox.information(self, t("Updates"), f"Je hebt de nieuwste versie (v{APP_VERSION}).")


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dravenlock.DraveSound")
        except Exception:
            pass
    app = QApplication(sys.argv)
    f = app.font(); f.setPointSize(13); app.setFont(f)
    app.setStyleSheet(DRAVENLOCK_QSS)
    ic = app_icon(); app.setWindowIcon(ic)
    # opstart-splash die na een momentje vanzelf verdwijnt
    splash = QSplashScreen(make_splash_pixmap(), Qt.WindowStaysOnTopHint)
    splash.show(); app.processEvents()
    win = DraveSound(); win.setWindowIcon(ic)

    def _start():
        splash.finish(win)
        win.show()
        try:
            win.check_updates(silent=True)
        except Exception:
            pass
        if load_config().get("show_guide_on_start", True):
            QuickGuideDialog(win).exec_()

    QTimer.singleShot(1600, _start)     # splash ~1,6 s zichtbaar
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
