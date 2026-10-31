"""Tela do mascote: ele muda de expressão, a câmera fica no canto e cada pessoa recebe 3 falas prontas.

  python painel.py               sobe o servidor e abre o Chrome com som e câmera liberados
  python painel.py --sem-abrir   só sobe o servidor

O navegador manda quadros da câmera para cá e o UniFace diz quem é. Na primeira vez que vê a pessoa,
o mascote toca as falas de saudacoes/. Nada sai do PC, a não ser nos botões "O que está vendo?" e "Conversar".
"""
import base64, json, os, re, shutil, subprocess, sys, threading, time, urllib.request, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import numpy as np
import cv2
import recepcao as r

AQUI = r.AQUI
CONFIG = r.CONFIG
NOME = CONFIG["nome"]
PORTA = CONFIG.get("porta", 7460)
EXPRESSOES = ("neutra", "feliz", "rindo", "surpresa", "pensando", "desconfiada", "brava", "triste", "apaixonada", "acenando", "cochichando", "comemorando")
DIR_EXPR = os.path.join(AQUI, "expressoes")
DADOS = os.path.join(AQUI, "dados")
os.makedirs(DADOS, exist_ok=True)
ARQ_RECEBIDOS = os.path.join(DADOS, "recebidos.json")
ROTULOS = CONFIG.get("rotulos", {})

trava = threading.Lock()
trava_ag = threading.Lock()
_ag = None
ultimo_quadro = None
pedido_ver = threading.Event()
nomes, embs = r.carregar()
seguidos = {}
presentes = []
recebidos = set(json.load(open(ARQ_RECEBIDOS, encoding="utf-8"))) if os.path.exists(ARQ_RECEBIDOS) else set()
falas = {}

estado = {"texto": "Oi! Fica na frente da câmera que eu já te vejo.", "ts": time.time(), "pensando": False, "expressao": "neutra"}

SISTEMA = (f"Você é {NOME}. {CONFIG.get('personalidade', '')} Você vê a câmera da entrada. Responda como um comentário ao vivo na tela: "
           "até 35 palavras, em português do Brasil, falando direto com a pessoa, leve e divertido. Nunca fale de preço, pagamento ou dinheiro. "
           "Comece toda resposta com a sua expressão entre colchetes, escolhida entre: " + ", ".join(EXPRESSOES) + ". "
           "Exemplo: [rindo] Essa cara de sono não engana ninguém.")


def pronuncia(txt):
    for palavra, fala in CONFIG.get("pronuncia", {}).items():
        txt = re.sub(rf"\b{re.escape(palavra)}\b", fala, txt)
    return txt


def gerar_voz(txt):
    """Fala na hora. Se falhar, o mascote segue só com o texto."""
    try:
        corpo = json.dumps({"text": pronuncia(txt), "model_id": CONFIG.get("modelo_voz", "eleven_v4"), "voice_settings": CONFIG.get("ajustes_voz", {})}).encode()
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{CONFIG['voz_id']}", data=corpo, method="POST",
                                     headers={"xi-api-key": r.segredo("ELEVENLABS_API_KEY"), "Content-Type": "application/json"})
        ident = str(int(time.time() * 1000))
        falas[ident] = urllib.request.urlopen(req, timeout=30).read()
        for velho in sorted(falas)[:-30]:
            falas.pop(velho)
        return ident
    except Exception as e:
        print("voz:", e, flush=True)


def url_conversa():
    """URL assinada do agente de voz. A chave fica aqui, nunca na página."""
    agente = r.segredo("ELEVENLABS_AGENT_ID")
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={agente}",
                                 headers={"xi-api-key": r.segredo("ELEVENLABS_API_KEY")})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())["signed_url"]


def responder(txt):
    m = re.match(r"\s*\[(\w+)\]\s*", txt)
    expressao = m.group(1).lower() if m and m.group(1).lower() in EXPRESSOES else "neutra"
    texto = txt[m.end():] if m else txt
    audio = gerar_voz(texto)
    estado.update(texto=texto, expressao=expressao, audio=audio, ts=time.time(), pensando=False)


def roteiro(nome):
    """As falas prontas de quem chegou, na ordem."""
    todas = json.load(open(os.path.join(AQUI, "falas.json"), encoding="utf-8")).get(nome, [])
    lista = []
    for n, fala in enumerate(todas, 1):
        if os.path.exists(os.path.join(r.SAUD, f"{nome}_{n}.mp3")):
            lista.append({**fala, "texto": re.sub(r"\s*\[\w+\]", "", fala["texto"]), "audio": f"/saudacoes/{nome}_{n}.mp3"})
    return lista


def arquivo_expressao(nome):
    final = os.path.join(DIR_EXPR, nome + ".jpg")
    if os.path.exists(final):
        return final
    base = os.path.join(AQUI, "mascote.png")  # enquanto as 12 expressões não existem, usa a imagem base
    return base if os.path.exists(base) else None


class Agente:
    """Sessão aberta do Claude Code: só para o botão "O que está vendo?"."""

    def __init__(self):
        cmd = [shutil.which("claude"), "-p", "--model", "haiku", "--strict-mcp-config", "--no-session-persistence",
               "--setting-sources", "", "--input-format", "stream-json", "--output-format", "stream-json",
               "--verbose", "--system-prompt", SISTEMA]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.n = 0

    def perguntar(self, texto):
        self.p.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": texto}}) + "\n")
        self.p.stdin.flush()
        for linha in self.p.stdout:
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            if d.get("type") == "result":
                self.n += 1
                return (d.get("result") or "").strip()
        raise RuntimeError("agente fechou")


