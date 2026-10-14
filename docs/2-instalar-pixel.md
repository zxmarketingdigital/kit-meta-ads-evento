# 2. Pixel na página de inscrição

A campanha aprende com o evento **`Lead`** (alguém que enviou o formulário de inscrição). Sem o pixel a disparar, a Meta não sabe quem procurar e o orçamento é gasto às cegas. **Não ligues a campanha antes de isto estar a funcionar.**

## O que instalar

Quem gere a página `eventos.be-pro.pt/ia-contactos/` acrescenta, no `<head>`, o código base do pixel (troca `PIXEL_ID` pelo teu):

```html
<script>
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'PIXEL_ID');
fbq('track', 'PageView');
</script>
```

E, **no momento em que o formulário de inscrição é enviado com sucesso** (antes de mostrar "como pagar"):

```js
fbq('track', 'Lead');
```

Quando o pagamento passar a ser feito numa plataforma com página de obrigado (ex.: Hotmart), essa página dispara `fbq('track', 'Purchase', {value: 10, currency: 'EUR'})` com o valor real pago. A partir daí, a campanha seguinte pode otimizar para compra.

## Como confirmar

1. Instala a extensão **Meta Pixel Helper** no Chrome, abre a página e faz uma inscrição de teste: tem de aparecer `PageView` e `Lead`.
2. No **Gestor de Eventos → Testar eventos** os dois eventos aparecem em tempo real.
3. Corre `python scripts/verificar_setup.py`: a linha "Evento Lead" tem de ser maior que zero.

O parâmetro `sck` que os anúncios acrescentam ao link já é preservado pela página: não o removas.
