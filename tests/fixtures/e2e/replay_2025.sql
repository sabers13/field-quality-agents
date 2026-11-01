-- Deterministic fixture data for Q8's replay run and Playwright test.
--
-- It is a tiny, synthetic stand-in for the committed NHTSA snapshot: sixteen
-- replay cases over three weeks in June 2025, a small knowledge base, two
-- recalls and one investigation, and a weekly series with one spike. No real
-- report is reproduced here.

CREATE TABLE complaints (
    id VARCHAR,
    received_at DATE,
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    component VARCHAR,
    "group" VARCHAR,
    narrative VARCHAR,
    safety_relevant BOOLEAN,
    mileage INTEGER
);

INSERT INTO complaints VALUES
    ('K-2021-0001', DATE '2021-01-05', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops when the cabin is cold and damp.', false, 12000),
    ('K-2021-0002', DATE '2021-02-11', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 18000),
    ('K-2021-0003', DATE '2021-03-02', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'After service the wiper motor failed again and the connector was loose.', false, 14000),
    ('K-2021-0004', DATE '2021-04-19', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'A vibration over rough roads makes the wiper motor stop.', false, 16000),
    ('K-2021-0005', DATE '2021-05-24', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'The battery dies intermittently in cold weather.', false, 31000),
    ('K-2021-0006', DATE '2021-07-08', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'Moisture in the door connector causes the window switch to fail.', false, 14000),
    ('K-2022-0001', DATE '2022-05-03', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'The charging port overheats during fast charging and the car stops charging.', true, 5000),
    ('K-2022-0002', DATE '2022-06-14', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'DC fast charging causes the charge port to overheat.', true, 6000),
    ('K-2022-0003', DATE '2022-07-21', 'TESLA', 'MODEL Y', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging in hot weather.', true, 7000),
    ('K-2022-0004', DATE '2022-08-30', 'HYUNDAI', 'IONIQ 5', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging is slow and the charge port overheats.', true, 9000),
    ('C-2025-0001', DATE '2025-06-02', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops when the cabin is cold and damp, and starts again after the cabin warms up.', false, 22000),
    ('C-2025-0002', DATE '2025-06-03', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 24000),
    ('C-2025-0003', DATE '2025-06-04', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'The charging port overheats during fast charging and the car stops charging.', true, 7000),
    ('C-2025-0004', DATE '2025-06-05', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'When it is cold the wiper motor stops and the visibility drops.', false, 25000),
    ('C-2025-0005', DATE '2025-06-06', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor is intermittent after service and the connector looks loose.', false, 26000),
    ('C-2025-0006', DATE '2025-06-09', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops when the cabin is cold and damp.', false, 27000),
    ('C-2025-0007', DATE '2025-06-10', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 28000),
    ('C-2025-0008', DATE '2025-06-11', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'When it is cold the wiper motor stops and the visibility drops.', false, 29000),
    ('C-2025-0009', DATE '2025-06-12', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor is intermittent after service and the connector looks loose.', false, 30000),
    ('C-2025-0010', DATE '2025-06-13', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops when the cabin is cold and damp.', false, 31000),
    ('C-2025-0011', DATE '2025-06-14', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 32000),
    ('C-2025-0012', DATE '2025-06-13', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'The battery dies intermittently in cold weather.', false, 33000),
    ('C-2025-0013', DATE '2025-06-16', 'TESLA', 'MODEL Y', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging in hot weather.', true, 8000),
    ('C-2025-0014', DATE '2025-06-17', 'HYUNDAI', 'IONIQ 5', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging is slow and the charge port overheats.', true, 9000),
    ('C-2025-0015', DATE '2025-06-18', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops when the cabin is cold and damp.', false, 34000),
    ('C-2025-0016', DATE '2025-06-19', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 35000);

-- The replay set is the sixteen C-2025 cases only; the knowledge base stays in
-- ``complaints``.
CREATE TABLE cases AS
SELECT * FROM complaints WHERE id LIKE 'C-2025-%';

CREATE TABLE recalls (
    id VARCHAR,
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    component VARCHAR,
    "group" VARCHAR,
    summary VARCHAR,
    open_date DATE
);

INSERT INTO recalls VALUES
    ('R-2024-0002', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charge port may overheat during fast charging.', DATE '2024-06-01'),
    ('R-2025-0001', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor may fail and reduce visibility.', DATE '2025-07-15'),
    ('R-2025-0003', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'Battery cable may chafe.', DATE '2025-08-01');

CREATE TABLE investigations (
    id VARCHAR,
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    component VARCHAR,
    "group" VARCHAR,
    summary VARCHAR,
    open_date DATE
);

INSERT INTO investigations VALUES
    ('I-2025-0001', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Investigation into wiper motor failures.', DATE '2025-08-20');

CREATE TABLE events (
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    "group" VARCHAR,
    event_type VARCHAR,
    event_date DATE,
    source_id VARCHAR
);

INSERT INTO events VALUES
    ('TESLA', 'MODEL 3', 2022, 'ev_propulsion', 'recall', DATE '2024-06-01', 'R-2024-0002'),
    ('FORD', 'F-150', 2021, 'body_controls', 'recall', DATE '2025-07-15', 'R-2025-0001'),
    ('FORD', 'F-150', 2021, 'body_controls', 'investigation', DATE '2025-08-20', 'I-2025-0001'),
    ('FORD', 'F-150', 2021, 'electrical_general', 'recall', DATE '2025-08-01', 'R-2025-0003');

CREATE TABLE fleet_weekly (
    week_start DATE,
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    "group" VARCHAR,
    "count" BIGINT
);

-- The wiper cluster: a quiet alternating baseline, four reports in the week of
-- 2025-06-02 and six in the week of 2025-06-09 (threshold five).
INSERT INTO fleet_weekly
SELECT CAST(DATE '2024-12-02' + CAST(index AS INTEGER) * 7 AS DATE),
       'FORD', 'F-150', 2021, 'body_controls',
       CASE
           WHEN index = 28 THEN 2
           WHEN index = 27 THEN 6
           WHEN index = 26 THEN 4
           WHEN index % 2 = 0 THEN 1
           ELSE 0
       END
FROM range(0, 29) AS weeks(index);

-- A quieter electrical cluster has one report and never spikes.
INSERT INTO fleet_weekly VALUES
    (DATE '2025-06-09', 'FORD', 'F-150', 2021, 'electrical_general', 1);
