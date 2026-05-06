from datetime import date, timedelta

import pandas as pd
from flask import Blueprint, flash, jsonify, render_template, request, session, url_for, redirect

from webapp.db import get_db
from webapp.hitter.calculations import compute_leaderboard
from webapp.hitter.id_mapping import map_roster_csv
from webapp.hitter.queries import BIP_QUERY, PA_QUERY, SCATTER_QUERY

hitter_bp = Blueprint("hitter", __name__, template_folder="templates")


def _default_dates():
    today = date.today()
    year = today.year
    season_start = date(year, 3, 25)
    start = season_start if today >= season_start else date(year - 1, 3, 25)
    return start.isoformat(), today.isoformat()


@hitter_bp.route("/")
def leaderboard():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    min_bip = int(request.args.get("min_bip", 0))

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()

    bip_tf = pd.read_sql_query(BIP_QUERY, db, params=(start_date, end_date))
    pa_tf = pd.read_sql_query(PA_QUERY, db, params=(start_date, end_date))

    today = date.today()
    l14_end = today.isoformat()
    l14_start = (today - timedelta(days=13)).isoformat()

    bip_l14 = pd.read_sql_query(BIP_QUERY, db, params=(l14_start, l14_end))
    pa_l14 = pd.read_sql_query(PA_QUERY, db, params=(l14_start, l14_end))

    hitters = compute_leaderboard(bip_tf, pa_tf, bip_l14, pa_l14, min_bip)

    roster_ids = session.get("roster_batter_ids", [])

    return render_template(
        "hitter/leaderboard.html",
        hitters=hitters,
        start_date=start_date,
        end_date=end_date,
        min_bip=min_bip,
        roster_ids=roster_ids,
    )


@hitter_bp.route("/<int:batter_id>")
def detail(batter_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()

    name_row = db.execute(
        "SELECT DISTINCT player_name FROM statcast_pitches WHERE batter = ? LIMIT 1",
        (batter_id,),
    ).fetchone()
    player_name = dict(name_row)["player_name"] if name_row else "Unknown"

    bip_tf = pd.read_sql_query(
        BIP_QUERY + " AND batter = ?",
        db,
        params=(start_date, end_date, batter_id),
    )
    pa_tf = pd.read_sql_query(
        PA_QUERY + " HAVING batter = ?",
        db,
        params=(start_date, end_date, batter_id),
    )

    today = date.today()
    l14_start = (today - timedelta(days=13)).isoformat()
    l14_end = today.isoformat()

    bip_l14 = pd.read_sql_query(
        BIP_QUERY + " AND batter = ?",
        db,
        params=(l14_start, l14_end, batter_id),
    )
    pa_l14 = pd.read_sql_query(
        PA_QUERY + " HAVING batter = ?",
        db,
        params=(l14_start, l14_end, batter_id),
    )

    hitters = compute_leaderboard(bip_tf, pa_tf, bip_l14, pa_l14, min_bip=1)
    hitter_stats = hitters[0] if hitters else {}

    return render_template(
        "hitter/detail.html",
        batter_id=batter_id,
        player_name=player_name,
        stats=hitter_stats,
        start_date=start_date,
        end_date=end_date,
    )


@hitter_bp.route("/api/scatter/<int:batter_id>")
def scatter_data(batter_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()
    rows = db.execute(
        SCATTER_QUERY, (batter_id, start_date, end_date)
    ).fetchall()

    data = []
    for r in rows:
        r = dict(r)
        data.append({
            "x": r["launch_angle"],
            "y": r["launch_speed"],
            "event": r["events"] or "",
            "bb_type": r["bb_type"] or "",
            "bat_speed": r["bat_speed"],
            "game_date": r["game_date"],
        })

    return jsonify(data)


@hitter_bp.route("/api/players")
def api_players():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    db = get_db()
    pattern = f"%{q}%"
    rows = db.execute(
        "SELECT DISTINCT batter, player_name FROM statcast_pitches "
        "WHERE player_name LIKE ? ORDER BY player_name LIMIT 50",
        (pattern,),
    ).fetchall()

    results = [{"id": str(r["batter"]), "text": r["player_name"]} for r in rows]
    return jsonify(results)


@hitter_bp.route("/upload-roster", methods=["POST"])
def upload_roster():
    file = request.files.get("roster_file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a .csv file.", "warning")
        return redirect(url_for("hitter.leaderboard"))

    batter_ids, total = map_roster_csv(file)
    unmatched = total - len(batter_ids)
    session["roster_batter_ids"] = batter_ids

    flash(
        f"Roster loaded: {len(batter_ids)} players matched"
        + (f", {unmatched} unmatched" if unmatched else ""),
        "success",
    )
    return redirect(url_for("hitter.leaderboard"))


@hitter_bp.route("/clear-roster")
def clear_roster():
    session.pop("roster_batter_ids", None)
    flash("Roster cleared.", "info")
    return redirect(url_for("hitter.leaderboard"))
