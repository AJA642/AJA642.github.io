-- =====================================================================
-- Formula 1 World Championship (1950-2024) — SQL Analysis
--
-- Database: f1.db (built by load_data.py from the Ergast dataset —
-- see README.md for source and setup).
--
-- Conventions used throughout:
-- - "Classified" / finished = results.position IS NOT NULL. Ergast sets
--   position to NULL for any result that didn't classify (accident,
--   mechanical failure, disqualification, etc.) — see the `status` table
--   for the specific reason. positionText/positionOrder are always
--   populated (used for ordering), but position itself is the clean
--   did-they-finish signal.
-- - "Decade" = (year / 10) * 10 via integer division. The 2020s bucket
--   only covers 2020-2024 (5 seasons) in this dataset, not a full decade
--   — flagged in REPORT.md rather than presented as equivalent to the
--   others.
-- - Every ranking-style query has a minimum-sample floor so a handful of
--   races/starts can't outrank a real multi-season pattern.
--
-- Each query is tagged "-- QUERY: <key>" so analysis.py can pull it out
-- and run it directly — this file is the single source of truth for the
-- SQL. Run the whole file directly with:
--   sqlite3 f1.db < queries.sql
-- =====================================================================


-- QUERY: constructor_dominance_by_decade
-- 1. Points share by constructor per decade — which teams dominated which
-- era. RANK() window function, partitioned by decade, picks the top 3
-- constructors in each one.
WITH constructor_decade_points AS (
    SELECT
        (r.year / 10) * 10 AS decade,
        res.constructorId,
        c.name AS constructor_name,
        SUM(res.points) AS decade_points
    FROM results res
    JOIN races r ON r.raceId = res.raceId
    JOIN constructors c ON c.constructorId = res.constructorId
    GROUP BY decade, res.constructorId, c.name
),
decade_totals AS (
    SELECT decade, SUM(decade_points) AS total_decade_points
    FROM constructor_decade_points
    GROUP BY decade
),
ranked AS (
    SELECT
        cdp.decade,
        cdp.constructor_name,
        cdp.decade_points,
        ROUND(100.0 * cdp.decade_points / dt.total_decade_points, 2) AS pct_share,
        RANK() OVER (PARTITION BY cdp.decade ORDER BY cdp.decade_points DESC) AS rank_in_decade
    FROM constructor_decade_points cdp
    JOIN decade_totals dt ON dt.decade = cdp.decade
)
SELECT decade, rank_in_decade, constructor_name, decade_points, pct_share
FROM ranked
WHERE rank_in_decade <= 3
ORDER BY decade, rank_in_decade;


-- QUERY: grid_vs_finish_correlation
-- 2. Does starting position predict the result, and has that changed
-- since the 2010 aero-rules era (refuelling ban, new wing regulations)?
-- SQLite has no built-in CORR(), so Pearson's r is computed directly from
-- its definition (sums of x, y, xy, x^2, y^2). Classified finishers only,
-- and grid > 0 to exclude pit-lane-start entries (no real grid slot).
WITH classified AS (
    SELECT
        CASE WHEN r.year < 2010 THEN 'Pre-2010' ELSE '2010-Present' END AS era,
        res.grid AS grid_pos,
        res.position AS finish_pos
    FROM results res
    JOIN races r ON r.raceId = res.raceId
    WHERE res.position IS NOT NULL AND res.grid > 0
),
stats AS (
    SELECT
        era,
        COUNT(*) AS n,
        SUM(grid_pos) AS sum_x,
        SUM(finish_pos) AS sum_y,
        SUM(grid_pos * finish_pos) AS sum_xy,
        SUM(grid_pos * grid_pos) AS sum_x2,
        SUM(finish_pos * finish_pos) AS sum_y2
    FROM classified
    GROUP BY era
)
SELECT
    era,
    n,
    ROUND(
        (n * sum_xy - sum_x * sum_y)
        / (SQRT(n * sum_x2 - sum_x * sum_x) * SQRT(n * sum_y2 - sum_y * sum_y)),
        4
    ) AS grid_finish_correlation
