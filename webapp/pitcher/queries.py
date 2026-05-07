BIP_QUERY = """
SELECT pitcher, player_name, launch_speed, launch_angle
FROM statcast_pitches
WHERE type = 'X'
  AND launch_speed IS NOT NULL
  AND launch_speed > 0
  AND game_date BETWEEN ? AND ?
"""

PITCH_QUERY = """
SELECT pitcher, player_name, release_speed, pitch_type,
       type, description, events
FROM statcast_pitches
WHERE game_date BETWEEN ? AND ?
"""

PA_QUERY = """
SELECT
    pitcher,
    MAX(player_name) as player_name,
    COUNT(*) as total_pitches,
    SUM(CASE WHEN events IS NOT NULL THEN 1 ELSE 0 END) as pa,
    SUM(CASE WHEN events IN ('strikeout','strikeout_double_play') THEN 1 ELSE 0 END) as k_count,
    SUM(CASE WHEN events IN ('walk','intent_walk','hit_by_pitch') THEN 1 ELSE 0 END) as bb_count,
    SUM(CASE WHEN description LIKE '%swinging_strike%' THEN 1 ELSE 0 END) as whiffs,
    SUM(CASE WHEN description LIKE '%called_strike%' THEN 1 ELSE 0 END) as called_strikes,
    SUM(CASE WHEN type IN ('S','X') THEN 1 ELSE 0 END) as strikes_total,
    SUM(CASE WHEN type='X' AND launch_speed > 0 THEN 1 ELSE 0 END) as bip_count
FROM statcast_pitches
WHERE game_date BETWEEN ? AND ?
GROUP BY pitcher
"""

FB_VELO_QUERY = """
SELECT pitcher, AVG(release_speed) as fb_velo
FROM statcast_pitches
WHERE pitch_type = 'FF'
  AND release_speed IS NOT NULL
  AND game_date BETWEEN ? AND ?
GROUP BY pitcher
"""

SCATTER_QUERY = """
SELECT release_speed, launch_angle, events, pitch_type, game_date
FROM statcast_pitches
WHERE pitcher = ?
  AND type = 'X'
  AND launch_speed IS NOT NULL
  AND launch_speed > 0
  AND game_date BETWEEN ? AND ?
ORDER BY game_date
"""
