

# ── A classe que o deck usa para navegar ──────────────────────────────────────

def test_container_slide_e_renomeado():
    """
    Defeito de 29/08: o modelo escolheu `class="slide"` para o container raiz
    em 4 dos 9 slides. O deck navega com `.slide{display:none!important}` e
    `.slide.active` — a <section> ganha `.active` e aparece, o div interno
    homônimo não ganha nada e some, levando o conteúdo junto.

    Resultado: 115 segundos de tela preta num vídeo de 344, sem erro em lugar
    nenhum — nem no job, nem no upload, nem no YouTube.
    """
    from slide_designer_agent import _renomear_container_slide

    html = '<div class="slide" data-capitulo="X"><div class="kicker">a</div></div>'
    novo = _renomear_container_slide(html)
    assert 'class="slide"' not in novo
    assert 'class="slide-container"' in novo
    assert 'class="kicker"' in novo


def test_renomear_preserva_as_outras_classes():
    from slide_designer_agent import _renomear_container_slide

    novo = _renomear_container_slide('<div class="slide fd destaque">x</div>')
    assert "slide-container" in novo and "fd" in novo and "destaque" in novo


def test_renomear_nao_toca_slide_container_nem_prefixos():
    """`slide-container` e `slide-id` já são nomes distintos — não renomear."""
    from slide_designer_agent import _renomear_container_slide

    original = '<div class="slide-container"><span class="slide-id">1</span></div>'
    assert _renomear_container_slide(original) == original


def test_grafia_de_pronuncia_nao_chega_a_tela():
    """
    O script vem em português fonético para o TTS e o designer copia trechos
    dele para o slide. Em 02/09 saiu "Tóquens por ciclo" queimado no vídeo, e
    a mesma imagem virou post no LinkedIn. Certo para o áudio, erro de
    português na tela.
    """
    from pronuncia import desfonetizar

    html = '<div class="kpi">1M+</div><p>Tóquens por ciclo com prómpti e ê-pê-í</p>'
    limpo = desfonetizar(html)
    assert "Tóquens" not in limpo and "prómpti" not in limpo and "ê-pê-í" not in limpo
    assert "Tokens" in limpo and "prompt" in limpo and "API" in limpo


def test_desfonetizar_preserva_o_html():
    """A troca é de palavra: tag, classe e atributo não podem ser tocados."""
    from pronuncia import desfonetizar

    html = '<div class="fd-hidden" id="fd2" data-teste="cache">quéxi</div>'
    limpo = desfonetizar(html)
    assert 'class="fd-hidden"' in limpo and 'id="fd2"' in limpo
    assert 'data-teste="cache"' in limpo
    assert ">cache<" in limpo
