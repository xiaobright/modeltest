#!/bin/bash
# 睡姿分类模型一键编译脚本
# 用法: bash build_model.sh
# 替换 model.c 后重新运行此脚本即可重新编译

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/posture_model"
SOURCE="${MODEL_DIR}/model.c"
OUTPUT="${MODEL_DIR}/libposture_model.so"

if [ ! -f "$SOURCE" ]; then
    echo "[ERROR] 找不到模型源文件: $SOURCE"
    echo "请将 m2cgen 生成的 model.c 放入 ${MODEL_DIR}/"
    exit 1
fi

echo "========================================="
echo "  睡姿分类模型编译"
echo "========================================="
echo "源文件: $SOURCE"
echo "输出:   $OUTPUT"
echo ""

gcc -shared -fPIC -o "$OUTPUT" "$SOURCE" -lm

echo ""
echo "[OK] 编译成功: $OUTPUT"
ls -lh "$OUTPUT"
