import csv
import os
import sys
import time
import threading
from datetime import datetime

CSV_FILE = "trials_execution_log.csv"
TIMEBOX_SECONDS = 35 * 60

timebox_reached = False


def trigger_timebox_alert():
    """Função disparada automaticamente ao atingir exatamente o time-box."""
    global timebox_reached
    timebox_reached = True

    print("\a", end="", flush=True)
    if os.name == "nt":
        try:
            import winsound
            winsound.Beep(1000, 1000)
        except Exception:
            pass

    print("\n\n" + "🚨" * 20)
    print("⚠️  TIME-BOX DE 35 MINUTOS ALCANÇADO! PARE DE CODAR AGORA! ⚠️")
    print("🚨" * 20)
    print("\nPressione ENTER para prosseguir e registrar os resultados...")


def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "participant",
                    "kata_id",
                    "treatment",
                    "start_time",
                    "end_time",
                    "duration_seconds",
                    "status",
                    "tests_passed",
                    "total_tests",
                ]
            )


def run_timer():
    global timebox_reached
    timebox_reached = False

    init_csv()
    print("=== CRONÔMETRO DE TRIALS - EXPERIMENTO IA ===")
    participant = input("Nome do participante: ").strip()
    kata_id = input("ID do Kata (ex: kata1, kata2...): ").strip()
    treatment = (
        input("Tratamento (1 - COM IA / 2 - SEM IA): ").strip().upper()
    )
    treatment_str = "WITH_AI" if treatment in ["1", "WITH_AI"] else "WITHOUT_AI"

    print(
        f"\nReady! Pressione ENTER para iniciar o trial ({kata_id} | {treatment_str})..."
    )
    input()

    start_epoch = time.time()
    start_dt = datetime.now().isoformat()
    
    timer = threading.Timer(TIMEBOX_SECONDS, trigger_timebox_alert)
    timer.daemon = True
    timer.start()

    print(f"⏱️  Trial INICIADO às {start_dt}")
    print("Pressione ENTER assim que PASSAR EM TODOS OS TESTES (Time-box: 35 min).")

    try:
        input()
        end_epoch = time.time()
        timer.cancel()

        elapsed = int(end_epoch - start_epoch)

        if timebox_reached or elapsed >= TIMEBOX_SECONDS:
            status = "CENSORED"
            elapsed = TIMEBOX_SECONDS
            print("⚠️  Trial encerrado pelo Time-box (35 min) -> Registrado como CENSORED.")
        else:
            status = "COMPLETED"
            print(f"✅ Trial concluído em {elapsed} segundos ({elapsed//60}m {elapsed%60}s)!")

    except KeyboardInterrupt:
        timer.cancel()
        end_epoch = time.time()
        elapsed = min(int(end_epoch - start_epoch), TIMEBOX_SECONDS)
        status = "CENSORED"
        print("\n⚠️  Trial abortado/interrompido manualmente.")

    end_dt = datetime.now().isoformat()

    print("\n--- REGISTRO FINAL DE RESULTADOS ---")
    tests_passed = input("Nº de testes PASSANDO ao final: ").strip()
    total_tests = input("Nº TOTAL de testes do Kata: ").strip()

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                participant,
                kata_id,
                treatment_str,
                start_dt,
                end_dt,
                elapsed,
                status,
                tests_passed,
                total_tests,
            ]
        )

    print(f"💾 Dados salvos com sucesso em '{CSV_FILE}'!\n")


if __name__ == "__main__":
    run_timer()