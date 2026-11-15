<p align="center">
  <img src="icone.png" width="140" alt="PConc Helper">
</p>

<h1 align="center">PConc Helper</h1>

<p align="center">
  <b>Overlay em português para Path of Exile 1:</b> guia da campanha ato a ato, árvore de passivos, checagem de chefes,<br>
  price check, comparador de itens e uma IA para tirar dúvidas da sua build. Tudo numa barrinha em cima da XP.
</p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ Baixar o PConc-Helper.exe</b></a> ·
  <a href="#como-usar">Como usar</a> ·
  <a href="#perguntas-frequentes">Perguntas frequentes</a>
</p>

---

Feito para a build **Poisonous Concoction of Bouncing Pathfinder** (guia do animeprincess no Mobalytics), mas funciona
com **qualquer build**: você pode colar o link do seu próprio guia (Path of Building / pobb.in / pastebin / Mobalytics)
ou usar sem guia, só com as dicas de cada ato.

## O que ele faz

| | |
|---|---|
| 🧭 **Guia ato a ato** | Lê o `Client.txt` do jogo e sabe em que ato, zona e nível você está. Mostra o próximo passo e dicas de navegação de cada mapa. Os passos se marcam sozinhos conforme você avança. |
| 🌳 **Árvore de passivos** | A árvore do guia dentro do programa, com as imagens oficiais, e **o que pegar no seu nível, em ordem de importância**. |
| ⚔ **Está pronto para o chefe?** | Ao entrar na área de um chefe, confere suas resistências, links, vida e frascos (pelo seu perfil público) e diz o que falta. |
| 💰 **Price check** | Mouse em cima do item + tecla: preço do poe.ninja ou busca no trade com os mods importantes, no estilo do Awakened PoE Trade. |
| ⚖ **Comparar com o item equipado** | Diz se o item do chão ou do inventário é **melhor ou pior** que o seu atual para a sua build: vida, resistências, defesas, dano, frascos… |
| 🤖 **Pergunte à IA** | Botão que manda sua pergunta + os dados da sua build (itens, gemas, resistências, ato) para o Claude. |
| 🎯 **Extras** | XP da área (penalidade), regex para a loja, trials do labirinto, tempo por ato (pausa quando você para), mortes, bandidos, checklist pós-campanha. |
| 🪟 **Feito para jogar junto** | Barra fininha perto da XP, fica transparente quando você não está usando, não rouba o foco do jogo, fecha junto com o jogo (opcional). |

Também vem um **filtro de loot** no estilo NeverSink, ajustado para a build (pasta [`filtros`](filtros)).

## Como usar

1. Baixe o **[PConc-Helper.exe](../../releases/latest)** (em "Assets") e abra. Não precisa instalar nada.
   > O Windows pode mostrar "O Windows protegeu o computador" porque o programa não tem assinatura de empresa.
   > Clique em **Mais informações → Executar assim mesmo**.
2. Na tela inicial, escolha: usar o guia da PConc, colar o link do **seu** guia, ou **não tenho guia**.
3. Jogue em **Tela cheia em janela** (Windowed Fullscreen) para o overlay ficar por cima do jogo.
4. (Opcional) Em **Configurações → Conta PoE**, coloque sua conta com o número (ex.: `Nome#1234`) e deixe a aba de
   personagens **pública** no site do PoE. Isso libera a checagem de chefes, o comparador e a IA com seus itens.

### Teclas (mouse em cima do item)

| Tecla | O que faz |
|---|---|
| `Ctrl+D` | Preço / comprar (trade) |
| `Alt+D` | Comparar com o seu item equipado |
| `Ctrl+C` / `Ctrl+Alt+C` | Também funcionam (copiar normal / avançado) |
| `F9` | Mostrar/esconder o programa |

Tudo pode ser trocado no botão **Atalhos** da barra.

## Perguntas frequentes

**Isso é permitido pela GGG?**
O programa só **lê** o arquivo de log do jogo e o texto do item que você copia. Cada tecla gera **uma** cópia do item
(o mesmo que o Awakened PoE Trade faz) e nenhuma ação no servidor. Não mexe na memória do jogo e não automatiza
jogabilidade. Mesmo assim, use por sua conta.

**A IA é paga?**
Sem configurar nada, o botão **IA** abre o Claude no navegador com a pergunta e os dados da build prontos (é só colar
com `Ctrl+V`), usando sua conta normal. Se quiser a resposta **dentro** do programa, coloque sua própria chave da API
da Anthropic em **IA → Chave (opcional)** (cobrada à parte, por uso). A chave fica só no seu PC.

**Onde ficam minhas configurações?**
Em `%APPDATA%\PConc Helper` (botão **Pasta de dados** nas Configurações).

**Não achou meu Client.txt.**
Use o botão **Client.txt** e escolha o arquivo em `...\Path of Exile\logs\Client.txt`.

## Rodar pelo código

Precisa de Python 3.9+ para Windows. Opcional: `pip install pillow` (imagens da árvore).

```bash
python src/pconc_helper.pyw
```

Para gerar o `.exe`: dois cliques em `src/Gerar_EXE.bat` (usa PyInstaller).

O `.exe` das versões é gerado automaticamente pelo GitHub Actions a partir deste código
([`.github/workflows/gerar-exe.yml`](.github/workflows/gerar-exe.yml)), então o que você baixa é exatamente o que está aqui.

## Créditos

- Build e guia: **animeprincess** — [Poisonous Concoction of Bouncing Pathfinder (Mobalytics)](https://mobalytics.gg/poe/builds/poisonous-concoction-of-bouncing-pathfinder-animeprincess)
- Preços: [poe.ninja](https://poe.ninja) · Trade e dados da árvore: [pathofexile.com](https://www.pathofexile.com)
- Estilo do filtro inspirado no [NeverSink's Filter](https://github.com/NeverSinkDev/NeverSink-Filter)
- Criado por **Gabriel Correa (FL)**, com a ajuda do Claude.

Projeto de fã, sem ligação com a Grinding Gear Games. Path of Exile é marca da Grinding Gear Games.

Licença [MIT](LICENSE).
