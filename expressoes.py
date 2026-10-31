"""Gera as 12 expressões do mascote com o Codex, a partir de mascote.png. Uso: python expressoes.py [nome ...]"""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
D = AQUI / "expressoes"
BRUTO = D / "_bruto"
REF = AQUI / "mascote.png"
VISUAL = json.load(open(AQUI / "config.json", encoding="utf-8"))["visual"]
BASE = (f"Same character as the attached reference image: {VISUAL} Very expressive face, funny, never scary. Waist-up, centered, looking straight at the "
        "viewer as if on a video call, the same framing in every image. Plain very dark studio background with a soft glow behind the character. "
        "High-end 3D animated film render, soft cinematic light. Wide 16:9 landscape (1536x1024). Keep the bottom quarter dark and simple, captions "
        "will sit there. No text, no letters, no numbers, no logos, no watermark.")
CENAS = {
    "neutra": "Calm, attentive neutral expression, a tiny friendly smile, listening.",
    "feliz": "Big warm happy smile, eyes bright.",
    "rindo": "Laughing out loud, eyes squeezed shut, head tilted back.",
    "surpresa": "Huge comic surprise, eyes wide, mouth open.",
    "pensando": "Thinking hard, looking up to the side, one hand on the chin.",
    "desconfiada": "Deep suspicion, one eyebrow raised, side-eye at the viewer, half smile.",
    "brava": "Playfully grumpy, frowning, arms crossed, tiny puffs of steam from the ears, still cute.",
    "triste": "Dramatically sad puppy eyes, lower lip trembling, one big tear.",
    "apaixonada": "Melting with affection, both hands on the cheeks, dreamy eyes, small hearts floating around.",
    "acenando": "Waving hello with one hand raised high, big welcoming smile.",
    "cochichando": "Leaning toward the viewer, one hand beside the mouth, whispering a secret, mischievous eyes.",
    "comemorando": "Celebrating with both hands up, mouth open in joy, confetti falling.",
}


def gera(item):
    nome, desc = item
    bruto, final = BRUTO / f"{nome}.png", D / f"{nome}.jpg"
    if not bruto.exists():
        prompt = (f"Use your image generation tool (image_gen) to create ONE image. Prompt: '{desc} {BASE}' "
                  f"Save the resulting image file into the directory {BRUTO} as {nome}.png. Reply only with the saved file path.")
        cmd = ["codex", "exec", "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", prompt, "-i", str(REF)]
        try:
            subprocess.run(cmd, cwd=BRUTO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, shell=sys.platform == "win32")
        except subprocess.TimeoutExpired:
            return f"{nome}: TEMPO ESGOTADO"
    if not bruto.exists():
        return f"{nome}: FALHOU"
    imagem = Image.open(bruto).convert("RGB")
    imagem.thumbnail((1920, 1920))
    imagem.save(final, quality=86, optimize=True)
    return f"{nome}: ok {final.stat().st_size // 1024} KB"


BRUTO.mkdir(parents=True, exist_ok=True)
pedidos = set(sys.argv[1:])
with ThreadPoolExecutor(3) as ex:
    for linha in ex.map(gera, [i for i in CENAS.items() if not pedidos or i[0] in pedidos]):
        print(linha, flush=True)
