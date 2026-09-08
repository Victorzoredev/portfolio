"""
tests/test_gate_duracao.py
===========================
O manifesto tem que respeitar a duração que o próprio prompt manda.

O scriptwriter já pedia 5–12 minutos e segmentos de slide de 25–45s. O vídeo
de 27/08 saiu com 3min29 e slides de 13,5 a 21,4s — porque NADA validava.
`validate_manifest` conferia proporção de avatar, contagem de segmentos e fala
vazia, e nenhuma duração.

O mecanismo de 3 tentativas corretivas já existia. Faltava o que checar.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from manifest_builder import (  # noqa: E402
    DURACAO_MAX_S,
    DURACAO_MIN_S,
    validate_manifest,
)


def _manifesto(segs):
    return {"youtube": {"segments": segs}}


def _seg(sid, kind, dur, script="fala do segmento com palavras suficientes"):
    s = {"id": sid, "kind": kind, "script": script, "min_duration_s": dur}
    if kind == "slide":
        s["slide"] = sid
    return s


def _equilibrado(n_slides, dur_slide, dur_avatar=20):
    """Alterna avatar e slide mantendo a proporção dentro da faixa do produto."""
    segs = [_seg("yt-01", "avatar", dur_avatar)]
    for i in range(n_slides):
        segs.append(_seg(f"yt-s{i}", "slide", dur_slide))
        if i % 3 == 2:
            segs.append(_seg(f"yt-a{i}", "avatar", dur_avatar))
    segs.append(_seg("yt-fim", "avatar", dur_avatar))
    return segs


def test_video_curto_demais_e_recusado():
    """O caso exato de 27/08: 12 segmentos somando 3min29."""
    problemas, stats = validate_manifest(_manifesto(_equilibrado(8, 16)))
    assert stats["total_duration_s"] < DURACAO_MIN_S
    assert any("abaixo do piso" in p for p in problemas)


def test_video_na_faixa_passa():
    problemas, stats = validate_manifest(_manifesto(_equilibrado(14, 32)))
    assert DURACAO_MIN_S <= stats["total_duration_s"] <= DURACAO_MAX_S
    assert not any("piso" in p or "teto" in p for p in problemas), problemas


def test_video_longo_demais_e_recusado():
    problemas, _ = validate_manifest(_manifesto(_equilibrado(30, 40)))
    assert any("acima do teto" in p for p in problemas)


def test_slide_curto_e_recusado_mesmo_com_total_na_faixa():
    """
    Um total dentro da faixa pode esconder muitos slides atropelados. Foi
    assim que o vídeo saiu: cada slide com metade do tempo especificado.
    """
    segs = _equilibrado(24, 14)          # muitos slides curtos, total alto
    problemas, stats = validate_manifest(_manifesto(segs))
    assert stats["total_duration_s"] >= DURACAO_MIN_S
    assert any("curtos demais" in p for p in problemas)


def test_a_mensagem_diz_como_corrigir():
    """
    A nota volta para o modelo numa retentativa. "Alongue" e "não corte o
    assunto" evitam a saída fácil de encher com segmento vazio.
    """
    problemas, _ = validate_manifest(_manifesto(_equilibrado(8, 16)))
    curta = next(p for p in problemas if "abaixo do piso" in p)
    assert "Alongue" in curta and "não corte o assunto" in curta


def test_segmento_sem_duracao_declarada_nao_quebra():
    """`min_duration_s` ausente é estimado pelo texto; não pode levantar."""
    segs = [
        {"id": "yt-01", "kind": "avatar", "script": "palavra " * 40},
        {"id": "yt-02", "kind": "slide", "slide": "yt-02", "script": "palavra " * 90},
    ]
    problemas, _ = validate_manifest(_manifesto(segs))
    assert isinstance(problemas, list)


# ── CTAs ──────────────────────────────────────────────────────────────────────

def _com_ctas(segs):
    """Insere os dois CTAs onde o roteiro real os teria."""
    meio = len(segs) // 2
    return (
        segs[:meio]
        + [_seg("yt-cta", "avatar", 12)]
        + segs[meio:-1]
        + [_seg("yt-art", "avatar", 14), segs[-1]]
    )


def test_roteiro_sem_cta_e_recusado():
    """
    Nenhum dos beats disponíveis era CTA e o roteirista nunca foi instruído a
    criar um — o vídeo fechava no assunto e não convidava a nada.
    """
    problemas, _ = validate_manifest(_manifesto(_equilibrado(14, 32)))
    assert any("cta_meio" in p for p in problemas)
    assert any("cta_artigo" in p for p in problemas)


def test_roteiro_com_os_dois_ctas_passa():
    segs = _com_ctas(_equilibrado(14, 32))
    segs[len(segs) // 2]["beat"] = "cta_meio"
    segs[-2]["beat"] = "cta_artigo"
    problemas, _ = validate_manifest(_manifesto(segs))
    assert not any("cta" in p for p in problemas), problemas


def test_video_nao_pode_terminar_num_pedido():
    """O vídeo fecha no resumo. Terminar pedindo algo desperdiça o fecho."""
    segs = _equilibrado(14, 32)
    segs[len(segs) // 2]["beat"] = "cta_meio"
    segs[-1]["beat"] = "cta_artigo"
    problemas, _ = validate_manifest(_manifesto(segs))
    assert any("termina num pedido" in p for p in problemas)


# ── Quase-acerto ──────────────────────────────────────────────────────────────
#
# Em 08/09 o Studio perdeu QUATRO ciclos seguidos, todos por 6% a 12% abaixo do
# piso de duração — 4,4 / 4,5 / 4,7 min contra 5. Em cada um deles o artigo já
# tinha sido escrito, revisado e publicado como rascunho no blog, e o
# `RuntimeError` do nó de vídeo jogou tudo fora por causa de trinta segundos.
#
# A regra continua certa; o modo de falhar é que estava errado. Violação
# ESTRUTURAL (o vídeo sai errado) segue fatal; violação DIMENSIONAL dentro da
# tolerância vira aviso, e sobe para o humano no gate decidir.

from manifest_builder import TOLERANCIA_DIMENSIONAL  # noqa: E402


def _com_ctas_ok(segs):
    segs = _com_ctas(segs)
    segs[len(segs) // 2]["beat"] = "cta_meio"
    segs[-2]["beat"] = "cta_artigo"
    return segs


def test_quase_no_piso_vira_aviso_e_nao_mata_o_ciclo():
    """
    O caso literal de 08/09: 4,5 min contra o piso de 5.

    Passar não é afrouxar a régua — é não jogar fora um artigo já publicado por
    causa de meio minuto de vídeo.
    """
    # 270s exatos: 10% abaixo do piso, dentro dos 15% de tolerância.
    # Montado à mão porque `_equilibrado` não dá controle fino do total.
    segs = _com_ctas_ok(_equilibrado(9, 22, dur_avatar=12))
    total = sum(x["min_duration_s"] for x in segs)
    segs[1]["min_duration_s"] += 270 - total      # ajusta um slide para fechar 270
    problemas, stats = validate_manifest(_manifesto(segs))

    total = stats["total_duration_s"]
    assert DURACAO_MIN_S * (1 - TOLERANCIA_DIMENSIONAL) <= total < DURACAO_MIN_S, total
    assert not any("abaixo do piso" in p for p in problemas), problemas
    assert any("abaixo do piso" in a for a in stats["avisos"]), stats["avisos"]


def test_curto_demais_continua_fatal():
    """
    O vídeo de 27/08 — 3min29, 30% abaixo. A tolerância não pode salvá-lo: ali
    o problema não era meio minuto, era um vídeo pela metade.
    """
    problemas, stats = validate_manifest(_manifesto(_equilibrado(8, 16)))
    assert stats["total_duration_s"] < DURACAO_MIN_S * (1 - TOLERANCIA_DIMENSIONAL)
    assert any("abaixo do piso" in p for p in problemas)


def test_slide_no_limite_vira_aviso():
    """19s contra o piso de 20 é legível. 14s é um slide piscando."""
    segs = _com_ctas_ok(_equilibrado(14, 32))
    segs[2]["min_duration_s"] = 19          # 5% abaixo — dentro da tolerância
    problemas, stats = validate_manifest(_manifesto(segs))
    assert not any("curtos demais" in p for p in problemas), problemas
    assert any("no limite" in a for a in stats["avisos"]), stats["avisos"]


def test_slide_muito_curto_continua_fatal():
    segs = _com_ctas_ok(_equilibrado(14, 32))
    segs[2]["min_duration_s"] = 12          # 40% abaixo
    problemas, _ = validate_manifest(_manifesto(segs))
    assert any("curtos demais" in p for p in problemas)


def test_violacao_estrutural_ignora_a_tolerancia():
    """
    Avatar fora da faixa produz um vídeo ERRADO, não um vídeo pior — foi assim
    que um roteiro achatado virou 163s de avatar puro. Nenhuma margem se aplica.
    """
    segs = [_seg("yt-01", "avatar", 200), _seg("yt-02", "slide", 200)]
    problemas, _ = validate_manifest(_manifesto(segs))
    assert any("avatar ocupa" in p for p in problemas)

    sem_slide = [_seg("yt-01", "avatar", 320)]
    problemas, _ = validate_manifest(_manifesto(sem_slide))
    assert any("ilustração" in p for p in problemas)


def test_manifesto_limpo_nao_gera_aviso():
    segs = _com_ctas_ok(_equilibrado(14, 32))
    problemas, stats = validate_manifest(_manifesto(segs))
    assert problemas == [], problemas
    assert stats["avisos"] == [], stats["avisos"]


# ── A nota corretiva ──────────────────────────────────────────────────────────

def test_nota_de_video_curto_aponta_secao_do_artigo_nao_pede_palavras():
    """
    Vídeo curto é falta de ASSUNTO, não falta de palavras.

    A primeira versão desta nota respondia "vídeo de 4,5 min" com "escreva ~58
    palavras". Isso é pedir enchimento: o modelo alonga o que já disse, bate a
    duração e piora o vídeo. A duração sai da contagem de palavras, que sai de
    quanto assunto o roteiro cobriu — então a nota tem que dizer QUAL seção do
    artigo ficou de fora.
    """
    from graph.nodes import _nota_corretiva

    artigo = (
        "Intro solta\n\n"
        "## O colapso matemático\ntexto\n\n"
        "## O ciclo no Cursor\ntexto\n\n"
        "### Subseção que não conta\ntexto\n\n"
        "## Matriz de decisão\ntexto\n"
    )
    manifesto = {"youtube": {"segments": [
        {"id": "yt-01", "beat": "hook"}, {"id": "yt-02", "beat": "teoria"},
    ]}}

    nota = _nota_corretiva(
        ["vídeo de 4.5 min — abaixo do piso de 5 min"],
        {"avatar_share": 0.2},
        manifesto=manifesto,
        artigo_markdown=artigo,
    )

    # Nomeia o inventário do artigo e o que já foi coberto.
    assert "Matriz de decisão" in nota
    assert "O ciclo no Cursor" in nota
    assert "hook, teoria" in nota
    # `###` não é seção de primeiro nível.
    assert "Subseção que não conta" not in nota
    # E manda ACRESCENTAR, não esticar.
    assert "ACRESCENTE" in nota
    assert "NÃO alongue" in nota


def test_nota_sem_artigo_nao_quebra():
    """O caminho legado chama sem o markdown; a nota degrada, não levanta."""
    from graph.nodes import _nota_corretiva

    nota = _nota_corretiva(["vídeo de 4.5 min — abaixo do piso de 5 min"], {"avatar_share": 0.2})
    assert "abaixo do piso" in nota


def test_nota_de_avatar_alto_continua_falando_de_proporcao():
    """A correção de avatar é de PROPORÇÃO — nada a ver com assunto faltando."""
    from graph.nodes import _nota_corretiva

    nota = _nota_corretiva(
        ["avatar ocupa 55% do vídeo (teto 40%)"],
        {"avatar_share": 0.55},
        artigo_markdown="## Uma seção\ntexto\n",
    )
    assert "55%" in nota and "20%" in nota
    assert "ACRESCENTE" not in nota      # não é problema de assunto
