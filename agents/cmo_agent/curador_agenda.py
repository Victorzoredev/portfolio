# -*- coding: utf-8 -*-
"""
curador_agenda.py — O calendário como um todo, não peça a peça.

O agendamento anterior colocava cada peça no primeiro horário livre daquela
plataforma. Isso resolve colisão e não resolve RITMO: uma campanha inteira
cabia em sete dias, duas campanhas sobrepostas empilhavam, e a fila real de
06/09 tinha de 0 a 31 peças por dia — com uma semana inteira de silêncio no
meio.

Dois problemas distintos, e o segundo é pior:

  RAJADA      31 peças num dia e zero por sete. Todo algoritmo lê isso como
              perfil irregular; consistência vale mais que volume.
  OVERPOST    No LinkedIn, mais de um post por dia reduz o alcance dos dois —
              é canibalização de conteúdo, não soma. Duas peças no mesmo dia
              rendem menos que uma.

Este módulo trata a fila inteira como um calendário e redistribui: respeita o
teto de cada rede, espalha para que todo dia tenha alguma coisa, e diversifica
formato dentro do dia.

## Os tetos, e de onde vêm

Frequência ótima por plataforma (dados de 2026, ver LIMITES). O importante não
é o número em si — é que ele existe por rede, porque as redes são diferentes:

  LinkedIn    3 a 5 por SEMANA, no máximo 1 por dia. Acima disso o alcance cai
              nos dois posts.
  Feed do IG  3 a 5 por semana. Carrossel e Reel disputam o mesmo espaço.
  Story       uma sequência por dia. Story é presença, não volume.
  Threads     1 a 3 por dia — é a exceção, a rede espera frequência alta.
  Comunidade  2 a 3 por semana. Fala com quem já é inscrito; repetir cansa.

## O que este módulo NÃO faz

Não decide o que escrever nem reescreve peça. Ele só move no tempo. Quem
decide conteúdo é o `distribuidor`; quem decide horário do dia é o
`RITMO_POR_PLATAFORMA` em `social_publish`.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

logger = logging.getLogger("cmo_agent.curador_agenda")


# ── Tetos por plataforma ──────────────────────────────────────────────────────

# `dia` é o limite que evita overpost; `semana` é o que evita rajada.
#
# Uma "peça" aqui é a UNIDADE que o público percebe: uma sequência de stories é
# uma peça, não três. Contar documentos faria o teto de story disparar no
# primeiro post e o de LinkedIn nunca disparar.
LIMITES: dict[str, dict[str, int]] = {
    "linkedin":          {"dia": 1, "semana": 5},
    "instagram_feed":    {"dia": 1, "semana": 5},   # carrossel e reel dividem
    "instagram_story":   {"dia": 1, "semana": 7},   # presença diária
    "threads":           {"dia": 2, "semana": 10},  # a rede espera frequência
    "youtube_community": {"dia": 1, "semana": 3},
    "youtube_shorts":    {"dia": 1, "semana": 3},
}

# Quantos dias à frente o curador pode empurrar uma peça. Além disto ela perde
# relação com o vídeo que promove — melhor aceitar um dia mais cheio.
HORIZONTE_DIAS = 21

# Meta de presença: todo dia deveria ter pelo menos uma peça, em pelo menos
# duas redes quando houver material. Não é limite rígido — é o critério de
# desempate que espalha em vez de empilhar.
MIN_PECAS_POR_DIA = 1


def faixa_de_limite(platform: str, formato: str) -> str:
    """
    Qual teto governa esta peça.

    Carrossel e Reel são as duas peças de FEED do Instagram e disputam a mesma
    atenção; story é outro consumo e tem teto próprio. Tratá-los como uma coisa
    só faria uma semana de stories bloquear o feed inteiro.
    """
    if platform == "instagram":
        return "instagram_story" if formato == "story" else "instagram_feed"
    return platform


# ── Agrupamento em peças ──────────────────────────────────────────────────────

_SUFIXO_FRAME = re.compile(r"\s·\s\d+/\d+$")


def chave_da_peca(doc: dict[str, Any]) -> str:
    """
    Identidade da PEÇA, não do documento.

    Os frames de uma sequência de stories são documentos separados (o
    publisher exige isso — ver CLAUDE.md), mas o público vê uma publicação só.
    O título deles é "gancho · 2/3": tirar o sufixo reagrupa a sequência.
    """
    titulo = str(doc.get("title") or "")
    base = _SUFIXO_FRAME.sub("", titulo)
    return f"{doc.get('platform')}|{doc.get('format')}|{base}"


def _quando(doc: dict[str, Any]) -> str:
    return str(doc.get("scheduled_at") or doc.get("scheduledAt") or "")


def _dia_brt(iso: str, offset_h: int = 3) -> Optional[datetime]:
    """A data LOCAL da peça. O teto é por dia do calendário de quem vê."""
    if not iso:
        return None
    try:
        return (datetime.fromisoformat(iso) - timedelta(hours=offset_h)).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
    except ValueError:
        return None


# ── O curador ─────────────────────────────────────────────────────────────────

def diagnosticar(docs: Iterable[dict[str, Any]]) -> list[str]:
    """
    O que está errado no calendário atual, em linguagem de revisão.

    Roda antes e depois do rebalanceamento: é assim que se vê se ele ajudou.
    """
    por_dia: dict[Any, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for d in docs:
        dia = _dia_brt(_quando(d))
        if not dia:
            continue
        por_dia[dia][faixa_de_limite(str(d.get("platform")), str(d.get("format")))].add(
            chave_da_peca(d)
        )

    if not por_dia:
        return ["calendário vazio"]

    avisos: list[str] = []
    for dia in sorted(por_dia):
        for faixa, pecas in por_dia[dia].items():
            teto = LIMITES.get(faixa, {}).get("dia", 99)
            if len(pecas) > teto:
                avisos.append(
                    f"{dia:%d/%m}: {len(pecas)} peças em {faixa} (teto {teto}/dia) "
                    f"— acima do teto o alcance cai nas duas"
                )

    dias = sorted(por_dia)
    vazios = 0
    cur = dias[0]
    while cur <= dias[-1]:
        if cur not in por_dia:
            vazios += 1
        cur += timedelta(days=1)
    if vazios:
        avisos.append(
            f"{vazios} dia(s) sem nenhuma publicação entre {dias[0]:%d/%m} e "
            f"{dias[-1]:%d/%m} — silêncio ensina o algoritmo a não distribuir"
        )

    totais = [sum(len(p) for p in por_dia[d].values()) for d in dias]
    if totais and max(totais) >= 3 * max(1, min(totais)):
        avisos.append(
            f"volume irregular: de {min(totais)} a {max(totais)} peças por dia"
        )
    return avisos


def reagendar(
    docs: list[dict[str, Any]],
    *,
    agora: Optional[datetime] = None,
    offset_h: int = 3,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Redistribui as peças pendentes respeitando os tetos de cada rede.

    Devolve `(mudancas, relatorio)`. Cada mudança é
    `{"doc": <o documento>, "de": iso, "para": iso}` — o chamador decide se
    grava. Não muta os documentos: um curador que escreve direto no banco não
    é revisável, e a revisão é o ponto.

    Regras, em ordem de força:

      1. Peça já publicada NUNCA se move. O post existe.
      2. Peça no passado não se move para o futuro sem necessidade — ela já
         está atrasada e o publisher vai pegá-la na próxima rodada.
      3. O teto DIÁRIO é rígido: é ele que evita a canibalização.
      4. O dia preferido é o original; empurra para frente só quando lota.
      5. Entre dois dias possíveis, ganha o mais VAZIO — é o que espalha e
         cobre os dias de silêncio.

    Os frames de uma story andam JUNTOS, mantendo o intervalo entre eles: são
    uma publicação só, e separá-los quebra a sequência.
    """
    agora = agora or datetime.now(timezone.utc)
    hoje_brt = (agora - timedelta(hours=offset_h)).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )

    # Só peças pendentes entram no rebalanceamento.
    pendentes = [d for d in docs if str(d.get("status")) == "planned"]
    if not pendentes:
        return [], ["nada pendente para reagendar"]

    # Agrupa documentos na PEÇA que o público vê.
    grupos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in pendentes:
        grupos[chave_da_peca(d)].append(d)

    # Ocupação inicial: o que já está publicado também conta para o teto do
    # dia. Ignorar isso deixaria o curador empilhar em cima do que já saiu.
    ocupacao: dict[tuple[Any, str], set[str]] = defaultdict(set)
    for d in docs:
        if str(d.get("status")) != "published":
            continue
        dia = _dia_brt(_quando(d), offset_h)
        if dia:
            faixa = faixa_de_limite(str(d.get("platform")), str(d.get("format")))
            ocupacao[(dia, faixa)].add(chave_da_peca(d))

    # Ordena por vencimento: a peça mais antiga escolhe primeiro, senão o
    # rebalanceamento privilegia quem foi criado por último.
    ordenados = sorted(grupos.items(), key=lambda kv: min(_quando(d) for d in kv[1]))

    mudancas: list[dict[str, Any]] = []
    for chave, docs_da_peca in ordenados:
        primeiro = min(docs_da_peca, key=_quando)
        iso_orig = _quando(primeiro)
        dia_orig = _dia_brt(iso_orig, offset_h)
        if not dia_orig:
            continue

        faixa = faixa_de_limite(str(primeiro.get("platform")), str(primeiro.get("format")))
        teto_dia = LIMITES.get(faixa, {}).get("dia", 99)

        # Peça atrasada fica onde está: já está devendo, e empurrar para o
        # futuro só aumenta o atraso.
        if dia_orig < hoje_brt:
            ocupacao[(dia_orig, faixa)].add(chave)
            continue

        alvo = None
        for salto in range(0, HORIZONTE_DIAS):
            candidato = dia_orig + timedelta(days=salto)
            if len(ocupacao[(candidato, faixa)]) < teto_dia:
                alvo = candidato
                break

        if alvo is None:
            # Horizonte esgotado: mantém o dia original e aceita o excesso, em
            # vez de jogar a peça para longe do vídeo que ela promove.
            logger.warning("[curador] %s sem dia livre em %d dias", faixa, HORIZONTE_DIAS)
            alvo = dia_orig

        ocupacao[(alvo, faixa)].add(chave)

        if alvo != dia_orig:
            delta = alvo - dia_orig
            for doc in docs_da_peca:
                antes = _quando(doc)
                try:
                    novo = (datetime.fromisoformat(antes) + delta).isoformat()
                except ValueError:
                    continue
                mudancas.append({"doc": doc, "de": antes, "para": novo})

    relatorio = [
        f"{len(grupos)} peça(s) pendente(s), {len(mudancas)} documento(s) movido(s)"
    ]
    return mudancas, relatorio
