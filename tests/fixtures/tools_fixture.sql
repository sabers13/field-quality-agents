-- Small deterministic DuckDB used by tests/tools/.
-- The shapes match docs/INTERFACES.md §Q1; the values are synthetic.

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
    ('c01', DATE '2021-01-05', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'The wiper motor stops intermittently when the cabin is cold and damp.', false, 12000),
    ('c02', DATE '2021-02-11', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent in cold weather and then quits.', false, 18000),
    ('c03', DATE '2021-03-02', 'FORD', 'F-150', 2021, 'RADIO/TAPE DECK/CD ETC.', 'body_controls',
     'The radio display flickers intermittently when it is cold.', false, 9000),
    ('c04', DATE '2022-01-07', 'FORD', 'F-150', 2022, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor is intermittent when cold.', false, 22000),
    ('c05', DATE '2021-04-19', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'The battery dies intermittently in cold weather.', false, 31000),
    ('c06', DATE '2022-05-03', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'The charging port overheats during fast charging and the car stops charging.', true, 5000),
    ('c07', DATE '2022-06-14', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'DC fast charging causes the charge port to overheat.', true, 6000),
    ('c08', DATE '2022-07-21', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging in hot weather.', true, 7000),
    ('c09', DATE '2022-08-30', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging.', true, 8000),
    ('c10', DATE '2022-09-02', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging.', true, 8100),
    ('c11', DATE '2023-01-12', 'TESLA', 'MODEL Y', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging port overheats during fast charging.', true, 9000),
    ('c12', DATE '2023-02-16', 'HYUNDAI', 'IONIQ 5', 2023, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging is slow and the charge port overheats.', true, 1000),
    ('c13', DATE '2021-05-24', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'body_controls',
     'Moisture in the door connector causes the window switch to fail.', false, 14000),
    ('c14', DATE '2021-06-30', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'After service the wiper motor failed again; the connector was loose.', false, 15000),
    ('c15', DATE '2021-07-08', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'body_controls',
     'A vibration over rough roads makes the display flicker.', false, 16000),
    ('c16', DATE '2021-08-17', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'When it is hot the wiper motor stops.', false, 17000),
    ('c17', DATE '2021-09-21', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Intermittent wiper failure after the battery was replaced.', false, 19000),
    ('c18', DATE '2022-10-05', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charging works normally after the software update.', false, 20000),
    ('c19', DATE '2021-10-28', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'body_controls',
     'The charging pad for the phone stops working.', false, 21000),
    ('c20', DATE '2021-11-02', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     repeat('The wiper motor grinds and stops. ', 15), false, 500);

CREATE TABLE cases AS SELECT * FROM complaints;

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
    ('r01', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor may fail and reduce visibility.', DATE '2023-05-01'),
    ('r02', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Second wiper motor recall for the same vehicle.', DATE '2024-02-01'),
    ('r03', 'FORD', 'F-150', 2021, 'ELECTRICAL SYSTEM', 'electrical_general',
     'Battery cable may chafe.', DATE '2022-01-01'),
    ('r04', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Charge port may overheat during fast charging.', DATE '2024-06-01'),
    ('r05', 'FORD', 'F-150', 2022, 'VISIBILITY/WIPER', 'body_controls',
     'Wiper motor may fail on the next model year.', DATE '2024-03-01');

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
    ('i01', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Investigation into wiper motor failures.', DATE '2024-01-15'),
    ('i02', 'FORD', 'F-150', 2021, 'VISIBILITY/WIPER', 'body_controls',
     'Earlier wiper query.', DATE '2023-01-15'),
    ('i03', 'TESLA', 'MODEL 3', 2022, 'ELECTRICAL SYSTEM', 'ev_propulsion',
     'Investigation into charge port overheating.', DATE '2024-05-01');

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
    ('FORD', 'F-150', 2021, 'body_controls', 'recall', DATE '2023-05-01', 'r01'),
    ('FORD', 'F-150', 2021, 'body_controls', 'investigation', DATE '2024-01-15', 'i01');

CREATE TABLE fleet_weekly (
    week_start DATE,
    make VARCHAR,
    model VARCHAR,
    year INTEGER,
    "group" VARCHAR,
    "count" BIGINT
);

-- 26 baseline weeks from 2025-01-06 plus the observed week 2025-07-07.
-- Key A: trailing mean 0.5, observed 5 -> spike (threshold 5).
INSERT INTO fleet_weekly
SELECT CAST(DATE '2025-01-06' + CAST(index AS INTEGER) * 7 AS DATE), 'FORD', 'F-150', 2021, 'body_controls',
       CASE WHEN index = 26 THEN 5 WHEN index % 2 = 0 THEN 1 ELSE 0 END
FROM range(0, 27) AS weeks(index);

-- Key B: quiet baseline, observed 2 -> no spike.
INSERT INTO fleet_weekly
SELECT CAST(DATE '2025-01-06' + CAST(index AS INTEGER) * 7 AS DATE), 'FORD', 'F-150', 2022, 'body_controls',
       CASE WHEN index = 26 THEN 2 ELSE 0 END
FROM range(0, 27) AS weeks(index);

-- Key C: trailing mean 1.0, observed 3 -> no spike.
INSERT INTO fleet_weekly
SELECT CAST(DATE '2025-01-06' + CAST(index AS INTEGER) * 7 AS DATE), 'TESLA', 'MODEL 3', 2022, 'ev_propulsion',
       CASE WHEN index = 26 THEN 3 ELSE 1 END
FROM range(0, 27) AS weeks(index);

-- Key D: no rows at all; every week zero-fills.
-- Key E: quiet baseline, observed 4 -> no spike (threshold 5).
INSERT INTO fleet_weekly
SELECT CAST(DATE '2025-01-06' + CAST(index AS INTEGER) * 7 AS DATE), 'FORD', 'F-150', 2021, 'electrical_general',
       CASE WHEN index = 26 THEN 4 ELSE 0 END
FROM range(0, 27) AS weeks(index);
