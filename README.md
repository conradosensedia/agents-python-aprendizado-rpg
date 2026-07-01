\# RPG Narrado por IA



Projeto de estudo para compreender na prática como funcionam \*\*agentes de inteligência artificial\*\* — construído do zero, passo a passo, usando Python, React e a API da OpenAI.



\## Objetivo



O projeto não é apenas um jogo. É um laboratório onde cada funcionalidade implementada corresponde a um conceito fundamental de sistemas com LLMs e agentes de IA:



| Conceito aprendido | Onde aparece no projeto |

|---|---|

| Chamada à API / messages / roles | Qualquer interação com o narrador |

| Loop de conversa (multi-turn) | Histórico acumulado entre turnos |

| System prompt dinâmico | Estado do personagem injetado no prompt |

| Tool use e loop agêntico | Narrador rola dados automaticamente |

| RAG com embeddings | Busca semântica no lore da campanha |

| Banco de dados vetorial | ChromaDB para lore e memória entre sessões |

| Streaming (SSE) | Narração aparece palavra por palavra |

| Persistência de estado | Save/load de sessões em JSON |



A documentação de cada conceito está em `conceitos\_aprendizado/doc/`.



\---



\## Estrutura do projeto



```

RPG/

├── docker-compose.yml          # MongoDB + Mongo Express

├── .env                        # Chaves e variáveis de ambiente

│

├── backend/                    # API FastAPI (Python)

│   ├── main.py                 # Rotas: /sistemas, /sessoes, /acao

│   ├── requirements.txt

│   ├── agents/

│   │   ├── onboarding.py       # Agente que cria a ficha via conversa

│   │   └── narrator.py         # Agente narrador com streaming + tool use

│   ├── systems/

│   │   └── dnd5e.json          # Definição do sistema D\&D 5e

│   └── database/

│       └── mongo.py            # Conexão com MongoDB (Motor async)

│

├── frontend/                   # Interface React + Vite

│   └── src/

│       ├── api.js              # Chamadas ao backend (incluindo SSE)

│       ├── App.jsx             # Roteamento entre telas

│       └── pages/

│           ├── Home.jsx        # Lista de aventuras + nova aventura

│           ├── Onboarding.jsx  # Chat com o agente de criação de personagem

│           └── Game.jsx        # Tela do jogo com streaming e cartas de dado

│

├── conceitos\_aprendizado/      # Scripts de estudo (passo a passo)

│   ├── passos/                 # Um arquivo Python por conceito

│   └── doc/                   # Documentação de cada passo

│

└── storage/

&#x20;   ├── saves/                  # Saves de sessão em JSON (passo 8)

&#x20;   └── vector\_db/              # Banco vetorial ChromaDB (passo 6)

```



\---



\## Pré-requisitos



| Ferramenta | Versão mínima | Para que serve |

|---|---|---|

| Python | 3.11+ | Backend e scripts de estudo |

| Node.js | 18+ | Frontend React |

| Docker Desktop | Qualquer | Subir o MongoDB |

| Chave OpenAI | — | Chamadas à API (gpt-4o-mini + embeddings) |



> \*\*Nota:\*\* O projeto foi desenvolvido com Python 3.14. Se usar versões anteriores, os pacotes instalam mais rápido pois há wheels pré-compilados disponíveis.



\---



\## Configuração



\### 1. Clonar e configurar variáveis de ambiente



Crie o arquivo `.env` na raiz do projeto:



```env

OPENAI\_API\_KEY=sk-proj-...sua-chave-aqui...

MONGO\_URL=mongodb://rpg:rpg123@localhost:27017/rpg\_db?authSource=admin

```



Para rodar os \*\*scripts de estudo\*\* (`conceitos\_aprendizado/passos/`), crie também:



```

conceitos\_aprendizado/passos/.env

```

Com o mesmo conteúdo acima.



\### 2. Instalar dependências do backend



```bash

cd backend

pip install -r requirements.txt

```



\### 3. Instalar dependências do frontend



```bash

cd frontend

npm install

```



\---



\## Como executar



Abra \*\*três terminais\*\* e execute um comando em cada:



\*\*Terminal 1 — Banco de dados (MongoDB via Docker):\*\*

```bash

docker compose up -d

```



\*\*Terminal 2 — Backend (FastAPI):\*\*

```bash

cd backend

python -m uvicorn main:app --reload --port 8000

```



\*\*Terminal 3 — Frontend (React):\*\*

```bash

cd frontend

npm run dev

```



Acesse o jogo em: \*\*http://localhost:5173\*\*



Interface do banco de dados: \*\*http://localhost:8081\*\* (Mongo Express)



\---



