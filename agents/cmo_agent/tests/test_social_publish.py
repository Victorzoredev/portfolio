# -*- coding: utf-8 -*-
"""
Cobertura da conversão `plano_social` → documentos de `social_queue`.

Por que existe: este é o ponto onde o conteúdo deixa de ser preview e vira
publicação sob a marca do dono do canal. Um mapeamento errado aqui não dá
erro — dá post publicado errado. Em particular:

  - thread sem a raiz publica a resposta como se fosse o post principal;
  - story com 4 frames num documento só publica 1 e descarta 3 em silêncio;
  - carrossel sem imagem é recusado pelo Instagram no momento da publicação,
    dias depois de qualquer chance de perceber;
  - peça agendada para D+0 sai antes do vídeo que ela promete.
"""

from datetime import datetime, timezone

import pytest

from social_publish import (
    BRT_OFFSET_HOURS,
    MINUTOS_ENTRE_FRAMES,
    SLOTS_BRT,
    montar_itens,
)

BASE = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)


def _plano(**over):
    plano = {
        "linkedin": [{
            "id": "li-01", "gancho": "Gancho", "corpo": "Corpo",
            "hashtags": ["ia", "ml"], "comentario_fixado": "[LINK_ARTIGO]",
            "dia_offset": 1,
        }],
        "threads": [{"id": "th-01", "gancho": "Raiz", "posts": ["r1", "r2"], "dia_offset": 2}],
        "carrossel": [{
            "id": "ca-01", "gancho": "Gancho", "legenda": "Legenda", "dia_offset": 3,
            "slides": [
                {"numero": 2, "titulo": "T2", "corpo": "C2"},
                {"numero": 1, "titulo": "T1", "corpo": "C1"},
            ],
        }],
        "stories": [{
            "id": "st-01", "gancho": "Story", "dia_offset": 4,
            "frames": [
                {"ordem": 2, "texto": "F2", "ilustracao": "b",
                 "enquete": "Você já mediu isso?"},
                {"ordem": 1, "texto": "F1", "ilustracao": "a"},
            ],
        }],
        "youtube_community": [{
            "id": "yc-01", "gancho": "G", "texto": "Texto",
            "enquete_opcoes": ["a", "b"], "dia_offset": 5,
        }],
    }
    plano.update(over)
    return plano


def montar(**over):
    return montar_itens(
        _plano(**over),
        artigo_slug="meu-post",
        artigo_titulo="Meu post",
        artigo_url="https://eozore.com/pt-BR/blog/meu-post",
        serie="ia-para-lideres",
        session_id="s1",
        base=BASE,
    )


def por_canal(itens, platform, fmt=None):
    return [i for i in itens if i["platform"] == platform and (fmt is None or i["format"] == fmt)]


# ── Mapeamento de canal ───────────────────────────────────────────────────────

def test_cada_canal_vira_o_par_platform_format_que_o_publisher_conhece():
    itens = montar()
    pares = {(i["platform"], i["format"]) for i in itens}
    assert pares == {
        ("linkedin", "text"),
        ("threads", "thread"),
        ("instagram", "carousel"),
        ("instagram", "story"),
        ("youtube_community", "text"),
    }


def test_thread_leva_a_raiz_como_primeiro_post():
    # publish_thread_series posta a lista na ordem. Sem a raiz, a primeira
    # resposta vira o post principal e a thread perde o gancho.
    (t,) = por_canal(montar(), "threads")
    assert t["thread_posts"] == ["Raiz", "r1", "r2"]


def test_linkedin_mantem_o_link_fora_do_corpo():
    (p,) = por_canal(montar(), "linkedin")
    assert p["comentario_fixado"] == "[LINK_ARTIGO]"
    assert "[LINK_ARTIGO]" not in p["copy"]


def test_linkedin_anexa_as_hashtags_ao_corpo():
    (p,) = por_canal(montar(), "linkedin")
    assert p["copy"].endswith("#ia #ml")


def test_enquete_da_comunidade_entra_no_corpo_do_post():
    # A API do YouTube não expõe Community Posts: o publisher marca como
    # manual, então as opções precisam estar no texto para serem recriadas.
    (p,) = por_canal(montar(), "youtube_community")
    assert "• a" in p["copy"] and "• b" in p["copy"]


# ── Imagens ───────────────────────────────────────────────────────────────────

