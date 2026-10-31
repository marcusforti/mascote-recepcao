"""Gera saudacoes/<Nome>_1.mp3, _2.mp3, _3.mp3 a partir de falas.json. Só gera o que falta.

  python falas.py              gera tudo o que falta
  python falas.py Joao Maria   refaz só essas pessoas
"""
import json, os, re, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
CONFIG = json.load(open(os.path.join(AQUI, "config.json"), encoding="utf-8"))


def segredo(nome):
    if os.environ.get(nome):
        return os.environ[nome]
    for linha in open(os.path.join(AQUI, ".env"), encoding="utf-8"):
        if linha.strip().startswith(nome + "="):
            return linha.split("=", 1)[1].strip()
    return ""


CHAVE = segredo("ELEVENLABS_API_KEY")
SAUD = os.path.join(AQUI, "saudacoes")
os.makedirs(SAUD, exist_ok=True)
so = sys.argv[1:]
for nome, lista in json.load(open(os.path.join(AQUI, "falas.json"), encoding="utf-8")).items():
    if so and nome not in so:
        continue
    for n, fala in enumerate(lista, 1):
        arq = os.path.join(SAUD, f"{nome}_{n}.mp3")
        if os.path.exists(arq) and not so:
            continue
        txt = fala["texto"]
        for palavra, som in CONFIG.get("pronuncia", {}).items():
            txt = re.sub(rf"\b{re.escape(palavra)}\b", som, txt)
        corpo = json.dumps({"text": txt, "model_id": CONFIG.get("modelo_voz", "eleven_v4"), "voice_settings": CONFIG.get("ajustes_voz", {})}).encode()
        q = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{CONFIG['voz_id']}", data=corpo, method="POST",
                                   headers={"xi-api-key": CHAVE, "Content-Type": "application/json"})
        open(arq + ".tmp", "wb").write(urllib.request.urlopen(q, timeout=120).read())
        os.replace(arq + ".tmp", arq)
        print("ok", os.path.basename(arq), flush=True)
