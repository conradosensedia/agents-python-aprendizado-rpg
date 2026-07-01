"""
PASSO 5 — RAG com Embeddings
==============================
Conceito: em vez de injetar todo o lore no prompt, usamos embeddings
para encontrar e injetar apenas os trechos relevantes para o momento.

Fluxo do RAG:
  1. INDEXAÇÃO (feita uma vez):
     - Carrega os chunks de lore (lore_valdris.json)
     - Converte cada chunk em um vetor via API de embeddings
     - Salva os vetores em disco (cache)

  2. RETRIEVAL (a cada turno):
     - Converte a ação do jogador em vetor
     - Calcula a similaridade cosseno com todos os chunks
     - Retorna os N chunks mais próximos semanticamente

  3. AUGMENTED GENERATION:
     - Injeta os chunks recuperados no system prompt
     - O narrador responde com precisão sem ter visto todo o lore
"""

import json
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

LORE_PATH   = Path(__file__).parent / "lore_valdris.json"
CACHE_PATH  = Path(__file__).parent / "lore_embeddings_cache.json"


# ── 1. EMBEDDINGS ─────────────────────────────────────────────────────────────

def gerar_embedding(texto: str) -> list[float]:
    """Converte um texto em vetor via API da OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-3-small",  # modelo mais barato de embeddings
        input=texto,
    )
    return response.data[0].embedding   # lista de 1536 floats


def similaridade_cosseno(vetor_a: list, vetor_b: list) -> float:
    """
    Mede o quão 'próximos' dois vetores são em direção.
    Retorna 1.0 para vetores idênticos e 0.0 para perpendiculares.
    """
    a = np.array(vetor_a)
    b = np.array(vetor_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── 2. INDEXAÇÃO ──────────────────────────────────────────────────────────────

def carregar_ou_indexar_lore() -> list[dict]:
    """
    Carrega os chunks com seus embeddings.
    Se o cache não existe, gera os embeddings e salva para não repetir o custo.
    """
    chunks = json.loads(LORE_PATH.read_text(encoding="utf-8"))

    if CACHE_PATH.exists():
        print("  Carregando embeddings do cache...")
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        for chunk in chunks:
            chunk["embedding"] = cache[chunk["id"]]
        return chunks

    print(f"  Gerando embeddings para {len(chunks)} chunks de lore...")
    cache = {}
    for i, chunk in enumerate(chunks):
        texto_para_embedding = f"{chunk['titulo']}: {chunk['texto']}"
        chunk["embedding"] = gerar_embedding(texto_para_embedding)
        cache[chunk["id"]] = chunk["embedding"]
        print(f"    [{i+1}/{len(chunks)}] {chunk['titulo']}")

    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  Cache salvo em lore_embeddings_cache.json\n")
    return chunks


# ── 3. RETRIEVAL ──────────────────────────────────────────────────────────────

def buscar_lore_relevante(consulta: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    """
    Encontra os chunks mais relevantes para a consulta do jogador.

    1. Converte a consulta em vetor
    2. Calcula similaridade com cada chunk
    3. Retorna os top_k mais similares
    """
    vetor_consulta = gerar_embedding(consulta)

    pontuados = []
    for chunk in chunks:
        score = similaridade_cosseno(vetor_consulta, chunk["embedding"])
        pontuados.append((score, chunk))

    # Ordena do mais similar para o menos
    pontuados.sort(key=lambda x: x[0], reverse=True)

    top = pontuados[:top_k]

    # Debug: mostra o que foi encontrado e com qual score
    print(f"\n  [RAG] Chunks recuperados para: '{consulta[:50]}'")
    for score, chunk in top:
        print(f"    {score:.3f} → {chunk['titulo']}")

    return [chunk for _, chunk in top]


# ── 4. AUGMENTED GENERATION ───────────────────────────────────────────────────

def montar_system_prompt(personagem: dict, mundo: dict, chunks_lore: list[dict]) -> str:
    inventario = ", ".join(personagem["inventario"]) if personagem["inventario"] else "nenhum"

    # Formata apenas os chunks recuperados — não o lore inteiro
    lore_injetado = ""
    if chunks_lore:
        trechos = "\n\n".join(
            f"[{c['titulo']}]\n{c['texto']}" for c in chunks_lore
        )
        lore_injetado = f"\n## CONTEXTO DO MUNDO (relevante para este momento)\n{trechos}\n"

    return f"""Você é um narrador de RPG de fantasia medieval sombria.

