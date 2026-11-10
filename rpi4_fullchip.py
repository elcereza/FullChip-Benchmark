#!/usr/bin/env python3
"""Raspberry Pi 4 full-chip thermal benchmark v1.3, EGL surfaceless headless."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

STAGES = ["cpu_single", "cpu_multi", "gpu_3d", "cpu_gpu", "cpu_gpu_ram"]
GPU_STAGES = {"gpu_3d", "cpu_gpu", "cpu_gpu_ram"}
CSV_COLS = ["timestamp_iso", "unix_s", "elapsed_s", "label", "freq_target_mhz",
 "stage", "phase", "temperature_c", "cpu_util_pct", "cpu_freq_mhz",
 "gpu_v3d_clock_mhz", "throttled_hex", "undervoltage_now", "freq_capped_now",
 "throttling_now", "softtemp_now", "undervoltage_ever", "throttling_ever",
 "load1", "mem_available_mib", "cpu_limit_max_mhz", "cpu_limit_min_mhz", "stress_process_alive", "gpu_process_alive"]
STOP_REQUESTED = False

def signal_handler(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True

for signum in (signal.SIGINT, signal.SIGTERM):
    signal.signal(signum, signal_handler)


def ts():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")


def command_output(argv, timeout=3):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def textfile(path, default=""):
    try:
        return Path(path).read_text().strip("\x00\n ")
    except OSError:
        return default


def temp_c():
    raw = textfile("/sys/class/thermal/thermal_zone0/temp")
    if raw:
        try:
            n = float(raw)
            return round(n / 1000 if n > 1000 else n, 3)
        except ValueError:
            pass
    raw = command_output(["vcgencmd", "measure_temp"])
    m = re.search(r"(-?\d+(?:\.\d+)?)", raw)
    return float(m.group(1)) if m else None


def cpu_clock_mhz():
    raw = textfile("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    if raw.isdigit():
        return round(int(raw) / 1000, 2)
    raw = command_output(["vcgencmd", "measure_clock", "arm"])
    m = re.search(r"=(\d+)", raw)
    return round(int(m.group(1)) / 1e6, 2) if m else None


def v3d_clock_mhz():
    raw = command_output(["vcgencmd", "measure_clock", "v3d"])
    m = re.search(r"=(\d+)", raw)
    return round(int(m.group(1)) / 1e6, 2) if m else None


def throttle_mask():
    raw = command_output(["vcgencmd", "get_throttled"])
    m = re.search(r"0x[0-9a-fA-F]+", raw)
    return int(m.group(0), 16) if m else None


def proc_cpu():
    try:
        nums = list(map(int, Path("/proc/stat").read_text().splitlines()[0].split()[1:]))
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
        return sum(nums), idle
    except (OSError, ValueError, IndexError):
        return None


def mem_available_mib():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    return None


def gpu_hw_renderer(text):
    lower = text.lower()
    renderers = re.findall(r"(?:gl_renderer|opengl renderer string)\s*:\s*([^\n\r]+)", text, re.I)
    if not renderers:
        return False, "GL_RENDERER ausente"
    renderer = renderers[0].strip()
    if re.search(r"llvmpipe|softpipe|swrast|software rasterizer", renderer, re.I):
        return False, "renderizacao por software: " + renderer
    if re.search(r"v3d|videocore|vc4", renderer, re.I):
        return True, renderer
    return False, "renderizador nao comprovado: " + renderer


def maxfreq_path():
    paths = [Path("/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"),
             Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq")]
    for p in paths:
        if p.exists():
            return p
    return None


def cpufreq_state(path):
    """Snapshot of kernel policy. scaling_cur_freq is not the maximum cap."""
    root = path.parent
    return {key: textfile(root / key) for key in (
        "scaling_min_freq", "scaling_max_freq", "scaling_cur_freq",
        "cpuinfo_min_freq", "cpuinfo_max_freq", "scaling_governor",
        "scaling_available_frequencies")}


def set_max_cpufreq(path, target_khz):
    """Apply a cap and validate kernel readback. Never raise CPU max above CPU limits."""
    root = path.parent
    minimum = root / "scaling_min_freq"
    before = cpufreq_state(path)
    changes = []
    try:
        cpuinfo_max = int(before.get("cpuinfo_max_freq") or 0)
        if not cpuinfo_max or target_khz > cpuinfo_max:
            return False, {"error": "target_above_cpuinfo_max", "before": before}
        current_min = int(before.get("scaling_min_freq") or 0)
        if current_min > target_khz:
            # A max lower than the current minimum may be silently clamped.
            safe_min = min(target_khz, int(before.get("cpuinfo_min_freq") or target_khz))
            minimum.write_text(str(safe_min))
            changes.append({"set_scaling_min_freq": safe_min})
        path.write_text(str(target_khz))
        changes.append({"set_scaling_max_freq": target_khz})
        # A different clock policy manager may race or override our writes.
        seen = []
        for delay in (0.1, 0.35, 0.75):
            time.sleep(delay)
            state = cpufreq_state(path)
            seen.append(state)
            if int(state.get("scaling_max_freq") or 0) != target_khz:
                continue
            # Require cap to persist at least another 0.5 s.
            time.sleep(0.5)
            final = cpufreq_state(path)
            seen.append(final)
            if int(final.get("scaling_max_freq") or 0) == target_khz:
                return True, {"before": before, "changes": changes, "after": final}
        return False, {"error": "kernel_or_other_service_rejected_max", "before": before,
                       "changes": changes, "readbacks": seen}
    except (OSError, ValueError) as e:
        return False, {"error": repr(e), "before": before, "changes": changes,
                       "after": cpufreq_state(path)}


def restore_cpufreq(path, original_min, original_max):
    """Restore both limits, adjusting them in a safe order."""
    if path is None or original_max is None:
        return False
    minimum = path.parent / "scaling_min_freq"
    for _ in range(3):
        try:
            now_min = int(textfile(minimum, "0") or "0")
            if now_min > original_max:
                minimum.write_text(str(original_max))
            path.write_text(str(original_max))
            if original_min is not None:
                minimum.write_text(str(original_min))
            time.sleep(0.25)
            good_max = int(path.read_text()) == original_max
            good_min = original_min is None or int(minimum.read_text()) == original_min
            if good_max and good_min:
                return True
        except (OSError, ValueError) as e:
            print("AVISO: tentativa de restauracao cpufreq:",e,file=sys.stderr)
        time.sleep(0.3)
    return False


def preflight(args):
    model = textfile("/proc/device-tree/model")
    problems = []
    if "Raspberry Pi 4" not in model:
        problems.append("Modelo nao confirmado como Raspberry Pi 4: " + repr(model))
    if os.geteuid() != 0 and not args.dry_run:
        problems.append("Execute com sudo para configurar limite temporario de clock")
    if not shutil.which("stress-ng"):
        problems.append("Falta stress-ng (sudo apt install stress-ng)")
    if not shutil.which(args.gpu_bin) and not args.headless_gpu_bin.is_file():
        problems.append(f"GPU: faltam {args.gpu_bin} e gpu_headless_v3d. Execute instalar_dependencias.sh")
    p = maxfreq_path()
    if not p:
        problems.append("cpufreq sysfs nao encontrado")
    current = int(p.read_text()) if p else None
    policy = p.parent if p else None
    cpuinfo_max = int(textfile(policy / "cpuinfo_max_freq", "0") or "0") if policy else 0
    if current:
        for f in args.freqs:
            if f * 1000 > current:
                problems.append(f"{f} MHz excede limite existente de {current/1000:.0f} MHz; nao faremos overclock")
    print("=== PRE-FLIGHT ===")
    print("Modelo:", model)
    print("Kernel:", command_output(["uname", "-r"]))
    print("MemTotal:", next((s.strip() for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemTotal:")), "?"))
    print("Clock max configurado:", current / 1000 if current else "?", "MHz")
    print("Clock max suportado pelo driver:", cpuinfo_max / 1000 if cpuinfo_max else "?", "MHz")
    print("GPU bin:", args.gpu_bin)
    print("GPU devices:", ", ".join(str(x) for x in Path("/dev/dri").glob("*")) or "nenhum")
    print("DRM drivers:", command_output(["sh", "-c", "lsmod | grep -E '^(v3d|vc4) ' || true"]))
    print("Temperatura:", temp_c(), "C")
    print("Throttled:", hex(throttle_mask() or 0))
    for s in problems:
        print("ERRO:", s)
    return not problems, current, model


def gpu_command(args, smoke=False):
    dur = 3 if smoke else 20
    return (["stdbuf", "-oL", "-eL"] if shutil.which("stdbuf") else []) + [args.gpu_bin, "--off-screen", "--size", f"{args.gpu_width}x{args.gpu_height}",
            "--run-forever" if not smoke else "--reuse-context",
            "-b", f"shading:duration={dur}",
            "-b", f"texture:duration={dur}",
            "-b", f"build:duration={dur}"]


def gpu_smoke(args, folder):
    """Prefer true render-node GPU in headless hosts; reject software rendering."""
    logparts=[]
    if args.headless_gpu_bin.is_file() and os.access(args.headless_gpu_bin, os.X_OK):
        print("Verificando EGL/GBM surfaceless em /dev/dri/renderD*...", flush=True)
        try:
            r=subprocess.run(headless_command(args, smoke=True),capture_output=True,text=True,timeout=20)
            output=r.stdout+"\n"+r.stderr
            logparts.append("==== EGL HEADLESS V1.2 ====\n"+output)
            valid,renderer=gpu_hw_renderer(output)
            frames=re.search(r"GPU_DRAW_FRAMES:\s*(\d+)",output)
            if valid and r.returncode==0 and frames and int(frames.group(1))>0:
                (folder / "gpu_preflight.log").write_text("\n".join(logparts))
                return True,"V3D EGL headless: "+renderer,"headless"
            print(f"EGL indisponivel: {renderer} (rc={r.returncode}). Tentando DRM...",flush=True)
        except (OSError,subprocess.TimeoutExpired) as ex:
            logparts.append("==== HEADLESS: "+repr(ex)+" ====\n")
    if shutil.which(args.gpu_bin):
        print("Verificando glmark2 DRM/KMS como fallback (pode exigir monitor)...", flush=True)
        try:
            r=subprocess.run(gpu_command(args, smoke=True), capture_output=True, text=True, timeout=22)
            output=r.stdout+"\n"+r.stderr
            logparts.append("==== DRM glmark2 ====\n"+output)
            valid, renderer=gpu_hw_renderer(output)
            if valid and r.returncode==0:
                (folder / "gpu_preflight.log").write_text("\n".join(logparts))
                return True,"V3D via glmark2: "+renderer,"glmark2"
        except (OSError,subprocess.TimeoutExpired) as ex:
            logparts.append("==== DRM glmark2: "+repr(ex)+" ====\n")
    (folder / "gpu_preflight.log").write_text("\n".join(logparts))
    return False,"GPU V3D nao comprovada; examine o gpu_preflight.log",None


def headless_command(args, smoke=False):
    return [str(args.headless_gpu_bin),"--width",str(args.gpu_width),
            "--height",str(args.gpu_height),"--seconds", "3" if smoke else "0"]


def start_child(cmd, logfile):
    stream = open(logfile, "w", buffering=1)
    try:
        proc = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        return proc, stream
    except Exception:
        stream.close()
        raise


def stop_children(children):
    for p, _ in children:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 5
    for p, handle in children:
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        handle.close()


class Collector:
    def __init__(self, csv_path, label, target, writer):
        self.path = csv_path
        self.label = label
        self.target = target
        self.writer = writer
        self.prev_cpu = proc_cpu()
        self.rows = []

    def sample(self, stage, phase, elapsed, children):
        prev = self.prev_cpu
        now = proc_cpu()
        usage = None
        if prev and now and now[0] > prev[0]:
            total = now[0] - prev[0]
            idle = now[1] - prev[1]
            usage = round(100 * (total - idle) / total, 2)
        self.prev_cpu = now
        mask = throttle_mask()
        row = dict(timestamp_iso=ts(), unix_s=round(time.time(), 3),
            elapsed_s=round(elapsed, 3), label=self.label,
            freq_target_mhz=self.target, stage=stage, phase=phase,
            temperature_c=temp_c(), cpu_util_pct=usage,
            cpu_freq_mhz=cpu_clock_mhz(), gpu_v3d_clock_mhz=v3d_clock_mhz(),
            throttled_hex=hex(mask) if mask is not None else "",
            undervoltage_now=int(bool(mask & 1)) if mask is not None else "",
            freq_capped_now=int(bool(mask & 2)) if mask is not None else "",
            throttling_now=int(bool(mask & 4)) if mask is not None else "",
            softtemp_now=int(bool(mask & 8)) if mask is not None else "",
            undervoltage_ever=int(bool(mask & 0x10000)) if mask is not None else "",
            throttling_ever=int(bool(mask & 0x40000)) if mask is not None else "",
            load1=round(os.getloadavg()[0], 2), mem_available_mib=mem_available_mib(),
            cpu_limit_max_mhz=(int(textfile("/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq"))/1000
                               if textfile("/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq").isdigit() else None),
            cpu_limit_min_mhz=(int(textfile("/sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq"))/1000
                               if textfile("/sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq").isdigit() else None),
            stress_process_alive=int(any(p.poll() is None for name, p, f in children if name == "stress")),
            gpu_process_alive=int(any(p.poll() is None for name, p, f in children if name == "gpu")))
        self.writer.writerow(row)
        self.rows.append(row)
        return row


def run_period(seconds, stage, phase, collector, children, cutoff, every_display=10):
    start = time.monotonic()
    last_print = -1
    i = 0
    while time.monotonic() - start < seconds and not STOP_REQUESTED:
        elapsed = time.monotonic() - start
        row = collector.sample(stage, phase, elapsed, children)
        if i == 0 or int(elapsed) // every_display > last_print:
            last_print = int(elapsed) // every_display
            print(f" {stage:12} {phase:10} t={elapsed:5.0f}/{seconds}s "
                  f"CPU={row['temperature_c']} C  ARM={row['cpu_freq_mhz']}MHz "
                  f"uso={row['cpu_util_pct']}%  throttled={row['throttled_hex']}", flush=True)
        # Fail safe active in all phases. Persistent/historical bits deliberately not used.
        t = row["temperature_c"]
        if t is None:
            return "sensor_temperatura_indisponivel"
        if t >= cutoff:
            return "limite_termico"
        if row["undervoltage_now"] == 1:
            return "subtensao_ativa"
        # Prevent misleading thermal comparisons if another service changes CPU cap.
        if (row["cpu_limit_max_mhz"] is not None and
                abs(row["cpu_limit_max_mhz"] - collector.target) > 1):
            return "limite_cpu_alterado"
        if row["mem_available_mib"] is not None and row["mem_available_mib"] < 128:
            return "memoria_livre_abaixo_128MiB"
        if row["throttling_now"] == 1:
            return "thermal_throttling_ativo"
        if phase == "stress":
            for name, proc, handle in children:
                if proc.poll() is not None:
                    return f"processo_{name}_encerrou_antes"
        i += 1
        next_at = start + i
        time.sleep(max(0.0, min(1.1, next_at - time.monotonic())))
    return "interrompido" if STOP_REQUESTED else "ok"


def stats(rows, phase):
    sub = [r for r in rows if r["phase"] == phase]
    temps = [float(r["temperature_c"]) for r in sub if r["temperature_c"] is not None]
    freqs = [float(r["cpu_freq_mhz"]) for r in sub if r["cpu_freq_mhz"] is not None]
    usages = [float(r["cpu_util_pct"]) for r in sub if r["cpu_util_pct"] is not None]
    return dict(samples=len(sub), first_c=temps[0] if temps else None,
                last_c=temps[-1] if temps else None, max_c=max(temps) if temps else None,
                mean_c=round(statistics.mean(temps), 3) if temps else None,
                mean_arm_mhz=round(statistics.mean(freqs), 2) if freqs else None,
                mean_cpu_util_pct=round(statistics.mean(usages), 2) if usages else None,
                undervoltage_samples=sum(r["undervoltage_now"] == 1 for r in sub),
                throttling_samples=sum(r["throttling_now"] == 1 for r in sub))


def user_results_dir():
    user = os.environ.get("SUDO_USER")
    if user and user != "root":
        try:
            return Path(pwd.getpwnam(user).pw_dir) / "rpi4-fullchip-results"
        except KeyError:
            pass
    return Path.home() / "rpi4-fullchip-results"


def output_ownership(root):
    try:
        uid = int(os.environ["SUDO_UID"])
        gid = int(os.environ["SUDO_GID"])
    except (KeyError, ValueError):
        return
    for p in [root] + list(root.rglob("*")):
        try:
            os.chown(p, uid, gid)
        except OSError:
            pass


def run(args):
    ready, original_max, model = preflight(args)
    if not ready:
        return 2
    if args.dry_run:
        print("DRY-RUN: nenhuma frequencia ou hardware foi alterado")
        return 0
    root = args.output or user_results_dir()
    folder = Path(root).expanduser() / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + re.sub("[^A-Za-z0-9_-]", "-", args.label))
    folder.mkdir(parents=True, exist_ok=False)
    notes = {"model":model, "label":args.label, "timestamp":ts(),
      "os":textfile("/etc/os-release"), "kernel":command_output(["uname","-a"]),
      "original_cpufreq_max_khz": original_max,
      "original_cpufreq_min_khz": int(textfile(maxfreq_path().parent / "scaling_min_freq", "0")),
      "freqs_mhz":args.freqs,
      "durations_s":dict(rest=args.rest_sec, stress=args.stress_sec, cool=args.cool_sec),
      "stop_temp_c":args.temp_stop, "gpu_bin":args.gpu_bin,
      "gpu_resolution":f"{args.gpu_width}x{args.gpu_height}",
      "ambient_c_optional":args.ambient_c, "fan_note":args.fan_note,
      "hardware_power_watts_measured":False,
      "note":"Temperatura nao determina potencia dissipada absoluta em W; GPU clock != GPU usage.",
      "stages":[], "status":"em_execucao"}
    pathfreq = maxfreq_path()
    original_min = notes["original_cpufreq_min_khz"]
    restore_ok = False
    active_children = []
    print("Resultados:", folder)
    try:
        gpu_available, gpu_detail, gpu_mode = gpu_smoke(args, folder)
        notes["gpu_validated"] = gpu_available
        notes["gpu_check_detail"] = gpu_detail
        notes["gpu_backend"] = gpu_mode
        print(gpu_detail)
        # Stages requiring GPU are skipped explicitly if no hardware renderer is confirmed.
        for target in args.freqs:
            if STOP_REQUESTED:
                break
            applied, details = set_max_cpufreq(pathfreq, target * 1000)
            if not applied:
                details.update(requested_mhz=target,
                    firmware_arm_freq=command_output(["vcgencmd", "get_config", "arm_freq"]))
                notes.setdefault("clock_rejections", []).append(details)
                print("AVISO: cpufreq nao manteve limite de",target,"MHz;",details,flush=True)
                for stage in args.stages:
                    notes["stages"].append({"stage":stage,"freq_target_mhz":target,
                        "status":"NAO_EXECUTADO", "reason":"limite cpufreq nao confirmado"})
                # The next frequency group may still be valid (e.g. 1800 MHz).
                continue
            print("Limite de frequencia validado:", target, "MHz;",
                  "minimo atual:", details["after"].get("scaling_min_freq"), "kHz", flush=True)
            print(f"\n===== {target} MHz =====", flush=True)
            for stage in args.stages:
                if STOP_REQUESTED:
                    break
                report = {"stage":stage, "freq_target_mhz":target, "start":ts()}
                if stage in GPU_STAGES and not gpu_available:
                    report.update(status="NAO_EXECUTADO", reason="GPU 3D nao validada: " + gpu_detail)
                    notes["stages"].append(report)
                    print("PULADO:",stage,"-",report["reason"])
                    continue
                name = f"{target}MHz_{stage}"
                phase_file = folder / (name + "_amostras_1s.csv")
                print("\n---", name, "---", flush=True)
                with phase_file.open("w", newline="", buffering=1) as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLS)
                    writer.writeheader()
                    col = Collector(phase_file, args.label, target, writer)
                    idle_result = run_period(args.rest_sec, stage, "repouso", col, [], args.temp_stop)
                    report["repouso"] = stats(col.rows, "repouso")
                    if idle_result != "ok":
                        report.update(status="INTERROMPIDO",reason=idle_result)
                        notes["stages"].append(report)
                        break
                    children = []
                    active_children = children
                    try:
                        stress = []
                        if stage == "cpu_single":
                            stress = ["stress-ng", "--cpu", "1", "--cpu-method", "matrixprod", "--metrics-brief"]
                        elif stage in ("cpu_multi", "cpu_gpu", "cpu_gpu_ram"):
                            stress = ["stress-ng", "--cpu", "4", "--cpu-method", "matrixprod", "--metrics-brief"]
                        if stage == "cpu_gpu_ram":
                            available = mem_available_mib()
                            if available is None or available < 500:
                                raise RuntimeError("Memoria disponivel insuficiente/indisponivel")
                            # Bound to 20% available memory or at most 512 MiB to protect running services.
                            vm_mib = max(64, min(512, int(available * 0.20)))
                            stress += ["--vm", "1", "--vm-bytes", f"{vm_mib}M", "--vm-keep"]
                            report["vm_mib"] = vm_mib
                        if stress:
                            proc, log = start_child(stress, folder / (name+"_stress.log"))
                            children.append(("stress",proc,log))
                        if stage in GPU_STAGES:
                            proc, log = start_child(headless_command(args) if gpu_mode=="headless" else gpu_command(args), folder / (name+"_gpu.log"))
                            children.append(("gpu",proc,log))
                        result = run_period(args.stress_sec, stage, "stress", col, children, args.temp_stop)
                    except Exception as e:
                        result = "erro_execucao: " + str(e)
                    finally:
                        stop_children([(p,h) for _,p,h in children])
                        active_children = []
                    report["stress"] = stats(col.rows, "stress")
                    # Verify runtime GPU log reports hardware renderer, not only preflight.
                    if stage in GPU_STAGES:
                        g_log = folder / (name+"_gpu.log")
                        g_text = g_log.read_text(errors="replace") if g_log.exists() else ""
                        gpu_ok, actual_renderer = gpu_hw_renderer(g_text)
                        if gpu_mode=="headless":
                            # For a forcibly stopped process, renderer plus proof of frames
                            # may be buffered; line-buffered helper prints progress/renderer.
                            gpu_ok = gpu_ok and ("gpu frames=" in g_text or "GPU_DRAW_FRAMES:" in g_text)
                        report["renderer_validated"] = gpu_ok
                        report["renderer"] = actual_renderer
                        if not gpu_ok and result == "ok":
                            result = "GPU nao comprovada durante etapa: " + actual_renderer
                    report["stress_status"] = result
                    # Cooling still collected after thermal cutoff; if persistently unsafe, stop.
                    coolres = run_period(args.cool_sec, stage, "resfriamento", col, [], args.temp_stop)
                    report["resfriamento"] = stats(col.rows, "resfriamento")
                    report["cool_status"] = coolres
                    report["end"] = ts()
                    report["csv"] = phase_file.name
                    report["status"] = "OK" if result == "ok" and coolres == "ok" else "INTERROMPIDO"
                    report["reason"] = "" if report["status"] == "OK" else f"stress={result}; cooling={coolres}"
                    notes["stages"].append(report)
                    print("Resultado",name,report["status"],report["reason"],flush=True)
                    f.flush()
                (folder / "resumo.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False))
                if report["status"] != "OK":
                    if result in ("limite_termico", "subtensao_ativa", "thermal_throttling_ativo", "limite_cpu_alterado", "interrompido") or coolres != "ok" or STOP_REQUESTED:
                        print("Parando bateria de testes por seguranca/interrupcao")
                        return 3
                    # Test workload failure marks stage but allows others. Cannot accept GPU invalid as OK.
            # restore between frequency groups via next write; cooling precedes next loop.
        notes["status"] = "INTERROMPIDO" if STOP_REQUESTED else "CONCLUIDO_COM_FALHAS" if any(s["status"] != "OK" for s in notes["stages"]) else "CONCLUIDO"
        return 0 if notes["status"] == "CONCLUIDO" else 4
    finally:
        if active_children:
            stop_children([(p,h) for _,p,h in active_children])
        if pathfreq and original_max is not None:
            restore_ok = restore_cpufreq(pathfreq, original_min, original_max)
            if not restore_ok:
                print("ATENCAO: politica cpufreq nao restaurada. Verifique scaling_min_freq e scaling_max_freq!",file=sys.stderr)
        notes["restore_clock_original_ok"] = restore_ok
        if notes["status"] == "em_execucao":
            notes["status"] = "INTERROMPIDO"
        (folder / "resumo.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False))
        output_ownership(folder)
        print("\nRESULTADOS:",folder)
        print("CPU max original restaurado:",restore_ok)
        print("STATUS:",notes["status"])


def parse_args():
    a = argparse.ArgumentParser(description="Raspberry Pi 4 CPU/GPU/RAM comparative benchmark")
    a.add_argument("--label",required=True,help="case-passivo ou torre-ventilada")
    a.add_argument("--stages",default=",".join(STAGES),help="cenarios separados por virgula")
    a.add_argument("--freqs",default="1500",help="Lista MHz: 1500 ou 1500,1800")
    a.add_argument("--rest-sec",type=int,default=30)
    a.add_argument("--stress-sec",type=int,default=300)
    a.add_argument("--cool-sec",type=int,default=180)
    a.add_argument("--temp-stop",type=float,default=78.)
    a.add_argument("--gpu-bin",default="glmark2-es2-drm")
    a.add_argument("--headless-gpu-bin",type=Path,default=Path(__file__).resolve().parent/"gpu_headless_v3d")
    a.add_argument("--gpu-width",type=int,default=1280)
    a.add_argument("--gpu-height",type=int,default=720)
    a.add_argument("--ambient-c",type=float,default=None)
    a.add_argument("--fan-note",default="")
    a.add_argument("--output",type=Path,default=None)
    a.add_argument("--dry-run",action="store_true")
    a.add_argument("--smoke",action="store_true",help="Ensaio curto para validar cadeia")
    args = a.parse_args()
    try:
        args.freqs = [int(x) for x in args.freqs.split(",")]
    except ValueError:
        a.error("--freqs deve ser lista em MHz, ex: 1500,1800")
    args.stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    if not args.stages or any(x not in STAGES for x in args.stages):
        a.error("--stages invalido. Opcoes: " + ",".join(STAGES))
    if any(x not in (1500,1800) for x in args.freqs):
        a.error("Este protocolo permite somente 1500 ou 1800 MHz")
    if not 65 <= args.temp_stop <= 80:
        a.error("--temp-stop deve ficar entre 65 e 80 C")
    if args.smoke:
        args.rest_sec, args.stress_sec, args.cool_sec = 3, 8, 4
    for n in ("rest_sec","stress_sec","cool_sec"):
        if getattr(args,n) < 1:
            a.error("Tempos devem ser >=1s")
    return args


if __name__ == "__main__":
    try:
        sys.exit(run(parse_args()))
    except Exception as ex:
        print("ERRO FATAL:",str(ex),file=sys.stderr)
        sys.exit(5)
