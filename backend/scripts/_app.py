"""Põe backend/app no caminho de import dos scripts desta pasta.

O código do sistema mora em backend/app (main.py, infra/, regras/), e os
scripts importam dele como o servidor importa: `from regras.x import ...`.
Cada script começa com `import _app`, que funciona porque o Python põe no
caminho de import a pasta do script que está rodando.

Os scripts rodam de dentro de backend/ (`python scripts/seed_demo.py`): o
banco e a pasta uploads/ são relativos à pasta de onde se roda, como no
servidor.
"""

import os
import sys

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP not in sys.path:
    sys.path.insert(0, APP)
