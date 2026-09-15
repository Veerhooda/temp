#!/usr/bin/env python3
"""
===============================================================================
  Automated OpenGL (FreeGLUT) & MinGW-w64 Setup with Live Progress & ETA
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
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

if sys.platform != "win32":
    print("\n[ERROR] This script must be run on Windows.")
    sys.exit(1)

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False

DEFAULT_MINGW_DIR = r"C:\MinGW"

# 64-bit MinGW-w64 standalone zips (WinLibs)
MINGW64_URLS = [
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "13.2.0posix-18.1.5-11.0.1-ucrt-r5/"
    "winlibs-x86_64-posix-seh-gcc-13.2.0-mingw-w64ucrt-11.0.1-r5.zip",
    "https://github.com/brechtsanders/winlibs_mingw/releases/download/"
    "12.2.0-16.0.0-10.0.0-ucrt-r5/"
    "winlibs-x86_64-posix-seh-gcc-12.2.0-mingw-w64ucrt-10.0.0-r5.zip",
]

# High-availability mirrors for FreeGLUT MinGW 64-bit
FREEGLUT_URLS = [
    # Primary: Active & verified FreeGLUT 3.8.0 for MinGW
    "https://www.songho.ca/opengl/files/freeglut-mingw-3.8.0.zip",
    # Backup: Archive.org permanent CDN snapshot
    "https://web.archive.org/web/20220401102719if_/https://www.transmissionzero.co.uk/files/software/development/GLUT/freeglut-MinGW-3.0.0-1.mp.zip",
]

class Colors:
    RESET   = "\033[0m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

def enable_ansi():
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        Colors.RESET = Colors.RED = Colors.GREEN = Colors.YELLOW = Colors.CYAN = Colors.BOLD = Colors.DIM = ""

def log_info(msg):  print(f"  {Colors.CYAN}[INFO]{Colors.RESET}  {msg}")
def log_ok(msg):    print(f"  {Colors.GREEN}[ OK ]{Colors.RESET}  {msg}")
def log_warn(msg):  print(f"  {Colors.YELLOW}[WARN]{Colors.RESET}  {msg}")
def log_err(msg):   print(f"  {Colors.RED}[FAIL]{Colors.RESET}  {msg}")
def log_step(step, total, msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}== Step {step}/{total}: {msg} =={Colors.RESET}")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

# ==========================================================================
#  PROGRESS BAR RENDERER (LIVE SPEED + ETA)
# ==========================================================================

def render_progress(current, total, start_time, prefix="[PROG]", unit="MB", bar_len=24):
    elapsed = max(time.time() - start_time, 0.001)
    fraction = min(max(current / total, 0.0), 1.0) if total > 0 else 0
    pct = int(fraction * 100)

    filled = int(bar_len * fraction)
    bar = "█" * filled + "░" * (bar_len - filled)

    speed = current / elapsed
    remaining = (total - current) / speed if speed > 0 else 0

    if remaining < 60:
        eta_str = f"{int(remaining)}s"
    elif remaining < 3600:
        eta_str = f"{int(remaining//60)}m {int(remaining%60):02d}s"
    else:
        eta_str = ">1h"

    if unit == "MB":
        cur_mb = current / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        spd_mb = speed / (1024 * 1024)
        status = f"{cur_mb:.1f}/{tot_mb:.1f} MB | {spd_mb:.1f} MB/s"
    else:
        status = f"{current}/{total} {unit} | {int(speed)} {unit}/s"

    print(f"\r  {Colors.CYAN}{prefix}{Colors.RESET} [{Colors.GREEN}{bar}{Colors.RESET}] {pct:3d}% | {status} | ETA: {Colors.YELLOW}{eta_str}{Colors.RESET}  ", end="", flush=True)

# ==========================================================================
#  DOWNLOAD & EXTRACT
# ==========================================================================

def download_file_with_progress(urls, dest_path, desc):
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    for idx, url in enumerate(urls):
        log_info(f"Connecting to {desc} (source {idx+1}/{len(urls)})...")
        try:
            req = Request(url, headers=req_headers)
            with urlopen(req, timeout=30) as resp, open(dest_path, "wb") as out:
                total_len = resp.getheader("Content-Length")
                total_size = int(total_len) if total_len else 0
                downloaded = 0
                start_time = time.time()
                last_render = 0

                while chunk := resp.read(128 * 1024):
                    out.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if total_size > 0 and (now - last_render >= 0.1):
                        render_progress(downloaded, total_size, start_time, prefix="[DOWN]", unit="MB")
                        last_render = now

                if total_size > 0:
                    render_progress(total_size, total_size, start_time, prefix="[DOWN]", unit="MB")
            print()
            log_ok(f"Downloaded {desc} successfully.")
            return True
        except Exception as e:
            print()
            log_warn(f"Mirror #{idx+1} failed: {e}")
            if idx < len(urls) - 1:
                log_info("Trying fallback mirror...")
    log_err(f"Failed to download {desc} from all available mirrors.")
    return False

def extract_zip_with_progress(zip_path, dest_dir, prefix="[EXTR]"):
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        total_files = len(members)
        start_time = time.time()
        last_render = 0

        for i, member in enumerate(members, start=1):
            zf.extract(member, dest_dir)
            now = time.time()
            if now - last_render >= 0.1 or i == total_files:
                render_progress(i, total_files, start_time, prefix=prefix, unit="files")
                last_render = now
    print()
    log_ok("Extraction complete.")

# ==========================================================================
#  DETECTION & INSTALLATION
# ==========================================================================

def find_existing_mingw():
    candidates = []
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        path_dir = path_dir.strip().strip('"')
        if os.path.isfile(os.path.join(path_dir, "g++.exe")):
            root = os.path.dirname(os.path.normpath(path_dir))
            if root not in candidates:
                candidates.append(root)

    standard_locs = [
        r"C:\MinGW", r"C:\mingw64", r"C:\msys64\mingw64",
        r"C:\msys64\ucrt64", r"C:\TDM-GCC-64", os.path.expanduser(r"~\mingw64")
    ]
    for loc in standard_locs:
        if os.path.isfile(os.path.join(loc, "bin", "g++.exe")) and loc not in candidates:
            candidates.append(loc)
    return candidates

def check_freeglut_installed(mingw_root):
    inc_glut = [
        os.path.join(mingw_root, "include", "GL", "glut.h"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "include", "GL", "glut.h"),
    ]
    lib_glut = [
        os.path.join(mingw_root, "lib", "libfreeglut.a"),
        os.path.join(mingw_root, "lib", "libfreeglut.dll.a"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "lib", "libfreeglut.a"),
    ]
    dll_glut = [
        os.path.join(mingw_root, "bin", "freeglut.dll"),
        os.path.join(mingw_root, "bin", "libfreeglut.dll"),
    ]
    return any(os.path.isfile(p) for p in inc_glut) and any(os.path.isfile(p) for p in lib_glut) and any(os.path.isfile(p) for p in dll_glut)

def install_mingw(target_dir):
    log_info(f"Setting up 64-bit MinGW-w64 at {target_dir}...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "mingw.zip")
        if not download_file_with_progress(MINGW64_URLS, zip_path, "MinGW-w64 (~150-200 MB)"):
            return None

        log_info("Extracting GCC compiler files...")
        try:
            extract_zip_with_progress(zip_path, tmp_dir, prefix="[EXTR]")
        except Exception as e:
            log_err(f"Extraction failed: {e}")
            return None

        extracted_root = None
        for root, dirs, files in os.walk(tmp_dir):
            if "g++.exe" in files:
                extracted_root = os.path.dirname(root)
                break

        if not extracted_root:
            log_err("Could not find extracted compiler binaries.")
            return None

        if os.path.exists(target_dir):
            try:
                shutil.rmtree(target_dir)
            except Exception:
                target_dir = target_dir + f"_new_{int(time.time())}"

        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        shutil.move(extracted_root, target_dir)
        log_ok(f"MinGW-w64 deployed to: {target_dir}")
        return target_dir

def install_freeglut(mingw_root):
    log_info("Installing FreeGLUT headers, libraries, and runtime DLL...")
    inc_dirs = [
        os.path.join(mingw_root, "include", "GL"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "include", "GL"),
    ]
    lib_dirs = [
        os.path.join(mingw_root, "lib"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "lib"),
    ]
    bin_dir = os.path.join(mingw_root, "bin")

    for d in inc_dirs + lib_dirs + [bin_dir]:
        os.makedirs(d, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        fg_zip = os.path.join(tmp_dir, "freeglut.zip")
        if not download_file_with_progress(FREEGLUT_URLS, fg_zip, "FreeGLUT Package (~1 MB)"):
            return False

        log_info("Extracting FreeGLUT package...")
        with zipfile.ZipFile(fg_zip, "r") as zf:
            zf.extractall(tmp_dir)

        # 1. Install headers
        header_count = 0
        for root, dirs, files in os.walk(tmp_dir):
            if any(h in files for h in ["glut.h", "freeglut.h"]):
                for file in files:
                    if file.endswith(".h"):
                        src = os.path.join(root, file)
                        for dest in inc_dirs:
                            shutil.copy2(src, os.path.join(dest, file))
                        header_count += 1
                break
        log_ok(f"Installed {header_count} OpenGL/GLUT headers.")

        # 2. Install 64-bit libraries
        # Prefer x64 folder if present, otherwise general lib folder
        lib_folder = None
        for root, dirs, files in os.walk(tmp_dir):
            if "x64" in root.lower() and any(f.endswith(".a") for f in files):
                lib_folder = root
                break
        if not lib_folder:
            for root, dirs, files in os.walk(tmp_dir):
                if any(f.endswith(".a") for f in files):
                    lib_folder = root
                    break

        if lib_folder:
            for file in os.listdir(lib_folder):
                if file.endswith((".a", ".lib")):
                    src = os.path.join(lib_folder, file)
                    for dest in lib_dirs:
                        shutil.copy2(src, os.path.join(dest, file))
                    # Ensure canonical 'libfreeglut.a' always exists
                    if "freeglut" in file.lower():
                        for dest in lib_dirs:
                            shutil.copy2(src, os.path.join(dest, "libfreeglut.a"))
            log_ok("Installed FreeGLUT static and import libraries.")

        # 3. Install runtime DLL
        dll_found = False
        for root, dirs, files in os.walk(tmp_dir):
            # Prefer 64-bit DLL
            if "x64" in root.lower() and any(f.endswith(".dll") for f in files):
                for f in files:
                    if f.endswith(".dll"):
                        src = os.path.join(root, f)
                        # Copy as both freeglut.dll and libfreeglut.dll for universal compatibility
                        shutil.copy2(src, os.path.join(bin_dir, "freeglut.dll"))
                        shutil.copy2(src, os.path.join(bin_dir, "libfreeglut.dll"))
                        dll_found = True
                break

        if not dll_found:
            for root, dirs, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith(".dll") and "freeglut" in f.lower():
                        src = os.path.join(root, f)
                        shutil.copy2(src, os.path.join(bin_dir, "freeglut.dll"))
                        shutil.copy2(src, os.path.join(bin_dir, "libfreeglut.dll"))
                        dll_found = True
                        break

        if dll_found:
            log_ok(f"Installed runtime DLLs (freeglut.dll & libfreeglut.dll) to: {bin_dir}")
        else:
            log_warn("Could not locate freeglut DLL in archive.")

    return True

# ==========================================================================
#  PATH MANAGEMENT & VERIFICATION
# ==========================================================================

def update_path(mingw_bin):
    norm_bin = os.path.normpath(mingw_bin).lower()
    cur_path = os.environ.get("PATH", "")

    if any(os.path.normpath(p).lower() == norm_bin for p in cur_path.split(os.pathsep)):
        log_ok(f"Already in active PATH: {mingw_bin}")
        return True

    os.environ["PATH"] = mingw_bin + os.pathsep + cur_path

    if not _WINREG_AVAILABLE:
        return False

    hive = winreg.HKEY_LOCAL_MACHINE if is_admin() else winreg.HKEY_CURRENT_USER
    sub = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment" if is_admin() else r"Environment"

    try:
        with winreg.OpenKey(hive, sub, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                reg_path, ptype = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                reg_path, ptype = "", winreg.REG_EXPAND_SZ

            parts = [p.strip() for p in reg_path.split(";") if p.strip()]
            if not any(os.path.normpath(p).lower() == norm_bin for p in parts):
                parts.append(mingw_bin)
                winreg.SetValueEx(key, "Path", 0, ptype, ";".join(parts))
                scope = "SYSTEM" if is_admin() else "USER"
                log_ok(f"Permanently registered in {scope} PATH.")

                try:
                    ctypes.windll.user32.SendMessageTimeoutW(
                        0xFFFF, 0x001A, 0, "Environment", 0x0002, 3000, ctypes.byref(ctypes.c_long())
                    )
                except Exception:
                    pass
                return True
    except Exception as e:
        log_warn(f"Could not write to registry PATH: {e}")

    return True

def verify_setup(mingw_root):
    log_info("Testing compilation and runtime DLL execution...")
    gpp = os.path.join(mingw_root, "bin", "g++.exe")
    if not os.path.isfile(gpp):
        log_err("g++.exe not found.")
        return False

    code = """
    #include <GL/glut.h>
    #include <iostream>
    int main(int argc, char** argv) {
        glutInit(&argc, argv);
        std::cout << "FREEGLUT_VERIFIED_SUCCESS" << std::endl;
        return 0;
    }
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        src = os.path.join(tmp_dir, "test.cpp")
        exe = os.path.join(tmp_dir, "test.exe")
        with open(src, "w") as f:
            f.write(code)

        env = os.environ.copy()
        env["PATH"] = os.path.join(mingw_root, "bin") + os.pathsep + env.get("PATH", "")

        res = subprocess.run([gpp, src, "-o", exe, "-lfreeglut", "-lopengl32", "-lglu32"],
                             capture_output=True, text=True, env=env)
        if res.returncode != 0:
            log_err("Compilation failed:")
            print(res.stderr)
            return False

        log_ok("Compilation & linking passed (-lfreeglut -lopengl32 -lglu32).")

        try:
            run_res = subprocess.run([exe], capture_output=True, text=True, env=env, timeout=10)
            if "FREEGLUT_VERIFIED_SUCCESS" in run_res.stdout:
                log_ok("Runtime test passed! (DLL loaded and initialized successfully).")
                return True
            else:
                log_err(f"Runtime failed: {run_res.stderr}")
                return False
        except Exception as e:
            log_err(f"Execution test failed: {e}")
            return False

