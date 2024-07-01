# run_both.py
import subprocess
from multiprocessing import Process

def run_fetch_tenders():
    subprocess.run(["python", "fetch_tenders.py"])

def run_process_signatures():
    subprocess.run(["python", "process_signatures.py"])

if __name__ == "__main__":
    p1 = Process(target=run_fetch_tenders)
    p2 = Process(target=run_process_signatures)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
