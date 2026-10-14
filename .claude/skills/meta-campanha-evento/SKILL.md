---
name: meta-campanha-evento
description: Cria a campanha de Meta Ads (Facebook/Instagram) do Workshop Prático de Vendas com IA de 31/10 em Lisboa, do zero até ficar no ar. Usar quando o Bruno pedir "criar a campanha", "subir os anúncios", "montar o tráfego do workshop", "ligar a campanha" ou trocar/acrescentar criativos.
model: claude-sonnet-5-5
effort: high
---

# Criar a campanha do workshop

Conduz o Bruno, em português de Portugal e tratando por "tu", desde a configuração até à campanha no ar. Tudo passa pelos scripts em `scripts/` (Python, só biblioteca padrão). **Nunca criar nada fora deles** e nunca pelo browser.

## Ordem obrigatória

1. **Setup** — `python scripts/verificar_setup.py`. Se faltar config, guiar por `docs/1-configurar-meta.md`. O token é colado pelo Bruno no ficheiro `~/.meta-ads/config.env`; **nunca pedir o token no chat nem o escrever em ficheiro dentro do repositório**.
2. **Pixel a disparar** — o setup tem de mostrar o evento `Lead` nos últimos 7 dias. Sem isso, parar e seguir `docs/2-instalar-pixel.md`. Campanha que otimiza para um evento que nunca disparou não aprende e queima orçamento.
3. **Criativos** — ficheiros em `criativos/`, regras em `docs/3-criativos.md`. **Mínimo 3 anúncios.**
4. **Plano** — preencher `campanha/evento-31-10.json`. Os campos `A_DEFINIR` são decisões do Bruno: perguntar, não inventar (orçamento diário, raio, início, textos). Propor com a razão, ele decide.
5. **Simular** — `python scripts/criar_campanha.py campanha/evento-31-10.json` mostra o plano sem criar nada. Ler com ele.
6. **Criar PAUSADO** — `... --criar`. Tudo nasce pausado.
7. **Conferir** — `python scripts/verificar_campanha.py resultados/evento-31-10.ids.json`. Rever com ele: orçamento, datas, geografia, rastreio `sck` em cada criativo, destino. Pedir-lhe que veja a pré-visualização no Gestor de Anúncios.
8. **Ativar** — só com o OK explícito dele: `python scripts/criar_campanha.py campanha/evento-31-10.json --ativar --sim`.

## Regras que não se negociam (vêm de campanhas reais)

| Regra | Porquê |
|---|---|
| 1 campanha = 1 conjunto; orçamento diário na campanha | o orçamento concentra-se e a aprendizagem não se divide |
| Otimizar para `LEAD` enquanto a compra não for medida pelo pixel | o pagamento hoje é MB WAY/PayPal com comprovativo: a Meta não vê a compra. Quando houver checkout com evento `Purchase` a disparar, trocar para `PURCHASE` numa campanha nova |
| Início sempre à meia-noite de Lisboa e no futuro | ligar a meio do dia gasta o orçamento do dia inteiro em poucas horas |
| Fim antes do evento (`2026-10-31T00:00`) | não pagar anúncio de evento que já começou |
| Rastreio (`sck`) dentro do criativo | fora do criativo a Meta ignora em silêncio e a venda fica sem origem |
| Melhorias automáticas de criativo desligadas | a Meta altera texto e imagem sem pedir |
| Nunca botão de WhatsApp/mensagem no anúncio | leva a conversa para um número pessoal |
| Portugal: leilão mais caro que o Brasil | não comparar custos com referências brasileiras |
| Conferir sempre pelo ID (`verificar_campanha.py`) | a listagem do Gestor atrasa e mostra estados velhos |

## Textos dos anúncios

- Português de Portugal, "tu". Factos só do `campanha/evento-31-10.json` e da página: data, hora, Lisboa, 100 lugares, preço.
- **Sem promessa de ganhos** nem números de resultado que não estejam provados.
- **Urgência só se for real**: o preço passa de 10 € para 20 € depois de 15/10 às 23:59; os lugares são 100. Nada de "últimos lugares" sem contagem real.
- O texto não pode dizer que precisa de um computador ou sistema específico.

## Erros comuns da Meta e o que fazer

| Erro | Causa | Ação |
|---|---|---|
| subcode 1885499 / 1341012 | o utilizador do token não pode anunciar pela página | no Business Manager, dar ao utilizador do sistema acesso à página com permissão de anúncios |
| `3858504` | campo de melhorias automáticas inválido | não mexer no `DOF` do script |
| "start time in the past" | início já passou | `scripts/ajustar.py ... --inicio <próxima meia-noite>` |
| anúncio `DISAPPROVED` | política da Meta | ler `ad_review_feedback` no `verificar_campanha.py`, corrigir texto/imagem, criar anúncio novo |
| falha de rede ou 5xx ao criar | pode ter sido criado | correr `--criar` de novo: o script procura pelo nome antes de criar |

## Depois de ligada

Passar para a skill `meta-estrategista-evento` (análise diária e decisões).
