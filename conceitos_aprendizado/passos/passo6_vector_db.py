"""
PASSO 6 — Banco de Dados Vetorial com ChromaDB
================================================
Conceito: substituir o cache JSON por um banco vetorial real,
com duas coleções separadas:

  - "lore"      → a história pré-criada (estática)
  - "historico" → o que aconteceu na sessão (cresce durante o jogo)

A cada turno, o RAG busca em AMBAS as coleções — o narrador
tem acesso tanto ao lore do mundo quanto ao que já foi jogado.

Isso resolve dois problemas de escala:
  1. Lore muito grande: o banco indexa e busca eficientemente
  2. Campanhas longas: o histórico jogado vira memória pesquisável
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

load_dotenv(Path(__file__).parent / ".env")

client = OpenAI()

DB_PATH   = Path(__file__).parent.parent / "storage" / "vector_db"
LORE_PATH = Path(__file__).parent / "lore_valdris.json"


# ── Função de embedding compartilhada ────────────────────────────────────────
# ChromaDB aceita uma "embedding function" que ele chama internamente
# ao adicionar ou buscar documentos. Usamos a da OpenAI.

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    model_name="text-embedding-3-small",
)


# ── Inicialização do banco ────────────────────────────────────────────────────

def inicializar_banco() -> tuple:
    """
    Cria (ou abre se já existir) o banco vetorial e suas coleções.
    ChromaDB persiste tudo automaticamente em DB_PATH.
    """
    DB_PATH.mkdir(parents=True, exist_ok=True)

    banco = chromadb.PersistentClient(path=str(DB_PATH))

    # get_or_create: cria a coleção na primeira vez, abre nas seguintes
    colecao_lore = banco.get_or_create_collection(
        name="lore",
        embedding_function=openai_ef,
        metadata={"descricao": "Lore estático do mundo de Valdris"},
    )

    colecao_historico = banco.get_or_create_collection(
        name="historico",
        embedding_function=openai_ef,
        metadata={"descricao": "Eventos ocorridos durante as sessões de jogo"},
    )

    return colecao_lore, colecao_historico


# ── Indexação do lore ─────────────────────────────────────────────────────────

def indexar_lore(colecao) -> None:
    """
    Adiciona os chunks de lore ao banco vetorial.
    Verifica antes se já foram adicionados para não duplicar.
    """
    chunks = json.loads(LORE_PATH.read_text(encoding="utf-8"))

    # Verifica quantos documentos já existem na coleção
    if colecao.count() >= len(chunks):
        print(f"  Lore já indexado ({colecao.count()} chunks no banco).")
        return

    print(f"  Indexando {len(chunks)} chunks de lore no ChromaDB...")

    colecao.add(
        ids=[c["id"] for c in chunks],
        documents=[f"{c['titulo']}: {c['texto']}" for c in chunks],
        metadatas=[{"titulo": c["titulo"], "tipo": "lore"} for c in chunks],
    )
    print(f"  Indexação concluída. {colecao.count()} chunks no banco.\n")


# ── Registro do histórico jogado ──────────────────────────────────────────────

def registrar_no_historico(colecao, turno: int, jogador: str, narrador: str) -> None:
    """
    Salva cada turno jogado como um documento no banco vetorial.
    O texto combinado (ação + resposta) é o que será buscado depois.

    Metadados permitem filtrar por turno, sessão ou tipo depois.
    """
    texto = f"Jogador: {jogador}\nNarrador: {narrador}"

    colecao.add(
        ids=[str(uuid.uuid4())],
        documents=[texto],
        metadatas=[{
            "turno": turno,
            "timestamp": datetime.now().isoformat(),
            "tipo": "historico",
        }],
    )


# ── RAG: busca em ambas as coleções ──────────────────────────────────────────

def buscar_contexto(consulta: str, col_lore, col_historico, top_k: int = 2) -> dict:
    """
    Busca os chunks mais relevantes em lore e histórico separadamente.
    Retorna um dicionário com os resultados de cada coleção.
    """
    resultados_lore = col_lore.query(
        query_texts=[consulta],
        n_results=min(top_k, col_lore.count()),
    )

    resultados = {"lore": [], "historico": []}

    # Extrai documentos e scores do lore
    if resultados_lore["documents"][0]:
        for doc, meta, dist in zip(
            resultados_lore["documents"][0],
            resultados_lore["metadatas"][0],
            resultados_lore["distances"][0],
        ):
            score = 1 - dist  # ChromaDB retorna distância; convertemos para similaridade
            resultados["lore"].append({"texto": doc, "titulo": meta["titulo"], "score": score})

    # Busca no histórico (só se já tiver registros)
    if col_historico.count() > 0:
        resultados_historico = col_historico.query(
            query_texts=[consulta],
            n_results=min(top_k, col_historico.count()),
        )
        for doc, dist in zip(
            resultados_historico["documents"][0],
            resultados_historico["distances"][0],
        ):
            score = 1 - dist
            if score > 0.5:  # só inclui histórico realmente relevante
                resultados["historico"].append({"texto": doc, "score": score})

    # Debug: mostra o que foi encontrado
    print(f"\n  [RAG] Consulta: '{consulta[:50]}'")
    for item in resultados["lore"]:
        print(f"    lore      {item['score']:.3f} → {item['titulo']}")
    for item in resultados["historico"]:
        print(f"    histórico {item['score']:.3f} → {item['texto'][:60]}...")

    return resultados


# ── System prompt com RAG duplo ───────────────────────────────────────────────

def montar_system_prompt(personagem: dict, mundo: dict, contexto: dict) -> str:
    inventario = ", ".join(personagem["inventario"]) or "nenhum"

    secao_lore = ""
    if contexto["lore"]:
        trechos = "\n\n".join(f"[{i['titulo']}]\n{i['texto']}" for i in contexto["lore"])
        secao_lore = f"\n## LORE DO MUNDO (relevante agora)\n{trechos}\n"

    secao_historico = ""
    if contexto["historico"]:
        trechos = "\n\n".join(f"- {i['texto']}" for i in contexto["historico"])
        secao_historico = f"\n## MEMÓRIA DE SESSÕES ANTERIORES (relevante agora)\n{trechos}\n"

    return f"""Você é um narrador de RPG de fantasia medieval sombria.

