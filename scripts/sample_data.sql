-- Sample M-Pesa transaction data for development and testing
-- This file populates the mpesa_transactions_raw table with realistic test data

INSERT INTO mpesa_transactions_raw 
    (transaction_id, phone_number, amount, account_reference, transaction_time, source, payload)
VALUES
    ('LHG31SV2QV', '254712345678', 500.00, 'INV001', '2024-05-14 12:00:00', 'c2b_webhook', 
     '{"event_type":"c2b_confirmation","merchant":"ABC Store","timestamp":"20240514120000"}'),
    ('LHG31SV2QW', '254722456789', 1000.00, 'INV002', '2024-05-14 12:05:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"XYZ Store","timestamp":"20240514120500"}'),
    ('LHG31SV2QX', '254702567890', 250.50, 'INV003', '2024-05-14 12:10:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"DEF Store","timestamp":"20240514121000"}'),
    ('LHG31SV2QY', '254712678901', 1500.00, 'INV004', '2024-05-14 12:15:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"GHI Store","timestamp":"20240514121500"}'),
    ('LHG31SV2QZ', '254722789012', 750.00, 'INV005', '2024-05-14 12:20:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"JKL Store","timestamp":"20240514122000"}'),
    ('LHG31SV2RA', '254712890123', 2000.00, 'INV006', '2024-05-14 12:25:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"MNO Store","timestamp":"20240514122500"}'),
    ('LHG31SV2RB', '254702901234', 600.00, 'INV007', '2024-05-14 12:30:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"PQR Store","timestamp":"20240514123000"}'),
    ('LHG31SV2RC', '254712345679', 900.00, 'INV008', '2024-05-14 12:35:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"STU Store","timestamp":"20240514123500"}'),
    ('LHG31SV2RD', '254722456790', 1200.00, 'INV009', '2024-05-14 12:40:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"VWX Store","timestamp":"20240514124000"}'),
    ('LHG31SV2RE', '254702567891', 450.00, 'INV010', '2024-05-14 12:45:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"YZA Store","timestamp":"20240514124500"}');

-- Insert more transactions across different hours for time-series analysis
INSERT INTO mpesa_transactions_raw 
    (transaction_id, phone_number, amount, account_reference, transaction_time, source, payload)
VALUES
    ('LHG31SV2RF', '254712345680', 550.00, 'INV011', '2024-05-14 13:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"ABC Store","timestamp":"20240514130000"}'),
    ('LHG31SV2RG', '254722456791', 850.00, 'INV012', '2024-05-14 13:15:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"XYZ Store","timestamp":"20240514131500"}'),
    ('LHG31SV2RH', '254702567892', 1100.00, 'INV013', '2024-05-14 13:30:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"DEF Store","timestamp":"20240514133000"}'),
    ('LHG31SV2RI', '254712678902', 650.00, 'INV014', '2024-05-14 14:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"GHI Store","timestamp":"20240514140000"}'),
    ('LHG31SV2RJ', '254722789013', 950.00, 'INV015', '2024-05-14 14:30:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"JKL Store","timestamp":"20240514143000"}');

-- Transactions from different days for daily aggregations
INSERT INTO mpesa_transactions_raw 
    (transaction_id, phone_number, amount, account_reference, transaction_time, source, payload)
VALUES
    ('LHG31SV2RK', '254712345681', 700.00, 'INV016', '2024-05-13 10:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"ABC Store","timestamp":"20240513100000"}'),
    ('LHG31SV2RL', '254722456792', 1100.00, 'INV017', '2024-05-13 14:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"XYZ Store","timestamp":"20240513140000"}'),
    ('LHG31SV2RM', '254702567893', 400.00, 'INV018', '2024-05-13 18:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"DEF Store","timestamp":"20240513180000"}'),
    ('LHG31SV2RN', '254712678903', 1300.00, 'INV019', '2024-05-12 11:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"GHI Store","timestamp":"20240512110000"}'),
    ('LHG31SV2RO', '254722789014', 800.00, 'INV020', '2024-05-12 15:00:00', 'c2b_webhook',
     '{"event_type":"c2b_confirmation","merchant":"JKL Store","timestamp":"20240512150000"}');

-- Verify data
SELECT 
    COUNT(*) as total_transactions,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MIN(amount) as min_amount,
    MAX(amount) as max_amount,
    COUNT(DISTINCT phone_number) as unique_customers
FROM mpesa_transactions_raw;
