#!/usr/bin/env python3
"""Coleta do experimento: Blender 4.5 LTS x 5.2 LTS (Cycles, CPU), em duas cargas de trabalho.

Funciona em Windows, macOS e Linux. Não precisa instalar o Blender: baixe a versão "portable"
(zip/tar) de cada uma em https://www.blender.org/download/lts/ e extraia em pastas separadas.

Uso (substitua os caminhos pelos seus):

  # 1) confere se os dois Blenders rodam, aquece e ESTIMA quanto tempo a coleta vai levar
  python3 blender_bench.py check --blender 4.5=/caminho/blender-4.5/blender --blender 5.2=/caminho/blender-5.2/blender

  # 2) piloto (3 repetições por célula)
  python3 blender_bench.py pilot --blender 4.5=... --blender 5.2=...

  # 3) coleta completa (20 repetições por célula)
  python3 blender_bench.py full  --blender 4.5=... --blender 5.2=...

Caminho do executável: Windows  ...\\blender.exe | macOS  .../Blender.app/Contents/MacOS/Blender | Linux  .../blender
O texto antes do '=' é o RÓTULO da versão (aparece no CSV e nos gráficos). Use o mais antigo primeiro.

Saídas (em --data-dir, padrão ../../dados): raw_pilot.csv / raw_full.csv, env_snapshot.txt, logs/*.log
"""
import argparse
import csv
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# A cena é definida por Leonardo (método) e fica em leonardo/scripts/ no repositório.
# Procura primeiro ao lado deste arquivo e depois na pasta do repositório.
_SCENE_CANDIDATES = [
    HERE / "blender_scene_render.py",
    HERE.parent.parent / "leonardo" / "scripts" / "blender_scene_render.py",
]
SCENE_SCRIPT = next((c for c in _SCENE_CANDIDATES if c.exists()), _SCENE_CANDIDATES[-1])
WORKLOADS = ["diffuse", "glass"]

COLUMNS = [
    "timestamp_utc", "phase", "rep", "order_in_rep", "version", "workload",
    "blender_version", "samples", "threads", "resolution",
    "render_s", "total_s", "build_s", "image_mean", "returncode",
]


def parse_blenders(items):
    out = []
    for it in items:
        if "=" not in it:
            sys.exit(f"--blender deve ser RÓTULO=CAMINHO (recebi: {it})")
        label, path = it.split("=", 1)
        path = os.path.expanduser(path.strip().strip('"'))
        if not os.path.isfile(path):
            sys.exit(f"Executável não encontrado para {label}: {path}")
        out.append((label.strip(), path))
    if len(out) != 2:
        sys.exit("Passe exatamente duas vezes --blender (versão antiga e versão nova).")
    return out


