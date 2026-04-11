#!/usr/bin/env python3

import json
import os
import datetime
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import curses
import time

DATA_FILE = "timetracker.json"

# ----------------------
# Data Layer
# ----------------------

def get_data_path():
    return os.path.abspath(DATA_FILE)


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"sessions": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def now():
    return datetime.datetime.now()


# ----------------------
# Core Logic
# ----------------------

def get_active_session(data):
    for s in reversed(data["sessions"]):
        if s.get("end") is None:
            return s
    return None


def start_session():
    data = load_data()
    if get_active_session(data):
        return "Already running"

    data["sessions"].append({"start": now().isoformat(), "end": None})
    save_data(data)
    return "Started"


def stop_session():
    data = load_data()
    session = get_active_session(data)

    if session:
        session["end"] = now().isoformat()
        save_data(data)
        return "Stopped"

    return "No active session"


def add_time(minutes):
    data = load_data()
    end = now()
    start = end - datetime.timedelta(minutes=minutes)

    data["sessions"].append({
        "start": start.isoformat(),
        "end": end.isoformat()
    })

    save_data(data)
    return f"Added {minutes} min"


def calculate_summary(period="day"):
    data = load_data()
    now_dt = now()

    total = datetime.timedelta()

    for s in data["sessions"]:
        if not s.get("end"):
            continue

        start = datetime.datetime.fromisoformat(s["start"])
        end = datetime.datetime.fromisoformat(s["end"])

        if period == "day" and start.date() != now_dt.date():
            continue
        if period == "week" and start.isocalendar()[1] != now_dt.isocalendar()[1]:
            continue
        if period == "month" and start.month != now_dt.month:
            continue

        total += (end - start)

    return total


# ----------------------
# TUI
# ----------------------

def format_td(td):
    seconds = int(td.total_seconds())
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"


def tui(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    input_mode = False
    input_buffer = ""

    while True:
        stdscr.clear()
        data = load_data()

        active = get_active_session(data)

        day = calculate_summary("day")
        week = calculate_summary("week")
        month = calculate_summary("month")

        # Header
        stdscr.addstr(1, 2, "⏱ Minimal Time Tracker", curses.A_BOLD)

        # Status
        if active:
            start = datetime.datetime.fromisoformat(active["start"])
            running_for = now() - start
            stdscr.addstr(3, 2, "Status: RUNNING", curses.A_BOLD)
            stdscr.addstr(4, 4, f"Running: {format_td(running_for)}")
        else:
            stdscr.addstr(3, 2, "Status: STOPPED")

        # Stats
        stdscr.addstr(6, 2, f"Today : {format_td(day)}")
        stdscr.addstr(7, 2, f"Week  : {format_td(week)}")
        stdscr.addstr(8, 2, f"Month : {format_td(month)}")

        # Controls
        stdscr.addstr(10, 2, "Controls:")
        stdscr.addstr(11, 4, "s = start   e = stop   a = add time")
        stdscr.addstr(12, 4, "q = quit")

        # Input mode
        if input_mode:
            stdscr.addstr(14, 2, f"Add minutes: {input_buffer}_")
        else:
            stdscr.addstr(14, 2, "Press 'a' to add custom minutes")

        # File path
        stdscr.addstr(16, 2, f"Data: {get_data_path()}")

        stdscr.refresh()

        try:
            key = stdscr.getch()
        except:
            key = -1

        if key == -1:
            time.sleep(0.2)
            continue

        if input_mode:
            if key in (10, 13):  # Enter
                if input_buffer.isdigit():
                    add_time(int(input_buffer))
                input_buffer = ""
                input_mode = False
            elif key == 27:  # ESC
                input_mode = False
                input_buffer = ""
            elif key in (8, 127):  # backspace
                input_buffer = input_buffer[:-1]
            elif chr(key).isdigit():
                input_buffer += chr(key)
            continue

        if key == ord('q'):
            break
        elif key == ord('s'):
            start_session()
        elif key == ord('e'):
            stop_session()
        elif key == ord('a'):
            input_mode = True


# ----------------------
# API
# ----------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/sessions"):
            self._send_json(load_data())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/start":
            start_session()
            self._send_json({"status": "started"})
        elif self.path == "/stop":
            stop_session()
            self._send_json({"status": "stopped"})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_server(port=8000):
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"API running on http://localhost:{port}")
    server.serve_forever()


# ----------------------
# CLI
# ----------------------

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("start")
    sub.add_parser("stop")

    add_cmd = sub.add_parser("add")
    add_cmd.add_argument("minutes", type=int)

    sub.add_parser("day")
    sub.add_parser("week")
    sub.add_parser("month")

    sub.add_parser("serve")
    sub.add_parser("tui")

    args = parser.parse_args()

    if args.cmd == "start":
        print(start_session())
    elif args.cmd == "stop":
        print(stop_session())
    elif args.cmd == "add":
        print(add_time(args.minutes))
    elif args.cmd == "day":
        print(format_td(calculate_summary("day")))
    elif args.cmd == "week":
        print(format_td(calculate_summary("week")))
    elif args.cmd == "month":
        print(format_td(calculate_summary("month")))
    elif args.cmd == "serve":
        run_server()
    elif args.cmd == "tui":
        curses.wrapper(tui)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

