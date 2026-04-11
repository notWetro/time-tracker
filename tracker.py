#!/usr/bin/env python3

import json
import os
import datetime
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import curses

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
    return datetime.datetime.now().isoformat()


# ----------------------
# Core Logic
# ----------------------

def is_running(data):
    return any(s.get("end") is None for s in data["sessions"])


def start_session():
    data = load_data()
    if is_running(data):
        return "Already running"

    data["sessions"].append({"start": now(), "end": None})
    save_data(data)
    return "Started"


def stop_session():
    data = load_data()

    for s in reversed(data["sessions"]):
        if s.get("end") is None:
            s["end"] = now()
            save_data(data)
            return "Stopped"

    return "No active session"


def add_time(minutes):
    data = load_data()
    end = datetime.datetime.now()
    start = end - datetime.timedelta(minutes=minutes)

    data["sessions"].append({
        "start": start.isoformat(),
        "end": end.isoformat()
    })

    save_data(data)
    return f"Added {minutes} min"


def calculate_summary(period="day"):
    data = load_data()
    now_dt = datetime.datetime.now()

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

    return total.total_seconds() / 3600


# ----------------------
# TUI (curses)
# ----------------------

def tui(stdscr):
    curses.curs_set(0)

    while True:
        stdscr.clear()
        data = load_data()

        running = is_running(data)
        day = calculate_summary("day")
        week = calculate_summary("week")
        month = calculate_summary("month")

        stdscr.addstr(1, 2, "Minimal Time Tracker", curses.A_BOLD)
        stdscr.addstr(3, 2, f"Status: {'RUNNING' if running else 'STOPPED'}")

        stdscr.addstr(5, 2, f"Today:  {day:.2f} h")
        stdscr.addstr(6, 2, f"Week:   {week:.2f} h")
        stdscr.addstr(7, 2, f"Month:  {month:.2f} h")

        stdscr.addstr(9, 2, "Controls:")
        stdscr.addstr(10, 4, "s = start")
        stdscr.addstr(11, 4, "e = end/stop")
        stdscr.addstr(12, 4, "a = add 30min")
        stdscr.addstr(13, 4, "q = quit")

        stdscr.addstr(15, 2, f"Data file: {get_data_path()}")

        stdscr.refresh()

        key = stdscr.getch()

        if key == ord('q'):
            break
        elif key == ord('s'):
            start_session()
        elif key == ord('e'):
            stop_session()
        elif key == ord('a'):
            add_time(30)


# ----------------------
# Simple API Server
# ----------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/sessions"):
            data = load_data()
            self._send_json(data)
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
    parser = argparse.ArgumentParser(description="Minimal Work Time Tracker")
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
        print(calculate_summary("day"))
    elif args.cmd == "week":
        print(calculate_summary("week"))
    elif args.cmd == "month":
        print(calculate_summary("month"))
    elif args.cmd == "serve":
        run_server()
    elif args.cmd == "tui":
        curses.wrapper(tui)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