FROM stats
ORDER BY era DESC;


-- QUERY: driver_consistency_by_season
-- 3. Which driver-seasons were the most consistent (tight finish-position
-- spread) versus the most boom-or-bust (win-or-DNF)? Variance computed via
-- the standard E[x^2] - E[x]^2 identity (SQLite has no built-in STDEV/
-- VARIANCE aggregate), square-rooted back to a standard deviation.
-- Floor: >=10 starts and >=5 classified finishes that season, so a
-- three-race substitute drive can't register as "most consistent."
WITH driver_season_results AS (
    SELECT
        r.year,
        res.driverId,
        d.forename || ' ' || d.surname AS driver_name,
        res.position AS finish_pos,
        CASE WHEN res.position IS NULL THEN 1 ELSE 0 END AS is_dnf
    FROM results res
    JOIN races r ON r.raceId = res.raceId
    JOIN drivers d ON d.driverId = res.driverId
)
SELECT
    year,
    driver_name,
    COUNT(*) AS starts,
    SUM(is_dnf) AS dnfs,
    ROUND(100.0 * SUM(is_dnf) / COUNT(*), 1) AS dnf_pct,
    ROUND(AVG(CASE WHEN is_dnf = 0 THEN finish_pos END), 2) AS avg_finish,
    ROUND(SQRT(
        AVG(CASE WHEN is_dnf = 0 THEN finish_pos * finish_pos END)
        - AVG(CASE WHEN is_dnf = 0 THEN finish_pos END) * AVG(CASE WHEN is_dnf = 0 THEN finish_pos END)
    ), 2) AS finish_stdev
FROM driver_season_results
GROUP BY year, driverId, driver_name
HAVING COUNT(*) >= 10 AND SUM(CASE WHEN is_dnf = 0 THEN 1 ELSE 0 END) >= 5
ORDER BY finish_stdev ASC;


-- QUERY: home_advantage_overall
-- 4a. Do drivers outperform their own season average at their home
-- country's race? For every (driver, race) at a home Grand Prix, this
-- compares that result to the SAME driver's average finish across their
-- OTHER races that same season (a self-join, computed per-race so the
-- home result itself never pollutes its own baseline).
-- Nationality -> country is necessarily an approximate mapping (see
-- README/REPORT for the full list and its gaps): dual nationalities and
-- countries with no corresponding circuit in this dataset are excluded
-- (they simply never match a race_country and drop out silently, which
-- is the correct behaviour here, not an error).
WITH driver_home_country AS (
    SELECT driverId, CASE TRIM(nationality)
        WHEN 'American' THEN 'USA' WHEN 'British' THEN 'UK'
        WHEN 'Argentine' THEN 'Argentina' WHEN 'Australian' THEN 'Australia'
        WHEN 'Austrian' THEN 'Austria' WHEN 'Belgian' THEN 'Belgium'
        WHEN 'Brazilian' THEN 'Brazil' WHEN 'Canadian' THEN 'Canada'
        WHEN 'Chinese' THEN 'China' WHEN 'Dutch' THEN 'Netherlands'
        WHEN 'French' THEN 'France' WHEN 'German' THEN 'Germany'
        WHEN 'Hungarian' THEN 'Hungary' WHEN 'Indian' THEN 'India'
        WHEN 'Italian' THEN 'Italy' WHEN 'Japanese' THEN 'Japan'
        WHEN 'Malaysian' THEN 'Malaysia' WHEN 'Mexican' THEN 'Mexico'
        WHEN 'Monegasque' THEN 'Monaco' WHEN 'Portuguese' THEN 'Portugal'
        WHEN 'Russian' THEN 'Russia' WHEN 'South African' THEN 'South Africa'
        WHEN 'Spanish' THEN 'Spain' WHEN 'Swedish' THEN 'Sweden'
        WHEN 'Swiss' THEN 'Switzerland'
        ELSE NULL
    END AS home_country
    FROM drivers
),
race_country AS (
    SELECT r.raceId, r.year,
           CASE ci.country WHEN 'United States' THEN 'USA' ELSE ci.country END AS country
    FROM races r JOIN circuits ci ON ci.circuitId = r.circuitId
),
results_ctx AS (
    SELECT res.driverId, res.raceId, rc.year, res.position AS finish_pos,
           dhc.home_country, rc.country AS race_country
    FROM results res
    JOIN race_country rc ON rc.raceId = res.raceId
    JOIN driver_home_country dhc ON dhc.driverId = res.driverId
    WHERE res.position IS NOT NULL
),
other_races_avg AS (
    SELECT rc1.driverId, rc1.raceId, rc1.year,
           AVG(rc2.finish_pos) AS other_races_avg_position,
           COUNT(*) AS other_races_count
    FROM results_ctx rc1
    JOIN results_ctx rc2
        ON rc2.driverId = rc1.driverId AND rc2.year = rc1.year AND rc2.raceId != rc1.raceId
    GROUP BY rc1.driverId, rc1.raceId, rc1.year
)
SELECT
    COUNT(*) AS home_race_instances,
    ROUND(AVG(rc.finish_pos), 2) AS avg_home_finish_position,
    ROUND(AVG(ora.other_races_avg_position), 2) AS avg_other_races_finish_position,
    ROUND(AVG(ora.other_races_avg_position - rc.finish_pos), 3) AS avg_positions_gained_at_home
