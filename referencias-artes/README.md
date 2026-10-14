# Referências de artes

Modelos de arte de anúncio que já venderam em campanhas reais, para servirem de base às artes do workshop.

## O que está aqui

| Pasta / ficheiro | O que é |
|---|---|
| `validadas/` | 12 artes que mais venderam em campanhas de produto de entrada (ordenadas da que mais vendeu, `01`, para baixo). **São referência de layout**: os textos, preços em reais e nomes de produto são de outra oferta e **não se copiam**. |
| `formatos.json` | Catálogo de 92 layouts escritos como prompt para gerador de imagem (ChatGPT/DALL·E, Gemini, Midjourney, Ideogram…). Cada um tem `{marcadores}` para preencher com os dados do workshop. |

## O que as artes validadas têm em comum

1. **Título enorme no topo**, em duas cores (preto/branco + laranja), legível no telemóvel sem ampliar.
2. **Lista do que a pessoa leva** em 3–5 linhas curtas com ícone, sempre visível.
3. **Um elemento visual central concreto**: ecrã com o sistema a funcionar, telemóvel, portátil, organigrama, mascote. Nunca uma imagem genérica de banco.
4. **Faixa de oferta em baixo** com o preço e um botão ("Saber mais", "Quero o meu lugar").
5. **Selos pequenos no rodapé** (ex.: data, local, lugares limitados).
6. Fundo claro off-white **ou** fundo escuro com acento laranja. Os dois venderam; testar os dois.

| Ficheiro | Padrão |
|---|---|
| `01`, `05` | faixa "oferta" no topo, título, lista à esquerda e ecrã do sistema à direita (fundo claro) |
| `02` | pergunta de dor no topo ("Ainda fazes X à mão?") + checklist + portátil |
| `03`, `13` | fundo escuro, título à esquerda, objeto 3D/telemóvel à direita, caixa de preço |
| `04` | título gigante de promessa concreta + 3 selos + bloco de oferta |
| `06` | fundo escuro, organigrama com a peça central e os ramos (o que faz) |
| `07`, `12` | frase curta forte no topo + lista do que está incluído |
| `08`, `09` | mascote/personagem a apresentar a oferta |
| `11` | **especialista em pessoa** à frente de um painel — o formato mais natural para ti: a tua foto real + o que se aprende |

## Como montar uma arte do workshop

1. Escolhe 3 formatos diferentes (ex.: `11` com a tua foto, `06` organigrama, `02` pergunta de dor). Variar o **layout e o ângulo**, não só a cor.
2. Abre `formatos.json`, copia a `descricao_layout` do formato e troca `{base}` pelo bloco abaixo.
3. Troca cada marcador pelos valores da tabela. **Tudo o que não estiver na página de inscrição não entra na arte.**
4. Gera em 4:5 (1080×1350). Para Stories/Reels, gera também em 9:16 (1080×1920) deixando livres os 14% de cima e os 25% de baixo (ver `docs/3-criativos.md`).
5. Confere cada letra antes de usar: o gerador erra acentos e às vezes inventa palavras. Arte com erro não sobe.
6. Guarda em `criativos/` e aponta no `campanha/evento-31-10.json`.

### Bloco `{base}` (cola no lugar de `{base}`)

```
Anúncio de tráfego pago em PORTUGUÊS DE PORTUGAL, formato vertical 4:5, estilo infográfico de oferta premium, limpo e organizado. Cores: preto grafite #1A1A1A, off-white #FAFAF9 e laranja/âmbar #D97706 como acento. Tipografia sans-serif bold condensada e moderna, com proporções naturais de todos os elementos — pessoas, rostos, mãos, ecrãs e letras nunca esticados nem distorcidos. Cards brancos com cantos arredondados e sombra suave. Todo o texto em português de Portugal com acentuação perfeita, nada cortado nas bordas. O título principal é o nome do workshop ou a headline; o preço nunca é o título e só aparece na faixa de oferta. Nenhuma logo, marca ou nome de empresa inventado. Alta legibilidade, contraste forte.
```

### Valores dos marcadores

| Marcador | O que pôr | Exemplo / fonte |
|---|---|---|
| `{topo}` | faixa curta no topo com público ou data | "SÁBADO 31/10 · LISBOA · 08:00–12:00" ou "PARA CONSULTORES IMOBILIÁRIOS" |
| `{h1}` / `{h2}` | título em duas partes (preto + laranja) | "WORKSHOP PRÁTICO" / "DE VENDAS COM IA" |
| `{pill}` | pílula por baixo do título | "PRESENCIAL EM LISBOA" |
| `{badge}` | selo pequeno | "100 LUGARES" |
| `{bullets}` / `{bullets_curtos}` | o que a pessoa leva do workshop, 3–5 itens | **tirar da página de inscrição**, palavra por palavra quando possível |
| `{mockup}` | o que aparece no ecrã/telemóvel | ex.: "uma conversa de WhatsApp com um cliente a ser respondida" — só se isso for mostrado no workshop |
| `{PRECO_DE}` / `{PRECO_POR}` | **não usar "De/Por"** se não houver preço riscado de verdade | até 15/10: "Bilhete 10 € até 15/10 (depois 20 €)" · depois de 15/10: "Bilhete 20 €" |
| `{cta}` | texto do botão | "QUERO O MEU LUGAR" · "SABER MAIS" |
| `{selos}` | 2–3 selos no rodapé | "31/10 · LISBOA", "08:00–12:00", "100 LUGARES" |
| `{nome}` | nome do evento | "Workshop Prático de Vendas com IA" |
| `{selo_faixa}` | selo da faixa de oferta | "LUGARES LIMITADOS" (só enquanto for verdade) |

### Regras que valem para todas

- Público nomeado na arte sempre que possível: consultores imobiliários, gestores de crédito, network marketing. Uma arte por público converte melhor do que uma arte para todos.
- **Sem números de faturação, percentagens de resultado nem gráficos a subir.** O único valor em euros é o do bilhete.
- **Urgência só a real**: a subida de preço depois de 15/10 e os lugares que de facto restam.
- Alguns prompts falam de "Claude Code", "agentes" ou "sistema": troca pelo que o workshop realmente mostra. Se não se aplicar, escolhe outro formato.
- Formatos com `"elemento_tech": true` e `"lista_entregaveis": true` são os que seguem o padrão das artes que venderam: começa por esses.
