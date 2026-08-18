#!/usr/bin/env python3
"""
===============================================================================
  MinGW-w64 & graphics.h (WinBGIm) — Bullet-Proof Automated Setup for Windows
===============================================================================

  Handles every scenario:
    1. No MinGW installed              -> Fresh download & install
    2. MinGW present, no graphics.h    -> Downloads & patches graphics.h
    3. Corrupted MinGW installation    -> Detects corruption, reinstalls
    4. Outdated MinGW installation     -> Detects old version, upgrades
    5. MSYS2 / TDM-GCC / Cygwin       -> Detected & handled properly
    6. Multiple conflicting installs   -> Picks best, warns about conflicts
    7. Chocolatey / Scoop / Winget     -> Detected installs via pkg managers
    8. 32-bit system                   -> Offers 32-bit MinGW download
    9. No internet / proxy required    -> Detected, instructions provided
   10. Antivirus blocking downloads    -> Detected and warned
   11. Locked files / permission errors-> Retried with guidance
   12. Unicode paths / spaces in paths -> Handled safely
   13. Disk space insufficient         -> Checked before download

  Usage:
    python setup_graphics_mingw.py            # Normal
    python setup_graphics_mingw.py --silent   # Auto-accept all prompts
    python setup_graphics_mingw.py --log      # Write log to file

  License: MIT
===============================================================================
"""

import os
import sys
import subprocess
import shutil
import tempfile
import zipfile
import ctypes
import time
import re
import struct
import socket
import hashlib
import logging
import argparse
import traceback as tb_module
from pathlib import Path
from urllib.request import urlopen, Request, ProxyHandler, build_opener
from urllib.error import URLError, HTTPError

# Only import Windows-specific modules when actually on Windows
_WINREG_AVAILABLE = False
if sys.platform == "win32":
    try:
        import winreg
        _WINREG_AVAILABLE = True
    except ImportError:
        pass


# ==========================================================================
#  CONFIGURATION
# ==========================================================================

DEFAULT_MINGW_INSTALL_DIR = r"C:\MinGW"

# MinGW-w64 64-bit download URLs (WinLibs standalone zips)
MINGW64_DOWNLOAD_URLS = [
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "13.2.0posix-18.1.5-11.0.1-ucrt-r5/"
    "winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64ucrt-11.0.1-r5.zip",
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "12.2.0-16.0.0-10.0.0-ucrt-r5/"
    "winlibs-x86_64-posix-seh-gcc-12.2.0-mingw-w64ucrt-10.0.0-r5.zip",
    "https://github.com/niXman/mingw-builds-binaries/releases/download/"
    "13.2.0-rt_v11-rev0/"
    "x86_64-13.2.0-release-posix-seh-ucrt-rt_v11-rev0.7z",
]

# MinGW-w64 32-bit download URLs
MINGW32_DOWNLOAD_URLS = [
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "13.2.0posix-18.1.5-11.0.1-ucrt-r5/"
    "winlibs-i686-posix-dwarf-gcc-13.2.0-mingw-w64ucrt-11.0.1-r5.zip",
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "12.2.0-16.0.0-10.0.0-ucrt-r5/"
    "winlibs-i686-posix-dwarf-gcc-12.2.0-mingw-w64ucrt-10.0.0-r5.zip",
]

# WinBGIm (graphics.h) files — multiple mirrors for resilience
GRAPHICS_FILES = {
    "graphics.h": [
        "https://raw.githubusercontent.com/ArvindAgarwal1310/graphics.h/master/graphics.h",
        "http://www.cs.colorado.edu/~main/bgi/cs1300/graphics.h",
    ],
    "winbgim.h": [
        "https://raw.githubusercontent.com/ArvindAgarwal1310/graphics.h/master/winbgim.h",
        "http://www.cs.colorado.edu/~main/bgi/cs1300/winbgim.h",
    ],
    "libbgi.a": [
        "https://raw.githubusercontent.com/ArvindAgarwal1310/graphics.h/master/libbgi.a",
        "http://www.cs.colorado.edu/~main/bgi/cs1300/libbgi.a",
    ],
}

MIN_GCC_VERSION = (8, 0, 0)

# Files that must exist for a healthy MinGW (relaxed - mingw32-make may
# be absent in some distributions, so we only hard-require gcc/g++/ld/as)
CRITICAL_MINGW_FILES_HARD = [
    "bin/gcc.exe",
    "bin/g++.exe",
]

CRITICAL_MINGW_FILES_SOFT = [
    "bin/ld.exe",
    "bin/as.exe",
    "bin/mingw32-make.exe",
]

GRAPHICS_H_TARGETS = {
    "graphics.h": "include/graphics.h",
    "winbgim.h": "include/winbgim.h",
    "libbgi.a": "lib/libbgi.a",
}

# Required disk space in MB for MinGW download + extraction
REQUIRED_DISK_SPACE_MB = 2000  # 2 GB (zip ~300MB, extracted ~1.5GB, buffer)

# Download retry settings
MAX_DOWNLOAD_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds (exponential: 2, 4, 8)

# Timeout settings
DOWNLOAD_TIMEOUT = 180  # seconds
COMPILE_TIMEOUT = 60    # seconds
VERSION_TIMEOUT = 15    # seconds

# Common antivirus process names
ANTIVIRUS_PROCESSES = [
    "MsMpEng.exe",       # Windows Defender
    "avp.exe",           # Kaspersky
    "avgnt.exe",         # Avira
    "avguard.exe",       # Avira
    "mcshield.exe",      # McAfee
    "bdagent.exe",       # Bitdefender
    "ekrn.exe",          # ESET
    "SophosUI.exe",      # Sophos
    "ccSvcHst.exe",      # Norton
    "NortonSecurity.exe", # Norton
]


# ==========================================================================
#  GLOBAL STATE
# ==========================================================================

# Parse command-line arguments early
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--silent", action="store_true", default=False)
_parser.add_argument("--log", action="store_true", default=False)
_parser.add_argument("-h", "--help", action="store_true", default=False)
try:
    ARGS, _ = _parser.parse_known_args()
except SystemExit:
    ARGS = argparse.Namespace(silent=False, log=False, help=False)

LOG_FILE = None  # set in main() if --log


# ==========================================================================
#  LOGGING & UI
# ==========================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET   = "\033[0m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"


def enable_ansi_colors():
    """Enable ANSI escape sequences on Windows 10+ terminals."""
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        # If ANSI is not supported, strip color codes
        Colors.RESET = Colors.RED = Colors.GREEN = Colors.YELLOW = ""
        Colors.BLUE = Colors.MAGENTA = Colors.CYAN = Colors.WHITE = ""
        Colors.BOLD = Colors.DIM = ""


def _log_to_file(level, msg):
    """Append a line to the log file if logging is enabled."""
    global LOG_FILE
    if LOG_FILE:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                # Strip ANSI codes for log file
                clean = re.sub(r"\033\[[0-9;]*m", "", msg)
                f.write(f"[{timestamp}] [{level}] {clean}\n")
        except Exception:
            pass


def log_info(msg):
    print(f"  {Colors.CYAN}[INFO]{Colors.RESET}  {msg}")
    _log_to_file("INFO", msg)

def log_ok(msg):
    print(f"  {Colors.GREEN}[ OK ]{Colors.RESET}  {msg}")
    _log_to_file("OK", msg)

def log_warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET}  {msg}")
    _log_to_file("WARN", msg)

def log_error(msg):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET}  {msg}")
    _log_to_file("FAIL", msg)

def log_debug(msg):
    """Only written to log file, not printed to console."""
    _log_to_file("DEBUG", msg)

def log_step(step_num, total, msg):
    line = (f"\n{Colors.BOLD}{Colors.MAGENTA}"
            f"  == Step {step_num}/{total}: {msg} =={Colors.RESET}")
    print(line)
    _log_to_file("STEP", f"Step {step_num}/{total}: {msg}")


def print_banner():
    print(f"""
{Colors.BOLD}{Colors.CYAN}
  +================================================================+
  |  MinGW-w64 & graphics.h  --  Bullet-Proof Setup for Windows   |
  |                                                                |
  |  Handles: Fresh install | Missing graphics.h | Corrupted       |
  |  installs | Outdated GCC | MSYS2 | TDM-GCC | Cygwin | 32-bit  |
  |  systems  | No internet  | Antivirus issues  | Locked files    |
  +================================================================+
{Colors.RESET}""")


def ask_user(prompt, default="y"):
    """Ask user a yes/no question. In --silent mode, use default."""
    if ARGS.silent:
        log_info(f"[silent mode] Auto-answering '{default}' for: {prompt}")
        return default.lower()
    try:
        resp = input(
            f"  {Colors.CYAN}{prompt} [{default.upper()}/{'n' if default == 'y' else 'y'}]: "
            f"{Colors.RESET}"
        ).strip().lower()
        return resp if resp else default.lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default.lower()


def ask_user_input(prompt, default=""):
    """Ask user for text input. In --silent mode, use default."""
    if ARGS.silent:
        log_info(f"[silent mode] Using default '{default}' for: {prompt}")
        return default
    try:
        resp = input(f"  {Colors.CYAN}{prompt}{Colors.RESET}").strip()
        return resp if resp else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


# ==========================================================================
#  PLATFORM & SYSTEM CHECKS
# ==========================================================================

def check_platform():
    """Ensure we are running on Windows."""
    if sys.platform != "win32":
        log_error("This script is designed for Windows only.")
        log_info(f"Detected platform: {sys.platform}")
        sys.exit(1)


