# Passo 6 — Conceitos: Banco de Dados Vetorial com ChromaDB

## O que foi construído?

Um sistema de memória de duas camadas: lore estático do mundo (indexado uma vez) e histórico das sessões jogadas (cresce a cada turno). Ambos são consultados via RAG a cada ação do jogador, dando ao narrador acesso ao passado sem estourar o contexto.

--- 

## 1. Por que um Banco Vetorial em vez do Cache JSON?

O cache JSON do Passo 5 funciona para dezenas de chunks. Mas em campanhas grandes:

| Problema                  | Cache JSON           | Banco Vetorial              |
|---------------------------|----------------------|-----------------------------|
| 10.000 chunks de lore     | Carrega tudo na RAM  | Indexado, busca eficiente   |
| Histórico de 500 turnos   | Arquivo gigante      | Coleção separada, filtros   |
| Múltiplas campanhas       | Arquivos conflitam   | Coleções isoladas por nome  |
| Busca com filtros         | Não suporta          | Filtra por metadados        |

O banco vetorial foi feito para esse problema — armazenar e buscar vetores em escala.

---

## 2. ChromaDB — Banco Vetorial Local

ChromaDB é um banco vetorial que roda localmente, persiste no disco e tem uma API simples. Não precisa de servidor separado.

```python
import chromadb

banco = chromadb.PersistentClient(path="storage/vector_db")
```

O banco inteiro fica salvo na pasta `storage/vector_db/`. Ao rodar o programa de novo, os dados já estão lá — sem re-indexar, sem re-gerar embeddings.

---

## 3. Coleções — Tabelas do Banco Vetorial

Uma coleção é um grupo isolado de documentos com seus embeddings. Equivale a uma tabela em banco relacional, mas para vetores.

```python
# Cria a coleção na primeira vez; abre nas seguintes
colecao = banco.get_or_create_collection(
    name="lore",
    embedding_function=openai_ef,
)
```

No projeto, duas coleções separadas com propósitos distintos:

| Coleção      | Conteúdo                        | Quando cresce         |
|--------------|---------------------------------|-----------------------|
| `lore`       | História pré-criada do mundo    | Só na indexação inicial |
| `historico`  | Turnos jogados nas sessões      | A cada turno do jogo  |

Separar em coleções permite buscar em cada uma com parâmetros diferentes e evita que o histórico "contamone" a busca no lore.

---

## 4. Adicionando Documentos ao Banco

```python
colecao.add(
    ids=["historia_01", "historia_02"],        # identificador único
    documents=["texto do chunk 1", "..."],     # o texto que vira embedding
    metadatas=[{"titulo": "A Fundação", "tipo": "lore"}],  # dados extras
)
```

O ChromaDB gera os embeddings automaticamente usando a `embedding_function` configurada na coleção. Você não chama a API de embeddings manualmente — o banco faz isso.

Os **metadados** são campos livres que ficam associados ao documento mas não influenciam a busca por similaridade. Usamos para guardar `turno`, `timestamp`, `tipo` — dados que podem ser usados para filtrar depois.

---

## 5. Buscando por Similaridade

```python
resultados = colecao.query(
    query_texts=["pergunto sobre o castelo"],  # texto da consulta
    n_results=2,                               # quantos chunks retornar
)
```

O ChromaDB converte a consulta em embedding internamente e retorna os documentos mais similares com suas distâncias.

**Atenção:** o ChromaDB retorna **distância**, não similaridade. São inversas:

```python
similaridade = 1 - distancia
# distancia 0.2  →  similaridade 0.8  (muito relevante)
# distancia 0.8  →  similaridade 0.2  (pouco relevante)
```

---

## 6. Memória de Longo Prazo entre Sessões

Cada turno jogado é salvo no banco como um documento:

```python
def registrar_no_historico(colecao, turno, jogador, narrador):
    texto = f"Jogador: {jogador}\nNarrador: {narrador}"
    colecao.add(
        ids=[str(uuid.uuid4())],
        documents=[texto],
        metadatas={"turno": turno, "timestamp": datetime.now().isoformat()},
    )
```

Na próxima sessão, quando o jogador fizer uma ação relacionada a algo que aconteceu antes, o RAG recupera aquele turno do banco — mesmo que tenha sido em uma sessão semanas atrás.

Isso implementa a distinção clássica em sistemas de agentes:

| Tipo de memória    | Implementação             | Duração           |
|--------------------|---------------------------|-------------------|
| Memória de trabalho | `historico_chat` (lista) | Só na sessão atual |
| Memória de longo prazo | Coleção `historico` (ChromaDB) | Entre sessões |

---

## 7. RAG com Duas Fontes

A função `buscar_contexto()` consulta lore e histórico em paralelo e combina os resultados:

```
Ação do jogador
      ↓
  ┌───────────────────────┐
  │  busca em "lore"      │ → chunks do mundo (estático)
  │  busca em "historico" │ → turnos passados (dinâmico)
  └───────────────────────┘
      ↓
  chunks mais relevantes de cada fonte
      ↓
  injetados em seções separadas do system prompt
```

O narrador recebe duas seções distintas: `## LORE DO MUNDO` e `## MEMÓRIA DE SESSÕES ANTERIORES`. Isso permite que ele saiba tanto a história do mundo quanto o que o jogador fez antes.

---

## 8. Estrutura de Arquivos Gerada

```
storage/
└── vector_db/           ← ChromaDB persiste tudo aqui automaticamente
    ├── chroma.sqlite3   ← índice e metadados
    └── [arquivos internos do banco]
```

Você não interage com esses arquivos diretamente. O ChromaDB gerencia tudo. Para "resetar" a memória, basta apagar a pasta `vector_db/`.

---

## Resumo: o que mudou do Passo 5 para o Passo 6

| Aspecto              | Passo 5 (cache JSON)         | Passo 6 (ChromaDB)                    |
|----------------------|------------------------------|---------------------------------------|
| Armazenamento        | Arquivo JSON na pasta        | Banco persistente em `storage/`       |
| Escala               | Centenas de chunks           | Milhares a milhões de chunks          |
| Coleções             | Uma (lore)                   | Duas: lore + histórico                |
| Histórico de sessões | Não existe                   | Salvo a cada turno, consultável       |
| Memória entre sessões| Não existe                   | Sim — o narrador lembra o passado     |
| Embeddings           | Gerados manualmente          | Gerados automaticamente pelo banco    |
| Filtros              | Não suporta                  | Filtra por metadados (turno, tipo...) |