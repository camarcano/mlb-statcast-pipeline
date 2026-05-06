BIP_QUERY = """
SELECT batter, player_name, launch_speed, launch_angle, bat_speed
FROM statcast_pitches
WHERE type = 'X'
  AND launch_speed IS NOT NULL
  AND launch_speed > 0
  AND game_date BETWEEN ? AND ?
"""

PA_QUERY = """
SELECT
    batter,
    MAX(player_name) as player_name,
    COUNT(*) as pa,
    SUM(CASE WHEN events IN ('strikeout','strikeout_double_play') THEN 1 ELSE 0 END) as k_count,
    SUM(CASE WHEN type='X' AND launch_speed > 0 THEN 1 ELSE 0 END) as bip_count,
    SUM(CASE WHEN type='X' AND launch_speed > 0
        AND estimated_ba_using_speedangle IS NOT NULL
        THEN estimated_ba_using_speedangle ELSE 0 END) as xba_num,
    SUM(CASE WHEN events IN ('walk','intent_walk','hit_by_pitch') THEN 1 ELSE 0 END) as non_ab,
    SUM(CASE WHEN type='X' AND launch_speed > 0
        AND estimated_woba_using_speedangle IS NOT NULL
        THEN estimated_woba_using_speedangle ELSE 0 END) as xwoba_bip,
    SUM(CASE WHEN events IN ('walk','intent_walk','hit_by_pitch',
                              'strikeout','strikeout_double_play')
        AND woba_value IS NOT NULL THEN woba_value ELSE 0 END) as xwoba_nonbip,
    SUM(COALESCE(woba_denom, 0)) as woba_denom_total
FROM statcast_pitches
WHERE events IS NOT NULL
  AND game_date BETWEEN ? AND ?
GROUP BY batter
"""

SCATTER_QUERY = """
SELECT launch_speed, launch_angle, events, bb_type, bat_speed, game_date
FROM statcast_pitches
WHERE batter = ?
  AND type = 'X'
  AND launch_speed IS NOT NULL
  AND launch_speed > 0
  AND game_date BETWEEN ? AND ?
ORDER BY game_date
"""
