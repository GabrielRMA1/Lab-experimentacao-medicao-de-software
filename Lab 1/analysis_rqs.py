import sys
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BASE_DIR / "dados_repositorios_github.csv"
DEFAULT_OUTPUT = BASE_DIR / "analise_rqs.md"

LANGUAGE_COLUMN = "linguagem"
NUMERIC_COLUMNS = [
    "idade_anos",
    "idade_dias",
    "prs_aceitas",
    "contagem_releases",
    "ultima_atualizacao",
    "estrelas",
    "total_issues",
    "issues_fechadas",
    "percentual_issues_fechadas",
    "tempo_atividade_continuada_dias",
    "issues_por_estrela",
    "proporcao_contribuicoes_externas",
]


def count_language_nulls(df):
    if LANGUAGE_COLUMN not in df.columns:
        return None

    normalized = df[LANGUAGE_COLUMN].fillna("Nao informada")
    return int((normalized == "Nao informada").sum())


def get_iqr_outliers(df, column):
    values = pd.to_numeric(df[column], errors="coerce").dropna()

    if values.empty:
        return {
            "q1": None,
            "q3": None,
            "lower_limit": None,
            "upper_limit": None,
            "outliers": 0,
        }

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    lower_limit = q1 - 1.5 * iqr
    upper_limit = q3 + 1.5 * iqr
    outliers = values[(values < lower_limit) | (values > upper_limit)]

    return {
        "q1": q1,
        "q3": q3,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "outliers": int(outliers.count()),
    }


def format_number(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def describe_column(df, column):
    values = pd.to_numeric(df[column], errors="coerce").dropna()

    if values.empty:
        return None

    return {
        "mean": values.mean(),
        "median": values.median(),
        "minimum": values.min(),
        "maximum": values.max(),
    }


def build_report(df):
    total_repos = len(df)
    lines = [
        "# Analise das RQs",
        "",
        f"Total de repositorios analisados: {total_repos}",
        "",
        "## Nulos",
        "",
    ]

    for column in [LANGUAGE_COLUMN] + NUMERIC_COLUMNS:
        if column in df.columns:
            nulls = int(df[column].isna().sum())
            lines.append(f"- {column}: {nulls} valores nulos")
        else:
            lines.append(f"- {column}: coluna nao encontrada")

    language_nulls = count_language_nulls(df)
    if language_nulls is not None:
        lines.append(f"- linguagem marcada como 'Nao informada': {language_nulls}")

    lines.extend(["", "## Estatisticas descritivas", ""])

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            lines.append(f"- {column}: coluna nao encontrada")
            continue

        result = describe_column(df, column)
        if result is None:
            lines.append(f"- {column}: sem valores numericos")
            continue

        lines.append(
            f"- {column}: media {format_number(result['mean'])}, "
            f"mediana {format_number(result['median'])}, "
            f"minimo {format_number(result['minimum'])}, "
            f"maximo {format_number(result['maximum'])}"
        )

    lines.extend(["", "## Outliers por IQR", ""])

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            lines.append(f"- {column}: coluna nao encontrada")
            continue

        result = get_iqr_outliers(df, column)
        lines.append(
            f"- {column}: {result['outliers']} outliers "
            f"(limite inferior {format_number(result['lower_limit'])}, "
            f"limite superior {format_number(result['upper_limit'])})"
        )

    lines.extend(["", "## Hipoteses informais", ""])
    lines.append(
        "- RQ01: repositorios populares tendem a ser mais antigos e maduros, "
        "mas uma distribuicao assimetrica pode indicar que poucos projetos "
        "muito antigos concentram grande parte da idade observada."
    )
    lines.append(
        "- RQ02: repositorios populares tendem a receber contribuicoes externas "
        "por meio de pull requests mescladas. Valores muito altos podem estar "
        "concentrados em poucos projetos com comunidades maiores."
    )
    lines.append(
        "- RQ03: a quantidade de releases pode indicar frequencia de entrega e "
        "maturidade, embora projetos com estrategias de versionamento diferentes "
        "nao sejam diretamente comparaveis."
    )
    lines.append(
        "- RQ04: poucos dias desde a ultima atualizacao sugerem atividade recente. "
        "Projetos arquivados, sazonais ou com baixa frequencia de commits podem "
        "aparecer como pouco ativos mesmo quando continuam relevantes."
    )
    lines.append(
        "- RQ05: a distribuicao de linguagens tende a ser concentrada em poucas "
        "linguagens populares. Repositorios sem linguagem principal podem indicar "
        "documentacao, configuracao, colecoes de exemplos ou projetos com arquivos "
        "muito heterogeneos."
    )
    lines.append(
        "- RQ06: estrelas costumam ter distribuicao assimetrica. Poucos repositorios "
        "muito famosos podem puxar a media para cima, entao mediana e outliers sao "
        "mais informativos que apenas a media."
    )
    lines.append(
        "- RQ07: muitos issues ou alto percentual de issues fechadas podem indicar "
        "projetos grandes e maduros, mas tambem processos diferentes de triagem. "
        "Repositorios com poucas issues podem distorcer percentuais."
    )
    lines.append(
        "- RQ10: uma maior proporcao de PRs merged por issue fechada pode sugerir "
        "um fluxo de contribuicoes mais aberto e maduro. A metrica usa todas as "
        "PRs merged, portanto nao identifica com precisao se o autor e externo "
        "a equipe do repositorio; repositorios sem issues fechadas nao possuem "
        "razao calculavel."
    )

    if LANGUAGE_COLUMN in df.columns:
        lines.extend(["", "## Linguagens mais frequentes", ""])
        language_counts = df[LANGUAGE_COLUMN].fillna("Nao informada").value_counts().head(10)
        for language, count in language_counts.items():
            lines.append(f"- {language}: {count}")

    return "\n".join(lines) + "\n"


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo CSV nao encontrado: {input_path}")

    df = pd.read_csv(input_path)
    report = build_report(df)
    output_path.write_text(report, encoding="utf-8")

    print(f"Analise gerada em: {output_path}")


if __name__ == "__main__":
    main()
