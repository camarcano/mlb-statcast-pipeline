from datetime import date, timedelta

import pandas as pd
from flask import Blueprint, flash, jsonify, render_template, request, session, url_for, redirect

from webapp.db import get_db
from webapp.hitter.id_mapping import map_roster_csv
from webapp.pitcher.calculations import compute_leaderboard
from webapp.pitcher.names import get_pitcher_name, load_pitcher_names, resolve_names
from webapp.pitcher.queries import BIP_QUERY, PA_QUERY, FB_VELO_QUERY, SCATTER_QUERY

pitcher_bp = Blueprint("pitcher", __name__, template_folder="templates")


def _default_dates():
    today = date.today()
    year = today.year
    season_start = date(year, 3, 25)
    start = season_start if today >= season_start else date(year - 1, 3, 25)
    return start.isoformat(), today.isoformat()


@pitcher_bp.route("/")
def leaderboard():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    min_bip = int(request.args.get("min_bip", 0))

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()

    bip_tf = pd.read_sql_query(BIP_QUERY, db, params=(start_date, end_date))
    pa_tf = pd.read_sql_query(PA_QUERY, db, params=(start_date, end_date))
    fb_tf = pd.read_sql_query(FB_VELO_QUERY, db, params=(start_date, end_date))

    today = date.today()
    l14_end = today.isoformat()
    l14_start = (today - timedelta(days=13)).isoformat()

    bip_l14 = pd.read_sql_query(BIP_QUERY, db, params=(l14_start, l14_end))
    pa_l14 = pd.read_sql_query(PA_QUERY, db, params=(l14_start, l14_end))
    fb_l14 = pd.read_sql_query(FB_VELO_QUERY, db, params=(l14_start, l14_end))

    pitchers = compute_leaderboard(bip_tf, pa_tf, fb_tf, bip_l14, pa_l14, fb_l14, min_bip)
    resolve_names(pitchers)

    roster_ids = session.get("pitcher_roster_ids", [])

    return render_template(
        "pitcher/leaderboard.html",
        pitchers=pitchers,
        start_date=start_date,
        end_date=end_date,
        min_bip=min_bip,
        roster_ids=roster_ids,
    )


@pitcher_bp.route("/<int:pitcher_id>")
def detail(pitcher_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()

    player_name = get_pitcher_name(pitcher_id)

    bip_tf = pd.read_sql_query(
        BIP_QUERY + " AND pitcher = ?",
        db,
        params=(start_date, end_date, pitcher_id),
    )
    pa_tf = pd.read_sql_query(
        PA_QUERY + " HAVING pitcher = ?",
        db,
        params=(start_date, end_date, pitcher_id),
    )
    fb_tf = pd.read_sql_query(
        FB_VELO_QUERY + " AND pitcher = ?",
        db,
        params=(start_date, end_date, pitcher_id),
    )

    today = date.today()
    l14_start = (today - timedelta(days=13)).isoformat()
    l14_end = today.isoformat()

    bip_l14 = pd.read_sql_query(
        BIP_QUERY + " AND pitcher = ?",
        db,
        params=(l14_start, l14_end, pitcher_id),
    )
    pa_l14 = pd.read_sql_query(
        PA_QUERY + " HAVING pitcher = ?",
        db,
        params=(l14_start, l14_end, pitcher_id),
    )
    fb_l14 = pd.read_sql_query(
        FB_VELO_QUERY + " AND pitcher = ?",
        db,
        params=(l14_start, l14_end, pitcher_id),
    )

    pitchers = compute_leaderboard(bip_tf, pa_tf, fb_tf, bip_l14, pa_l14, fb_l14, min_bip=0)
    stats = pitchers[0] if pitchers else {}

    return render_template(
        "pitcher/detail.html",
        pitcher_id=pitcher_id,
        player_name=player_name,
        stats=stats,
        start_date=start_date,
        end_date=end_date,
    )


@pitcher_bp.route("/api/scatter/<int:pitcher_id>")
def scatter_data(pitcher_id):
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        start_date, end_date = _default_dates()

    db = get_db()
    rows = db.execute(
        SCATTER_QUERY, (pitcher_id, start_date, end_date)
    ).fetchall()

    data = []
    for r in rows:
        r = dict(r)
        data.append({
            "x": r["launch_angle"],
            "y": r["launch_speed"],
            "event": r["events"] or "",
            "pitch_type": r["pitch_type"] or "",
            "game_date": r["game_date"],
        })

    return jsonify(data)


@pitcher_bp.route("/api/players")
def api_players():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])

    db = get_db()
    pitcher_ids = [r[0] for r in db.execute("SELECT DISTINCT pitcher FROM statcast_pitches").fetchall()]
    names = load_pitcher_names()

    results = []
    for pid in pitcher_ids:
        name = names.get(str(pid), "")
        if q in name.lower():
            results.append({"id": str(pid), "text": name})
        if len(results) >= 50:
            break

    results.sort(key=lambda x: x["text"])
    return jsonify(results)


@pitcher_bp.route("/upload-roster", methods=["POST"])
def upload_roster():
    file = request.files.get("roster_file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a .csv file.", "warning")
        return redirect(url_for("pitcher.leaderboard"))

    pitcher_ids, total = map_roster_csv(file)
    unmatched = total - len(pitcher_ids)
    session["pitcher_roster_ids"] = pitcher_ids

    flash(
        f"Roster loaded: {len(pitcher_ids)} pitchers matched"
        + (f", {unmatched} unmatched" if unmatched else ""),
        "success",
    )
    return redirect(url_for("pitcher.leaderboard"))


@pitcher_bp.route("/clear-roster")
def clear_roster():
    session.pop("pitcher_roster_ids", None)
    flash("Roster cleared.", "info")
    return redirect(url_for("pitcher.leaderboard"))
