#!/usr/bin/env python3
"""
===============================================================================
  Automated OpenGL (FreeGLUT) & MinGW Setup (Auto 32-bit / 64-bit Aware)
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

if sys.platform != "win32":
    print("\n[ERROR] This script must be run on Windows.")
    sys.exit(1)

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False

DEFAULT_MINGW_DIR = r"C:\MinGW"

# FreeGLUT MinGW package (contains both 32-bit and 64-bit builds)
FREEGLUT_URLS = [
    "https://www.songho.ca/opengl/files/freeglut-mingw-3.8.0.zip",
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

def get_compiler_arch(mingw_root):
    """Detects whether the installed GCC is 32-bit (x86) or 64-bit (x64)."""
    gcc = os.path.join(mingw_root, "bin", "gcc.exe")
    if not os.path.isfile(gcc):
        return "x86"
    try:
        out = subprocess.check_output([gcc, "-dumpmachine"], text=True, timeout=5).strip().lower()
        if "64" in out:
            return "x64"
        else:
            return "x86"
    except Exception:
        return "x86"

# ==========================================================================
#  PROGRESS BAR RENDERER
# ==========================================================================

def render_progress(current, total, start_time, prefix="[PROG]", unit="MB", bar_len=24):
    elapsed = max(time.time() - start_time, 0.001)
    fraction = min(max(current / total, 0.0), 1.0) if total > 0 else 0
    pct = int(fraction * 100)
    filled = int(bar_len * fraction)
    bar = "█" * filled + "░" * (bar_len - filled)
    speed = current / elapsed
    remaining = (total - current) / speed if speed > 0 else 0

    eta_str = f"{int(remaining)}s" if remaining < 60 else f"{int(remaining//60)}m {int(remaining%60):02d}s"

    if unit == "MB":
        cur_mb = current / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        spd_mb = speed / (1024 * 1024)
        status = f"{cur_mb:.1f}/{tot_mb:.1f} MB | {spd_mb:.1f} MB/s"
    else:
        status = f"{current}/{total} {unit} | {int(speed)} {unit}/s"

    print(f"\r  {Colors.CYAN}{prefix}{Colors.RESET} [{Colors.GREEN}{bar}{Colors.RESET}] {pct:3d}% | {status} | ETA: {Colors.YELLOW}{eta_str}{Colors.RESET}  ", end="", flush=True)

def download_file_with_progress(urls, dest_path, desc):
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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
    return False

# ==========================================================================
#  INSTALLATION ROUTINE (ARCH-AWARE)
# ==========================================================================

def find_existing_mingw():
    candidates = []
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        path_dir = path_dir.strip().strip('"')
        if os.path.isfile(os.path.join(path_dir, "gcc.exe")):
            root = os.path.dirname(os.path.normpath(path_dir))
            if root not in candidates:
                candidates.append(root)

    for loc in [r"C:\MinGW", r"C:\mingw64", r"C:\mingw32", r"C:\msys64\mingw64", r"C:\msys64\ucrt64"]:
        if os.path.isfile(os.path.join(loc, "bin", "gcc.exe")) and loc not in candidates:
            candidates.append(loc)
    return candidates

def install_freeglut(mingw_root, arch):
    log_info(f"Deploying FreeGLUT for {Colors.BOLD}{arch.upper()}{Colors.RESET} MinGW architecture...")

    # Include directories
    inc_dirs = [
        os.path.join(mingw_root, "include", "GL"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "include", "GL"),
        os.path.join(mingw_root, "i686-w64-mingw32", "include", "GL"),
        os.path.join(mingw_root, "mingw32", "include", "GL"),
    ]
    # Library directories
    lib_dirs = [
        os.path.join(mingw_root, "lib"),
        os.path.join(mingw_root, "x86_64-w64-mingw32", "lib"),
        os.path.join(mingw_root, "i686-w64-mingw32", "lib"),
        os.path.join(mingw_root, "mingw32", "lib"),
    ]
    bin_dir = os.path.join(mingw_root, "bin")

    # Only create existing / valid directories
    valid_inc = [d for d in inc_dirs if os.path.isdir(os.path.dirname(d)) or d == inc_dirs[0]]
    valid_lib = [d for d in lib_dirs if os.path.isdir(d) or d == lib_dirs[0]]
    for d in valid_inc + valid_lib + [bin_dir]:
        os.makedirs(d, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        fg_zip = os.path.join(tmp_dir, "freeglut.zip")
        if not download_file_with_progress(FREEGLUT_URLS, fg_zip, "FreeGLUT Package (~1 MB)"):
            return False

        with zipfile.ZipFile(fg_zip, "r") as zf:
            zf.extractall(tmp_dir)

        # 1. Install headers
        for root, dirs, files in os.walk(tmp_dir):
            if any(h in files for h in ["glut.h", "freeglut.h"]):
                for file in files:
                    if file.endswith(".h"):
                        src = os.path.join(root, file)
                        for dest in valid_inc:
                            shutil.copy2(src, os.path.join(dest, file))
                break
        log_ok("Headers copied (GL/glut.h, GL/freeglut.h).")

        # 2. Select matching library folder based on detected architecture
        lib_folder = None
        if arch == "x64":
            for root, dirs, files in os.walk(tmp_dir):
                if "x64" in root.lower() and any(f.endswith(".a") for f in files):
                    lib_folder = root
                    break
        else:
            # 32-bit (x86): Pick the 'lib' folder that does NOT have x64 in its path
            for root, dirs, files in os.walk(tmp_dir):
                if "lib" in root.lower() and "x64" not in root.lower() and any(f.endswith(".a") for f in files):
                    lib_folder = root
                    break

        if lib_folder:
            for file in os.listdir(lib_folder):
                if file.endswith((".a", ".lib")):
                    src = os.path.join(lib_folder, file)
                    for dest in valid_lib:
                        shutil.copy2(src, os.path.join(dest, file))
                    if "freeglut" in file.lower():
                        for dest in valid_lib:
                            # Create both libfreeglut.a and libfreeglut.dll.a
                            shutil.copy2(src, os.path.join(dest, "libfreeglut.a"))
                            shutil.copy2(src, os.path.join(dest, "libfreeglut.dll.a"))
            log_ok(f"Installed {arch.upper()} static & import libraries.")

        # 3. Select matching DLL based on detected architecture
        dll_folder = None
        if arch == "x64":
            for root, dirs, files in os.walk(tmp_dir):
                if "x64" in root.lower() and any(f.endswith(".dll") for f in files):
                    dll_folder = root
                    break
        else:
            # 32-bit (x86): Pick the 'bin' folder that does NOT have x64 in its path
            for root, dirs, files in os.walk(tmp_dir):
                if "bin" in root.lower() and "x64" not in root.lower() and any(f.endswith(".dll") for f in files):
                    dll_folder = root
                    break

        if dll_folder:
            for f in os.listdir(dll_folder):
                if f.endswith(".dll") and "freeglut" in f.lower():
                    src = os.path.join(dll_folder, f)
                    shutil.copy2(src, os.path.join(bin_dir, "freeglut.dll"))
                    shutil.copy2(src, os.path.join(bin_dir, "libfreeglut.dll"))
            log_ok(f"Installed {arch.upper()} runtime DLLs to: {bin_dir}")

    return True

# ==========================================================================
#  VERIFICATION
# ==========================================================================

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

        cmd = [gpp, src, "-o", exe, "-lfreeglut", "-lopengl32", "-lglu32"]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
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
    if not installs:
        log_err("No MinGW compiler found. Please ensure MinGW is at C:\\MinGW.")
        return 1

    selected_mingw = installs[0]
    arch = get_compiler_arch(selected_mingw)
    log_ok(f"Using compiler at: {selected_mingw}")
    log_info(f"Detected Compiler Architecture: {Colors.BOLD}{arch.upper()}{Colors.RESET} ({'32-bit' if arch == 'x86' else '64-bit'})")

    # Step 2: Confirmation
    log_step(2, total_steps, "Target Verification")
    log_ok(f"Targeting {arch.upper()} environment in {selected_mingw}")

    # Step 3: FreeGLUT
    log_step(3, total_steps, "FreeGLUT Deployment")
    if not install_freeglut(selected_mingw, arch):
        log_err("FreeGLUT installation failed.")
        return 1
    log_ok("FreeGLUT successfully configured.")

    # Step 4: Verification
    log_step(4, total_steps, "Verifying Setup")
    if verify_setup(selected_mingw):
        print(f"\n{Colors.BOLD}{Colors.GREEN}"
              f"  =========================================================\n"
              f"                SETUP COMPLETED SUCCESSFULLY!              \n"
              f"  ========================================================={Colors.RESET}\n")
        print(f"  Architecture   : {Colors.GREEN}{arch.upper()} ({'32-bit' if arch == 'x86' else '64-bit'}){Colors.RESET}")
        print(f"  MinGW Location : {Colors.GREEN}{selected_mingw}{Colors.RESET}")
        print(f"  Headers        : {Colors.GREEN}{os.path.join(selected_mingw, 'include', 'GL', 'glut.h')}{Colors.RESET}")
        print(f"  FreeGLUT DLL   : {Colors.GREEN}{os.path.join(selected_mingw, 'bin', 'freeglut.dll')}{Colors.RESET}\n")

        print(f"  {Colors.BOLD}How to compile your OpenGL assignments:{Colors.RESET}")
        print(f"  {Colors.CYAN}g++ ass2_opengl.cpp -o ass2.exe -lfreeglut -lopengl32 -lglu32{Colors.RESET}\n")
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
