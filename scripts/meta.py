"""Cliente mínimo da Graph API da Meta (só biblioteca padrão do Python).

Lê a configuração de ~/.meta-ads/config.env (ou variáveis de ambiente) e
expõe get/post/upload com retry em erro transitório. Nunca imprime o token.
"""
from __future__ import annotations

import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("META_ADS_CONFIG", Path.home() / ".meta-ads" / "config.env"))
API_VERSION = os.environ.get("META_API_VERSION", "v21.0")
GRAPH = f"https://graph.facebook.com/{API_VERSION}"


def _env_int(nome: str, default: int) -> int:
    try:
        v = int(os.environ.get(nome, default))
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default


# Timeout de cada chamada (upload de vídeo demora mais). Override por env.
HTTP_TIMEOUT = _env_int("META_HTTP_TIMEOUT", 60)
UPLOAD_TIMEOUT = _env_int("META_UPLOAD_TIMEOUT", 600)
MAX_TENTATIVAS = _env_int("META_MAX_TENTATIVAS", 4)

CAMPOS_CONFIG = ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PIXEL_ID", "META_PAGE_ID")


class MetaErro(Exception):
    def __init__(self, msg: str, payload: dict | None = None, status: int | None = None):
        super().__init__(msg)
        self.payload = payload or {}
        self.status = status


def carregar_config(obrigatorios=CAMPOS_CONFIG) -> dict:
    cfg: dict[str, str] = {}
    if CONFIG_PATH.exists():
        for linha in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k in list(CAMPOS_CONFIG) + ["META_INSTAGRAM_ID"]:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    faltam = [k for k in obrigatorios if not cfg.get(k)]
    if faltam:
        raise SystemExit(
            f"Config incompleta em {CONFIG_PATH}: faltam {', '.join(faltam)}.\n"
            "Copia config/config.exemplo.env para esse caminho e preenche (ver docs/1-configurar-meta.md)."
        )
    act = cfg.get("META_AD_ACCOUNT_ID", "")
    if act and not act.startswith("act_"):
        cfg["META_AD_ACCOUNT_ID"] = "act_" + act
    return cfg


def _mascarar(texto: str, token: str) -> str:
    return texto.replace(token, "***") if token else texto


def _rate_limit(status: int | None, payload: dict) -> bool:
    """Limite de chamadas: o pedido NÃO foi processado, repetir é seguro mesmo num POST."""
    err = payload.get("error", {}) if isinstance(payload, dict) else {}
    return status == 429 or err.get("code") in (4, 17, 32, 613, 80004)


def _transitorio(status: int | None, payload: dict) -> bool:
    if _rate_limit(status, payload):
        return True
    if status is not None and status >= 500:
        return True
    err = payload.get("error", {}) if isinstance(payload, dict) else {}
    return bool(err.get("is_transient")) or err.get("code") in (1, 2)


def _abrir(req: urllib.request.Request, timeout: int, token: str) -> dict:
    """Executa o pedido (leitura do corpo incluída) com retry só em erro transitório.

    GET repete em erro transitório. POST só repete em limite de chamadas (pedido não
    processado); erro 5xx/rede num POST pode já ter criado o objeto, por isso para
    e manda conferir no Gestor de Anúncios em vez de duplicar.
    """
    eh_post = req.get_method() == "POST"
    ultimo: Exception | None = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = {}
            err = payload.get("error", {}) if isinstance(payload, dict) else {}
            msg = err.get("error_user_msg") or err.get("message") or str(e)
            sub = err.get("error_subcode")
            ultimo = MetaErro(_mascarar(f"{msg} (code {err.get('code')}, subcode {sub})", token), payload, e.code)
            pode_repetir = _rate_limit(e.code, payload) if eh_post else _transitorio(e.code, payload)
            if not pode_repetir:
                if eh_post and e.code >= 500:
                    raise MetaErro(_mascarar(
                        f"{msg} — erro do servidor num pedido de criação/alteração: pode ter sido aplicado. "
                        "Confere no Gestor de Anúncios antes de repetir.", token), payload, e.code)
                raise ultimo
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo = MetaErro(_mascarar(f"falha de rede: {e}", token))
            if eh_post:
                raise MetaErro(_mascarar(
                    f"falha de rede num pedido de criação/alteração ({e}) — pode ter sido aplicado. "
                    "Confere no Gestor de Anúncios antes de repetir.", token))
        if tentativa < MAX_TENTATIVAS:
            time.sleep(min(30, 2 ** tentativa) + random.random())
    raise ultimo or MetaErro("falha desconhecida")