def is_admin():
    """Check if running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_system_arch():
    """Detect if the system is 32-bit or 64-bit."""
    # struct.calcsize("P") returns pointer size: 8 on 64-bit, 4 on 32-bit
    # But Python might be 32-bit on a 64-bit OS, so also check env vars
    is_64bit_os = (
        os.environ.get("PROCESSOR_ARCHITECTURE", "").endswith("64")
        or os.environ.get("PROCESSOR_ARCHITEW6432", "").endswith("64")
    )
    is_64bit_python = struct.calcsize("P") == 8
    return {
        "os_64bit": is_64bit_os,
        "python_64bit": is_64bit_python,
        "arch_str": "x86_64" if is_64bit_os else "i686",
    }


def get_windows_version():
    """Get the Windows version string."""
    try:
        result = subprocess.run(
            ["cmd", "/c", "ver"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "Unknown"


def check_disk_space(path, required_mb):
    """Check if there is enough disk space at the given path."""
    try:
        if hasattr(shutil, "disk_usage"):
            total, used, free = shutil.disk_usage(path)
            free_mb = free // (1024 * 1024)
            return free_mb, free_mb >= required_mb
        # Fallback for very old Python
        return -1, True
    except Exception:
        return -1, True  # Can't check, assume OK


def check_internet_connection():
    """Test internet connectivity by trying to reach multiple hosts."""
    test_hosts = [
        ("github.com", 443),
        ("raw.githubusercontent.com", 443),
        ("8.8.8.8", 53),         # Google DNS
        ("1.1.1.1", 53),         # Cloudflare DNS
    ]
    results = {}
    for host, port in test_hosts:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            results[host] = True
        except (socket.timeout, socket.error, OSError):
            results[host] = False

    any_connected = any(results.values())
    github_ok = results.get("github.com", False)
    return {
        "connected": any_connected,
        "github_reachable": github_ok,
        "details": results,
    }


def detect_proxy():
    """Try to detect system proxy settings."""
    proxy_vars = {}
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                "ALL_PROXY", "all_proxy"]:
        val = os.environ.get(var)
        if val:
            proxy_vars[var] = val

    # Also check Windows registry for IE proxy settings
    if _WINREG_AVAILABLE:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                proxy_enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
                if proxy_enabled:
                    proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                    proxy_vars["_system_ie_proxy"] = proxy_server
        except Exception:
            pass

    return proxy_vars


def detect_running_antivirus():
    """Detect known antivirus processes that may interfere."""
    detected = []
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            running = result.stdout.lower()
            for av_process in ANTIVIRUS_PROCESSES:
                if av_process.lower() in running:
                    detected.append(av_process)
    except Exception:
        pass
    return detected


def detect_package_manager_installs():
    """Detect MinGW installations via Chocolatey, Scoop, or Winget."""
    found = []

    # Chocolatey
    choco_dir = os.path.join(
        os.environ.get("ChocolateyInstall", r"C:\ProgramData\chocolatey"),
        "lib"
    )
    if os.path.isdir(choco_dir):
        try:
            for entry in os.listdir(choco_dir):
                if "mingw" in entry.lower():
                    pkg_path = os.path.join(choco_dir, entry)
                    found.append({
                        "source": "Chocolatey",
                        "name": entry,
                        "path": pkg_path,
                    })
        except PermissionError:
            pass

    # Scoop
    scoop_dir = os.path.expanduser(r"~\scoop\apps")
    if os.path.isdir(scoop_dir):
        try:
            for entry in os.listdir(scoop_dir):
                if "mingw" in entry.lower() or "gcc" in entry.lower():
                    pkg_path = os.path.join(scoop_dir, entry)
                    found.append({
                        "source": "Scoop",
                        "name": entry,
                        "path": pkg_path,
                    })
        except PermissionError:
            pass

    # Winget — check standard install locations
    winget_paths = [
        os.path.expanduser(r"~\AppData\Local\Programs"),
    ]
    for wp in winget_paths:
        if os.path.isdir(wp):
            try:
                for entry in os.listdir(wp):
                    if "mingw" in entry.lower():
                        found.append({
                            "source": "Winget",
                            "name": entry,
                            "path": os.path.join(wp, entry),
                        })
            except PermissionError:
                pass

    return found


def is_file_locked(filepath):
    """Check if a file is locked by another process."""
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath, "r+b"):
            return False
    except (IOError, PermissionError):
        return True


def safe_remove_tree(path, max_retries=3):
    """
    Remove a directory tree with retries for locked files.
    Returns True if successful, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, ignore_errors=False)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                log_warn(
                    f"Files locked, retrying in {attempt + 1}s... ({e})"
                )
                time.sleep(attempt + 1)
                # Try to kill processes using the directory
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "gcc.exe"],
                        capture_output=True, timeout=5,
                    )
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "g++.exe"],
                        capture_output=True, timeout=5,
                    )
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "ld.exe"],
                        capture_output=True, timeout=5,
                    )
                except Exception:
                    pass
            else:
                log_error(f"Cannot remove {path}: files are locked.")
                return False
        except Exception as e:
            log_error(f"Cannot remove {path}: {e}")
            return False
    return False