FROM results_ctx rc
JOIN other_races_avg ora ON ora.driverId = rc.driverId AND ora.raceId = rc.raceId AND ora.year = rc.year
WHERE rc.home_country IS NOT NULL
  AND rc.home_country = rc.race_country
  AND ora.other_races_count >= 5;


-- QUERY: home_advantage_by_nationality
-- 4b. Same comparison, broken out by nationality. Floor of >=10 home-race
-- instances so a nationality with one long-ago driver and two home races
-- doesn't produce a noisy 100%-swing headline.
WITH driver_home_country AS (
    SELECT driverId, CASE TRIM(nationality)
        WHEN 'American' THEN 'USA' WHEN 'British' THEN 'UK'
        WHEN 'Argentine' THEN 'Argentina' WHEN 'Australian' THEN 'Australia'
        WHEN 'Austrian' THEN 'Austria' WHEN 'Belgian' THEN 'Belgium'
        WHEN 'Brazilian' THEN 'Brazil' WHEN 'Canadian' THEN 'Canada'
        WHEN 'Chinese' THEN 'China' WHEN 'Dutch' THEN 'Netherlands'
        WHEN 'French' THEN 'France' WHEN 'German' THEN 'Germany'
        WHEN 'Hungarian' THEN 'Hungary' WHEN 'Indian' THEN 'India'
        WHEN 'Italian' THEN 'Italy' WHEN 'Japanese' THEN 'Japan'
        WHEN 'Malaysian' THEN 'Malaysia' WHEN 'Mexican' THEN 'Mexico'
        WHEN 'Monegasque' THEN 'Monaco' WHEN 'Portuguese' THEN 'Portugal'
        WHEN 'Russian' THEN 'Russia' WHEN 'South African' THEN 'South Africa'
        WHEN 'Spanish' THEN 'Spain' WHEN 'Swedish' THEN 'Sweden'
        WHEN 'Swiss' THEN 'Switzerland'
        ELSE NULL
    END AS home_country, nationality
    FROM drivers
),
race_country AS (
    SELECT r.raceId, r.year,
           CASE ci.country WHEN 'United States' THEN 'USA' ELSE ci.country END AS country
    FROM races r JOIN circuits ci ON ci.circuitId = r.circuitId
),
results_ctx AS (
    SELECT res.driverId, res.raceId, rc.year, res.position AS finish_pos,
           dhc.home_country, dhc.nationality, rc.country AS race_country
    FROM results res
    JOIN race_country rc ON rc.raceId = res.raceId
    JOIN driver_home_country dhc ON dhc.driverId = res.driverId
    WHERE res.position IS NOT NULL
),
other_races_avg AS (
    SELECT rc1.driverId, rc1.raceId, rc1.year,
           AVG(rc2.finish_pos) AS other_races_avg_position,
           COUNT(*) AS other_races_count
    FROM results_ctx rc1
    JOIN results_ctx rc2
        ON rc2.driverId = rc1.driverId AND rc2.year = rc1.year AND rc2.raceId != rc1.raceId
    GROUP BY rc1.driverId, rc1.raceId, rc1.year
)
SELECT
    rc.nationality,
    COUNT(*) AS home_race_instances,
    ROUND(AVG(ora.other_races_avg_position - rc.finish_pos), 3) AS avg_positions_gained_at_home