def test_carrossel_pede_uma_imagem_por_slide_na_ordem_do_numero():
    (c,) = por_canal(montar(), "instagram", "carousel")
    assert [r["nome"] for r in c["_render"]] == ["carrossel_ca-01_1", "carrossel_ca-01_2"]
    # Ordenado por `numero`, não pela ordem em que o modelo devolveu.
    assert "T1" in c["_render"][0]["html"]
    assert "T2" in c["_render"][1]["html"]


def test_cada_frame_de_story_vira_um_documento_com_sua_propria_imagem():
    frames = por_canal(montar(), "instagram", "story")
    assert len(frames) == 2
    assert [len(f["_render"]) for f in frames] == [1, 1]
    assert "F1" in frames[0]["_render"][0]["html"]
    assert "F2" in frames[1]["_render"][0]["html"]


def test_enquete_do_frame_e_renderizada_como_pergunta():
    # `enquete` é a pergunta inteira (FrameStory), não opções separadas por
    # '|'. Tratá-la como lista imprimia a pergunta dentro de um único botão.
    frames = por_canal(montar(), "instagram", "story")
    assert "Você já mediu isso?" in frames[1]["_render"][0]["html"]


def test_peca_de_texto_nao_pede_render():
    for canal in ("linkedin", "threads", "youtube_community"):
        for item in por_canal(montar(), canal):
            assert "_render" not in item or not item["_render"]


def test_carrossel_sem_slide_nao_entra_na_fila():
    # Instagram recusa carrossel sem mídia; melhor não enfileirar do que
    # falhar dias depois no publisher.
    itens = montar(carrossel=[{"id": "ca-x", "legenda": "L", "dia_offset": 1, "slides": []}])
    assert por_canal(itens, "instagram", "carousel") == []


def test_story_sem_frame_nao_entra_na_fila():
    itens = montar(stories=[{"id": "st-x", "gancho": "G", "dia_offset": 1, "frames": []}])
    assert por_canal(itens, "instagram", "story") == []


# ── Agenda ────────────────────────────────────────────────────────────────────

def _hora_brt(iso: str) -> int:
    return datetime.fromisoformat(iso).hour - BRT_OFFSET_HOURS


def test_nada_e_agendado_para_o_mesmo_dia_do_video():
    # O vídeo é a âncora e sai primeiro. Uma peça em D+0 promete um vídeo que
    # ainda não existe.
    itens = montar(linkedin=[{"id": "li-x", "gancho": "G", "corpo": "C",
                              "hashtags": [], "dia_offset": 0}])
    (p,) = por_canal(itens, "linkedin")
    assert datetime.fromisoformat(p["scheduled_at"]).date() > BASE.date()


def test_dia_offset_do_modelo_e_respeitado():
    itens = montar()
    dia = {i["platform"]: datetime.fromisoformat(i["scheduled_at"]).day for i in itens}
    assert dia["linkedin"] == BASE.day + 1
    assert dia["threads"] == BASE.day + 2


def test_pecas_do_mesmo_dia_ocupam_slots_diferentes():
    # Sem isto, três posts do mesmo dia saem todos às 9h e o publisher despeja
    # a campanha inteira numa execução.
    #
    # As horas vêm da escada DAQUELA plataforma (`RITMO_POR_PLATAFORMA`), não
    # de uma lista única: LinkedIn é manhã de dia útil, Instagram é meio-dia e
    # noite. O que este teste protege é que sejam DISTINTAS.
    from social_publish import RITMO_POR_PLATAFORMA

    itens = montar(
        linkedin=[
            {"id": f"li-{n}", "gancho": "G", "corpo": "C", "hashtags": [], "dia_offset": 1}
            for n in range(3)
        ],
        threads=[], carrossel=[], stories=[], youtube_community=[],
    )
    horas = [_hora_brt(i["scheduled_at"]) for i in itens]
    assert len(set(horas)) == 3, f"horários repetidos: {horas}"
    preferidas = set(RITMO_POR_PLATAFORMA["linkedin"]["slots"])
    assert set(horas) <= preferidas, (
        f"caiu fora da escada preferida do LinkedIn: {sorted(set(horas) - preferidas)}"
    )