def get_safe_temp_dir():
    """
    Get a temp directory that is safe for extraction.
    Avoids paths with spaces, unicode, or excessively long paths.
    """
    # Prefer a short path on the same drive as install target
    candidates = [
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        r"C:\Temp",
        r"D:\Temp",
        tempfile.gettempdir(),
    ]

    for candidate in candidates:
        if candidate and os.path.isdir(os.path.dirname(candidate)):
            try:
                os.makedirs(candidate, exist_ok=True)
                # Test that we can create files here
                test_file = os.path.join(candidate, f"_test_{os.getpid()}.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)

                # Check path length (Windows MAX_PATH = 260)
                if len(candidate) < 200:
                    return candidate
            except Exception:
                continue

    # Last resort
    return tempfile.gettempdir()


# ==========================================================================
#  MinGW DETECTION — COMPREHENSIVE
# ==========================================================================

def find_mingw_installations():
    """
    Exhaustive search for MinGW installations. Checks:
      - PATH environment variable
      - Common installation directories (30+ locations)
      - Windows Registry (Uninstall keys)
      - MSYS2 installations
      - TDM-GCC installations
      - Cygwin installations
      - Package manager installs (Chocolatey, Scoop, Winget)
      - Environment variables (MINGW_HOME, GCC_HOME, etc.)
      - All drive letters
    """
    installations = []
    search_locations = set()

    # 1. Check PATH for gcc.exe
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for d in path_dirs:
        d = d.strip().strip('"')  # Handle quoted paths
        if not d:
            continue
        gcc_path = os.path.join(d, "gcc.exe")
        if os.path.isfile(gcc_path):
            mingw_root = os.path.dirname(d)
            search_locations.add(os.path.normpath(mingw_root))

    # 2. Common installation directories — exhaustive list
    common_paths = [
        r"C:\MinGW",
        r"C:\mingw",
        r"C:\mingw32",
        r"C:\mingw64",
        r"C:\MinGW-w64",
        r"C:\MinGW-W64",
        r"C:\mingw-w64",

        # MSYS2
        r"C:\msys64\mingw64",
        r"C:\msys64\mingw32",
        r"C:\msys64\ucrt64",
        r"C:\msys64\clang64",
        r"C:\msys32\mingw32",

        # TDM-GCC
        r"C:\TDM-GCC-64",
        r"C:\TDM-GCC-32",
        r"C:\TDM-GCC",

        # Dev-C++ bundled
        r"C:\Program Files (x86)\Dev-Cpp\MinGW64",
        r"C:\Program Files (x86)\Dev-Cpp\MinGW32",

        # Code::Blocks bundled
        r"C:\Program Files\CodeBlocks\MinGW",
        r"C:\Program Files (x86)\CodeBlocks\MinGW",

        # Program Files
        r"C:\Program Files\mingw-w64",
        r"C:\Program Files (x86)\mingw-w64",
        r"C:\Program Files\MinGW",
        r"C:\Program Files (x86)\MinGW",

        # User home
        os.path.expanduser(r"~\mingw64"),
        os.path.expanduser(r"~\mingw32"),
        os.path.expanduser(r"~\MinGW"),
        os.path.expanduser(r"~\MinGW-w64"),

        # Strawberry Perl (ships with gcc)
        r"C:\Strawberry\c",

        # WinLibs default extracts
        r"C:\winlibs\mingw64",
        r"C:\winlibs\mingw32",
    ]

    # 3. Scan all drive letters for common MinGW locations
    for drive_letter in "CDEFGHIJ":
        drive = f"{drive_letter}:\\"
        if os.path.isdir(drive):
            for name in ["MinGW", "mingw64", "mingw32", "MinGW-w64",
                         "TDM-GCC-64", "TDM-GCC-32", "msys64"]:
                candidate = os.path.join(drive, name)
                if os.path.isdir(candidate):
                    common_paths.append(candidate)
                    # MSYS2 sub-environments
                    if "msys" in name.lower():
                        for sub in ["mingw64", "mingw32", "ucrt64", "clang64"]:
                            common_paths.append(os.path.join(candidate, sub))

    # 4. Scan Program Files for any mingw/gcc folders
    for pf in [r"C:\Program Files", r"C:\Program Files (x86)"]:
        if os.path.isdir(pf):
            try:
                for entry in os.listdir(pf):
                    entry_lower = entry.lower()
                    if any(kw in entry_lower for kw in
                           ["mingw", "gcc", "tdm", "codeblocks", "dev-c"]):
                        full_path = os.path.join(pf, entry)
                        common_paths.append(full_path)
                        # Check for nested mingw dirs
                        if os.path.isdir(full_path):
                            try:
                                for sub in os.listdir(full_path):
                                    if "mingw" in sub.lower():
                                        common_paths.append(
                                            os.path.join(full_path, sub)
                                        )
                            except PermissionError:
                                pass
            except PermissionError:
                pass

    # 5. Check environment variables
    env_vars = [
        "MINGW_HOME", "GCC_HOME", "MINGW64_HOME", "MINGW32_HOME",
        "MSYSTEM_PREFIX", "MSYS2_DIR",
    ]
    for var in env_vars:
        val = os.environ.get(var)
        if val and os.path.isdir(val):
            common_paths.append(val)

    # 6. Package manager installs
    pkg_installs = detect_package_manager_installs()
    for pkg in pkg_installs:
        common_paths.append(pkg["path"])
        # Also check subdirectories
        if os.path.isdir(pkg["path"]):
            try:
                for entry in os.listdir(pkg["path"]):
                    sub = os.path.join(pkg["path"], entry)
                    if os.path.isdir(sub):
                        common_paths.append(sub)
                        # Chocolatey nests inside tools/
                        tools_dir = os.path.join(sub, "tools")
                        if os.path.isdir(tools_dir):
                            try:
                                for t in os.listdir(tools_dir):
                                    if "mingw" in t.lower():
                                        common_paths.append(
                                            os.path.join(tools_dir, t)
                                        )
                            except PermissionError:
                                pass
            except PermissionError:
                pass

    # 7. Windows Registry
    if _WINREG_AVAILABLE:
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, key_path in registry_paths:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(
                                        subkey, "DisplayName"
                                    )[0]
                                    name_lower = display_name.lower()
                                    if any(kw in name_lower for kw in
                                           ["mingw", "gcc", "tdm", "msys2"]):
                                        try:
                                            install_loc = winreg.QueryValueEx(
                                                subkey, "InstallLocation"
                                            )[0]
                                            if install_loc:
                                                common_paths.append(install_loc)
                                        except FileNotFoundError:
                                            pass
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass

    # Add all common paths to search set
    for p in common_paths:
        p = os.path.normpath(p)
        if os.path.isdir(p):
            search_locations.add(p)

    # Deduplicate and validate — find gcc.exe
    seen_roots = set()
    for loc in sorted(search_locations):
        # Possible gcc.exe locations relative to search location
        gcc_candidates = [
            os.path.join(loc, "bin", "gcc.exe"),
            os.path.join(loc, "mingw64", "bin", "gcc.exe"),
            os.path.join(loc, "mingw32", "bin", "gcc.exe"),
            os.path.join(loc, "ucrt64", "bin", "gcc.exe"),
            os.path.join(loc, "usr", "bin", "gcc.exe"),  # Cygwin-style
        ]
        for gcc_path in gcc_candidates:
            try:
                if os.path.isfile(gcc_path):
                    actual_root = os.path.normpath(
                        os.path.dirname(os.path.dirname(gcc_path))
                    )
                    if actual_root not in seen_roots:
                        seen_roots.add(actual_root)
                        try:
                            info = analyze_mingw_installation(actual_root)
                            installations.append(info)
                        except Exception as e:
                            log_debug(
                                f"Error analyzing {actual_root}: {e}"
                            )
                    break
            except (PermissionError, OSError):
                continue

    return installations


def analyze_mingw_installation(mingw_root):
    """
    Analyze a MinGW installation for health, version, type, and graphics.h.
    Detects installation type: Standard MinGW, MSYS2, TDM-GCC, Cygwin, etc.
    """
    info = {
        "root": mingw_root,
        "gcc_path": None,
        "version": None,
        "version_tuple": (0, 0, 0),
        "install_type": "Unknown",  # MinGW-w64, MSYS2, TDM-GCC, Cygwin, etc.
        "arch": "unknown",          # x86_64 or i686
        "is_healthy": True,
        "is_outdated": False,
        "has_graphics_h": False,
        "has_winbgim_h": False,
        "has_libbgi_a": False,
        "missing_files": [],
        "corruption_details": [],
        "health_score": 100,  # 0-100, used for ranking
    }

    # Detect installation type from path
    root_lower = mingw_root.lower()
    if "msys" in root_lower:
        info["install_type"] = "MSYS2"
    elif "tdm" in root_lower:
        info["install_type"] = "TDM-GCC"
    elif "cygwin" in root_lower:
        info["install_type"] = "Cygwin"
    elif "dev-cpp" in root_lower or "devcpp" in root_lower:
        info["install_type"] = "Dev-C++"
    elif "codeblocks" in root_lower:
        info["install_type"] = "Code::Blocks"
    elif "strawberry" in root_lower:
        info["install_type"] = "Strawberry Perl"
    elif "winlibs" in root_lower:
        info["install_type"] = "WinLibs"
    else:
        info["install_type"] = "MinGW-w64"

    # Check critical files (hard requirements)
    for rel_path in CRITICAL_MINGW_FILES_HARD:
        full_path = os.path.join(mingw_root, rel_path)
        if not os.path.isfile(full_path):
            info["missing_files"].append(rel_path)
            info["is_healthy"] = False
            info["health_score"] -= 30

    # Check soft requirements (warn but don't fail)
    for rel_path in CRITICAL_MINGW_FILES_SOFT:
        full_path = os.path.join(mingw_root, rel_path)
        if not os.path.isfile(full_path):
            info["missing_files"].append(f"{rel_path} (optional)")
            info["health_score"] -= 5

    # Get GCC path
    gcc_path = os.path.join(mingw_root, "bin", "gcc.exe")
    if os.path.isfile(gcc_path):
        info["gcc_path"] = gcc_path
    else:
        info["is_healthy"] = False
        info["corruption_details"].append("gcc.exe not found in bin/")
        info["health_score"] = 0
        return info

    # Check if gcc.exe is locked (another process using it)
    if is_file_locked(gcc_path):
        info["corruption_details"].append(
            "gcc.exe is locked by another process"
        )
        info["health_score"] -= 10

    # Check gcc.exe file size (corrupted downloads can leave tiny files)
    try:
        gcc_size = os.path.getsize(gcc_path)
        if gcc_size < 10000:  # gcc.exe should be at least 10KB
            info["is_healthy"] = False
            info["corruption_details"].append(
                f"gcc.exe is suspiciously small ({gcc_size} bytes) "
                f"- possibly corrupted"
            )
            info["health_score"] -= 40
    except OSError:
        pass

    # Get version
    try:
        result = subprocess.run(
            [gcc_path, "--version"],
            capture_output=True, text=True, timeout=VERSION_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            info["version"] = version_line

            match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_line)
            if match:
                info["version_tuple"] = tuple(
                    int(x) for x in match.groups()
                )
            else:
                info["corruption_details"].append(
                    "Could not parse version number from gcc output"
                )
                info["health_score"] -= 5
        else:
            info["is_healthy"] = False
            info["corruption_details"].append(
                f"gcc --version returned exit code {result.returncode}"
            )
            if result.stderr:
                stderr_clean = result.stderr.strip()[:200]
                info["corruption_details"].append(f"stderr: {stderr_clean}")
            info["health_score"] -= 30
    except subprocess.TimeoutExpired:
        info["is_healthy"] = False
        info["corruption_details"].append(
            "gcc --version timed out — possible corruption or AV interference"
        )
        info["health_score"] -= 40
    except OSError as e:
        info["is_healthy"] = False
        err_str = str(e)
        if "WinError 216" in err_str:
            info["corruption_details"].append(
                "gcc.exe cannot run — wrong architecture "
                "(32-bit gcc on 64-bit Python or vice versa)"
            )
        elif "WinError 193" in err_str:
            info["corruption_details"].append(
                "gcc.exe is not a valid executable — file may be corrupted"
            )
        else:
            info["corruption_details"].append(f"Failed to execute gcc: {e}")
        info["health_score"] -= 40

    # Detect architecture from GCC output or target triple
    if info["version"]:
        if "x86_64" in info["version"] or "64" in info["version"]:
            info["arch"] = "x86_64"
        elif "i686" in info["version"] or "i386" in info["version"]:
            info["arch"] = "i686"

    # If we couldn't determine from version, try gcc -dumpmachine
    if info["arch"] == "unknown" and info["gcc_path"]:
        try:
            result = subprocess.run(
                [info["gcc_path"], "-dumpmachine"],
                capture_output=True, text=True, timeout=VERSION_TIMEOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                machine = result.stdout.strip()
                if "x86_64" in machine:
                    info["arch"] = "x86_64"
                elif "i686" in machine or "i386" in machine:
                    info["arch"] = "i686"
        except Exception:
            pass

    # Test compilation ability (only if basic checks passed)
    if info["is_healthy"] and info["health_score"] > 50:
        compilation_result = test_basic_compilation(mingw_root)
        if compilation_result == "pass":
            info["health_score"] = min(info["health_score"], 100)
        elif compilation_result == "compile_fail":
            info["is_healthy"] = False
            info["corruption_details"].append(
                "Failed to compile a trivial program — "
                "compiler or headers may be corrupted"
            )
            info["health_score"] -= 30
        elif compilation_result == "link_fail":
            info["is_healthy"] = False
            info["corruption_details"].append(
                "Compiled but failed to link — "
                "linker or standard libraries may be corrupted"
            )
            info["health_score"] -= 25
        elif compilation_result == "run_fail":
            # Can compile and link, but exe doesn't run — DLL issue
            info["corruption_details"].append(
                "Compiled successfully but test executable failed to run — "
                "possible missing DLLs"
            )
            info["health_score"] -= 10
        elif compilation_result == "timeout":
            info["corruption_details"].append(
                "Compilation timed out — possible AV interference"
            )
            info["health_score"] -= 15
        else:
            info["corruption_details"].append(
                f"Unexpected compilation test result: {compilation_result}"
            )
            info["health_score"] -= 10

    # Check if outdated
    if info["version_tuple"] < MIN_GCC_VERSION:
        info["is_outdated"] = True
        info["health_score"] -= 15

    # Check for graphics.h files — search multiple possible locations
    include_dirs = [
        os.path.join(mingw_root, "include"),
        os.path.join(mingw_root, "include", "c++"),
    ]
    lib_dirs = [
        os.path.join(mingw_root, "lib"),
        os.path.join(mingw_root, "lib64"),
    ]

    # Also check cross-compiled paths for MSYS2
    if info["install_type"] == "MSYS2":
        target = "x86_64-w64-mingw32" if info["arch"] == "x86_64" else "i686-w64-mingw32"
        include_dirs.append(
            os.path.join(mingw_root, target, "include")
        )
        lib_dirs.append(
            os.path.join(mingw_root, target, "lib")
        )

    for inc_dir in include_dirs:
        if os.path.isfile(os.path.join(inc_dir, "graphics.h")):
            info["has_graphics_h"] = True
        if os.path.isfile(os.path.join(inc_dir, "winbgim.h")):
            info["has_winbgim_h"] = True

    for lib_dir in lib_dirs:
        if os.path.isfile(os.path.join(lib_dir, "libbgi.a")):
            info["has_libbgi_a"] = True

    # Clamp health score
    info["health_score"] = max(0, min(100, info["health_score"]))

    return info


def test_basic_compilation(mingw_root):
    """
    Test that GCC can compile, link, and run a trivial C program.
    Returns: "pass", "compile_fail", "link_fail", "run_fail", "timeout",
             or "error"
    """
    gcc_path = os.path.join(mingw_root, "bin", "gcc.exe")
    if not os.path.isfile(gcc_path):
        return "compile_fail"

    test_dir = tempfile.mkdtemp(prefix="mingw_test_")
    test_c = os.path.join(test_dir, "test.c")
    test_o = os.path.join(test_dir, "test.o")
    test_exe = os.path.join(test_dir, "test.exe")

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        # Write test source
        with open(test_c, "w", encoding="ascii") as f:
            f.write('#include <stdio.h>\n'
                    'int main(){printf("ok");return 0;}\n')

        # Step 1: Compile only (test preprocessor + compiler)
        try:
            result = subprocess.run(
                [gcc_path, "-c", test_c, "-o", test_o],
                capture_output=True, text=True,
                timeout=COMPILE_TIMEOUT,
                cwd=test_dir,
                creationflags=creation_flags,
            )
            if result.returncode != 0:
                return "compile_fail"
        except subprocess.TimeoutExpired:
            return "timeout"
        except OSError:
            return "compile_fail"

        # Step 2: Link (test linker + standard libs)
        try:
            result = subprocess.run(
                [gcc_path, test_o, "-o", test_exe],
                capture_output=True, text=True,
                timeout=COMPILE_TIMEOUT,
                cwd=test_dir,
                creationflags=creation_flags,
            )
            if result.returncode != 0:
                return "link_fail"
        except subprocess.TimeoutExpired:
            return "timeout"
        except OSError:
            return "link_fail"

        # Step 3: Run the executable
        try:
            # Add mingw bin to PATH for DLL resolution
            env = os.environ.copy()
            mingw_bin = os.path.join(mingw_root, "bin")
            env["PATH"] = mingw_bin + os.pathsep + env.get("PATH", "")

            result = subprocess.run(
                [test_exe],
                capture_output=True, text=True,
                timeout=10,
                cwd=test_dir,
                env=env,
                creationflags=creation_flags,
            )
            if result.returncode == 0 and "ok" in result.stdout:
                return "pass"
            else:
                return "run_fail"
        except subprocess.TimeoutExpired:
            return "run_fail"
        except OSError:
            return "run_fail"

    except Exception as e:
        log_debug(f"Compilation test error: {e}")
        return "error"
    finally:
        # Clean up, but don't fail if we can't
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except Exception:
            pass


# ==========================================================================
#  DOWNLOAD ENGINE — ROBUST
# ==========================================================================

def _build_opener_with_proxy():
    """Build a URL opener that respects proxy settings."""
    proxy_settings = detect_proxy()
    if proxy_settings:
        proxies = {}
        for key, val in proxy_settings.items():
            if key.lower().startswith("http"):
                proxies[key.split("_")[0].lower()] = val
            elif key == "_system_ie_proxy":
                if "=" in val:
                    # Format: "ftp=...; http=...; https=..."
                    for part in val.split(";"):
                        part = part.strip()
                        if "=" in part:
                            proto, addr = part.split("=", 1)
                            proxies[proto.strip()] = addr.strip()
                else:
                    proxies["http"] = val
                    proxies["https"] = val
        if proxies:
            handler = ProxyHandler(proxies)
            return build_opener(handler)
    return None


def download_file(url, dest_path, description="file", retry_count=0):
    """
    Download a file with progress, retries, and error handling.
    Handles: timeouts, partial downloads, proxy, corrupt data.
    """
    if retry_count == 0:
        log_info(f"Downloading {description}...")
        log_info(f"  URL: {url}")

    try:
        req = Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Encoding": "identity",  # Don't compress, we want progress
        })

        # Use proxy-aware opener if available
        opener = _build_opener_with_proxy()
        if opener:
            response = opener.open(req, timeout=DOWNLOAD_TIMEOUT)
        else:
            response = urlopen(req, timeout=DOWNLOAD_TIMEOUT)

        total_size = response.getheader("Content-Length")
        total_size = int(total_size) if total_size else None

        downloaded = 0
        block_size = 1024 * 64  # 64 KB
        last_progress = -1
        hash_obj = hashlib.sha256()

        # Use a temporary file first, then rename
        temp_path = dest_path + ".downloading"

        with open(temp_path, "wb") as f:
            while True:
                try:
                    chunk = response.read(block_size)
                except (socket.timeout, URLError) as e:
                    # Connection dropped during download
                    log_warn(f"Connection interrupted: {e}")
                    if retry_count < MAX_DOWNLOAD_RETRIES:
                        wait = RETRY_BACKOFF_BASE ** (retry_count + 1)
                        log_info(f"Retrying in {wait}s... "
                                 f"(attempt {retry_count + 2}/{MAX_DOWNLOAD_RETRIES + 1})")
                        time.sleep(wait)
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
                        return download_file(
                            url, dest_path, description, retry_count + 1
                        )
                    raise

                if not chunk:
                    break
                f.write(chunk)
                hash_obj.update(chunk)
                downloaded += len(chunk)

                if total_size:
                    progress = int(downloaded * 100 / total_size)
                    if progress != last_progress and progress % 5 == 0:
                        size_mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        print(
                            f"\r  {Colors.DIM}     [{progress:3d}%] "
                            f"{size_mb:.1f} / {total_mb:.1f} MB"
                            f"{Colors.RESET}",
                            end="", flush=True,
                        )
                        last_progress = progress

        if total_size:
            print()

        # Verify download completeness
        if total_size and downloaded < total_size:
            log_warn(
                f"Incomplete download: got {downloaded} of "
                f"{total_size} bytes"
            )
            if retry_count < MAX_DOWNLOAD_RETRIES:
                wait = RETRY_BACKOFF_BASE ** (retry_count + 1)
                log_info(f"Retrying in {wait}s...")
                time.sleep(wait)
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                return download_file(
                    url, dest_path, description, retry_count + 1
                )
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return False

        # Verify file is not empty
        if downloaded == 0:
            log_error("Downloaded file is empty.")
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return False

        # Rename temp file to final path
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_path, dest_path)
        except OSError:
            shutil.move(temp_path, dest_path)

        file_hash = hash_obj.hexdigest()[:16]
        log_ok(f"Downloaded {description} "
               f"({downloaded / 1024:.0f} KB, sha256:{file_hash})")
        log_debug(f"Full SHA256: {hash_obj.hexdigest()}")
        return True

    except HTTPError as e:
        log_error(f"HTTP error {e.code}: {e.reason}")
        if e.code == 403:
            log_info("Possible rate-limiting or access restriction.")
        elif e.code == 404:
            log_info("File not found at this URL.")
        return False
    except URLError as e:
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        log_error(f"Connection error: {reason}")
        if "SSL" in reason or "CERTIFICATE" in reason.upper():
            log_info("SSL/TLS certificate error — proxy or firewall may be "
                     "intercepting HTTPS traffic.")
        elif "timed out" in reason.lower():
            if retry_count < MAX_DOWNLOAD_RETRIES:
                wait = RETRY_BACKOFF_BASE ** (retry_count + 1)
                log_info(f"Retrying in {wait}s...")
                time.sleep(wait)
                return download_file(
                    url, dest_path, description, retry_count + 1
                )
        return False
    except socket.timeout:
        log_error("Connection timed out.")
        if retry_count < MAX_DOWNLOAD_RETRIES:
            wait = RETRY_BACKOFF_BASE ** (retry_count + 1)
            log_info(f"Retrying in {wait}s...")
            time.sleep(wait)
            return download_file(
                url, dest_path, description, retry_count + 1
            )
        return False
    except PermissionError:
        log_error(f"Permission denied writing to {dest_path}")
        log_info("Check that the directory is writable and not blocked "
                 "by antivirus.")
        return False
    except Exception as e:
        log_error(f"Download error: {e}")
        log_debug(f"Traceback: {tb_module.format_exc()}")
        return False
    finally:
        # Clean up partial temp file
        temp_path = dest_path + ".downloading"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def download_with_fallback(urls, dest_path, description="file"):
    """Try downloading from multiple URLs. Returns True on first success."""
    for i, url in enumerate(urls):
        if i > 0:
            log_warn(f"Trying mirror #{i + 1} of {len(urls)}...")
        if download_file(url, dest_path, description):
            return True
    return False