FROM results_ctx rc
JOIN other_races_avg ora ON ora.driverId = rc.driverId AND ora.raceId = rc.raceId AND ora.year = rc.year
WHERE rc.home_country IS NOT NULL
  AND rc.home_country = rc.race_country
  AND ora.other_races_count >= 5
GROUP BY rc.nationality
HAVING COUNT(*) >= 10
ORDER BY avg_positions_gained_at_home DESC;


-- QUERY: pit_stop_trend_by_year
-- 5a. Average pit stop duration by year. Ergast's pit_stops table only
-- starts in 2011 (F1 didn't record per-stop timing electronically before
-- then) — see README/REPORT for what that means for this query's scope.
-- Stops outside 1-60s are excluded as stop-go penalties, red-flag
-- stoppages, or data errors, not representative tyre-change times.
SELECT
    r.year,
    COUNT(*) AS stops,
    ROUND(AVG(ps.milliseconds) / 1000.0, 2) AS avg_pit_stop_seconds
FROM pit_stops ps
JOIN races r ON r.raceId = ps.raceId
WHERE ps.milliseconds BETWEEN 1000 AND 60000
GROUP BY r.year
ORDER BY r.year;


-- QUERY: pit_stop_by_constructor_recent
-- 5b. Same metric, most recent 3 seasons only, broken out by constructor
-- (which teams' pit crews are fastest right now). Floor of >=20 stops in
-- the window so a team that missed most of a season on a technicality
-- doesn't rank on a handful of stops.
WITH recent_years AS (
    SELECT DISTINCT year FROM races ORDER BY year DESC LIMIT 3
)
SELECT
    c.name AS constructor_name,
    COUNT(*) AS stops,
    ROUND(AVG(ps.milliseconds) / 1000.0, 2) AS avg_pit_stop_seconds
FROM pit_stops ps
JOIN races r ON r.raceId = ps.raceId
JOIN results res ON res.raceId = ps.raceId AND res.driverId = ps.driverId
JOIN constructors c ON c.constructorId = res.constructorId
WHERE ps.milliseconds BETWEEN 1000 AND 60000
  AND r.year IN (SELECT year FROM recent_years)
GROUP BY c.name
HAVING COUNT(*) >= 20
ORDER BY avg_pit_stop_seconds ASC;


-- QUERY: pit_stop_trend_same_circuit
-- 5c. Controls for the fact that different circuits have different pit
-- lane lengths/speed limits (a real confound in query 5a's cross-circuit
-- year trend) by tracking ONE circuit that ran every season 2011-2024.
-- Monza chosen because it's on the calendar every year in this window,
-- with no layout change recorded in this dataset across that span.
SELECT
    r.year,
    COUNT(*) AS stops,
    ROUND(AVG(ps.milliseconds) / 1000.0, 2) AS avg_pit_stop_seconds
FROM pit_stops ps
JOIN races r ON r.raceId = ps.raceId
JOIN circuits ci ON ci.circuitId = r.circuitId
WHERE ps.milliseconds BETWEEN 1000 AND 60000
  AND ci.name = 'Autodromo Nazionale di Monza'
GROUP BY r.year
ORDER BY r.year;


-- QUERY: dnf_rate_by_circuit
-- 6a. DNF rate by circuit — which tracks are hardest on cars/drivers.
-- Floor of >=200 starts (roughly 10+ full grids) at that circuit.
SELECT
    ci.name AS circuit_name,
    ci.country,
    COUNT(*) AS starts,
    SUM(CASE WHEN res.position IS NULL THEN 1 ELSE 0 END) AS dnfs,
    ROUND(100.0 * SUM(CASE WHEN res.position IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS dnf_pct
FROM results res
JOIN races r ON r.raceId = res.raceId
JOIN circuits ci ON ci.circuitId = r.circuitId
GROUP BY ci.circuitId, ci.name, ci.country
HAVING COUNT(*) >= 200
ORDER BY dnf_pct DESC;


-- QUERY: dnf_rate_by_decade
-- 6b. DNF rate by decade, league-wide — has reliability improved over
-- time? Same decade bucketing as query 1; the 2020s bucket is 5 seasons,
-- not 10 (see the note at the top of this file).
SELECT
    (r.year / 10) * 10 AS decade,
    COUNT(*) AS starts,
    SUM(CASE WHEN res.position IS NULL THEN 1 ELSE 0 END) AS dnfs,
    ROUND(100.0 * SUM(CASE WHEN res.position IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS dnf_pct
FROM results res
JOIN races r ON r.raceId = res.raceId
GROUP BY decade
ORDER BY decade;


-- QUERY: best_season_nobody_remembers_constructors
-- 7. Constructors who finished 2nd in the final championship standings in
-- some season, but never won a title outright (in any season in this
-- dataset) — quantified by how many points behind the champion they
-- finished. "Final standings" = the standings row from that season's
-- last round.
WITH final_round_per_year AS (
    SELECT year, MAX(round) AS final_round FROM races GROUP BY year
),
final_standings AS (
    SELECT r.year, cs.constructorId, cs.position, cs.points
    FROM constructor_standings cs
    JOIN races r ON r.raceId = cs.raceId
    JOIN final_round_per_year f ON f.year = r.year AND f.final_round = r.round
),
ever_champion AS (
    SELECT DISTINCT constructorId FROM final_standings WHERE position = 1
),
runner_up_finishes AS (
    SELECT
        fs.year,
        c.name AS constructor_name,
        fs.points AS runner_up_points,
        champ.points AS champion_points,
        ROUND(champ.points - fs.points, 1) AS points_behind
    FROM final_standings fs
    JOIN constructors c ON c.constructorId = fs.constructorId
    JOIN final_standings champ ON champ.year = fs.year AND champ.position = 1
    WHERE fs.position = 2
      AND fs.constructorId NOT IN (SELECT constructorId FROM ever_champion)
)
SELECT year, constructor_name, runner_up_points, champion_points, points_behind
FROM runner_up_finishes
ORDER BY points_behind ASC;


-- QUERY: best_season_nobody_remembers_drivers
-- 7b. Same question for drivers: runner-up in the championship, but never
-- won a title themselves.
WITH final_round_per_year AS (
    SELECT year, MAX(round) AS final_round FROM races GROUP BY year
),
final_standings AS (
    SELECT r.year, ds.driverId, ds.position, ds.points
    FROM driver_standings ds
    JOIN races r ON r.raceId = ds.raceId
    JOIN final_round_per_year f ON f.year = r.year AND f.final_round = r.round
),
ever_champion AS (
    SELECT DISTINCT driverId FROM final_standings WHERE position = 1
),
runner_up_finishes AS (
    SELECT
        fs.year,
        d.forename || ' ' || d.surname AS driver_name,
        fs.points AS runner_up_points,
        champ.points AS champion_points,
        ROUND(champ.points - fs.points, 1) AS points_behind
    FROM final_standings fs
    JOIN drivers d ON d.driverId = fs.driverId
    JOIN final_standings champ ON champ.year = fs.year AND champ.position = 1
    WHERE fs.position = 2
      AND fs.driverId NOT IN (SELECT driverId FROM ever_champion)
)
SELECT year, driver_name, runner_up_points, champion_points, points_behind
FROM runner_up_finishes
ORDER BY points_behind ASC;
