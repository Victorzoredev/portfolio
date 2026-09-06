"""
tests/test_reprocesso_publisher.py
===================================
Republicar não pode duplicar o vídeo no canal.

Em 27/08, reprocessar a publicação de um projeto subiu o arquivo de novo em
vez de atualizar o que já estava lá. O canal ficou com TRÊS vídeos do mesmo
tema — o truncado, o corrigido, e o do teste de reprocesso.

O YouTube não permite trocar o ARQUIVO de um vídeo, mas permite trocar tudo em
volta. Então:

  - a EDIÇÃO refez o vídeo  → arquivo novo → upload novo, e aí o id anterior
    tem que ser esquecido;
  - só a descrição ou a capa mudaram → atualiza no lugar, mesmo id.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_cliente_do_youtube_sabe_atualizar_no_lugar():
    """
    Sem `update_video_metadata` a única saída é reupload, e reupload em
    correção de descrição sempre gera duplicata.
    """
    from publisher_job.youtube_client import YouTubeClient

    assert hasattr(YouTubeClient, "update_video_metadata")


def test_update_usa_videos_update_e_nao_o_endpoint_de_upload():
    """
    `videos.update` é PUT em /youtube/v3/videos. Bater no /upload/ criaria um
    vídeo novo, que é exatamente o defeito.
    """
    import inspect

    from publisher_job.youtube_client import YouTubeClient

    src = inspect.getsource(YouTubeClient.update_video_metadata)
    assert "requests.put" in src
    assert "/videos?part=snippet" in src
    assert "UPLOAD_API" not in src


def test_publisher_atualiza_em_vez_de_pular_quando_ja_publicado():
    """
    A versão anterior devolvia o post_id e seguia adiante. Descrição e capa
    regeradas nunca chegavam ao vídeo — foi por isso que corrigir a descrição
    de 27/08 exigiu chamar a API à mão.
    """
    import inspect

    from publisher_job.job import PublisherJob

    src = inspect.getsource(PublisherJob)
    assert "update_video_metadata" in src, (
        "o caminho de 'já publicado' precisa atualizar o vídeo, não só pular"
    )


def test_falha_do_update_nao_vira_reupload():
    """
    Se a atualização falhar, o vídeo antigo continua no ar e visível. Subir de
    novo criaria o duplicado que este caminho existe para evitar.
    """
    import inspect

    from publisher_job.job import PublisherJob

    src = inspect.getsource(PublisherJob)
    trecho = src[src.index("update_video_metadata"):]
    # O except em volta do update apenas registra e segue com o post_id antigo.
    assert "logger.warning" in trecho[:900]


# ── Timeout de rede não pode custar uma produção ──────────────────────────────

def test_upload_tenta_de_novo_em_falha_de_rede():
    """
    Em 02/09 um `Read timed out` numa conexão derrubou o upload inteiro. O
    projeto ficou `published_partial`, e como a saída oferecida foi aprovar de
    novo, o pacote foi refeito do zero — com o avatar do HeyGen gerado uma
    SEGUNDA vez pela mesma fala. Um soluço de rede custou uma produção.

    O protocolo é resumable justamente para isso, e o código não usava.
    """
    import inspect
    from publisher_job.youtube_client import YouTubeClient, TENTATIVAS_POR_CHUNK

    assert TENTATIVAS_POR_CHUNK >= 2
    corpo = inspect.getsource(YouTubeClient._put_com_retry)
    assert "requests.Timeout" in corpo and "requests.ConnectionError" in corpo


def test_so_falha_de_rede_e_repetida():
    """
    Um 4xx do YouTube é resposta, não soluço: repetir não muda nada e só
    atrasa o diagnóstico.
    """
    import inspect
    from publisher_job.youtube_client import YouTubeClient

    corpo = inspect.getsource(YouTubeClient._put_com_retry)
    # A captura é específica; um `except Exception` engoliria erro de negócio.
    assert "except Exception" not in corpo


def test_retry_pergunta_ao_servidor_onde_parou():
    """
    Depois de um timeout não dá para saber se o chunk chegou. Reenviar do
    offset local duplica ou pula bytes — o protocolo resumable responde até
    onde recebeu, e é essa resposta que manda.
    """
    import inspect
    from publisher_job.youtube_client import YouTubeClient

    assert hasattr(YouTubeClient, "_offset_no_servidor")
    corpo = inspect.getsource(YouTubeClient._offset_no_servidor)
    assert "bytes */" in corpo, "o PUT de consulta usa Content-Range: bytes */total"
