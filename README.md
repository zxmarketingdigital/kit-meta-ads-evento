# Kit Meta Ads — Workshop Prático de Vendas com IA (31/10, Lisboa)

Duas skills para o Claude Code criarem e gerirem a campanha de Facebook/Instagram do workshop:

- **`meta-campanha-evento`** — cria a campanha do zero (tudo pausado, conferido, depois ligado).
- **`meta-estrategista-evento`** — análise diária e decisões: escalar, pausar anúncio, trocar criativo.

Funciona em Windows, Mac ou Linux. Precisa de **Python 3.9+** e do **Claude Code**.

## Instalar

```bash
git clone https://github.com/zxmarketingdigital/kit-meta-ads-evento.git
cd kit-meta-ads-evento
claude
```

Dentro do Claude Code escreve: **"quero criar a campanha do workshop"**. Ele conduz o resto.

## O que vais precisar

1. Acesso de administrador ao **Business Manager** da Meta, com a conta de anúncios, a página e o pixel.
2. Um **token de utilizador do sistema** (passo a passo em [`docs/1-configurar-meta.md`](docs/1-configurar-meta.md)).
3. O **pixel instalado na página de inscrição** a enviar o evento `Lead` ([`docs/2-instalar-pixel.md`](docs/2-instalar-pixel.md)).
4. **Pelo menos 3 criativos** (imagem ou vídeo) em `criativos/` ([`docs/3-criativos.md`](docs/3-criativos.md)).

## Segurança

O token fica em `~/.meta-ads/config.env`, **fora desta pasta**, e nunca é enviado para o GitHub nem escrito no chat. Os scripts nunca o mostram.

## Comandos (o Claude corre-os por ti)

| Comando | O que faz |
|---|---|
| `python scripts/verificar_setup.py` | confere token, conta, página, pixel e página de inscrição |
| `python scripts/criar_campanha.py campanha/evento-31-10.json` | simula (não cria nada) |
| `... --criar` | cria tudo **pausado** |
| `python scripts/verificar_campanha.py resultados/evento-31-10.ids.json` | confere o que ficou criado |
| `python scripts/criar_campanha.py campanha/evento-31-10.json --ativar --sim` | liga a campanha |
| `python scripts/relatorio.py resultados/evento-31-10.ids.json` | resultados dia a dia |
| `python scripts/ajustar.py resultados/evento-31-10.ids.json ...` | orçamento, pausar/ativar anúncio, lance |

No Windows, se `python` não funcionar, usa `py`.