def get(caminho: str, params: dict | None = None, cfg: dict | None = None) -> dict:
    cfg = cfg or carregar_config()
    p = dict(params or {})
    for k, v in list(p.items()):
        if isinstance(v, (dict, list)):
            p[k] = json.dumps(v)
    p["access_token"] = cfg["META_ACCESS_TOKEN"]
    url = f"{GRAPH}/{caminho.lstrip('/')}?{urllib.parse.urlencode(p)}"
    return _abrir(urllib.request.Request(url, method="GET"), HTTP_TIMEOUT, cfg["META_ACCESS_TOKEN"])


def get_todos(caminho: str, params: dict | None = None, cfg: dict | None = None, limite: int = 5000) -> list:
    """Pagina até ao fim. Falha numa página do meio ABORTA (nunca devolve lista truncada)."""
    cfg = cfg or carregar_config()
    p = dict(params or {})
    p.setdefault("limit", 200)
    itens: list = []
    while True:
        r = get(caminho, p, cfg)
        itens.extend(r.get("data", []))
        nxt = r.get("paging", {}).get("next")
        after = r.get("paging", {}).get("cursors", {}).get("after")
        if not nxt or not after or len(itens) >= limite:
            return itens
        p["after"] = after


def post(caminho: str, dados: dict, cfg: dict | None = None) -> dict:
    cfg = cfg or carregar_config()
    d = dict(dados)
    for k, v in list(d.items()):
        if isinstance(v, (dict, list, bool)):
            d[k] = json.dumps(v)
    d["access_token"] = cfg["META_ACCESS_TOKEN"]
    body = urllib.parse.urlencode(d).encode("utf-8")
    req = urllib.request.Request(f"{GRAPH}/{caminho.lstrip('/')}", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    return _abrir(req, HTTP_TIMEOUT, cfg["META_ACCESS_TOKEN"])


def upload(caminho: str, arquivo: Path, campo: str, extra: dict | None = None, cfg: dict | None = None) -> dict:
    """Upload multipart (imagem em /adimages, vídeo em /advideos)."""
    cfg = cfg or carregar_config()
    fronteira = uuid.uuid4().hex
    partes: list[bytes] = []
    campos = dict(extra or {})
    campos["access_token"] = cfg["META_ACCESS_TOKEN"]
    for k, v in campos.items():
        partes.append(
            f"--{fronteira}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    tipo = mimetypes.guess_type(str(arquivo))[0] or "application/octet-stream"
    partes.append(
        f"--{fronteira}\r\nContent-Disposition: form-data; name=\"{campo}\"; filename=\"{arquivo.name}\"\r\n"
        f"Content-Type: {tipo}\r\n\r\n".encode("utf-8"))
    partes.append(arquivo.read_bytes())
    partes.append(f"\r\n--{fronteira}--\r\n".encode("utf-8"))
    req = urllib.request.Request(f"{GRAPH}/{caminho.lstrip('/')}", data=b"".join(partes), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={fronteira}")
    t0 = time.monotonic()
    r = _abrir(req, UPLOAD_TIMEOUT, cfg["META_ACCESS_TOKEN"])
    print(f"  upload {arquivo.name} levou {time.monotonic() - t0:.0f}s (teto {UPLOAD_TIMEOUT}s)")
    return r


def euros_para_centimos(valor: float) -> int:
    return int(round(float(valor) * 100))


def falhar(msg: str, codigo: int = 1):
    print(f"\n🔴 {msg}", file=sys.stderr)
    sys.exit(codigo)
