# -*- coding: utf-8 -*-
"""
tests/test_curador_agenda.py
============================
O calendário como um todo.

O agendamento antigo colocava cada peça no primeiro horário livre daquela
plataforma — resolvia colisão e não resolvia ritmo. Na fila real de 06/09
havia 8 sequências de story num dia só, 2 posts de LinkedIn no mesmo dia, e
uma semana inteira sem nada.

Os dois defeitos que este módulo existe para evitar:

  RAJADA     31 peças num dia e zero por sete. Todo algoritmo lê como perfil
             irregular.
  OVERPOST   No LinkedIn, dois posts no mesmo dia rendem MENOS que um: é
             canibalização, não soma.
"""

from datetime import datetime, timedelta, timezone

from curador_agenda import (
    LIMITES,
    chave_da_peca,
    diagnosticar,
    faixa_de_limite,
    reagendar,
)

AGORA = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def _doc(plataforma, formato, quando, titulo="peça", status="planned"):
    return {
        "platform": plataforma, "format": formato, "status": status,
        "scheduled_at": quando, "title": titulo,
    }


def _em(dias, hora=12):
    """ISO de um instante `dias` à frente, no fuso de gravação (UTC)."""
    return (AGORA + timedelta(days=dias)).replace(hour=hora).isoformat()


# ── A peça é o que o público vê, não o documento ──────────────────────────────

def test_frames_de_uma_story_contam_como_uma_peca():
    """
    Uma sequência de stories são 3-4 DOCUMENTOS (o publisher exige um por
    frame) e UMA publicação. Contar documentos faria o teto de story disparar
    no primeiro post e o de LinkedIn nunca disparar.
    """
    frames = [
        _doc("instagram", "story", _em(1), "Gancho da story · 1/3"),
        _doc("instagram", "story", _em(1), "Gancho da story · 2/3"),
        _doc("instagram", "story", _em(1), "Gancho da story · 3/3"),
    ]
    assert len({chave_da_peca(f) for f in frames}) == 1


def test_carrossel_e_reel_dividem_o_teto_do_feed():
    """
    Os dois ocupam o mesmo espaço de atenção no perfil. Tetos separados
    deixariam o feed com o dobro do que a rede recomenda.
    """
    assert faixa_de_limite("instagram", "carousel") == "instagram_feed"
    assert faixa_de_limite("instagram", "reel") == "instagram_feed"
    assert faixa_de_limite("instagram", "story") == "instagram_story"


# ── Overpost ──────────────────────────────────────────────────────────────────

def test_dois_linkedin_no_mesmo_dia_viram_um_por_dia():
    """
    Mais de um post por dia no LinkedIn reduz o alcance dos DOIS — o algoritmo
    trata como canibalização de conteúdo. Aconteceu em 01/09.
    """
    docs = [
        _doc("linkedin", "text", _em(2), "primeiro"),
        _doc("linkedin", "text", _em(2), "segundo"),
    ]
    mudancas, _ = reagendar(docs, agora=AGORA)
    assert len(mudancas) == 1, "uma das duas peças tinha que sair do dia"
    assert mudancas[0]["para"] > mudancas[0]["de"]


def test_threads_aceita_mais_de_um_por_dia():
    """
    O teto é POR REDE, não global. O Threads espera frequência alta — aplicar
    a regra do LinkedIn ali desperdiça a rede.
    """
    docs = [
        _doc("threads", "thread", _em(2), "a"),
        _doc("threads", "thread", _em(2), "b"),
    ]
    mudancas, _ = reagendar(docs, agora=AGORA)
    assert mudancas == [], "Threads suporta 2 no mesmo dia"
    assert LIMITES["threads"]["dia"] > LIMITES["linkedin"]["dia"]


def test_excesso_de_story_se_espalha_pelos_dias_seguintes():
    """
    Oito sequências num dia foi o caso real de 03/09. Story é presença
    diária, não volume diário.
    """
    docs = [_doc("instagram", "story", _em(1), f"story {i} · 1/3") for i in range(5)]
    mudancas, _ = reagendar(docs, agora=AGORA)

    finais = {}
    for d in docs:
        finais[chave_da_peca(d)] = d["scheduled_at"]
    for m in mudancas:
        finais[chave_da_peca(m["doc"])] = m["para"]

    dias = [datetime.fromisoformat(v).date() for v in finais.values()]
    assert len(set(dias)) == 5, f"as 5 sequências tinham que cair em 5 dias: {dias}"