## ESTADO ATUAL DO JOGO
Personagem : {personagem['nome']} ({personagem['classe']})
HP         : {personagem['hp']}/{personagem['hp_max']}
Inventário : {inventario}
Localização: {mundo['localizacao']} | {mundo['hora']} | {mundo['clima']}
{lore_injetado}
## REGRAS DE NARRAÇÃO
- Respostas curtas (3 a 5 linhas)
- Use o contexto do mundo acima para dar precisão histórica à narrativa
- Se o jogador perguntar sobre algo fora do contexto, você pode improvisar coerentemente
- Nunca decida ações pelo jogador
"""


def chamar_narrador(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


# ── Estado do jogo ────────────────────────────────────────────────────────────

personagem = {
    "nome": "Aldric",
    "classe": "Guerreiro",
    "hp": 20,
    "hp_max": 20,
    "inventario": ["espada enferrujada", "tocha"],
}

mundo = {
    "localizacao": "Vila de Cinzas",
    "hora": "noite",
    "clima": "névoa densa",
}


# ── Interface ─────────────────────────────────────────────────────────────────

def mostrar_status(personagem: dict, mundo: dict):
    print(f"\n  [{personagem['nome']} | HP: {personagem['hp']}/{personagem['hp_max']} | {mundo['localizacao']}]")


print("=" * 60)
print("  RPG NARRADO — Passo 5: RAG com Embeddings")
print("  Faça perguntas sobre o mundo e observe o [RAG] no terminal")
print("  Ex: 'Pergunto sobre o Castelo de Valdris'")
print("  Ex: 'Quero entrar nas catacumbas'")
print("  Ex: 'Vou à Taverna do Corvo Manco'")
print("  Digite 'sair' para encerrar")
print("=" * 60)
print()

# Indexação: feita uma vez antes do loop começar
chunks_lore = carregar_ou_indexar_lore()

historico = []

# Abertura sem RAG — só descreve a cena inicial
system_inicial = montar_system_prompt(personagem, mundo, [])
abertura = chamar_narrador([
    {"role": "system", "content": system_inicial},
    {"role": "user", "content": "Descreva a cena inicial na Vila de Cinzas."},
])
print(f"NARRADOR:\n{abertura}")
mostrar_status(personagem, mundo)
print()

historico.append({"role": "user", "content": "Descreva a cena inicial na Vila de Cinzas."})
historico.append({"role": "assistant", "content": abertura})


# ── Loop principal ────────────────────────────────────────────────────────────

while True:
    acao = input("\nJOGADOR: ").strip()

    if acao.lower() == "sair":
        print("\nAté a próxima aventura!")
        break

    if not acao:
        continue

    # RETRIEVAL: busca os chunks mais relevantes para a ação do jogador
    chunks_relevantes = buscar_lore_relevante(acao, chunks_lore, top_k=2)

    # AUGMENTED GENERATION: monta o prompt com apenas esses chunks
    system = montar_system_prompt(personagem, mundo, chunks_relevantes)
    messages = [{"role": "system", "content": system}] + historico + [
        {"role": "user", "content": acao}
    ]

    resposta = chamar_narrador(messages)

    historico.append({"role": "user", "content": acao})
    historico.append({"role": "assistant", "content": resposta})

    print(f"\nNARRADOR:\n{resposta}")
    mostrar_status(personagem, mundo)
