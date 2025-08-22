-- Add BERTScore benchmark datasets for multi-language translation evaluation
INSERT IGNORE INTO benchmark_datasets (name, description, task_type, evaluation_metric)
VALUES 
('flores_spanish_translation_bertscore', 'FLORES+ English to Spanish translation benchmark (BERTScore)', 'translation', 'bertscore'),
('flores_japanese_translation_bertscore', 'FLORES+ English to Japanese translation benchmark (BERTScore)', 'translation', 'bertscore'),
('flores_arabic_translation_bertscore', 'FLORES+ English to Arabic translation benchmark (BERTScore)', 'translation', 'bertscore'),
('flores_chinese_translation_bertscore', 'FLORES+ English to Chinese translation benchmark (BERTScore)', 'translation', 'bertscore'),
('flores_korean_translation_bertscore', 'FLORES+ English to Korean translation benchmark (BERTScore)', 'translation', 'bertscore'); 