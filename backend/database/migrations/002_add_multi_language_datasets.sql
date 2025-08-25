-- Migration: Add Multi-Language Translation Datasets
-- Adds Japanese, Arabic, and Chinese translation benchmarks

-- Insert Japanese translation benchmark dataset
INSERT IGNORE INTO benchmark_datasets (name, description, task_type, evaluation_metric) 
VALUES ('flores_japanese_translation', 'FLORES+ English to Japanese translation benchmark', 'translation', 'bleu');

-- Insert Arabic translation benchmark dataset  
INSERT IGNORE INTO benchmark_datasets (name, description, task_type, evaluation_metric) 
VALUES ('flores_arabic_translation', 'FLORES+ English to Arabic translation benchmark', 'translation', 'bleu');

-- Insert Chinese translation benchmark dataset
INSERT IGNORE INTO benchmark_datasets (name, description, task_type, evaluation_metric) 
VALUES ('flores_chinese_translation', 'FLORES+ English to Chinese translation benchmark', 'translation', 'bleu'); 