def perguntar_agente(conteudo):
    global _ag
    with trava_ag:
        if _ag is None or _ag.n > 40 or _ag.p.poll() is not None:
            _ag = Agente()
        try:
            return _ag.perguntar(conteudo)
        except Exception:
            _ag = None
            raise


def laco_agente():
    while True:
        pedido_ver.wait()
        pedido_ver.clear()
        try:
            if ultimo_quadro is None:
                estado.update(pensando=False)
                continue
            responder(perguntar_agente([
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(ultimo_quadro).decode()}},
                {"type": "text", "text": "Pediram: o que você está vendo? Descreva a cena da câmera com detalhes concretos, do seu jeito."}]))
        except Exception as e:
            estado.update(pensando=False)
            print("agente:", e, flush=True)


def analisar(jpg):
    global ultimo_quadro, presentes
    ultimo_quadro = jpg
    img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
    det, rec = r.modelos()
    out, tocar, agora = [], None, []
    for f in det.detect(img):
        emb = rec.get_normalized_embedding(img, f.landmarks).ravel()
        nome, s = r.quem(emb, nomes, embs) if len(nomes) else (None, 0.0)
        out.append({"bbox": [float(v) for v in f.bbox[:4]], "nome": nome, "rotulo": ROTULOS.get(nome, nome), "sim": round(float(s), 2)})
        if not nome:
            continue  # rosto de lado cai em desconhecido: quem não foi reconhecido não recebe fala
        agora.append(nome)
        seguidos[nome] = seguidos.get(nome, 0) + 1
        if nome not in recebidos and not tocar and seguidos[nome] >= 3 and os.path.exists(os.path.join(r.SAUD, nome + "_1.mp3")):
            tocar = nome
            recebidos.add(nome)
            json.dump(sorted(recebidos), open(ARQ_RECEBIDOS, "w", encoding="utf-8"))
    for chave in list(seguidos):
        if chave not in agora:
            seguidos.pop(chave)
    presentes = agora
    return {"rostos": out, "objetos": [], "tocar": tocar, "w": img.shape[1], "h": img.shape[0]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _env(self, corpo, tipo="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = open(os.path.join(AQUI, "palco.html"), encoding="utf-8").read().replace("{{NOME}}", NOME)
            return self._env(html.encode(), "text/html; charset=utf-8")
        if self.path.startswith("/expressao/"):
            arq = arquivo_expressao(os.path.basename(self.path))
            if arq:
                return self._env(open(arq, "rb").read(), "image/png" if arq.endswith(".png") else "image/jpeg")
        if self.path == "/agente":
            return self._env(json.dumps(estado).encode())
        if self.path == "/convai.js":
            return self._env(open(os.path.join(AQUI, "convai.js"), "rb").read(), "text/javascript")
        if self.path == "/convai/url":
            try:
                return self._env(json.dumps({"url": url_conversa()}).encode())
            except Exception as e:
                print("agente de voz:", e, flush=True)
                return self._env(b'{"url": null}')
        if self.path.startswith("/roteiro/"):
            return self._env(json.dumps(roteiro(os.path.basename(self.path))).encode())
        if self.path.startswith("/fala/"):
            corpo = falas.get(os.path.basename(self.path).replace(".mp3", ""))
            if corpo:
                return self._env(corpo, "audio/mpeg")
        if self.path.startswith("/saudacoes/"):
            arq = os.path.join(r.SAUD, os.path.basename(self.path))
            if os.path.exists(arq):
                return self._env(open(arq, "rb").read(), "audio/mpeg")
        self.send_error(404)

    def do_POST(self):
        if self.path == "/ver":
            pedido_ver.set()
            estado["pensando"] = True
            return self._env(b"{}")
        if self.path == "/chegada":
            for nome in presentes:
                recebidos.discard(nome)
                seguidos.pop(nome, None)
            json.dump(sorted(recebidos), open(ARQ_RECEBIDOS, "w", encoding="utf-8"))
            return self._env(json.dumps({"presentes": len(presentes)}).encode())
        if self.path == "/quadro":
            jpg = self.rfile.read(int(self.headers["Content-Length"]))
            with trava:
                res = analisar(jpg)
            res["agente"] = estado
            return self._env(json.dumps(res).encode())
        self.send_error(404)


def abrir_chrome():
    """Janela própria: aba comum bloqueia o áudio até o primeiro clique e a pessoa fica sem ouvir a fala."""
    url = f"http://localhost:{PORTA}/"
    locais = [os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"), os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
              os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    chrome = next((c for c in locais if os.path.exists(c)), None)
    if not chrome:
        return webbrowser.open(url)
    subprocess.Popen([chrome, "--user-data-dir=" + os.path.join(DADOS, "chrome"), "--app=" + url, "--autoplay-policy=no-user-gesture-required",
                      "--use-fake-ui-for-media-stream", "--no-first-run", "--no-default-browser-check", "--start-maximized"])


if __name__ == "__main__":
    threading.Thread(target=laco_agente, daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    print(f"painel em http://localhost:{PORTA}", flush=True)
    if "--sem-abrir" not in sys.argv:
        abrir_chrome()
    servidor.serve_forever()
