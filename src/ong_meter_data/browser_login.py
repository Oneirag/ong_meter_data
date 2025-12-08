import subprocess
from pathlib import Path
import json

def browser_login() -> dict:
    # Ejemplo con un comando que genera líneas cada segundo
    cmd = "xvfb-run python -m ong_meter_data.update_cookies_playwright"
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # si también quieres errores
        text=True,                  # devuelve str en vez de bytes
        bufsize=1,                  # line buffering (solo con text=True)
        cwd=Path(__file__).parent.parent,
        shell=True
    )
    result = {}
    # Itera línea a línea mientras el proceso sigue corriendo
    for line in iter(p.stdout.readline, ""):
        if line:  # evita que se imprima una línea vacía al final
            if "JSESSIONID" in line:
                print("[JSON]: ",line)
                result = json.loads(line.replace("'", '"'))
            print(f"[STDOUT] {line.rstrip()}")

    # Espera a que el proceso termine (opcional si ya sabes que ya terminó)
    p.wait()
    # Error code 12345 means MFA code was required
    if p.errorcode == 12345:
        result = dict(mfa=True)
    elif not result:
        # Other unknow error happened
        result = dict(internal_error=True)  
    print(f"Comando finalizado con código {p.returncode}")
    return result        
    

if __name__ == "__main__":
    print(browser_login())