def test_frames_do_mesmo_story_saem_em_sequencia():
    frames = por_canal(montar(), "instagram", "story")
    t0 = datetime.fromisoformat(frames[0]["scheduled_at"])
    t1 = datetime.fromisoformat(frames[1]["scheduled_at"])
    assert (t1 - t0).total_seconds() == MINUTOS_ENTRE_FRAMES * 60


# ── Contrato com o publisher ──────────────────────────────────────────────────

CAMPOS_OBRIGATORIOS = {
    "platform", "format", "title", "copy", "scheduled_at", "status",
    "article_slug", "article_title", "article_url", "language",
    "thread_posts", "image_url", "video_url", "asset_urls",
    "session_id", "retry_count", "error_message", "published_at",
    "platform_post_id", "created_at", "updated_at",
}


@pytest.mark.parametrize("item", montar())
def test_todo_item_traz_os_campos_que_o_publisher_le(item):
    assert CAMPOS_OBRIGATORIOS <= set(item)
    assert item["status"] == "planned"
    assert item["retry_count"] == 0
    assert item["published_at"] is None


def test_url_do_artigo_viaja_com_cada_item():
    # É o que resolve [LINK_ARTIGO] no momento da publicação, dias depois,
    # quando a sessão do Studio já pode ter sido descartada.
    for item in montar():
        assert item["article_url"] == "https://eozore.com/pt-BR/blog/meu-post"


# ── Agenda que enxerga a fila ─────────────────────────────────────────────────

def _plano_minimo(dia=1):
    return {
        "linkedin": [{"id": "li-1", "gancho": "Gancho", "corpo": "Corpo",
                      "dia_offset": dia, "cta": {"texto": "CTA"}}],
    }


def test_agenda_desvia_do_horario_ja_ocupado():
    """
    Defeito real: `base` era sempre "agora", então uma campanha nova começava
    em D+1 e caía por cima da anterior, que ainda tinha peças pendentes. Nada
    quebrava — o publisher publica tudo que está no horário — mas dois vídeos
    diferentes disputavam a mesma janela com CTAs para links diferentes.
    """
    from datetime import datetime, timezone
    from social_publish import montar_itens, _chave_agenda, SLOTS_BRT

    base = datetime(2026, 9, 10, tzinfo=timezone.utc)

    sem_conflito = montar_itens(_plano_minimo(), base=base)
    primeiro = sem_conflito[0]["scheduled_at"]

    # A mesma montagem, agora com aquele horário já tomado no LinkedIn.
    com_conflito = montar_itens(
        _plano_minimo(), base=base,
        agenda_ocupada={_chave_agenda("linkedin", primeiro)},
    )
    assert com_conflito[0]["scheduled_at"] != primeiro


def test_agenda_ignora_ocupacao_de_outra_plataforma():
    """
    LinkedIn e Instagram no mesmo horário é cross-posting normal, não colisão.
    Só o mesmo canal disputando a mesma janela é problema.
    """
    from datetime import datetime, timezone
    from social_publish import montar_itens, _chave_agenda

    base = datetime(2026, 9, 10, tzinfo=timezone.utc)
    livre = montar_itens(_plano_minimo(), base=base)[0]["scheduled_at"]

    itens = montar_itens(
        _plano_minimo(), base=base,
        agenda_ocupada={_chave_agenda("instagram", livre)},
    )
    assert itens[0]["scheduled_at"] == livre


def test_frames_da_story_dividem_a_mesma_hora():
    """
    Story é sequência: os frames saem de 3 em 3 minutos, na mesma hora.
    Reservar por frame espalharia a story por horas diferentes — e a
    granularidade da chave (hora, não minuto) é o que impede isso.
    """
    from datetime import datetime, timezone
    from social_publish import montar_itens

    plano = {"stories": [{
        "id": "st-1", "gancho": "Story", "dia_offset": 1,
        "cta": {"texto": "CTA"},
        "frames": [{"ordem": i, "texto": f"frame {i}"} for i in range(1, 4)],
    }]}
    itens = montar_itens(plano, base=datetime(2026, 9, 10, tzinfo=timezone.utc))
    horas = {i["scheduled_at"][:13] for i in itens}
    assert len(itens) == 3
    assert len(horas) == 1, f"frames espalhados por {horas}"