\## Fluxo do jogo



```

1\. Home         → escolhe sistema de RPG (D\&D 5e) ou continua aventura salva

2\. Onboarding   → conversa com o agente que cria a ficha do personagem

&#x20;                 (nome, raça, classe, atributos — salvo no MongoDB)

3\. Jogo         → digita ações, o narrador responde com streaming

&#x20;                 → para ações arriscadas, o narrador rola dados automaticamente

&#x20;                 → a carta de dado aparece com o resultado antes da narração

```



\---



\## Scripts de estudo



Os arquivos em `conceitos\_aprendizado/passos/` são scripts independentes, executáveis via terminal, que demonstram cada conceito isoladamente. Cada um tem uma documentação detalhada em `conceitos\_aprendizado/doc/`.



| Script | Conceito | Documentação |

|--------|----------|--------------|

| `passo1\_chamada\_simples.py` | Estrutura de uma chamada à API: messages, roles (`system`, `user`, `assistant`), tokens e variáveis de ambiente | \[passo1\_conceitos.md](conceitos\_aprendizado/doc/passo1\_conceitos.md) |

| `passo2\_loop\_conversa.py` | Loop multi-turn: como simular memória acumulando mensagens, context window e o padrão `while True` | \[passo2\_conceitos.md](conceitos\_aprendizado/doc/passo2\_conceitos.md) |

| `passo3\_system\_dinamico.py` | System prompt dinâmico: injetar estado do jogo no prompt, separação entre estado Python e representação textual, base do RAG | \[passo3\_conceitos.md](conceitos\_aprendizado/doc/passo3\_conceitos.md) |

| `passo4\_tool\_use.py` | Tool use e loop agêntico: schema de ferramentas, dispatcher, role `tool`, efeitos colaterais reais | \[passo4\_conceitos.md](conceitos\_aprendizado/doc/passo4\_conceitos.md) |

| `passo5\_rag.py` | RAG com embeddings: o que é um embedding, similaridade cosseno, chunking, os três estágios (indexação, retrieval, geração) | \[passo5\_conceitos.md](conceitos\_aprendizado/doc/passo5\_conceitos.md) |

| `passo6\_vector\_db.py` | Banco vetorial com ChromaDB: coleções, persistência, busca em múltiplas fontes, memória de longo prazo entre sessões | \[passo6\_conceitos.md](conceitos\_aprendizado/doc/passo6\_conceitos.md) |

| `passo7\_streaming.py` | Streaming de tokens: `stream=True`, acumular texto, `flush=True`, comparação visual sem vs. com streaming | \[passo7\_conceitos.md](conceitos\_aprendizado/doc/passo7\_conceitos.md) |

| `passo8\_persistencia.py` | Persistência de estado: save/load em JSON, UUID, autosave, truncagem do histórico, retomada com resumo | \[passo8\_conceitos.md](conceitos\_aprendizado/doc/passo8\_conceitos.md) |



Para executar qualquer script:



```bash

cd conceitos\_aprendizado/passos

python passo1\_chamada\_simples.py

```



> Os scripts de estudo usam o `.env` em `conceitos\_aprendizado/passos/.env`. O banco vetorial gerado pelo passo 6 fica em `storage/vector\_db/` e o cache de embeddings do passo 5 em `conceitos\_aprendizado/passos/lore\_embeddings\_cache.json`.



\---



\## Tecnologias utilizadas



\*\*Backend\*\*

\- \[FastAPI](https://fastapi.tiangolo.com/) — API REST + Server-Sent Events

\- \[Motor](https://motor.readthedocs.io/) — driver assíncrono para MongoDB

\- \[OpenAI Python SDK](https://github.com/openai/openai-python) — chamadas à API

\- \[ChromaDB](https://www.trychroma.com/) — banco de dados vetorial (scripts de estudo)



\*\*Frontend\*\*

\- \[React 19](https://react.dev/) + \[Vite](https://vitejs.dev/)

\- Fetch API com ReadableStream para consumo de SSE



\*\*Infraestrutura\*\*

\- \[MongoDB 7](https://www.mongodb.com/) via Docker

\- \[Mongo Express](https://github.com/mongo-express/mongo-express) — UI do banco



\---



\## Próximos passos sugeridos



\- \[ ] Adicionar mais sistemas de RPG (Call of Cthulhu, Shadowrun)

\- \[ ] Implementar o Passo 9: agentes múltiplos (narrador + árbitro de regras + inimigos)

\- \[ ] Integrar ChromaDB ao backend para memória semântica entre sessões

\- \[ ] Adicionar autenticação para múltiplos usuários

\- \[ ] Deploy em produção (Railway, Fly.io, etc.)



