import os
import sys
import subprocess
import argparse
import shutil
import platform
import re

# --- Auto-configure PATH ---
BASE_PATH = os.path.dirname(__file__)
TOOLCHAIN_BIN = os.path.abspath(os.path.join(BASE_PATH, "oss-cad-suite", "bin"))
TOOLCHAIN_LIB = os.path.abspath(os.path.join(BASE_PATH, "oss-cad-suite", "lib"))

# Prepend BOTH bin and lib to the PATH
paths_to_add = []
if os.path.exists(TOOLCHAIN_BIN):
    paths_to_add.append(TOOLCHAIN_BIN)
if os.path.exists(TOOLCHAIN_LIB):
    paths_to_add.append(TOOLCHAIN_LIB)

if paths_to_add:
    new_paths = os.pathsep.join(paths_to_add)
    os.environ["PATH"] = new_paths + os.pathsep + os.environ["PATH"]

# --- Configuration ---
TOP_MODULE = "fpmul"
RTL_SOURCES = ["fpmul.v"] 
TESTBENCH = "fpmul_stim1_new.v"
TB_MODULE = "fpmul_stim1_v_tf" # Top module name inside the testbench file
SYN_OUTPUT = "fpmul_syn.v"

IS_WINDOWS = platform.system() == "Windows"
EXE_EXT = ".exe" if IS_WINDOWS else ""

# Tool definitions
YOSYS = "yosys" + EXE_EXT
YOSYS_CONFIG = "yosys-config" 
IVERILOG = "iverilog" + EXE_EXT
VVP = "vvp" + EXE_EXT
VERILATOR = "verilator" + EXE_EXT
VERILATOR_COVERAGE = "verilator_coverage" + EXE_EXT
GENHTML = "genhtml" + ("" if not IS_WINDOWS else ".perl")

RTL_EXE = "simrtl"
GATES_EXE = "simgates"

def run_command(cmd, capture_output=False, allow_fail=False):
    """
    Runs a command. 
    If allow_fail=True, it raises the exception to the caller instead of exiting.
    """
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            text=True, 
            capture_output=capture_output,
            shell=False 
        )
        return result.stdout.strip() if capture_output else None
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # If the caller wants to handle the error (e.g. try a fallback), re-raise it.
        if allow_fail:
            raise e

        # Otherwise, print a helpful error and kill the script.
        print(f"\n[ERROR] Command failed: {' '.join(cmd)}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Return Code: {e.returncode}")
            if e.returncode == -1073741515:
                print("-> Diagnosis: Missing DLLs (0xC0000135).")
        elif isinstance(e, FileNotFoundError):
             print(f"-> Diagnosis: Command not found in PATH.")
             
        if capture_output and hasattr(e, 'stderr') and e.stderr:
            print("Error Output:")
            print(e.stderr)
        sys.exit(1)

def get_yosys_datdir():
    """Finds the Yosys data directory dynamically."""
    print("[...] Finding Yosys data directory...")
    
    # 1. First, try the standard relative path for OSS CAD Suite (Robust on Windows)
    # This avoids calling the 'yosys-config' script which fails on Windows.
    fallback = os.path.abspath(os.path.join(TOOLCHAIN_BIN, "..", "share", "yosys"))
    if os.path.exists(fallback):
        return fallback

    # 2. If that fails, try asking the tool (works better on Linux/macOS)
    try:
        datdir = run_command([YOSYS_CONFIG, "--datdir"], capture_output=True, allow_fail=True)
        return datdir
    except Exception:
        print(f"[ERROR] Could not determine Yosys data directory.")
        print(f"Checked relative path: {fallback}")
        print(f"Tried command: {YOSYS_CONFIG} --datdir")
        sys.exit(1)

def clean():
    print("--- Cleaning ---")
    files_to_remove = [RTL_EXE, GATES_EXE, SYN_OUTPUT, "synthesis_successful", "coverage.dat", "coverage.info"]
    files_to_remove.extend([f"{RTL_EXE}.exe", f"{GATES_EXE}.exe"]) 
    
    # 1. Remove individual files in root
    for filename in files_to_remove:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Removed {filename}")
            
    # 2. Remove folders that should be fully deleted
    dirs_to_remove = ["coverage_report"]
    for dirname in dirs_to_remove:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
            print(f"Removed directory {dirname}")

    # 3. Clean obj_dir but PRESERVE .hello
    if os.path.exists("obj_dir"):
        print("Cleaning obj_dir (preserving .hello)...")
        for item in os.listdir("obj_dir"):
            if item == ".hello":
                continue  # Skip the placeholder
            
            item_path = os.path.join("obj_dir", item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path) # Delete file
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path) # Delete directory
            except Exception as e:
                print(f"Failed to delete {item_path}: {e}")

def synthesize():
    print("--- Synthesizing ---")
    
    # 1. Run Yosys
    yosys_cmd = [
        YOSYS, 
        "-p", 
        f"read_verilog {TOP_MODULE}.v; synth -top {TOP_MODULE} -flatten; abc -g gates; opt_clean; rename -hide */w:*; write_verilog -noattr {SYN_OUTPUT}"
    ]
    run_command(yosys_cmd)
    
    # 2. Append simlib.v
    datdir = get_yosys_datdir()
    simlib_path = os.path.join(datdir, "simlib.v")
    
    if not os.path.exists(simlib_path):
        print(f"Error: Simulation library not found at {simlib_path}")
        sys.exit(1)

    print(f"Appending {simlib_path} to {SYN_OUTPUT}...")
    try:
        with open(SYN_OUTPUT, "a") as outfile:
            with open(simlib_path, "r") as infile:
                outfile.write("\n// Appended simlib.v \n")
                shutil.copyfileobj(infile, outfile)
    except IOError as e:
        print(f"Error appending library file: {e}")
        sys.exit(1)