def test_pecas_da_mesma_campanha_nao_colidem_entre_si():
    """O mesmo conjunto resolve as duas colisões: entre campanhas e interna."""
    from datetime import datetime, timezone
    from social_publish import montar_itens

    plano = {"linkedin": [
        {"id": f"li-{i}", "gancho": f"G{i}", "corpo": "C", "dia_offset": 1}
        for i in range(4)
    ]}
    itens = montar_itens(plano, base=datetime(2026, 9, 10, tzinfo=timezone.utc))
    horas = [i["scheduled_at"][:13] for i in itens]
    assert len(set(horas)) == len(horas), f"colisão interna: {horas}"


# ── Peça não pode mentir sobre o vídeo ────────────────────────────────────────

class _PlanoFake:
    """
    Só o que `checar_promessas_do_video` consome.

    Um PlanoSocial válido exige 10 stories, carrossel e threads — peso que não
    diz nada sobre a checagem em si, que age sobre as frases.
    """
    def __init__(self, *frases):
        self._frases = [("li-1", f) for f in frases]

    def afirmacoes_sobre_o_video(self):
        from social_schemas import MARCADORES_VIDEO, VERBOS_DE_DEMONSTRACAO
        return [
            (i, f) for i, f in self._frases
            if any(m in f.lower() for m in MARCADORES_VIDEO)
            and any(v in f.lower() for v in VERBOS_DE_DEMONSTRACAO)
        ]


def test_promessa_que_o_roteiro_nao_sustenta_vira_aviso():
    """
    Defeito de 01/09: uma peça afirmou que "no vídeo fizemos código mostrando e
    medindo a diferença". O vídeo não media nada — o código estava no ARTIGO.
    O agente recebe as duas peças e conflacionava as duas; quem clicou
    descobriu em quinze segundos.
    """
    from social_schemas import checar_promessas_do_video

    roteiro = "Falamos sobre especificação executável e contratos formais."
    plano = _PlanoFake("No vídeo eu mostro o código medindo a latência da requisição.")
    avisos = checar_promessas_do_video(plano, roteiro)
    assert avisos, "a promessa falsa tinha que virar aviso"
    assert "li-1" in avisos[0]


def test_promessa_sustentada_pelo_roteiro_nao_avisa():
    """Falso positivo aqui é ruído na revisão — a checagem tem que discriminar."""
    from social_schemas import checar_promessas_do_video

    roteiro = (
        "No vídeo eu mostro o código medindo a latência da requisição entre "
        "as duas abordagens, com o resultado na tela."
    )
    plano = _PlanoFake("No vídeo eu mostro o código medindo a latência da requisição.")
    assert checar_promessas_do_video(plano, roteiro) == []


def test_falar_sobre_o_tema_nao_e_promessa_de_conteudo():
    """
    "Falo sobre isso no vídeo" é promessa de TEMA e é honesta. Só promessa de
    CONTEÚDO — mostrar, medir, rodar — precisa existir em cena.
    """
    from social_schemas import checar_promessas_do_video

    plano = _PlanoFake("Falo sobre esse problema no vídeo desta semana.")
    assert checar_promessas_do_video(plano, "roteiro qualquer sem relação") == []


def test_sem_roteiro_nao_inventa_aviso():
    """Sessão antiga sem manifesto não pode encher a revisão de falso positivo."""
    from social_schemas import checar_promessas_do_video

    plano = _PlanoFake("No vídeo eu mostro o código medindo tudo.")
    assert checar_promessas_do_video(plano, "") == []


# ── LinkedIn: imagem do vídeo, completa ───────────────────────────────────────

_SLIDE = (
    '<!DOCTYPE html><html><head><style>#yt-02 .fd{animation:fadeIn .4s forwards}'
    '#yt-02 .fd-hidden{display:none}</style></head><body>'
    '<div id="fd1" class="fd">coluna esquerda</div>'
    '<div id="fd2" class="fd fd-hidden">coluna direita</div>'
    '<p>Tóquens por ciclo</p></body></html>'
)


def test_slide_estatico_revela_o_que_o_js_revelaria():
    """
    O slide se CONSTRÓI durante a fala: blocos nascem em `.fd-hidden` e o vídeo
    os revela por JS. Uma captura estática não roda esse JS — a primeira
    imagem de LinkedIn saiu com um comparativo de duas colunas mostrando só a
    da esquerda, e com um vão no meio onde estaria o resto.
    """
    from social_publish import preparar_slide_estatico

    pronto = preparar_slide_estatico(_SLIDE)
    assert "eozore-estatico" in pronto
    assert "display: revert !important" in pronto
    assert "opacity: 1 !important" in pronto


