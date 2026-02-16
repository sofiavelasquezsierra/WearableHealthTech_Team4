#!/bin/bash
# Run get_mapping.py on first CSV found in each dataset (except Yareta, HuGaDB).
# Usage: from sync_columns/ run: ./run_get_mapping.sh

cd "$(dirname "$0")"
BASE="/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets"
RAW="$BASE/00_raw"
SYNCED="$BASE/01_columns_synced"

echo "RAW=$RAW"
echo "SYNCED=$SYNCED"
[[ -d "$RAW" ]] || { echo "ERROR: RAW dir not found"; exit 1; }
echo ""

run_dataset() {
    local name="$1"
    local root="$2"
    local pattern="${3:-*.csv}"
    local sample
    echo "--- Checking $name at: $root (pattern: $pattern)"
    if [[ ! -d "$root" ]]; then
        echo "  SKIP: Directory does not exist"
        return 0
    fi
    sample=$(find "$root" -name "$pattern" -type f 2>/dev/null | head -1)
    if [[ -z "$sample" ]]; then
        echo "  SKIP: No CSV found"
        return 0
    fi
    echo "  Sample: $sample"
    echo "  Running get_mapping.py..."
    python get_mapping.py "$sample" -o "$SYNCED/test_$(echo "$name" | tr '[:upper:]' '[:lower:]').csv"
}

run_dataset "CAMARGO" "$RAW/CAMARGO/Camargo_CSV"
run_dataset "RealWorldHAR" "$RAW/RealWorldHAR/realworld2016_dataset"
run_dataset "NEWBEE" "$RAW/NEWBEE/multi_modal_gait_database/data_set" "xsens.csv"

echo ""
echo "Done."
