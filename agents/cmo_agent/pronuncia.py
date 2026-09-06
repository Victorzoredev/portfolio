# -*- coding: utf-8 -*-
"""
pronuncia.py — Grafia falada ↔ grafia escrita.

O roteirista escreve o script em português fonético para o ElevenLabs
pronunciar termos em inglês corretamente: "prompt" vira "prómpti", "tokens"
vira "tóquens", "API" vira "ê-pê-í". Está certo para o ÁUDIO.

O problema é que esse mesmo texto alimenta duas coisas que são LIDAS, não
ouvidas:

  - a legenda queimada no vídeo (corrigido em `pipeline/shared/captions.py`);
  - o texto das ILUSTRAÇÕES, que o slide_designer copia do script.

Num slide de 02/09 saiu "Tóquens por ciclo para falhas estruturais básicas",
queimado no vídeo e reaproveitado como imagem do LinkedIn. Num canal técnico
isso lê como erro de português.

A tabela é a mesma do prompt do scriptwriter (REGRA 2), que a declara
exaustiva — por isso a reversão é segura. Se um termo entrar lá, entra aqui.
"""

from __future__ import annotations

import re

PRONUNCIA_PARA_ESCRITA: dict[str, str] = {
    "lóra": "LoRA", "qiu-lóra": "QLoRA", "tiny-lóra": "TinyLoRA",
    "fain-tiúning": "fine-tuning", "tóquens": "tokens", "tóquen": "token",
    "freim-uórc": "framework", "éli-éli-êmi": "LLM", "ê-pê-í": "API",
    "êmbeding": "embedding", "bátch": "batch", "rênqui": "rank",
    "prómpti": "prompt", "prómptis": "prompts", "ínsait": "insight",
    "deplói": "deploy", "déshbord": "dashboard", "deitasséti": "dataset",
    "paip-lain": "pipeline", "mochin lérning": "machine learning",
    "cláud": "cloud", "tésti": "test", "cômit": "commit",
    "rilís": "release", "rôl-béqui": "rollback", "quéxi": "cache",
    "endi-point": "endpoint", "fítcher": "feature", "lógui": "log",
    "esse-qiu-éle": "SQL", "guê-cê-pê": "GCP", "á-dábliu-ésse": "AWS",
    "eme-éle-ops": "MLOps", "guê-pê-u": "GPU", "pê-valor": "p-valor",
    # Termos de duas palavras entram partidos também: o casamento acontece
    # palavra a palavra e "mochin lérning" inteiro nunca casaria num texto
    # onde as duas foram separadas por quebra de linha.
    "mochin": "machine", "lérning": "learning",
    "fain": "fine", "tiúning": "tuning",
}

# Maior primeiro: "prómptis" tem que casar antes de "prómpti", senão sobra um
# "s" solto na tela.
_RE = re.compile(
    r"(?<!\w)(" + "|".join(
        re.escape(k) for k in sorted(PRONUNCIA_PARA_ESCRITA, key=len, reverse=True)
    ) + r")(?!\w)",
    re.IGNORECASE,
)


def desfonetizar(texto: str) -> str:
    """
    Devolve a grafia REAL dos termos escritos por pronúncia.

    Usar só no que vai ser LIDO. O script que alimenta o TTS precisa manter a
    grafia fonética — é dela que depende a pronúncia.
    """
    if not texto:
        return texto

    def troca(m: re.Match) -> str:
        certo = PRONUNCIA_PARA_ESCRITA[m.group(1).lower()]
        # "Prómpti" no começo da frase vira "Prompt", não "prompt".
        return certo.capitalize() if m.group(1)[:1].isupper() and certo.islower() else certo

    return _RE.sub(troca, texto)


def tem_grafia_falada(texto: str) -> bool:
    """Há grafia de pronúncia neste texto? Usado para barrar antes de gastar."""
    return bool(_RE.search(texto or ""))