def run_blender(exe, workload, a):
    """Roda um render em um processo novo do Blender. Retorna dict com os campos medidos."""
    cmd = [exe, "-b", "--factory-startup", "-noaudio", "-P", str(SCENE_SCRIPT), "--",
           "--workload", workload, "--samples", str(a.samples), "--threads", str(a.threads),
           "--res-x", str(a.res_x), "--res-y", str(a.res_y)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
    total_s = time.perf_counter() - t0
    out = (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or "")
    m = re.search(r"BENCH_RESULT (\{.*\})", p.stdout or "")
    res = json.loads(m.group(1)) if m else {}
    res["total_s"] = round(total_s, 4)
    res["returncode"] = p.returncode if m else (p.returncode or 1)
    return res, out


def cpu_name():
    try:
        if sys.platform.startswith("linux"):
            for line in open("/proc/cpuinfo"):
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        if sys.platform == "darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        return os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor()
    except Exception:
        return platform.processor() or "desconhecido"


def ram_gb():
    try:
        if sys.platform.startswith("linux"):
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal"):
                    return f"{int(line.split()[1]) / 1024 / 1024:.1f} GB"
        if sys.platform == "darwin":
            return f"{int(subprocess.check_output(['sysctl', '-n', 'hw.memsize'], text=True)) / 1024**3:.1f} GB"
        if sys.platform == "win32":
            out = subprocess.check_output(["wmic", "computersystem", "get", "TotalPhysicalMemory"], text=True)
            total_bytes = int(re.findall(r"\d+", out)[0])
            return f"{total_bytes / 1024**3:.1f} GB"
    except Exception:
        pass
    return "não detectado (anote manualmente)"


def write_snapshot(a, blenders):
    path = Path(a.data_dir) / "env_snapshot.txt"
    lines = [f"# Snapshot do ambiente - {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
             "## Máquina",
             f"SO: {platform.platform()}",
             f"CPU: {cpu_name()}",
             f"Núcleos lógicos: {os.cpu_count()}",
             f"RAM: {ram_gb()}",
             f"Python: {platform.python_version()}",
             "(anote à mão: notebook ou desktop, ligado na tomada, modo de energia, temperatura ambiente)",
             "## Blender"]
    for label, exe in blenders:
        try:
            v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
        except Exception as e:
            v = f"erro: {e}"
        lines += [f"[{label}] {exe}", v.replace("\n", " | ")]
    lines += ["## Parâmetros do experimento",
              f"motor=Cycles CPU  samples={a.samples}  threads={a.threads}  resolução={a.res_x}x{a.res_y}",
              f"pausa={a.pause}s  semente da ordem={a.seed}  cargas={WORKLOADS}",
              "denoising=desligado  amostragem adaptativa=desligada  semente do Cycles=0"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def order_for_rep(labels, seed, rep):
    cells = [(v, w) for v in labels for w in WORKLOADS]
    random.Random(seed * 1000 + rep).shuffle(cells)
    return cells


def cmd_check(a, blenders):
    Path(a.data_dir).mkdir(parents=True, exist_ok=True)
    print(f"Snapshot: {write_snapshot(a, blenders)}")
    est = 0.0
    for label, exe in blenders:
        for w in WORKLOADS:
            res, log = run_blender(exe, w, a)
            ok = res.get("returncode") == 0 and "render_s" in res
            print(f"[{'OK' if ok else 'FALHOU'}] Blender {label:>4}  {w:<8}  "
                  f"{res.get('blender_version', '?'):<8} render={res.get('render_s', '-')}s  total={res.get('total_s', '-')}s  "
                  f"brilho médio={res.get('image_mean', '-')}")
            if not ok:
                print(log[-1500:])
                sys.exit(1)
            est += res["total_s"] + a.pause
    for reps, nome in ((a.reps_pilot, "piloto"), (a.reps_full, "coleta completa")):
        print(f"Estimativa da {nome} ({reps} repetições por célula): ~{est * reps / 60:.0f} min")
    print("Se a estimativa da coleta completa passar de ~90 min, reduza --samples (ex.: 32) ou --reps-full.")


def cmd_collect(a, blenders, phase):
    reps = a.reps_pilot if phase == "pilot" else a.reps_full
    labels = [b[0] for b in blenders]
    exe_of = dict(blenders)
    data = Path(a.data_dir)
    (data / "logs").mkdir(parents=True, exist_ok=True)
    csv_path = data / f"raw_{phase}.csv"
    if csv_path.exists():
        if not a.force:
            sys.exit(f"{csv_path} já existe. Para refazer a coleta use --force (o arquivo antigo vira .bak).")
        shutil.move(csv_path, str(csv_path) + ".bak")
    write_snapshot(a, blenders)

    if not a.no_warmup:
        print("Aquecimento (descartado): 1 render de cada célula...")
        for v in labels:
            for w in WORKLOADS:
                run_blender(exe_of[v], w, a)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS)
        wr.writeheader()
        for rep in range(1, reps + 1):
            for order, (v, w) in enumerate(order_for_rep(labels, a.seed, rep), start=1):
                res, log = run_blender(exe_of[v], w, a)
                (data / "logs" / f"{phase}_rep{rep:02d}_o{order}_v{v}_{w}.log").write_text(log, encoding="utf-8")
                row = {c: res.get(c, "") for c in COLUMNS}
                row.update({"timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "phase": phase, "rep": rep, "order_in_rep": order, "version": v, "workload": w})
                wr.writerow(row)
                f.flush()
                print(f"[{phase}] rep {rep}/{reps} ordem {order}  Blender {v:>4}  {w:<8}  "
                      f"render={res.get('render_s', 'ERRO')}s")
                time.sleep(a.pause)
    print(f"Coleta '{phase}' concluída: {csv_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "pilot", "full"])
    ap.add_argument("--blender", action="append", default=[], metavar="RÓTULO=CAMINHO")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--threads", type=int, default=4, help="threads fixas do Cycles (use o mesmo valor sempre)")
    ap.add_argument("--res-x", type=int, default=640)
    ap.add_argument("--res-y", type=int, default=360)
    ap.add_argument("--pause", type=float, default=3.0, help="segundos entre renders (esfriar a CPU)")
    ap.add_argument("--seed", type=int, default=2026, help="semente da ordem aleatória (registre no relatório)")
    ap.add_argument("--reps-pilot", type=int, default=3)
    ap.add_argument("--reps-full", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--data-dir", default=str(HERE / ".." / ".." / "dados"))
    ap.add_argument("--no-warmup", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    blenders = parse_blenders(a.blender)
    if a.command == "check":
        cmd_check(a, blenders)
    else:
        cmd_collect(a, blenders, a.command)


if __name__ == "__main__":
    main()