# ==========================================================================
#  MAIN ENTRY
# ==========================================================================

def main():
    enable_ansi()
    print(f"""
{Colors.BOLD}{Colors.CYAN}
  +================================================================+
  |    Automated OpenGL (FreeGLUT) & MinGW Setup for Windows       |
  |              [With Live Progress & ETA Tracking]               |
  +================================================================+
{Colors.RESET}""")

    total_steps = 4

    # Step 1: Detect
    log_step(1, total_steps, "Scanning System for Existing Installations")
    installs = find_existing_mingw()
    selected_mingw = None

    if installs:
        log_ok(f"Found existing MinGW installation(s):")
        for inst in installs:
            has_glut = check_freeglut_installed(inst)
            tag = f"{Colors.GREEN}(FreeGLUT ready){Colors.RESET}" if has_glut else f"{Colors.YELLOW}(FreeGLUT missing){Colors.RESET}"
            print(f"    - {inst} {tag}")
        selected_mingw = installs[0]
        log_info(f"Targeting: {selected_mingw}")
    else:
        log_warn("No MinGW compiler detected.")

    # Step 2: MinGW
    log_step(2, total_steps, "MinGW-w64 Deployment")
    if not selected_mingw:
        selected_mingw = install_mingw(DEFAULT_MINGW_DIR)
        if not selected_mingw:
            return 1
    else:
        log_ok(f"Using existing compiler at: {selected_mingw}")

    # Step 3: FreeGLUT
    log_step(3, total_steps, "FreeGLUT Deployment")
    if check_freeglut_installed(selected_mingw):
        log_ok("FreeGLUT is already fully configured.")
    else:
        if not install_freeglut(selected_mingw):
            return 1
        log_ok("FreeGLUT successfully configured.")

    # Step 4: PATH & Verify
    log_step(4, total_steps, "Configuring PATH & Verifying Setup")
    bin_path = os.path.join(selected_mingw, "bin")
    update_path(bin_path)

    if verify_setup(selected_mingw):
        print(f"\n{Colors.BOLD}{Colors.GREEN}"
              f"  =========================================================\n"
              f"                SETUP COMPLETED SUCCESSFULLY!              \n"
              f"  ========================================================={Colors.RESET}\n")
        print(f"  MinGW Location : {Colors.GREEN}{selected_mingw}{Colors.RESET}")
        print(f"  Headers        : {Colors.GREEN}{os.path.join(selected_mingw, 'include', 'GL', 'glut.h')}{Colors.RESET}")
        print(f"  FreeGLUT DLL   : {Colors.GREEN}{os.path.join(bin_path, 'freeglut.dll')}{Colors.RESET}\n")

        print(f"  {Colors.BOLD}How to compile your OpenGL assignments:{Colors.RESET}")
        print(f"  {Colors.CYAN}g++ ass2_opengl.cpp -o ass2.exe -lfreeglut -lopengl32 -lglu32{Colors.RESET}\n")
        print(f"  {Colors.DIM}(Please restart your terminal/CMD so the new PATH takes effect){Colors.RESET}\n")
        return 0
    else:
        log_err("Verification check failed.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[CANCELLED] Setup cancelled by user.")
        sys.exit(130)
