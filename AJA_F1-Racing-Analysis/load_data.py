"""
Loads the Ergast Formula 1 dataset (Kaggle: rohanrao/formula-1-world-
championship-1950-2020) into a SQLite database (f1.db) as a set of typed,
related tables covering seasons, circuits, races, drivers, constructors,
results, standings, qualifying, pit stops and lap times.

Run: python3 load_data.py
Reads from ./data/{races,results,drivers,constructors,circuits,
driver_standings,constructor_standings,qualifying,pit_stops,lap_times,
status,seasons}.csv

The source CSVs use "\\N" as their null marker (Ergast/MySQL convention) -
read_csv is told about this explicitly for every table, otherwise
unclassified finishes, missing lap times, etc. load as the literal string
"\\N" instead of NULL.
"""

import os
import sqlite3

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f1.db")

NA_VALUES = ["\\N"]

SCHEMA = """
CREATE TABLE seasons (
    year INTEGER PRIMARY KEY,
    url  TEXT
);

CREATE TABLE circuits (
    circuitId  INTEGER PRIMARY KEY,
    circuitRef TEXT,
    name       TEXT NOT NULL,
    location   TEXT,
    country    TEXT,
    lat        REAL,
    lng        REAL,
    alt        REAL,
    url        TEXT
);

CREATE TABLE races (
    raceId    INTEGER PRIMARY KEY,
    year      INTEGER NOT NULL,
    round     INTEGER NOT NULL,
    circuitId INTEGER NOT NULL,
    name      TEXT NOT NULL,
    date      TEXT NOT NULL,
    time      TEXT,
    url       TEXT,
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

CREATE TABLE drivers (
    driverId   INTEGER PRIMARY KEY,
    driverRef  TEXT,
    number     INTEGER,
    code       TEXT,
    forename   TEXT NOT NULL,
    surname    TEXT NOT NULL,
    dob        TEXT,
    nationality TEXT,
    url        TEXT
);

CREATE TABLE constructors (
    constructorId  INTEGER PRIMARY KEY,
    constructorRef TEXT,
    name           TEXT NOT NULL,
    nationality    TEXT,
    url            TEXT
);

CREATE TABLE status (
    statusId INTEGER PRIMARY KEY,
    status   TEXT NOT NULL
);

CREATE TABLE results (
    resultId        INTEGER PRIMARY KEY,
    raceId          INTEGER NOT NULL,
    driverId        INTEGER NOT NULL,
    constructorId   INTEGER NOT NULL,
    number          INTEGER,
    grid            INTEGER NOT NULL,
    position        INTEGER,   -- NULL = did not classify/finish (see status)
    positionText    TEXT,
    positionOrder   INTEGER NOT NULL,
    points          REAL NOT NULL,
    laps            INTEGER NOT NULL,
    time            TEXT,
    milliseconds    INTEGER,
    fastestLap      INTEGER,
    rank            INTEGER,   -- rank of this result's fastest lap in the race
    fastestLapTime  TEXT,
    fastestLapSpeed REAL,
    statusId        INTEGER NOT NULL,
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId),
    FOREIGN KEY (statusId) REFERENCES status(statusId)
);

CREATE TABLE driver_standings (
    driverStandingsId INTEGER PRIMARY KEY,
    raceId            INTEGER NOT NULL,
    driverId          INTEGER NOT NULL,
    points            REAL NOT NULL,
    position          INTEGER,
    positionText      TEXT,
    wins              INTEGER NOT NULL,
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

CREATE TABLE constructor_standings (
    constructorStandingsId INTEGER PRIMARY KEY,
    raceId                 INTEGER NOT NULL,
    constructorId          INTEGER NOT NULL,
    points                 REAL NOT NULL,
    position               INTEGER,
    positionText           TEXT,
    wins                   INTEGER NOT NULL,
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

CREATE TABLE qualifying (
    qualifyId     INTEGER PRIMARY KEY,
    raceId        INTEGER NOT NULL,
    driverId      INTEGER NOT NULL,
    constructorId INTEGER NOT NULL,
    number        INTEGER,
    position      INTEGER,
    q1            TEXT,
    q2            TEXT,
    q3            TEXT,
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- No surrogate key in the source data; (raceId, driverId, stop) is the
-- natural key (a driver's Nth stop of a given race).
CREATE TABLE pit_stops (
    raceId       INTEGER NOT NULL,
    driverId     INTEGER NOT NULL,
    stop         INTEGER NOT NULL,
    lap          INTEGER NOT NULL,
    time         TEXT,
    duration     TEXT,
    milliseconds INTEGER,
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Same pattern: (raceId, driverId, lap) is the natural key.
CREATE TABLE lap_times (
    raceId       INTEGER NOT NULL,
    driverId     INTEGER NOT NULL,
    lap          INTEGER NOT NULL,
    position     INTEGER,
    time         TEXT,
    milliseconds INTEGER,
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);
"""

