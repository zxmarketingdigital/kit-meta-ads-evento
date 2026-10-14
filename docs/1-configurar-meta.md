# 1. Configurar o acesso à Meta

Fazes isto **uma vez**. No fim tens o ficheiro `~/.meta-ads/config.env` preenchido.

## 1.1 Criar o utilizador do sistema e o token

1. Abre **business.facebook.com** → **Definições** → **Utilizadores** → **Utilizadores do sistema** → **Adicionar**. Nome: `claude-ads`, função **Administrador**.
2. Com o utilizador selecionado, **Atribuir ativos** e dá **controlo total** a:
   - a **conta de anúncios**,
   - a **página** do Facebook (com permissão de criar anúncios),
   - o **pixel** (Origens de dados → Pixels / Conjuntos de dados).
3. Ainda no utilizador: **Gerar novo token** → escolhe a app do Business (se não existir, cria uma em developers.facebook.com, tipo "Empresa") → validade **Nunca** → permissões:
   `ads_management`, `ads_read`, `business_management`, `pages_show_list`, `pages_read_engagement`, `pages_manage_ads`.
4. Copia o token. **Não o envies a ninguém e não o coles no chat.**

## 1.2 Os IDs

| Campo | Onde está |
|---|---|
| `META_AD_ACCOUNT_ID` | Gestor de Anúncios → número da conta no topo (escreve com `act_` à frente) |
| `META_PAGE_ID` | Página do Facebook → Sobre → Transparência da página → ID |
| `META_PIXEL_ID` | Gestor de Eventos → o teu pixel → ID |
| `META_INSTAGRAM_ID` (opcional) | Business Manager → Contas do Instagram → ID |

## 1.3 Gravar o ficheiro

Cria a pasta `.meta-ads` na tua pasta pessoal e, dentro dela, o ficheiro `config.env` com o conteúdo de `config/config.exemplo.env` preenchido.

- Mac/Linux: `~/.meta-ads/config.env`
- Windows: `C:\Users\<o-teu-utilizador>\.meta-ads\config.env`

Depois corre `python scripts/verificar_setup.py`. Tudo verde = pronto.
