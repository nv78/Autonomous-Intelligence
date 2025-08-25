-- Migration: Add Leaderboard Tables
-- Run this on existing databases that don't have the leaderboard functionality

-- Create leaderboard tables if they don't exist
CREATE TABLE IF NOT EXISTS benchmark_datasets (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    task_type VARCHAR(100) NOT NULL,
    evaluation_metric VARCHAR(100) NOT NULL,
    dataset_file_path VARCHAR(500),
    reference_data LONGTEXT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS model_submissions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    benchmark_dataset_id INTEGER NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    submitted_by VARCHAR(255),
    model_results LONGTEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (benchmark_dataset_id) REFERENCES benchmark_datasets(id)
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    model_submission_id INTEGER NOT NULL,
    score DECIMAL(10, 6) NOT NULL,
    evaluation_details LONGTEXT,
    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_submission_id) REFERENCES model_submissions(id)
);

-- Insert default Spanish translation benchmark dataset if it doesn't exist
INSERT IGNORE INTO benchmark_datasets (name, description, task_type, evaluation_metric) 
VALUES ('flores_spanish_translation', 'FLORES+ English to Spanish translation benchmark', 'translation', 'bleu');

-- Create indexes (ignore errors if they already exist)
CREATE INDEX idx_model_submissions_dataset ON model_submissions(benchmark_dataset_id);
CREATE INDEX idx_model_submissions_name ON model_submissions(model_name);
CREATE INDEX idx_evaluation_results_submission ON evaluation_results(model_submission_id);
CREATE INDEX idx_evaluation_results_score ON evaluation_results(score); 