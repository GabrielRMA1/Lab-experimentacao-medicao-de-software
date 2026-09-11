SRC_DIR="$1"
TRIAL_ID="$2"
OUTPUT_DIR="metrics_results"

if [ -z "$SRC_DIR" ] || [ -z "$TRIAL_ID" ]; then
    echo "Erro: forneça o diretório fonte e o ID do trial."
    echo "Uso: $0 <src_dir> <trial_id>"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
LIB_DIR="scripts/lib"

# Verifica dependências.
CK_JAR="$LIB_DIR/ck.jar"
PMD_DIR="$LIB_DIR/pmd-bin"

echo "=== Executando análise de métricas estáticas para: $TRIAL_ID ==="

# 1. Execução do CK (Java Metrics: WMC, LOC, CBO etc.).
if [ -f "$CK_JAR" ]; then
    echo "Running CK Metrics..."
    java -jar "$CK_JAR" "$SRC_DIR" false 0 false "$OUTPUT_DIR/${TRIAL_ID}_ck"
    # CK gera arquivos <prefix>class.csv e <prefix>method.csv.
else
    echo "AVISO: $CK_JAR não encontrado em $LIB_DIR! Baixe o CK do repositório oficial."
fi

# 2. Execução do PMD CPD (duplicação de código).
if [ -d "$PMD_DIR" ]; then
    echo "Running PMD CPD..."
    "$PMD_DIR/bin/pmd" cpd --minimum-tokens 10 --dir "$SRC_DIR" --language java
else
    echo "AVISO: PMD não encontrado em $LIB_DIR! Baixe o PMD binário oficial."
fi

echo "Análise concluída. Resultados salvos em '$OUTPUT_DIR/'."