def sim_rtl():
    print("--- RTL Simulation ---")
    cmd_compile = [IVERILOG, "-o", RTL_EXE, TESTBENCH] + RTL_SOURCES
    run_command(cmd_compile)
    cmd_run = [VVP, RTL_EXE]
    run_command(cmd_run)

def sim_rtl_coverage():
    print("--- RTL Coverage (Verilator) ---")
    
    # 1. Compile (Instrument for Coverage)
    # verilator --binary --coverage config.vlt fpmul.v fpmul_stim1_new.v --top-module fpmul_stim1_v_tf
    cmd_verilate = [
        VERILATOR,
        "--binary",
        "--coverage"
    ]
    
    # Conditionally add config.vlt if it exists
    if os.path.exists("config.vlt"):
        cmd_verilate.append("config.vlt")
    
    cmd_verilate.extend(RTL_SOURCES)
    cmd_verilate.extend([TESTBENCH, "--top-module", TB_MODULE])
    
    print(f"Running Verilator compilation...")
    run_command(cmd_verilate)
    
    # 2. Run Simulation
    # ./obj_dir/V[TB_MODULE]
    binary_name = f"V{TB_MODULE}" + EXE_EXT
    binary_path = os.path.join("obj_dir", binary_name)
    
    print(f"Running simulation binary: {binary_path}...")
    run_command([binary_path])
    
    # 3. Generate Report Info
    # verilator_coverage --write-info coverage.info coverage.dat
    print("Generating coverage info...")
    run_command([VERILATOR_COVERAGE, "--write-info", "coverage.info", "coverage.dat"])
    
    # 4. View Results (Annotated Source in obj_dir)
    # verilator_coverage --annotate-points --annotate obj_dir coverage.dat
    print("Generating annotated source code in obj_dir/...")
    run_command([VERILATOR_COVERAGE, "--annotate-points", "--annotate", "obj_dir", "coverage.dat"])

    # 5. Parse annotated file for statistics
    # Target file: obj_dir/fpmul.v (derived from TOP_MODULE)
    annotated_file = os.path.join("obj_dir", f"{TOP_MODULE}.v")
    
    if os.path.exists(annotated_file):
        try:
            with open(annotated_file, "r") as f:
                lines = f.readlines()

            num_positive = 0
            num_total_neg = 0
            num_real_neg = 0

            # Regex patterns matching grep
            # Matches lines starting with +xxxxxx (e.g. +000012)
            re_pos = re.compile(r"^\+[0-9]{6}")    
            # Matches lines starting with -xxxxxx (e.g. -000000 or -000005)
            re_total_neg = re.compile(r"^-[0-9]{6}") 
            # Matches lines specifically starting with -000000
            re_real_neg = re.compile(r"^-000000")   

            for line in lines:
                if re_pos.match(line):
                    num_positive += 1
                
                # Note: -000000 matches both "total_neg" and "real_neg" logic
                if re_total_neg.match(line):
                    num_total_neg += 1
                if re_real_neg.match(line):
                    num_real_neg += 1

            # Calculate Percentage
            denominator = num_total_neg + num_positive
            percent_miss = (num_real_neg / denominator) if denominator > 0 else 0.0
            percent_coverage = (1 - percent_miss) * 100

            print("-" * 30)
            print(f"num_positive: {num_positive}")
            print(f"num_total_neg: {num_total_neg}")
            print(f"num_real_neg: {num_real_neg}")
            print(f"percent_coverage: {percent_coverage:.4f}%")
            print("-" * 30)

        except Exception as e:
            print(f"[WARN] Failed to calculate coverage stats: {e}")
    else:
        print(f"[WARN] Annotated file not found: {annotated_file}")

def sim_gates():
    if not os.path.exists(SYN_OUTPUT):
        synthesize()
    print("--- Gate Simulation ---")
    cmd_compile = [IVERILOG, "-o", GATES_EXE, TESTBENCH, SYN_OUTPUT]
    run_command(cmd_compile)
    cmd_run = [VVP, GATES_EXE]
    run_command(cmd_run)

def main():
    parser = argparse.ArgumentParser(description="Build and Simulate FPMul")
    parser.add_argument("target", nargs="?", choices=["clean", "syn", "simrtl", "simgates", "rtlCoverage"], help="Build target")
    args = parser.parse_args()

    if args.target is None:
        print("Usage: python manage.py [command]")
        print("\nAvailable commands:")
        print("  clean       : Remove generated files")
        print("  syn         : Run Yosys synthesis (creates fpmul_syn.v)")
        print("  simrtl      : Run RTL simulation (uses fpmul.v)")
        print("  simgates    : Run Gate-level simulation (uses fpmul_syn.v)")
        print("  rtlCoverage : Run Verilator coverage flow (generates annotated source in obj_dir)")
        sys.exit(0)

    if args.target == "clean": clean()
    elif args.target == "syn": synthesize()
    elif args.target == "simrtl": sim_rtl()
    elif args.target == "simgates": sim_gates()
    elif args.target == "rtlCoverage": sim_rtl_coverage()

if __name__ == "__main__":
    main()