# ==========================================================================
#  MinGW INSTALLATION
# ==========================================================================

def install_mingw(install_dir, arch_info):
    """
    Download and install MinGW-w64 to the specified directory.
    Selects 32-bit or 64-bit based on system architecture.
    """
    log_info(f"Target install directory: {install_dir}")

    # Select download URLs based on architecture
    if arch_info["os_64bit"]:
        urls = MINGW64_DOWNLOAD_URLS
        log_info("Downloading 64-bit MinGW-w64...")
    else:
        urls = MINGW32_DOWNLOAD_URLS
        log_info("Downloading 32-bit MinGW-w64...")

    # Check disk space
    drive = os.path.splitdrive(install_dir)[0] or "C:"
    free_mb, has_space = check_disk_space(drive + "\\", REQUIRED_DISK_SPACE_MB)
    if not has_space:
        log_error(
            f"Insufficient disk space on {drive} — "
            f"need {REQUIRED_DISK_SPACE_MB} MB, have {free_mb} MB"
        )
        return None
    elif free_mb > 0:
        log_ok(f"Disk space OK: {free_mb} MB free on {drive}")

    # Use a safe temp directory
    temp_base = get_safe_temp_dir()
    temp_dir = tempfile.mkdtemp(prefix="mingw_setup_", dir=temp_base)
    zip_path = os.path.join(temp_dir, "mingw.zip")

    try:
        # Download
        if not download_with_fallback(urls, zip_path, "MinGW-w64"):
            log_error("Failed to download MinGW-w64 from all mirrors.")
            log_info("Possible causes:")
            log_info("  - No internet connection")
            log_info("  - Firewall/proxy blocking GitHub")
            log_info("  - Antivirus blocking the download")
            log_info("")
            log_info("Manual download:")
            log_info(f"  1. Visit: {urls[0]}")
            log_info(f"  2. Extract to: {install_dir}")
            log_info(f"  3. Re-run this script")
            return None

        # Verify the downloaded file is a valid zip
        log_info("Verifying download integrity...")
        try:
            if not zipfile.is_zipfile(zip_path):
                file_size = os.path.getsize(zip_path)
                log_error(
                    f"Downloaded file is not a valid ZIP archive "
                    f"({file_size} bytes)"
                )
                log_info("The download may have been corrupted or intercepted "
                         "by a firewall/proxy.")
                # Check if it's an HTML error page
                try:
                    with open(zip_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        first_bytes = f.read(500)
                    if "<html" in first_bytes.lower():
                        log_error("Downloaded file is an HTML page — "
                                  "likely a captive portal or error page.")
                except Exception:
                    pass
                return None
        except Exception as e:
            log_warn(f"Could not verify zip integrity: {e}")

        # Extract
        log_info("Extracting MinGW-w64 (this may take several minutes)...")
        log_info("  Please be patient and do not close this window.")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Check for zip bombs (extremely large extraction)
                total_uncompressed = sum(f.file_size for f in zf.infolist())
                total_compressed = os.path.getsize(zip_path)
                if total_uncompressed > 10 * 1024 * 1024 * 1024:  # >10 GB
                    log_error("Archive appears abnormally large. Aborting.")
                    return None
                log_info(
                    f"  Archive: {total_compressed // (1024*1024)} MB "
                    f"-> {total_uncompressed // (1024*1024)} MB extracted"
                )
                zf.extractall(temp_dir)
        except zipfile.BadZipFile:
            log_error("ZIP archive is corrupted. Please try again.")
            return None
        except PermissionError:
            log_error("Permission denied during extraction.")
            log_info("Try running as Administrator, or extract to a "
                     "different location.")
            return None
        except OSError as e:
            if "No space left" in str(e) or "28" in str(e):
                log_error("Ran out of disk space during extraction.")
            else:
                log_error(f"Extraction error: {e}")
            return None

        # Delete the zip to free space before moving
        try:
            os.remove(zip_path)
            log_debug("Deleted zip file to free space.")
        except OSError:
            pass

        # Find the extracted mingw directory (search up to 3 levels deep)
        extracted_root = _find_gcc_root(temp_dir, max_depth=3)

        if not extracted_root:
            log_error("Could not find gcc.exe in extracted archive.")
            log_info("The archive structure may have changed. "
                     "Please extract manually.")
            return None

        log_ok(f"Found GCC at: {extracted_root}")

        # Move to final location
        if os.path.exists(install_dir):
            backup_dir = install_dir + f"_backup_{int(time.time())}"
            log_warn(f"Existing directory found. Creating backup...")
            log_info(f"  Backup: {backup_dir}")

            # Check for locked files first
            gcc_in_old = os.path.join(install_dir, "bin", "gcc.exe")
            if os.path.isfile(gcc_in_old) and is_file_locked(gcc_in_old):
                log_error(
                    "gcc.exe is currently in use by another process."
                )
                log_info("Please close all programs using MinGW "
                         "(IDEs, terminals, etc.) and try again.")
                return None

            try:
                shutil.move(install_dir, backup_dir)
                log_ok(f"Backup created at: {backup_dir}")
            except PermissionError:
                log_error("Cannot move existing directory — files are locked.")
                log_info("Close all IDEs, terminals, and programs using "
                         "MinGW, then try again.")
                return None
            except Exception as e:
                log_error(f"Backup failed: {e}")
                return None

        # Create parent directory
        parent_dir = os.path.dirname(install_dir)
        if parent_dir:
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except PermissionError:
                log_error(f"Cannot create directory: {parent_dir}")
                log_info("Try running as Administrator.")
                return None

        # Move extracted files to final location
        try:
            shutil.move(extracted_root, install_dir)
        except PermissionError:
            log_error(f"Cannot move files to {install_dir} — "
                      f"permission denied.")
            log_info("Try running as Administrator.")
            return None
        except Exception as e:
            log_error(f"Failed to move files: {e}")
            return None

        # Verify installation
        final_gcc = os.path.join(install_dir, "bin", "gcc.exe")
        if not os.path.isfile(final_gcc):
            log_error("Installation verification failed — gcc.exe not found.")
            return None

        log_ok(f"MinGW-w64 installed to: {install_dir}")
        return install_dir

    except Exception as e:
        log_error(f"Installation failed: {e}")
        log_debug(f"Traceback: {tb_module.format_exc()}")
        return None
    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def _find_gcc_root(search_dir, max_depth=3):
    """Recursively find the directory containing bin/gcc.exe."""
    if max_depth <= 0:
        return None

    gcc_path = os.path.join(search_dir, "bin", "gcc.exe")
    if os.path.isfile(gcc_path):
        return search_dir

    try:
        for entry in os.listdir(search_dir):
            candidate = os.path.join(search_dir, entry)
            if os.path.isdir(candidate):
                result = _find_gcc_root(candidate, max_depth - 1)
                if result:
                    return result
    except (PermissionError, OSError):
        pass

    return None


# ==========================================================================
#  graphics.h SETUP
# ==========================================================================

def install_graphics_h(mingw_root, install_type="MinGW-w64"):
    """
    Download and install WinBGIm (graphics.h) files into MinGW.
    Handles different directory structures for MSYS2, TDM-GCC, etc.
    """
    log_info("Installing WinBGIm (graphics.h) library...")

    # Determine correct include and lib directories
    include_dir = os.path.join(mingw_root, "include")
    lib_dir = os.path.join(mingw_root, "lib")

    # For MSYS2, also install in the cross-compilation target directory
    extra_include_dirs = []
    extra_lib_dirs = []
    if install_type == "MSYS2":
        for target in ["x86_64-w64-mingw32", "i686-w64-mingw32"]:
            target_inc = os.path.join(mingw_root, target, "include")
            target_lib = os.path.join(mingw_root, target, "lib")
            if os.path.isdir(os.path.join(mingw_root, target)):
                extra_include_dirs.append(target_inc)
                extra_lib_dirs.append(target_lib)

    # Create directories
    for d in [include_dir, lib_dir] + extra_include_dirs + extra_lib_dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except PermissionError:
            log_error(f"Permission denied creating directory: {d}")
            log_info("Try running as Administrator.")
            return False
        except OSError as e:
            log_error(f"Cannot create directory {d}: {e}")
            return False

    temp_dir = tempfile.mkdtemp(prefix="graphics_h_")
    all_ok = True

    try:
        for filename, urls in GRAPHICS_FILES.items():
            temp_path = os.path.join(temp_dir, filename)

            if not download_with_fallback(urls, temp_path, filename):
                log_error(f"Failed to download {filename} from all mirrors.")
                all_ok = False
                continue

            # Verify downloaded file is not empty
            try:
                file_size = os.path.getsize(temp_path)
                if file_size == 0:
                    log_error(f"{filename} downloaded as empty file.")
                    all_ok = False
                    continue
                # Header files should be text, lib should be >1KB
                if filename.endswith(".a") and file_size < 1024:
                    log_warn(f"{filename} seems too small ({file_size} bytes)")
            except OSError:
                pass

            # Install to primary location
            dest_rel = GRAPHICS_H_TARGETS[filename]
            final_path = os.path.join(mingw_root, dest_rel)

            try:
                # Backup existing file
                if os.path.isfile(final_path):
                    backup_path = final_path + ".backup"
                    try:
                        shutil.copy2(final_path, backup_path)
                        log_debug(f"Backed up {final_path}")
                    except Exception:
                        pass

                shutil.copy2(temp_path, final_path)
                log_ok(f"Installed {filename} -> {final_path}")
            except PermissionError:
                log_error(f"Permission denied: cannot write {final_path}")
                log_info("Try running as Administrator.")
                all_ok = False
                continue
            except OSError as e:
                log_error(f"Cannot install {filename}: {e}")
                all_ok = False
                continue

            # Install to extra directories (MSYS2 etc.)
            if filename.endswith(".h"):
                for extra_dir in extra_include_dirs:
                    extra_path = os.path.join(extra_dir, filename)
                    try:
                        shutil.copy2(temp_path, extra_path)
                        log_ok(f"  Also installed to: {extra_path}")
                    except Exception as e:
                        log_debug(f"Could not copy to {extra_path}: {e}")
            elif filename.endswith(".a"):
                for extra_dir in extra_lib_dirs:
                    extra_path = os.path.join(extra_dir, filename)
                    try:
                        shutil.copy2(temp_path, extra_path)
                        log_ok(f"  Also installed to: {extra_path}")
                    except Exception as e:
                        log_debug(f"Could not copy to {extra_path}: {e}")

        # Patch graphics.h for modern GCC compatibility
        graphics_h_path = os.path.join(include_dir, "graphics.h")
        if os.path.isfile(graphics_h_path):
            patch_graphics_h(graphics_h_path)

        # Also patch in extra dirs
        for extra_dir in extra_include_dirs:
            extra_gh = os.path.join(extra_dir, "graphics.h")
            if os.path.isfile(extra_gh):
                patch_graphics_h(extra_gh)

    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return all_ok


def patch_graphics_h(filepath):
    """
    Apply compatibility patches to graphics.h for modern GCC.
    Patches applied:
      1. values.h -> limits.h + float.h (values.h removed in MinGW-w64)
      2. Ensure stddef.h included (for NULL)
      3. Fix deprecated throw() specifications (GCC 11+)
      4. Fix missing MAXINT definition
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        original = content
        patches_applied = []

        # Patch 1: Replace <values.h> with <limits.h> and <float.h>
        if "<values.h>" in content:
            content = content.replace(
                "#include <values.h>",
                "#include <limits.h>\n"
                "#include <float.h>  "
                "// patched: values.h -> limits.h + float.h",
            )
            patches_applied.append(
                "Replaced <values.h> with <limits.h> + <float.h>"
            )

        # Patch 2: Ensure stddef.h is included (for NULL)
        if "#include <stddef.h>" not in content and "NULL" in content:
            lines = content.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("#include"):
                    insert_idx = i + 1
            if insert_idx > 0:
                lines.insert(
                    insert_idx,
                    "#include <stddef.h>  "
                    "// patched: ensure NULL is defined",
                )
                content = "\n".join(lines)
                patches_applied.append(
                    "Added <stddef.h> for NULL definition"
                )

        # Patch 3: Fix MAXINT if not defined (removed in newer compilers)
        if "MAXINT" in content and "#define MAXINT" not in content:
            # Add after the includes block
            lines = content.split("\n")
            last_include = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("#include"):
                    last_include = i
            if last_include > 0:
                maxint_def = (
                    "\n#ifndef MAXINT\n"
                    "#define MAXINT INT_MAX  "
                    "// patched: MAXINT for modern compilers\n"
                    "#endif\n"
                )
                lines.insert(last_include + 1, maxint_def)
                content = "\n".join(lines)
                patches_applied.append("Added MAXINT definition")

        # Patch 4: Fix deprecated dynamic exception specifications
        # (throw() is deprecated in C++11, removed in C++17)
        if "throw()" in content:
            content = content.replace("throw()", "noexcept")
            patches_applied.append(
                "Replaced throw() with noexcept (C++17 compat)"
            )

        if content != original:
            # Write patched file
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                for patch in patches_applied:
                    log_ok(f"Patched: {patch}")
            except PermissionError:
                log_error(f"Cannot write patched file: {filepath}")
                log_info("Try running as Administrator.")
        else:
            log_info("graphics.h does not need patching.")

    except Exception as e:
        log_warn(f"Could not patch graphics.h: {e}")
        log_debug(f"Patch traceback: {tb_module.format_exc()}")


# ==========================================================================
#  PATH MANAGEMENT — ROBUST
# ==========================================================================

def is_in_path(mingw_bin):
    """Check if directory is in PATH (case-insensitive, handles trailing slash)."""
    mingw_bin_norm = os.path.normpath(mingw_bin).lower().rstrip("\\")
    for p in os.environ.get("PATH", "").split(os.pathsep):
        p_norm = os.path.normpath(p).lower().rstrip("\\")
        if p_norm == mingw_bin_norm:
            return True
    return False


def check_path_conflicts(mingw_bin):
    """
    Check for other gcc.exe entries in PATH that could cause conflicts.
    Returns list of conflicting paths.
    """
    conflicts = []
    mingw_bin_norm = os.path.normpath(mingw_bin).lower()

    for p in os.environ.get("PATH", "").split(os.pathsep):
        p = p.strip().strip('"')
        if not p:
            continue
        p_norm = os.path.normpath(p).lower()
        if p_norm == mingw_bin_norm:
            continue
        gcc_candidate = os.path.join(p, "gcc.exe")
        if os.path.isfile(gcc_candidate):
            conflicts.append(p)

    return conflicts


def add_to_system_path(mingw_bin):
    """
    Add MinGW bin to system PATH permanently.
    Handles: admin/non-admin, PATH length limits, conflicts.
    """
    mingw_bin = os.path.normpath(mingw_bin)

    if is_in_path(mingw_bin):
        log_ok(f"Already in PATH: {mingw_bin}")
        return True

    # Check for PATH conflicts
    conflicts = check_path_conflicts(mingw_bin)
    if conflicts:
        log_warn(f"Found {len(conflicts)} other GCC installation(s) in PATH:")
        for c in conflicts:
            log_warn(f"  - {c}")
        log_info("This may cause version conflicts. The first gcc.exe "
                 "found in PATH will be used.")

    log_info(f"Adding to system PATH: {mingw_bin}")

    if not _WINREG_AVAILABLE:
        log_error("Windows Registry module not available.")
        _print_manual_path_instructions(mingw_bin)
        return False

    # Try system-wide PATH first (requires admin)
    if is_admin():
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                current_path, path_type = winreg.QueryValueEx(key, "Path")

                # Deduplicate and clean existing PATH
                existing = []
                seen = set()
                for p in current_path.split(";"):
                    p_clean = p.strip()
                    if not p_clean:
                        continue
                    p_norm = os.path.normpath(p_clean).lower()
                    if p_norm not in seen:
                        seen.add(p_norm)
                        existing.append(p_clean)

                mingw_bin_norm = os.path.normpath(mingw_bin).lower()
                if mingw_bin_norm not in seen:
                    existing.append(mingw_bin)
                    new_path = ";".join(existing)

                    # Check PATH length (Windows limit is ~2048 chars
                    # for system PATH, 32767 for user)
                    if len(new_path) > 2000:
                        log_warn("System PATH is very long "
                                 f"({len(new_path)} chars). "
                                 "Will use User PATH instead.")
                    else:
                        # Preserve original type (REG_SZ vs REG_EXPAND_SZ)
                        winreg.SetValueEx(
                            key, "Path", 0,
                            path_type if path_type else winreg.REG_EXPAND_SZ,
                            new_path,
                        )
                        log_ok("Added to SYSTEM PATH (machine-wide).")
                        _broadcast_env_change()
                        return True
        except PermissionError:
            log_warn("Could not write to system PATH.")
        except Exception as e:
            log_warn(f"System PATH update failed: {e}")

    # Fallback: user-level PATH
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        ) as key:
            try:
                current_path, path_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
                path_type = winreg.REG_EXPAND_SZ

            existing = []
            seen = set()
            for p in current_path.split(";"):
                p_clean = p.strip()
                if not p_clean:
                    continue
                p_norm = os.path.normpath(p_clean).lower()
                if p_norm not in seen:
                    seen.add(p_norm)
                    existing.append(p_clean)

            mingw_bin_norm = os.path.normpath(mingw_bin).lower()
            if mingw_bin_norm not in seen:
                existing.append(mingw_bin)
                new_path = ";".join(existing)

                winreg.SetValueEx(
                    key, "Path", 0,
                    path_type if path_type else winreg.REG_EXPAND_SZ,
                    new_path,
                )
                log_ok("Added to USER PATH.")
                _broadcast_env_change()
                return True

    except Exception as e:
        log_warn(f"User PATH update failed: {e}")

    _print_manual_path_instructions(mingw_bin)
    return False


def _print_manual_path_instructions(mingw_bin):
    """Print manual PATH configuration instructions."""
    log_warn("Could not update PATH automatically.")
    print(f"\n  {Colors.YELLOW}Please add this to your PATH manually:"
          f"{Colors.RESET}")
    print(f"    {Colors.BOLD}{mingw_bin}{Colors.RESET}")
    print()
    print(f"  {Colors.DIM}Option 1 (GUI):{Colors.RESET}")
    print(f"  {Colors.DIM}  Win+R -> sysdm.cpl -> Advanced -> "
          f"Environment Variables{Colors.RESET}")
    print(f"  {Colors.DIM}  -> Path -> Edit -> New -> "
          f"paste the path above{Colors.RESET}")
    print()
    print(f"  {Colors.DIM}Option 2 (PowerShell, run as Admin):{Colors.RESET}")
    print(f"  {Colors.DIM}  [Environment]::SetEnvironmentVariable("
          f"'Path',{Colors.RESET}")
    print(f"  {Colors.DIM}    [Environment]::GetEnvironmentVariable("
          f"'Path','Machine')+';{mingw_bin}',{Colors.RESET}")
    print(f"  {Colors.DIM}    'Machine'){Colors.RESET}")
    print()


def _broadcast_env_change():
    """Notify all windows that environment variables have changed."""
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Environment", SMTO_ABORTIFHUNG, 5000,
            ctypes.byref(result),
        )
    except Exception:
        pass


# ==========================================================================
#  VERIFICATION
# ==========================================================================

def verify_graphics_compilation(mingw_root):
    """
    Compile a test program using graphics.h to verify everything works.
    Tests multiple compilation modes for maximum compatibility.
    """
    log_info("Verifying graphics.h compilation...")

    gpp_path = os.path.join(mingw_root, "bin", "g++.exe")
    if not os.path.isfile(gpp_path):
        log_error("g++.exe not found — cannot verify.")
        return False

    test_dir = tempfile.mkdtemp(prefix="gfx_test_")
    test_cpp = os.path.join(test_dir, "test_graphics.cpp")
    test_exe = os.path.join(test_dir, "test_graphics.exe")

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        with open(test_cpp, "w", encoding="ascii") as f:
            f.write(
                '#include <graphics.h>\n'
                '#include <stdio.h>\n'
                '\n'
                'int main() {\n'
                '    printf("graphics.h compilation successful!\\n");\n'
                '    return 0;\n'
                '}\n'
            )

        # Set up environment with mingw bin in PATH for DLL resolution
        env = os.environ.copy()
        mingw_bin = os.path.join(mingw_root, "bin")
        env["PATH"] = mingw_bin + os.pathsep + env.get("PATH", "")

        # Try multiple C++ standard flags in order of preference
        std_flags = ["-std=c++17", "-std=c++14", "-std=c++11", ""]
        link_libs = [
            "-lbgi", "-lgdi32", "-lcomdlg32",
            "-luuid", "-loleaut32", "-lole32",
        ]

        for std_flag in std_flags:
            cmd = [gpp_path, test_cpp, "-o", test_exe] + link_libs
            if std_flag:
                cmd.insert(3, std_flag)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True,
                    timeout=COMPILE_TIMEOUT,
                    cwd=test_dir,
                    env=env,
                    creationflags=creation_flags,
                )

                if result.returncode == 0:
                    std_label = std_flag if std_flag else "(default std)"
                    log_ok(f"graphics.h compilation PASSED with {std_label}")
                    return True

                # If it failed, log the error and try next standard
                if std_flag != std_flags[-1]:
                    log_debug(
                        f"Failed with {std_flag}: "
                        f"{result.stderr.strip()[:100]}"
                    )
                    # Remove old output for retry
                    if os.path.exists(test_exe):
                        os.remove(test_exe)
                    continue

            except subprocess.TimeoutExpired:
                log_warn("Compilation timed out — antivirus may be scanning.")
                continue
            except OSError as e:
                log_error(f"Cannot run g++: {e}")
                return False

        # All standards failed
        log_error("graphics.h compilation test FAILED with all C++ standards")
        if result and result.stderr:
            errors = result.stderr.strip().split("\n")[:8]
            for line in errors:
                print(f"    {Colors.DIM}{line}{Colors.RESET}")

            # Provide specific guidance based on error
            stderr_text = result.stderr
            if "graphics.h: No such file" in stderr_text:
                log_info("graphics.h not found in include path.")
            elif "cannot find -lbgi" in stderr_text:
                log_info("libbgi.a not found in lib path.")
            elif "undefined reference" in stderr_text:
                log_info("Linker errors — libbgi.a may be incompatible "
                         "with this GCC version.")
        return False

    except Exception as e:
        log_error(f"Verification error: {e}")
        log_debug(f"Traceback: {tb_module.format_exc()}")
        return False
    finally:
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except Exception:
            pass


# ==========================================================================
#  MAIN LOGIC
# ==========================================================================

def print_installation_report(info):
    """Print a formatted report of a MinGW installation."""
    type_color = Colors.GREEN if info["is_healthy"] else Colors.RED
    print(f"\n  {Colors.BOLD}Installation: {type_color}"
          f"{info['root']}{Colors.RESET}")
    print(f"    Type         : {info['install_type']}")
    print(f"    Architecture : {info['arch']}")
    print(f"    Version      : {info['version'] or 'Unknown'}")
    print(f"    Health       : "
          f"{'Healthy' if info['is_healthy'] else 'UNHEALTHY'} "
          f"(score: {info['health_score']}/100)")
    print(f"    Outdated     : "
          f"{'Yes' if info['is_outdated'] else 'No'}")
    print(f"    graphics.h   : "
          f"{'Installed' if info['has_graphics_h'] else 'Missing'}")
    print(f"    winbgim.h    : "
          f"{'Installed' if info['has_winbgim_h'] else 'Missing'}")
    print(f"    libbgi.a     : "
          f"{'Installed' if info['has_libbgi_a'] else 'Missing'}")

    if info["missing_files"]:
        print(f"    Missing      : {', '.join(info['missing_files'])}")
    if info["corruption_details"]:
        for detail in info["corruption_details"]:
            print(f"    {Colors.RED}! {detail}{Colors.RESET}")


def print_help():
    """Print usage information."""
    print(f"""
{Colors.BOLD}Usage:{Colors.RESET}
  python setup_graphics_mingw.py [options]

{Colors.BOLD}Options:{Colors.RESET}
  --silent    Auto-accept all prompts (unattended mode)
  --log       Write detailed log to setup_log.txt
  --help      Show this help message

{Colors.BOLD}Examples:{Colors.RESET}
  python setup_graphics_mingw.py              # Interactive setup
  python setup_graphics_mingw.py --silent     # Unattended setup
  python setup_graphics_mingw.py --log        # With logging
  python setup_graphics_mingw.py --silent --log  # Both
""")


def main():
    global LOG_FILE

    enable_ansi_colors()

    if ARGS.help:
        print_help()
        sys.exit(0)

    print_banner()
    check_platform()

    # Setup logging if requested
    if ARGS.log:
        LOG_FILE = os.path.join(os.getcwd(), "setup_log.txt")
        log_info(f"Logging to: {LOG_FILE}")
        _log_to_file("INFO", "=" * 60)
        _log_to_file("INFO", "Setup started")
        _log_to_file("INFO", f"Python: {sys.version}")
        _log_to_file("INFO", f"Platform: {sys.platform}")
        _log_to_file("INFO", f"CWD: {os.getcwd()}")

    total_steps = 7
    selected_mingw = None

    # == Step 1: System checks =============================================
    log_step(1, total_steps, "System & Environment Checks")

    # Admin check
    if is_admin():
        log_ok("Running with Administrator privileges.")
    else:
        log_warn("Not running as Administrator.")
        log_info("Some features (system PATH) may require admin.")
        log_info("Tip: Right-click -> 'Run as administrator'")
        resp = ask_user("Continue anyway?", "y")
        if resp == "n":
            log_info("Exiting. Please re-run as Administrator.")
            sys.exit(0)

    # Architecture
    arch_info = get_system_arch()
    log_ok(f"System architecture: {arch_info['arch_str']} "
           f"({'64-bit' if arch_info['os_64bit'] else '32-bit'} OS, "
           f"{'64-bit' if arch_info['python_64bit'] else '32-bit'} Python)")

    if not arch_info["os_64bit"]:
        log_warn("32-bit system detected. Will install 32-bit MinGW.")

    if arch_info["os_64bit"] and not arch_info["python_64bit"]:
        log_warn("Running 32-bit Python on 64-bit OS. "
                 "This is fine but 64-bit Python is recommended.")

    # Windows version
    win_ver = get_windows_version()
    log_info(f"Windows version: {win_ver}")

    # Disk space
    free_mb, has_space = check_disk_space("C:\\", REQUIRED_DISK_SPACE_MB)
    if not has_space:
        log_error(f"Low disk space on C: drive ({free_mb} MB free, "
                  f"need {REQUIRED_DISK_SPACE_MB} MB)")
        resp = ask_user("Continue anyway?", "n")
        if resp == "n":
            sys.exit(1)
    elif free_mb > 0:
        log_ok(f"Disk space: {free_mb} MB free on C: drive")

    # Antivirus detection
    av_detected = detect_running_antivirus()
    if av_detected:
        av_names = ", ".join(av_detected)
        log_warn(f"Antivirus detected: {av_names}")
        log_info("If the setup fails or hangs, your antivirus may be "
                 "blocking MinGW files.")
        log_info("Consider temporarily pausing real-time protection.")

    # == Step 2: Network check =============================================
    log_step(2, total_steps, "Network & Connectivity Check")

    net_info = check_internet_connection()
    if not net_info["connected"]:
        log_error("No internet connection detected!")
        log_info("This script needs to download files from the internet.")
        log_info("")
        log_info("If you are behind a proxy, set these environment variables:")
        log_info("  set HTTP_PROXY=http://your-proxy:port")
        log_info("  set HTTPS_PROXY=http://your-proxy:port")
        log_info("")
        resp = ask_user("Try to continue anyway?", "n")
        if resp == "n":
            sys.exit(1)
    elif not net_info["github_reachable"]:
        log_warn("GitHub is not reachable — downloads may fail.")
        log_info("If you are on a restricted network, a proxy may be needed.")
        proxy_info = detect_proxy()
        if proxy_info:
            log_info("Detected proxy settings:")
            for k, v in proxy_info.items():
                log_info(f"  {k} = {v}")
        else:
            log_info("No proxy settings detected.")
    else:
        log_ok("Internet connection OK (GitHub reachable).")

    proxy_info = detect_proxy()
    if proxy_info:
        log_info("Using proxy settings:")
        for k, v in proxy_info.items():
            if not k.startswith("_"):
                log_info(f"  {k} = {v}")

    # == Step 3: Scan for existing installations ===========================
    log_step(3, total_steps, "Scanning for Existing MinGW Installations")

    log_info("Scanning PATH, common directories, registry, "
             "package managers...")
    installations = find_mingw_installations()

    # Also report package manager installs
    pkg_installs = detect_package_manager_installs()
    if pkg_installs:
        log_info(f"Package manager installs found: "
                 f"{len(pkg_installs)}")
        for pkg in pkg_installs:
            log_info(f"  [{pkg['source']}] {pkg['name']} at {pkg['path']}")

    if not installations:
        log_warn("No MinGW installation found on this system.")
    else:
        log_ok(f"Found {len(installations)} installation(s):")
        for info in installations:
            print_installation_report(info)

    # == Step 4: Decide what to do =========================================
    log_step(4, total_steps, "Determining Required Actions")

    need_fresh_install = False
    need_graphics_only = False
    chosen_installation = None

    if not installations:
        need_fresh_install = True
        log_info("Action: Full MinGW-w64 installation + graphics.h setup")
    else:
        # Sort by health score (highest first)
        installations.sort(key=lambda x: x["health_score"], reverse=True)

        healthy = [
            i for i in installations
            if i["is_healthy"] and not i["is_outdated"]
        ]
        healthy_old = [
            i for i in installations
            if i["is_healthy"] and i["is_outdated"]
        ]
        unhealthy = [
            i for i in installations
            if not i["is_healthy"]
        ]

        if healthy:
            chosen_installation = healthy[0]
            has_all_graphics = (
                chosen_installation["has_graphics_h"]
                and chosen_installation["has_winbgim_h"]
                and chosen_installation["has_libbgi_a"]
            )
            if not has_all_graphics:
                need_graphics_only = True
                log_info(
                    f"Action: Install graphics.h files into "
                    f"{chosen_installation['install_type']} at "
                    f"{chosen_installation['root']}"
                )
            else:
                log_ok("MinGW is healthy and graphics.h is installed!")
                log_info("Action: Re-install & re-patch graphics.h for safety")
                need_graphics_only = True

        elif healthy_old:
            chosen_installation = healthy_old[0]
            log_warn(
                f"Best available MinGW is outdated "
                f"(GCC {'.'.join(str(v) for v in chosen_installation['version_tuple'])})"
            )
            log_info(
                f"Minimum recommended: GCC "
                f"{'.'.join(str(v) for v in MIN_GCC_VERSION)}"
            )
            resp = ask_user("Upgrade to latest MinGW-w64?", "y")
            if resp != "n":
                need_fresh_install = True
                log_info("Action: Upgrade MinGW-w64 + install graphics.h")
            else:
                need_graphics_only = True
                log_info("Action: Keep current MinGW, install graphics.h only")

        else:
            # All installations are corrupted
            log_error("All existing installations have issues:")
            for info in unhealthy:
                for detail in info["corruption_details"]:
                    log_error(f"  {info['root']}: {detail}")

            # Pick the best one and ask if user wants to try using it
            best_unhealthy = unhealthy[0] if unhealthy else None
            if best_unhealthy and best_unhealthy["health_score"] >= 40:
                log_info(
                    f"Best available has score {best_unhealthy['health_score']}/100."
                )
                resp = ask_user(
                    f"Try using {best_unhealthy['root']} anyway?", "n"
                )
                if resp == "y":
                    chosen_installation = best_unhealthy
                    need_graphics_only = True
                else:
                    need_fresh_install = True
            else:
                need_fresh_install = True

            if need_fresh_install:
                log_info("Action: Fresh MinGW-w64 install + graphics.h setup")

    # == Step 5: Install / Update MinGW ====================================
    log_step(5, total_steps, "Installing / Updating MinGW")

    if need_fresh_install:
        install_dir = DEFAULT_MINGW_INSTALL_DIR
        if chosen_installation:
            install_dir = chosen_installation["root"]

        custom_path = ask_user_input(
            f"Install to [{install_dir}] "
            f"(Enter for default, or type path): ",
            default=install_dir,
        )
        if custom_path:
            install_dir = custom_path

        # Validate install path
        install_dir = os.path.normpath(install_dir)

        # Warn about spaces in path
        if " " in install_dir:
            log_warn(f"Install path contains spaces: {install_dir}")
            log_info("Some tools may have issues with spaces in paths.")
            resp = ask_user("Use this path anyway?", "y")
            if resp == "n":
                install_dir = DEFAULT_MINGW_INSTALL_DIR
                log_info(f"Using default: {install_dir}")

        # Warn about very long paths
        if len(install_dir) > 100:
            log_warn(f"Install path is very long ({len(install_dir)} chars).")
            log_info("This may cause issues with Windows MAX_PATH limits.")

        mingw_root = install_mingw(install_dir, arch_info)
        if mingw_root is None:
            log_error("MinGW installation failed.")

            # Offer to try with a different path
            resp = ask_user("Try a different install location?", "y")
            if resp != "n":
                alt_dir = ask_user_input(
                    "Enter alternative path: ",
                    default=r"D:\MinGW",
                )
                if alt_dir:
                    mingw_root = install_mingw(alt_dir, arch_info)

            if mingw_root is None:
                log_error("MinGW installation failed. Aborting.")
                log_info("Please try:")
                log_info("  1. Run as Administrator")
                log_info("  2. Temporarily disable antivirus")
                log_info("  3. Check internet connection")
                log_info("  4. Download manually from "
                         "https://winlibs.com")
                sys.exit(1)

        selected_mingw = mingw_root
    else:
        selected_mingw = chosen_installation["root"]
        log_ok(f"Using existing MinGW: {selected_mingw}")

    # == Step 6: Install graphics.h ========================================
    log_step(6, total_steps, "Installing graphics.h (WinBGIm)")

    install_type = "MinGW-w64"
    if chosen_installation:
        install_type = chosen_installation["install_type"]

    if not install_graphics_h(selected_mingw, install_type):
        log_error("Some graphics.h files could not be installed.")
        log_info("You may need to download them manually from:")
        log_info("  https://github.com/ArvindAgarwal1310/graphics.h")
        # Don't abort — partial install might still work
    else:
        log_ok("All graphics.h files installed and patched successfully.")

    # == Step 7: PATH & Final Verification =================================
    log_step(7, total_steps, "Configuring PATH & Final Verification")

    mingw_bin = os.path.join(selected_mingw, "bin")

    # Update PATH
    add_to_system_path(mingw_bin)

    # Update current process PATH so verification works
    current_path = os.environ.get("PATH", "")
    if mingw_bin.lower() not in current_path.lower():
        os.environ["PATH"] = mingw_bin + os.pathsep + current_path

    # Verify GCC works
    log_info("Verifying GCC installation...")
    gcc_ok = False
    try:
        gcc_path = os.path.join(mingw_bin, "gcc.exe")
        result = subprocess.run(
            [gcc_path, "--version"],
            capture_output=True, text=True, timeout=VERSION_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            log_ok(f"GCC working: {version_line}")
            gcc_ok = True
        else:
            log_error("GCC verification failed.")
    except Exception as e:
        log_error(f"GCC verification error: {e}")

    # Verify g++ works
    gpp_ok = False
    try:
        gpp_path = os.path.join(mingw_bin, "g++.exe")
        result = subprocess.run(
            [gpp_path, "--version"],
            capture_output=True, text=True, timeout=VERSION_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            log_ok("G++ working.")
            gpp_ok = True
        else:
            log_error("G++ verification failed.")
    except Exception as e:
        log_error(f"G++ verification error: {e}")

    # Verify graphics.h compilation
    graphics_ok = False
    if gpp_ok:
        graphics_ok = verify_graphics_compilation(selected_mingw)
    else:
        log_warn("Skipping graphics.h compilation test (g++ not working).")

    # == Summary ===========================================================
    all_ok = gcc_ok and gpp_ok and graphics_ok

    if all_ok:
        status_color = Colors.GREEN
        status_text = "ALL CHECKS PASSED"
    else:
        status_color = Colors.YELLOW
        status_text = "SETUP COMPLETE (with warnings)"

    print(f"\n{Colors.BOLD}{status_color}"
          f"  ========================================================="
          f"{Colors.RESET}")
    print(f"{Colors.BOLD}{status_color}"
          f"                  {status_text}                   "
          f"{Colors.RESET}")
    print(f"{Colors.BOLD}{status_color}"
          f"  ========================================================="
          f"{Colors.RESET}\n")

    print(f"  MinGW Location : {Colors.GREEN}{selected_mingw}{Colors.RESET}")
    print(f"  GCC Binary     : {Colors.GREEN}"
          f"{os.path.join(selected_mingw, 'bin', 'gcc.exe')}{Colors.RESET}")
    print(f"  graphics.h     : {Colors.GREEN}"
          f"{os.path.join(selected_mingw, 'include', 'graphics.h')}"
          f"{Colors.RESET}")
    print(f"  GCC            : "
          f"{'Working' if gcc_ok else 'FAILED'}")
    print(f"  G++            : "
          f"{'Working' if gpp_ok else 'FAILED'}")
    print(f"  graphics.h     : "
          f"{'Working' if graphics_ok else 'FAILED'}")

    print(f"\n  {Colors.BOLD}Compile command:{Colors.RESET}")
    print(f"  {Colors.DIM}---------------------------------------------------"
          f"{Colors.RESET}")
    print(f"  g++ program.cpp -o program.exe "
          f"-lbgi -lgdi32 -lcomdlg32 -luuid -loleaut32 -lole32")

    print(f"\n  {Colors.BOLD}"
          f"Example program (save as hello_graphics.cpp):{Colors.RESET}")
    print(f"  {Colors.DIM}---------------------------------------------------"
          f"{Colors.RESET}")
    print(f"""{Colors.DIM}  #include <graphics.h>

  int main() {{
      int gd = DETECT, gm;
      initgraph(&gd, &gm, NULL);

      setcolor(WHITE);
      circle(320, 240, 100);
      outtextxy(270, 240, (char*)"Hello Graphics!");

      getch();
      closegraph();
      return 0;
  }}{Colors.RESET}
""")

    if not all_ok:
        print(f"  {Colors.YELLOW}Some issues were detected. "
              f"Troubleshooting tips:{Colors.RESET}")
        if not gcc_ok:
            print(f"    - GCC not working: "
                  f"reinstall MinGW or check antivirus")
        if not graphics_ok:
            print(f"    - graphics.h test failed: "
                  f"check compiler errors above")
        print(f"    - Restart your terminal/CMD for PATH changes")
        print(f"    - Run as Administrator if you had permission errors")
        if av_detected:
            print(f"    - Antivirus ({', '.join(av_detected)}) "
                  f"may be interfering")

    print(f"\n  {Colors.DIM}IMPORTANT: Open a NEW terminal/CMD window "
          f"for PATH changes to take effect.{Colors.RESET}")

    if LOG_FILE:
        print(f"  {Colors.DIM}Detailed log saved to: {LOG_FILE}{Colors.RESET}")

    print()

    # Return exit code
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Setup cancelled by user.{Colors.RESET}\n")
        exit_code = 130
    except Exception as e:
        print(f"\n  {Colors.RED}Unexpected error: {e}{Colors.RESET}")
        tb_module.print_exc()
        if LOG_FILE:
            _log_to_file("FATAL", f"Unexpected error: {e}")
            _log_to_file("FATAL", tb_module.format_exc())
            print(f"  {Colors.DIM}Check log file: {LOG_FILE}{Colors.RESET}")
        exit_code = 1
    finally:
        if LOG_FILE:
            _log_to_file("INFO", f"Setup finished with exit code {exit_code}")
            _log_to_file("INFO", "=" * 60)
    sys.exit(exit_code)
