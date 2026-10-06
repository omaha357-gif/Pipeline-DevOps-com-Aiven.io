"""
Módulo compartilhado: conexão com o Postgres da Aiven e leitura da API
de dados abertos do Banco Central (SGS). Usado por app.py, producer.py
e consumer.py — evita duplicar a lógica de acesso a dados em cada script.
"""

import os
import datetime
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import RealDictCursor
import requests

DB_URL = os.environ.get("AIVEN_DB_URL")

# Séries do SGS/BCB — dados abertos, sem autenticação.
# Referência completa de códigos: https://www3.bcb.gov.br/sgspub
SERIES = {
    1:   {"name": "Dólar comercial (venda)", "unit": "R$", "casas": 4},
    432: {"name": "Meta Selic definida pelo Copom", "unit": "% a.a.", "casas": 2},
    433: {"name": "IPCA - variação mensal", "unit": "%", "casas": 2},
}
POINTS_PER_SERIES = 30

# Pool de conexões: a Aiven fica em outra região/rede que o Render, então
# abrir uma conexão nova (TCP + handshake SSL) custa ~1s toda vez. Uma
# única página do dashboard faz várias consultas (visita, cache de cada
# série, contagem de acessos...), e abrir uma conexão nova pra cada uma
# multiplicava esse ~1s por 7-8, deixando a página bem lenta. Com o pool,
# as conexões são abertas uma vez e reaproveitadas entre requisições.
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not DB_URL:
            raise RuntimeError("AIVEN_DB_URL não configurada")
        _pool = psycopg2_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DB_URL,
            sslmode="require",
            cursor_factory=RealDictCursor,
            connect_timeout=10,
        )
    return _pool


@contextmanager
def get_connection():
    """Pega uma conexão emprestada do pool e devolve ao sair do bloco
    `with` — em vez de abrir/fechar uma conexão física nova toda vez."""
    conn = _get_pool().getconn()
    try:
        yield conn
    except Exception:
        # Se algo deu errado no meio de uma transação, desfaz antes de
        # devolver ao pool — senão a próxima requisição que reaproveitar
        # essa conexão herda uma transação "abortada" e falha em cascata.
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)


def init_db():
    """Cria as tabelas caso ainda não existam.

    Em produção, vários workers do gunicorn chamam esta função quase ao
    mesmo tempo na inicialização. `CREATE TABLE IF NOT EXISTS` não é
    100% atômico entre transações concorrentes no Postgres, então dois
    workers podem colidir tentando criar a mesma tabela ao mesmo tempo
    (erro de "duplicate key" no catálogo interno pg_type). Isso é
    inofensivo — só significa que outro worker já criou a tabela — então
    apenas ignoramos esse erro específico em vez de deixar o worker
    inteiro cair.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bcb_series (
                        series_code INTEGER NOT NULL,
                        ref_date    DATE NOT NULL,
                        value       NUMERIC NOT NULL,
                        fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (series_code, ref_date)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visits (
                        id SERIAL PRIMARY KEY,
                        path TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
            conn.commit()
    except psycopg2.errors.DuplicateTable:
        # Outro worker criou a tabela entre nossa checagem e nosso CREATE.
        # Tudo bem, o objetivo (tabela existir) já foi alcançado.
        pass
    except psycopg2.errors.UniqueViolation as exc:
        # Mesma corrida, mas manifestada como conflito no catálogo interno
        # pg_type em vez de "table already exists". Também inofensivo.
        if "pg_type" not in str(exc):
            raise


def fetch_series_from_bcb(series_code: int, n: int = POINTS_PER_SERIES):
    """Busca os últimos N pontos de uma série no SGS do Banco Central.

    Observação: o endpoint `/dados/ultimos/{n}` da API do BCB está
    respondendo 400 Bad Request no momento (testado manualmente). Por
    isso usamos aqui o endpoint padrão com `dataInicial`/`dataFinal`, que
    funciona normalmente, e pegamos só os últimos N pontos retornados.
    """
    days_back = n * 3  # margem folgada: nem todo dia tem valor (fins de semana, feriados etc.)
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_back)

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados"
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": today.strftime("%d/%m/%Y"),
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    raw = resp.json()  # [{"data": "27/08/2026", "valor": "5.3521"}, ...]

    parsed = []
    for item in raw:
        ref_date = datetime.datetime.strptime(item["data"], "%d/%m/%Y").date()
        parsed.append({"ref_date": ref_date, "value": float(item["valor"])})
    return parsed[-n:]


def upsert_series(series_code: int, points: list):
    """Grava (ou atualiza) pontos de uma série direto no Postgres —
    usado tanto pelo cache do app.py quanto pelo consumer.py do Kafka."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for p in points:
                cur.execute(
                    """
                    INSERT INTO bcb_series (series_code, ref_date, value, fetched_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (series_code, ref_date)
                    DO UPDATE SET value = EXCLUDED.value, fetched_at = now();
                    """,
                    (series_code, p["ref_date"], p["value"]),
                )
        conn.commit()