## ESTADO ATUAL
Personagem : {personagem['nome']} ({personagem['classe']})
HP         : {personagem['hp']}/{personagem['hp_max']}
Inventário : {inventario}
Localização: {mundo['localizacao']} | {mundo['hora']}
{secao_lore}{secao_historico}
## REGRAS
- Respostas curtas (3 a 5 linhas)
- Use o lore e a memória acima para manter coerência com o mundo e o passado
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
}


# ── Interface ─────────────────────────────────────────────────────────────────

def mostrar_status(personagem, mundo, col_historico):
    print(f"\n  [{personagem['nome']} | HP: {personagem['hp']}/{personagem['hp_max']} "
          f"| {mundo['localizacao']} | Memória: {col_historico.count()} turnos]")


print("=" * 60)
print("  RPG NARRADO — Passo 6: Banco Vetorial")
print("  Duas coleções: lore (mundo) + histórico (sessões)")
print("  O narrador lembra do que aconteceu em sessões anteriores!")
print("  Digite 'sair' para encerrar")
print("=" * 60)
print()

# Inicializa banco e indexa lore
col_lore, col_historico = inicializar_banco()
indexar_lore(col_lore)

historico_chat = []
turno = 0

# Abertura
contexto_inicial = buscar_contexto("vila de cinzas cena inicial", col_lore, col_historico)
system = montar_system_prompt(personagem, mundo, contexto_inicial)
abertura = chamar_narrador([
    {"role": "system", "content": system},
    {"role": "user", "content": "Descreva a cena inicial."},
])
print(f"\nNARRADOR:\n{abertura}")
mostrar_status(personagem, mundo, col_historico)
print()

historico_chat.append({"role": "user", "content": "Descreva a cena inicial."})
historico_chat.append({"role": "assistant", "content": abertura})
registrar_no_historico(col_historico, turno, "Descreva a cena inicial.", abertura)


# ── Loop principal ────────────────────────────────────────────────────────────

while True:
    acao = input("\nJOGADOR: ").strip()

    if acao.lower() == "sair":
        print(f"\nSessão encerrada. {col_historico.count()} turnos salvos na memória.")
        print("Na próxima sessão, o narrador lembrará do que aconteceu.")
        break

    if not acao:
        continue

    turno += 1

    # RAG: busca em lore E histórico
    contexto = buscar_contexto(acao, col_lore, col_historico)

    system = montar_system_prompt(personagem, mundo, contexto)
    messages = [{"role": "system", "content": system}] + historico_chat + [
        {"role": "user", "content": acao}
    ]

    resposta = chamar_narrador(messages)

    # Atualiza histórico de chat (contexto curto da sessão atual)
    historico_chat.append({"role": "user", "content": acao})
    historico_chat.append({"role": "assistant", "content": resposta})

    # Persiste no banco vetorial (memória de longo prazo entre sessões)
    registrar_no_historico(col_historico, turno, acao, resposta)

    print(f"\nNARRADOR:\n{resposta}")
    mostrar_status(personagem, mundo, col_historico)