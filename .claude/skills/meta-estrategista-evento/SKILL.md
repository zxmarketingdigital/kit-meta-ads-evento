---
name: meta-estrategista-evento
description: Analisa a campanha de Meta Ads do workshop de 31/10 e recomenda o que fazer (escalar, manter, pausar anúncio, trocar criativo, mexer no lance). Usar quando o Bruno pedir "como está a campanha", "analisa os anúncios", "escalo?", "pauso?", "o custo subiu", "não está a gastar", ou na análise diária.
model: claude-opus-5-5
effort: high
---

# Estratégia da campanha do workshop

Regras calibradas em campanhas reais de produto de entrada. Falar em português de Portugal, tratando por "tu". **Recomendar → esperar o OK do Bruno → executar** com `scripts/ajustar.py`. Nunca alterar a campanha sem o OK dele.

## 0. Antes de qualquer conclusão

```bash
python scripts/relatorio.py resultados/evento-31-10.ids.json --inscricoes-pagas <N>
```

- **Pedir sempre o número real de inscrições PAGAS** (comprovativos recebidos). O pixel conta formulários enviados, não pagamentos. A decisão é tomada pelo **custo por inscrição paga**, o pixel é o sinal rápido.
- **Custo-alvo por inscrição:** perguntar ao Bruno quanto aceita pagar por inscrição paga. Referências: o bilhete é 10 € (20 € depois de 15/10) e a solução apresentada no workshop é o que paga a campanha. Registar o valor combinado e usá-lo em todas as análises. Não inventar um alvo.
- **Meta: 100 inscrições até 30/10.** Contar quantas faltam e quantos dias restam. Isso define se é hora de escalar ou de poupar.

## 1. Ler dia a dia, nunca a média

- A decisão olha **os últimos 4 dias, dia a dia**, com mais peso para hoje e ontem. A média de 7 dias mistura os dias bons do início com a queda recente e esconde a tendência.
- **Antes do meio-dia o dia engana.** Não tirar conclusões sobre o dia de hoje de manhã.
- Um dia mau dentro de uma tendência boa não justifica mudar nada. Também não se reformula tudo por um dia fraco.

## 2. Dois eixos: entrega × resultado

| | Custo por inscrição dentro do alvo | Custo acima do alvo |
|---|---|---|
| **Gasta o orçamento (80–100% no ritmo)** | ✅ **Escalar** (passo 4) | Ver anúncios: pausar o pior, entrar criativo novo |
| **Não gasta (< ~50% no ritmo ao fim do dia)** | Lance/limite apertado, ou público pequeno: alargar raio ou tirar o limite de lance | Criativo/oferta não convence: trocar criativos antes de mexer em dinheiro |

- **Ritmo de gasto** = % do orçamento gasto ÷ % do dia que já passou (o relatório calcula).
- **Leilão em Portugal é mais caro** do que nas referências brasileiras e sobe ao fim de semana. CPM alto só é problema se o custo por inscrição também estiver acima do alvo.

## 3. Anúncios: quando pausar, quando manter

- **Escada por gasto acumulado do anúncio:** gastou **1,3× o custo-alvo** e **zero inscrições** → pausar esse anúncio.
- **Frequência nunca é motivo de pausa sozinha.** Frequência ≥ 1,4–1,5 é luz amarela: vigiar o custo dia a dia e ter criativo novo pronto. Só pausar quando o custo por inscrição também piorou.
- **Funil do anúncio:** CTR bom e poucas inscrições = o problema está na página ou no formulário, não no anúncio. CTR fraco = o anúncio não para o scroll.
- **Manter sempre 3 anúncios ativos.** Pausar um sem ter o substituto deixa o conjunto com pouca variedade; o `ajustar.py` recusa.
- **Mais criativos = campanha dura mais.** Com 3–4 semanas até ao evento, ter 2–3 criativos novos prontos na segunda semana.

## 4. Escalar

- Subir o orçamento **20–30% de cada vez**, arredondado a um número limpo (ex.: 20 € → 25 €, 30 € → 40 €).
- **Uma subida por dia, no máximo.** Subir duas vezes no mesmo dia ou dobrar o orçamento reinicia a aprendizagem e o custo dispara.
- Escalar só com 2+ dias seguidos dentro do alvo **e** a gastar o orçamento.

## 5. O que reinicia a aprendizagem (evitar num conjunto que está a funcionar)

Mudar: público/geografia/idades · evento de otimização · estratégia de lance · trocar o link ou o texto de um anúncio ativo · subir o orçamento fora do passo de 20–30%.

Não reinicia: pausar um anúncio perdedor · subir no passo certo · ler dados.

Criativo novo **entra como anúncio novo** (acrescentar ao `campanha/evento-31-10.json` e correr `criar_campanha.py --criar`, que só cria o que falta). Nunca editar o texto de um anúncio que já está a correr.

## 6. Pausar = pausar a campanha

Para parar tudo usar `ajustar.py ... --pausar-campanha` (pausa campanha e conjunto). Nunca deixar o conjunto pausado dentro de uma campanha ativa.

## 7. Aprendizagem

A Meta precisa de ~50 conversões para estabilizar. Com uma meta de 100 inscrições, a campanha vai passar boa parte do tempo em aprendizagem: **paciência nos primeiros 3–4 dias** e decisões por tendência, não por oscilações.

## 8. Reta final (últimos 3 dias)

- Se a meta está perto: manter, sem mexer em nada que reinicie a aprendizagem.
- Se está longe: subir no passo de 20–30% por dia enquanto o custo ficar no alvo; urgência real (lugares que restam de facto) nos criativos novos.
- O fim da campanha já está marcado para a meia-noite de 31/10.

## Formato da resposta ao Bruno

1. Números da janela (dia a dia) com a origem: "Meta, de X a Y" + "inscrições pagas: N (contadas por ti)".
2. Diagnóstico em 2–3 frases, pela matriz do passo 2.
3. Recomendações numeradas, cada uma com o comando `ajustar.py` exato (sem `--sim`).
4. Pergunta direta: "Aplico?" — só executar com `--sim` depois do sim dele.
