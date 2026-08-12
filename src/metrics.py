from collections import defaultdict


def calc_pod_index(posts):
    """
    posts: list[{"post_id": str, "commenters": list[str]}]

    "Pod" é um indício de engajamento combinado/artificial: um grupo de contas que
    comenta sistematicamente nos mesmos posts de um mesmo perfil. Aqui um comentarista
    é considerado "repetidor" quando aparece em 2 ou mais posts DISTINTOS do perfil
    (comentar 2x no mesmo post não conta como repetição entre posts).

    Retorna: {
        "total_comentarios": int,
        "comentaristas_unicos": int,
        "pod_index": float,  # proporção de comentários feitos por repetidores
        "top_repetidores": dict,  # {username: total de comentários feitos}, count >= 2
    }
    """
    posts_por_usuario = defaultdict(set)
    comentarios_por_usuario = defaultdict(int)
    total_comentarios = 0

    for post in posts:
        post_id = post.get("post_id")
        commenters = post.get("commenters") or []
        total_comentarios += len(commenters)
        for username in commenters:
            posts_por_usuario[username].add(post_id)
            comentarios_por_usuario[username] += 1

    comentaristas_unicos = len(posts_por_usuario)

    repetidores = {
        username: comentarios_por_usuario[username]
        for username, post_ids in posts_por_usuario.items()
        if len(post_ids) >= 2
    }

    comentarios_de_repetidores = sum(repetidores.values())
    pod_index = comentarios_de_repetidores / total_comentarios if total_comentarios else 0.0

    top_repetidores = dict(
        sorted(repetidores.items(), key=lambda item: item[1], reverse=True)
    )

    return {
        "total_comentarios": total_comentarios,
        "comentaristas_unicos": comentaristas_unicos,
        "pod_index": pod_index,
        "top_repetidores": top_repetidores,
    }
