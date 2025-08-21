-- Fall Detection Database Initialization Script

-- Create database if not exists (for manual setup)
-- CREATE DATABASE IF NOT EXISTS fall_detection;

-- Create main table for fall detection results
CREATE TABLE IF NOT EXISTS fall_detections (
    id SERIAL PRIMARY KEY,
    image_hash VARCHAR(64) UNIQUE NOT NULL,
    result VARCHAR(10) NOT NULL CHECK (result IN ('Yes', 'No')),
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_size VARCHAR(20),
    processing_time_ms INTEGER CHECK (processing_time_ms >= 0),
    votes_yes INTEGER DEFAULT 0,
    votes_no INTEGER DEFAULT 0,
    total_crops INTEGER DEFAULT 1
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_image_hash ON fall_detections(image_hash);
CREATE INDEX IF NOT EXISTS idx_created_at ON fall_detections(created_at);
CREATE INDEX IF NOT EXISTS idx_result ON fall_detections(result);
CREATE INDEX IF NOT EXISTS idx_processing_time ON fall_detections(processing_time_ms);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_fall_detections_updated_at 
    BEFORE UPDATE ON fall_detections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for testing (optional)
INSERT INTO fall_detections (image_hash, result, confidence, image_size, processing_time_ms, votes_yes, votes_no, total_crops) 
VALUES 
    ('sample_hash_1', 'Yes', 0.85, '640x480', 1250, 2, 1, 3),
    ('sample_hash_2', 'No', 0.92, '1920x1080', 890, 0, 3, 3)
ON CONFLICT (image_hash) DO NOTHING;

-- Create view for statistics
CREATE OR REPLACE VIEW fall_detection_stats AS
SELECT 
    COUNT(*) as total_processed,
    COUNT(CASE WHEN result = 'Yes' THEN 1 END) as fall_detected,
    COUNT(CASE WHEN result = 'No' THEN 1 END) as no_fall,
    ROUND(AVG(processing_time_ms)::numeric, 2) as avg_processing_time_ms,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
    COUNT(DISTINCT DATE(created_at)) as days_active,
    MIN(created_at) as first_detection,
    MAX(created_at) as last_detection
FROM fall_detections;

-- Grant permissions (if needed for specific user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Success message
SELECT 'Fall Detection Database initialized successfully!' as status;
