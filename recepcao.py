"""Reconhecimento de rosto do mascote. Tudo roda no PC (UniFace, MIT). Nenhuma foto sai da máquina.

  python recepcao.py cadastro     lê pessoas/<Nome>/*.jpg|png e grava rostos.npz
  python recepcao.py foto ARQ     testa uma foto (imprime quem é e a semelhança)
"""
import glob, json, os, sys
import numpy as np
import cv2
from uniface import RetinaFace, ArcFace

AQUI = os.path.dirname(os.path.abspath(__file__))
PESSOAS = os.path.join(AQUI, "pessoas")
BANCO = os.path.join(AQUI, "rostos.npz")
SAUD = os.path.join(AQUI, "saudacoes")
CONFIG = json.load(open(os.path.join(AQUI, "config.json"), encoding="utf-8"))
LIMIAR = CONFIG.get("limiar", 0.40)  # semelhança mínima (cosseno) para dizer que é a pessoa

_det = _rec = None


def segredo(nome):
    """Lê a variável do ambiente ou do arquivo .env desta pasta."""
    if os.environ.get(nome):
        return os.environ[nome]
    arq = os.path.join(AQUI, ".env")
    if os.path.exists(arq):
        for linha in open(arq, encoding="utf-8"):
            if linha.strip().startswith(nome + "="):
                return linha.split("=", 1)[1].strip()
    return ""


def modelos():
    global _det, _rec
    if _det is None:
        _det, _rec = RetinaFace(), ArcFace()
    return _det, _rec


def rostos(img):
    det, rec = modelos()
    out = []
    for f in det.detect(img):
        emb = rec.get_normalized_embedding(img, f.landmarks).ravel()
        out.append((f.bbox, emb))
    return out


def cadastro():
    nomes, embs = [], []
    for pasta in sorted(glob.glob(os.path.join(PESSOAS, "*"))):
        nome = os.path.basename(pasta)
        for arq in sorted(glob.glob(os.path.join(pasta, "*"))):
            img = cv2.imread(arq)
            if img is None:
                continue
            achados = rostos(img)
            if not achados:
                print("sem rosto:", arq)
                continue
            bbox, emb = max(achados, key=lambda r: (r[0][2] - r[0][0]) * (r[0][3] - r[0][1]))
            nomes.append(nome)
            embs.append(emb)
        print(nome, nomes.count(nome), "foto(s)")
    np.savez(BANCO, nomes=np.array(nomes), embs=np.array(embs))


def carregar():
    if not os.path.exists(BANCO):
        return [], np.zeros((0, 512))
    d = np.load(BANCO)
    return list(d["nomes"]), d["embs"]


def quem(emb, nomes, embs):
    sims = embs @ emb
    melhor = {}
    for n, s in zip(nomes, sims):
        melhor[n] = max(melhor.get(n, -1), float(s))
    nome, s = max(melhor.items(), key=lambda x: x[1])
    return (nome if s >= LIMIAR else None), s


def foto(arq):
    nomes, embs = carregar()
    img = cv2.imread(arq)
    for b, e in rostos(img):
        nome, s = quem(e, nomes, embs) if len(nomes) else (None, 0.0)
        print(f"{os.path.basename(arq)}: {nome or 'desconhecido'} ({s:.2f})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "cadastro":
        cadastro()
    elif cmd == "foto":
        for a in sys.argv[2:]:
            foto(a)
    else:
        print(__doc__)
