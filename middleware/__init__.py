"""
GameTrainer middleware: capture console gameplay and turn it into data points.

    capture/      hdmi_capture   open the capture card, request its mode, detect a black picture
                  usb_capture    find which video index is the card, check its USB link
                  game_tracker   one tracking session: capture -> detect -> gameplay.db
                  synthetic      generated test match for running without hardware
    analysis/     frame_processor  detection (color / template / motion), appearance, HUD OCR
                  replay_engine    rebuild a session from the database as replay.json
                  feature_extractor  Leetify-style per-player stats
    simulation/   game_simulator   smooth, interpolated playback states from a replay
                  replay_viewer    pygame viewer for replay.json
    integration/  system_integration  config lookup and run_session() pipeline
                  system_check        `gametrainer --check` diagnostics
"""

import os as _os

_os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
_os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
