睡眠分期部署包说明

1. models
- sleep_stage_rf_2class.joblib : 生理特征二分类模型（W / Sleep）
- rf_eeg_c4a1_N3merge.joblib   : EEG 五类分期参考模型

2. scripts
- fusion_with_eeg_conf.py : EEG + 生理模型融合脚本
- score_sleep_quality_per_record.py : 按record统计并评分
- extract_br_features_real.py / extract_hrv_features_real.py : 如存在，则用于从真实信号提取特征
- run_demo.py : 使用 examples 中示例数据进行快速演示

3. examples
- fusion_eeg_final_conf.csv : 融合输出示例
- sleep_quality_per_record.csv : 评分输出示例
- features_eeg_c4a1_N3merge.csv : EEG特征输入示例

4. 当前流程
真实信号 -> 提取 BR/HRV 特征 -> 生理模型判断 W/Sleep -> 与 EEG 结果融合 -> 输出五类睡眠阶段 -> 按record做睡眠结构分析和条件评分

5. 注意
- 评分模块只对时长足够的记录进行评分
- 当前代码适合先在上位机/RK3588侧验证，再迁移到开发板
- 如果开发板算力有限，可先部署二分类模型，再把EEG融合放在上位机

6. 快速运行
cd scripts
python run_demo.py