# ── O que não pode ser movido ─────────────────────────────────────────────────

def test_peca_publicada_nunca_se_move():
    """O post já existe na rede. Mover o registro não muda o mundo."""
    docs = [
        _doc("linkedin", "text", _em(2), "a", status="published"),
        _doc("linkedin", "text", _em(2), "b", status="published"),
    ]
    mudancas, _ = reagendar(docs, agora=AGORA)
    assert mudancas == []


def test_publicada_ocupa_o_dia_para_a_pendente():
    """
    Ignorar o que já saiu deixaria o curador empilhar em cima dele — o dia
    ficaria com dois posts de LinkedIn do mesmo jeito.
    """
    docs = [
        _doc("linkedin", "text", _em(2), "ja saiu", status="published"),
        _doc("linkedin", "text", _em(2), "pendente"),
    ]
    mudancas, _ = reagendar(docs, agora=AGORA)
    assert len(mudancas) == 1
    assert mudancas[0]["doc"]["title"] == "pendente"


def test_peca_atrasada_fica_onde_esta():
    """
    Ela já está devendo. Empurrar para o futuro aumenta o atraso em vez de
    resolver — o publisher a pega na próxima rodada.
    """
    docs = [_doc("linkedin", "text", _em(-3), "atrasada")]
    mudancas, _ = reagendar(docs, agora=AGORA)
    assert mudancas == []


def test_frames_da_mesma_story_andam_juntos():
    """
    Separar os frames quebra a sequência: o público veria o frame 2 num dia e
    o 3 no outro. O intervalo entre eles é preservado.
    """
    docs = [
        _doc("instagram", "story", _em(1, 12), "ocupa · 1/3"),
        _doc("instagram", "story", _em(1, 12), "move · 1/3"),
        _doc("instagram", "story",
             (AGORA + timedelta(days=1)).replace(hour=12, minute=3).isoformat(),
             "move · 2/3"),
        _doc("instagram", "story",
             (AGORA + timedelta(days=1)).replace(hour=12, minute=6).isoformat(),
             "move · 3/3"),
    ]
    mudancas, _ = reagendar(docs, agora=AGORA)
    movidos = [m for m in mudancas if "move" in m["doc"]["title"]]
    assert len(movidos) == 3, "os três frames tinham que se mover juntos"

    novos = sorted(datetime.fromisoformat(m["para"]) for m in movidos)
    assert (novos[1] - novos[0]) == timedelta(minutes=3)
    assert (novos[2] - novos[1]) == timedelta(minutes=3)
    assert len({d.date() for d in novos}) == 1, "a sequência não pode cruzar dias"


# ── Diagnóstico ───────────────────────────────────────────────────────────────

def test_diagnostico_acusa_overpost():
    docs = [
        _doc("linkedin", "text", _em(2), "a"),
        _doc("linkedin", "text", _em(2), "b"),
    ]
    avisos = diagnosticar(docs)
    assert any("linkedin" in a and "teto" in a for a in avisos)


def test_diagnostico_acusa_dia_vazio():
    """
    Silêncio ensina o algoritmo a não distribuir. Sete dias sem nada foi o
    que aconteceu entre 21 e 27/08.
    """
    docs = [
        _doc("linkedin", "text", _em(1), "a"),
        _doc("linkedin", "text", _em(6), "b"),
    ]
    avisos = diagnosticar(docs)
    assert any("sem nenhuma publicação" in a for a in avisos)


def test_rebalanceamento_reduz_as_violacoes():
    """A prova de que o curador serve: menos dias acima do teto depois dele."""
    docs = [_doc("instagram", "story", _em(1), f"s{i} · 1/3") for i in range(6)]
    docs += [_doc("linkedin", "text", _em(1), f"li{i}") for i in range(3)]

    antes = len([a for a in diagnosticar(docs) if "teto" in a])
    mudancas, _ = reagendar(docs, agora=AGORA)
    for m in mudancas:
        m["doc"]["scheduled_at"] = m["para"]
    depois = len([a for a in diagnosticar(docs) if "teto" in a])

    assert depois < antes, f"violações não caíram: {antes} → {depois}"
    assert depois == 0
