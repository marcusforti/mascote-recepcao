# Mascote de recepção

Um personagem na tela que vê quem chega pela câmera, fala o nome da pessoa e faz uma piada só dela. É o mesmo motor da Sheep na Imersão, sem nada da turma: você coloca o seu personagem, as suas pessoas e as suas falas.

## Começar

Abra o Claude Code ou o Codex em qualquer pasta e cole:

```text
Baixe https://github.com/marcusforti/mascote-recepcao com git clone, entre na pasta, leia o README.md inteiro e monte o meu mascote seguindo a seção "Prompt para o seu agente".
```

Prefere sem agente? Rode `git clone https://github.com/marcusforti/mascote-recepcao` e siga "Como montar o seu".

## Como funciona por trás

```
Câmera → navegador → seu PC reconhece o rosto → navegador toca a fala → mascote muda de expressão
```

1. **Cadastro.** Você põe fotos em `pessoas/<Nome>/`. O `recepcao.py` transforma cada rosto numa sequência de números e guarda em `rostos.npz`. As fotos não saem do PC.
2. **Tela.** O `palco.html` abre a câmera no Chrome e manda 5 quadros por segundo, mais ou menos, para o `painel.py`, que roda só no seu PC.
3. **Reconhecimento.** O `painel.py` acha os rostos (RetinaFace), calcula os números de cada um (ArcFace) e compara com o cadastro. Semelhança acima de 0,40 é a pessoa. Abaixo disso, é desconhecido e o mascote fica quieto.
4. **Chegada.** Com a pessoa reconhecida em 3 quadros seguidos, a tela toca as 3 falas dela, trocando a expressão em cada uma. O nome vai para `dados/recebidos.json`, para ela só ser recebida uma vez, mesmo reiniciando.
5. **Voz.** As falas são geradas antes, uma vez, pelo `falas.py` (ElevenLabs) e ficam em `saudacoes/`. No dia, tocar não gasta nada e não depende de internet.

Duas funções usam internet e só ligam no clique:

- **O que está vendo?** manda um quadro da câmera para o Claude descrever. Precisa do Claude Code logado.
- **Conversar** abre um agente de voz do ElevenLabs, e a voz da pessoa passa por lá. É opcional.

## O que cada arquivo faz

| Arquivo | Função |
|---|---|
| `config.json` | Nome, personalidade, visual, voz |
| `.env` | Chaves (nunca mande para ninguém) |
| `falas.json` | As 3 falas de cada pessoa |
| `pessoas/<Nome>/` | Fotos de cada pessoa |
| `mascote.png` | Imagem base do personagem |
| `expressoes/` | As 12 expressões |
| `recepcao.py` | Cadastro dos rostos |
| `falas.py` | Gera os áudios |
| `expressoes.py` | Gera as imagens (usa o Codex) |
| `painel.py` + `palco.html` | O sistema rodando |
| `convai.js` | Cliente oficial do ElevenLabs para o agente de voz |

## Como montar o seu

Precisa de: Python 3.12 ou mais novo, Google Chrome, conta no ElevenLabs, uma webcam e uma caixa de som. Para as imagens, o Codex ou qualquer gerador de imagem.

**O jeito fácil:** abra o Claude Code ou o Codex nesta pasta e cole o prompt do fim deste guia.

`pessoas/`, `rostos.npz`, `falas.json`, `saudacoes/`, `dados/`, `expressoes/`, `mascote.png` e `.env` já estão no `.gitignore`: rosto, fala, voz, imagem e chave não sobem para o GitHub.

**Na mão:**

1. Instale: `pip install -r requirements.txt`
2. Copie `.env.exemplo` para `.env` e cole a chave do ElevenLabs.
3. Preencha o `config.json`. O `voz_id` vem da página Voices do ElevenLabs.
4. Salve a imagem do personagem como `mascote.png`. Só com ela o sistema já roda.
5. Crie `pessoas/Joao/` com 3 a 6 fotos, com o nome da pasta sem acento. No `rotulos` do `config.json`, diga como o nome aparece na tela.
6. Rode `python recepcao.py cadastro`.
7. Copie `falas.exemplo.json` para `falas.json`, escreva as falas com a chave igual ao nome da pasta e rode `python falas.py`.
8. Opcional: `python expressoes.py` gera as 12 expressões. Sem o Codex, gere as imagens em outro lugar e salve em `expressoes/` com estes nomes, em `.jpg`: neutra, feliz, rindo, surpresa, pensando, desconfiada, brava, triste, apaixonada, acenando, cochichando, comemorando.
9. Rode `python painel.py`. A janela abre sozinha com câmera e som liberados.

**Teclas na tela:** 1 câmera no canto, 2 câmera inteira, 3 só o mascote, F tela cheia, C repete as falas de quem está na frente, T conversa, V "o que está vendo?".

Colocou gente nova? Rode o cadastro de novo e reinicie o `painel.py`, que lê os rostos ao abrir.

## O que já deu errado com a gente

- **O começo do áudio corta na caixa de som.** Se a fala começa com o nome, o nome some. Comece com 3 ou 4 palavras e só então diga o nome: "Para tudo, gente, é o João!".
- **Aba comum do Chrome não toca som** até alguém clicar. A pessoa passa, fica marcada como recebida e não ouve nada. Por isso o `painel.py` abre uma janela própria. Se abrir por outro caminho, clique na tela antes.
- **Quem sai e volta não pode ouvir "seja bem-vindo" de novo.** Por isso cada um recebe só uma vez, e rosto de lado, que cai em desconhecido, não dispara fala.
- **Poucas fotos erram.** Use de 3 a 6, de frente e com luz boa. Se confundir duas pessoas, suba o `limiar`. Se não reconhecer, desça um pouco.
- **Falas gerais não têm graça.** O que fez a turma rir foi detalhe de cada um: a profissão, o apelido, uma história. Escreva 15 segundos por pessoa.
- **A fala toca alta na porta.** Nunca fale de pagamento nem de nada que a pessoa não diria em público.
- **Câmera:** a tela prefere uma webcam externa. Para trocar, use o menu da barra de baixo (mexa o mouse para ela aparecer).

## Rosto é dado sensível (LGPD)

- Avise as pessoas antes e peça o aceite delas. Sem aceite, não cadastre.
- Não cadastre rosto de criança sem autorização dos responsáveis.
- Terminado o evento, apague `pessoas/`, `rostos.npz`, `saudacoes/` e `dados/`.
- O UniFace tem licença MIT. Os modelos de rosto que ele baixa no primeiro uso têm licenças próprias: confira antes de vender como produto.

## Prompt para o seu agente

```text
Esta pasta é um mascote de recepção. Leia o README.md inteiro e monte o meu, passo a passo.

Regras:
- Me faça uma pergunta por vez: nome do mascote, personalidade, aparência, voz e quem são as pessoas.
- Instale o que faltar e crie o .env. Peça a chave e me diga para colar direto no arquivo .env, nunca no chat.
- Escreva 3 falas para cada pessoa no falas.json. A primeira começa com 3 ou 4 palavras e só então diz o nome, com uma piada específica daquela pessoa. Me mostre as falas antes de gerar os áudios, porque gerar gasta crédito.
- Confirme que eu tenho o aceite das pessoas antes de cadastrar qualquer rosto.
- No final, rode o painel e me diga como testar.
```