INDEXES = """
CREATE INDEX idx_races_year ON races(year);
CREATE INDEX idx_races_circuit ON races(circuitId);

CREATE INDEX idx_results_race ON results(raceId);
CREATE INDEX idx_results_driver ON results(driverId);
CREATE INDEX idx_results_constructor ON results(constructorId);
CREATE INDEX idx_results_status ON results(statusId);

CREATE INDEX idx_driver_standings_race ON driver_standings(raceId);
CREATE INDEX idx_driver_standings_driver ON driver_standings(driverId);

CREATE INDEX idx_constructor_standings_race ON constructor_standings(raceId);
CREATE INDEX idx_constructor_standings_constructor ON constructor_standings(constructorId);

CREATE INDEX idx_qualifying_race ON qualifying(raceId);
CREATE INDEX idx_qualifying_driver ON qualifying(driverId);

CREATE INDEX idx_pit_stops_race ON pit_stops(raceId);
CREATE INDEX idx_pit_stops_driver ON pit_stops(driverId);

CREATE INDEX idx_lap_times_race ON lap_times(raceId);
CREATE INDEX idx_lap_times_driver ON lap_times(driverId);
"""

# (csv filename, table name, columns to keep in this order)
TABLES = [
    ("seasons.csv", "seasons", ["year", "url"]),
    ("circuits.csv", "circuits",
     ["circuitId", "circuitRef", "name", "location", "country", "lat", "lng", "alt", "url"]),
    ("races.csv", "races", ["raceId", "year", "round", "circuitId", "name", "date", "time", "url"]),
    ("drivers.csv", "drivers",
     ["driverId", "driverRef", "number", "code", "forename", "surname", "dob", "nationality", "url"]),
    ("constructors.csv", "constructors", ["constructorId", "constructorRef", "name", "nationality", "url"]),
    ("status.csv", "status", ["statusId", "status"]),
    ("results.csv", "results", [
        "resultId", "raceId", "driverId", "constructorId", "number", "grid", "position", "positionText",
        "positionOrder", "points", "laps", "time", "milliseconds", "fastestLap", "rank",
        "fastestLapTime", "fastestLapSpeed", "statusId",
    ]),
    ("driver_standings.csv", "driver_standings",
     ["driverStandingsId", "raceId", "driverId", "points", "position", "positionText", "wins"]),
    ("constructor_standings.csv", "constructor_standings",
     ["constructorStandingsId", "raceId", "constructorId", "points", "position", "positionText", "wins"]),
    ("qualifying.csv", "qualifying",
     ["qualifyId", "raceId", "driverId", "constructorId", "number", "position", "q1", "q2", "q3"]),
    ("pit_stops.csv", "pit_stops", ["raceId", "driverId", "stop", "lap", "time", "duration", "milliseconds"]),
    ("lap_times.csv", "lap_times", ["raceId", "driverId", "lap", "position", "time", "milliseconds"]),
]


def load_table(conn, csv_name, table_name, columns):
    df = pd.read_csv(os.path.join(DATA_DIR, csv_name), na_values=NA_VALUES, keep_default_na=True)
    df = df[columns]
    df.to_sql(table_name, conn, if_exists="append", index=False, chunksize=20_000)
    print(f"  {table_name}: {len(df):,} rows")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        for csv_name, table_name, columns in TABLES:
            load_table(conn, csv_name, table_name, columns)
        conn.executescript(INDEXES)
        conn.commit()
    finally:
        conn.close()

    print(f"Done. Database written to {DB_PATH}")


if __name__ == "__main__":
    main()
