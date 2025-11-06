#!/bin/bash

# 简单的批量处理脚本
# 遍历所有英文文献分组并处理其中的PDF文件

BASE_DIR="/mnt/e/大模型文献2025年3月/英文文献"
LOG_FILE="/home/axlhuang/kb_create/batch_processing.log"
PROCESSED_GROUPS_FILE="/home/axlhuang/kb_create/processed_groups.txt"

# 创建日志文件
touch $LOG_FILE
touch $PROCESSED_GROUPS_FILE

# 记录开始时间
echo "[$(date)] 开始批量处理所有英文文献" >> $LOG_FILE

# 遍历所有分组目录
find "$BASE_DIR" -type d -name "*" | while read group_dir; do
    # 跳过根目录
    if [ "$group_dir" = "$BASE_DIR" ]; then
        continue
    fi
    
    # 检查分组是否已处理
    if grep -q "$group_dir" "$PROCESSED_GROUPS_FILE"; then
        echo "[$(date)] 跳过分组 $group_dir (已处理)" >> $LOG_FILE
        continue
    fi
    
    # 检查分组中是否有PDF文件
    pdf_count=$(find "$group_dir" -maxdepth 1 -name "*.pdf" | wc -l)
    if [ $pdf_count -eq 0 ]; then
        echo "[$(date)] 跳过分组 $group_dir (无PDF文件)" >> $LOG_FILE
        continue
    fi
    
    echo "[$(date)] 处理分组: $group_dir (包含 $pdf_count 个PDF文件)" >> $LOG_FILE
    
    # 更新配置文件指向当前分组
    sed -i "s|INPUT_DIR=.*|INPUT_DIR=$group_dir|" /home/axlhuang/kb_create/config/config.env
    
    # 运行处理管道
    echo "[$(date)] 开始处理分组 $group_dir" >> $LOG_FILE
    cd /home/axlhuang/kb_create
    export DASHSCOPE_API_KEY=sk-2f1e5c15eed5463a9f05c2f8d6d49f8a
    python main.py --log-level INFO >> $LOG_FILE 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] 分组 $group_dir 处理成功" >> $LOG_FILE
        # 记录已处理的分组
        echo "$group_dir" >> $PROCESSED_GROUPS_FILE
    else
        echo "[$(date)] 分组 $group_dir 处理失败" >> $LOG_FILE
    fi
    
    # 等待一段时间再处理下一个分组
    sleep 60
done

echo "[$(date)] 批量处理完成" >> $LOG_FILE