def test_slide_estatico_corrige_a_grafia_de_pronuncia():
    """
    O designer copia trechos do script, que vem em português fonético para o
    TTS. Um slide de 02/09 saiu com "Tóquens por ciclo" queimado no vídeo — e
    a mesma imagem virou post.
    """
    from social_publish import preparar_slide_estatico

    pronto = preparar_slide_estatico(_SLIDE)
    assert "Tóquens" not in pronto
    assert "Tokens por ciclo" in pronto


def test_linkedin_com_enquete_nao_leva_imagem():
    """
    O post de votação do LinkedIn não aceita mídia. Mandar as duas coisas faz
    a API escolher uma em silêncio.
    """
    from datetime import datetime, timezone
    from social_publish import montar_itens

    plano = {"linkedin": [{
        "id": "li-1", "gancho": "G", "corpo": "C", "dia_offset": 1,
        "enquete": {"pergunta": "Onde valida o contrato?", "opcoes": ["CI", "Review"]},
    }]}
    item = montar_itens(plano, base=datetime(2026, 9, 10, tzinfo=timezone.utc),
                        slides_video={"a": _SLIDE})[0]
    assert item["format"] == "poll"
    assert item["poll_data"]["options"] == ["CI", "Review"]
    assert not item.get("_render"), "enquete não pode carregar imagem"


def test_linkedin_sem_enquete_leva_a_ilustracao_do_video():
    """
    O slide_designer desenha 9 ilustrações por vídeo e nenhuma virava peça
    social — o LinkedIn saía como texto puro.
    """
    from datetime import datetime, timezone
    from social_publish import montar_itens

    plano = {"linkedin": [{"id": "li-1", "gancho": "G", "corpo": "C", "dia_offset": 1}]}
    item = montar_itens(plano, base=datetime(2026, 9, 10, tzinfo=timezone.utc),
                        slides_video={"a": _SLIDE})[0]
    assert item["format"] == "text"
    assert item["_render"], "o post devia carregar a ilustração do vídeo"
    assert item["_render"][0]["size"] == (1920, 1080)


def test_linkedin_nao_agenda_em_fim_de_semana():
    """
    Plataforma de dia útil não gasta peça em sábado.

    Medido na fila real de 06/09: 30% de TODAS as peças caíam em fim de
    semana porque a escada de horários era a mesma para todo mundo. No
    Instagram isso é indiferente; no LinkedIn são 3 dos 11 posts publicados
    para um feed profissional vazio, e na Comunidade do YouTube eram 43%.
    """
    from datetime import datetime, timedelta, timezone
    from social_publish import montar_itens

    # Base numa SEXTA: o pior caso, a campanha começa colada no fim de semana.
    base = datetime(2026, 9, 11, tzinfo=timezone.utc)
    plano = {"linkedin": [
        {"id": f"li-{n}", "gancho": "G", "corpo": "C", "dia_offset": n + 1}
        for n in range(3)
    ]}
    for item in montar_itens(plano, base=base):
        brt = datetime.fromisoformat(item["scheduled_at"]) - timedelta(hours=3)
        assert brt.weekday() < 5, f"LinkedIn agendado num {brt:%A}: {item['scheduled_at']}"


def test_instagram_pode_usar_fim_de_semana():
    """
    O inverso também é regra: empurrar story para segunda desperdiça o
    domingo, que é quando o consumo pessoal acontece.
    """
    from social_publish import RITMO_POR_PLATAFORMA

    assert RITMO_POR_PLATAFORMA["instagram"]["evita_fds"] is False
    assert RITMO_POR_PLATAFORMA["linkedin"]["evita_fds"] is True


def test_story_nao_prefere_as_9_da_manha():
    """
    9h era onde 45 das 155 peças de Instagram caíam, por herdar a escada do
    LinkedIn. É o pior horário de story — o consumo é meio-dia e noite.
    """
    from social_publish import RITMO_POR_PLATAFORMA

    slots = RITMO_POR_PLATAFORMA["instagram"]["slots"]
    assert slots[0] != 9, "9h não pode ser a primeira escolha do Instagram"
    assert 9 in slots, "9h continua como degrau, só não como preferência"
