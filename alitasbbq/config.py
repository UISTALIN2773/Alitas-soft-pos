import os
import sys
import customtkinter as ctk


DB_NAME = "alitas_bbq.db"
APP_NAME = "AlaCrunch"


def init_ctk():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def app_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = getattr(sys, "_MEIPASS")
    else:
        base = app_dir()
    return os.path.join(base, *parts)


def db_path():
    base = app_dir()
    candidates = [
        os.path.join(base, DB_NAME),
        os.path.join(os.path.dirname(base), DB_NAME),
        os.path.join(os.path.dirname(os.path.dirname(base)), DB_NAME),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]
