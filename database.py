import sqlite3
import random
import string
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from config import DATABASE_PATH


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS groups_channels (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                type TEXT NOT NULL,
                registered_by INTEGER NOT NULL,
                registered_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raffles (
                raffle_id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                chat_id INTEGER,
                message_id INTEGER,
                inline_message_id TEXT,
                limit_participants INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                hide_participants INTEGER NOT NULL DEFAULT 0,
                hide_buttons INTEGER NOT NULL DEFAULT 0,
                old_members_only INTEGER NOT NULL DEFAULT 0,
                raffle_type TEXT NOT NULL DEFAULT 'regular',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raffle_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                join_time TEXT NOT NULL,
                UNIQUE(raffle_id, user_id),
                FOREIGN KEY (raffle_id) REFERENCES raffles(raffle_id)
            );

            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL,
                data TEXT
            );

            CREATE TABLE IF NOT EXISTS log_channels (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                title TEXT,
                code TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                PRIMARY KEY (user_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                remind_on_win INTEGER NOT NULL DEFAULT 0,
                hide_participants INTEGER NOT NULL DEFAULT 0,
                hide_buttons INTEGER NOT NULL DEFAULT 0,
                old_members_only INTEGER NOT NULL DEFAULT 0,
                default_limit INTEGER NOT NULL DEFAULT 10,
                custom_message TEXT DEFAULT '• مرحبا بكم في لعبه روليت 👑'
            );

            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                created_count INTEGER NOT NULL DEFAULT 0,
                joined_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raffle_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                winner_name TEXT,
                won_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                event TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS competitions (
                comp_id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER,
                title TEXT NOT NULL,
                max_contestants INTEGER NOT NULL DEFAULT 0,
                end_type TEXT NOT NULL DEFAULT 'time',
                end_value INTEGER NOT NULL DEFAULT 3600,
                win_notification INTEGER NOT NULL DEFAULT 1,
                results_announcement INTEGER NOT NULL DEFAULT 1,
                approval_system INTEGER NOT NULL DEFAULT 0,
                premium_only INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS competition_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comp_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                votes INTEGER NOT NULL DEFAULT 0,
                approved INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT NOT NULL,
                UNIQUE(comp_id, user_id),
                FOREIGN KEY (comp_id) REFERENCES competitions(comp_id)
            );

            CREATE TABLE IF NOT EXISTS competition_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                vote_msg_id INTEGER,
                UNIQUE(contest_id, user_id),
                FOREIGN KEY (contest_id) REFERENCES competitions(comp_id)
            );

            CREATE TABLE IF NOT EXISTS competition_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id TEXT NOT NULL,
                contestant_id INTEGER NOT NULL,
                voter_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(contest_id, contestant_id, voter_id),
                FOREIGN KEY (contest_id) REFERENCES competitions(comp_id)
            );
            """
        )
        for col in ["hide_participants", "hide_buttons", "old_members_only"]:
            try:
                conn.execute(f"ALTER TABLE user_settings ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("ALTER TABLE competition_applications ADD COLUMN vote_msg_id INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE user_settings ADD COLUMN default_limit INTEGER NOT NULL DEFAULT 10")
        except sqlite3.OperationalError:
            pass
            
        # New columns for Advanced Giveaways
        new_cols = [
            ("giveaway_text", "TEXT"),
            ("winners_count", "INTEGER NOT NULL DEFAULT 1"),
            ("condition_channel", "INTEGER NOT NULL DEFAULT 0"),
            ("boost_channel", "INTEGER NOT NULL DEFAULT 0"),
            ("vote_contestant", "INTEGER NOT NULL DEFAULT 0"),
            ("premium_only", "INTEGER NOT NULL DEFAULT 0"),
            ("anti_spam", "INTEGER NOT NULL DEFAULT 0"),
            ("auto_draw", "INTEGER NOT NULL DEFAULT 0"),
            ("condition_channel_ids", "TEXT"),
            ("condition_channel_type", "TEXT"),
            ("vote_code", "TEXT"),
            ("auto_draw_type", "TEXT"),
            ("auto_draw_value", "INTEGER NOT NULL DEFAULT 0"),
            ("end_time", "INTEGER"),
            ("status", "TEXT NOT NULL DEFAULT 'active'"),
        ]
        for col_name, col_type in new_cols:
            try:
                conn.execute(f"ALTER TABLE raffles ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass
                
        # Add is_banned to users table for the admin dashboard
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass



def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name, _now()),
        )


def generate_raffle_id(prefix: str = "R") -> str:
    digits = "".join(random.choices(string.digits, k=6))
    return f"{prefix}-{digits}"


def _ensure_user_stats(conn, user_id: int) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)
        """,
        (user_id,),
    )


def get_user_stats(user_id: int) -> dict:
    with get_connection() as conn:
        _ensure_user_stats(conn, user_id)
        row = conn.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        ).fetchone()
        active = conn.execute(
            """
            SELECT COUNT(DISTINCT p.raffle_id) AS c
            FROM participants p
            JOIN raffles r ON r.raffle_id = p.raffle_id
            WHERE p.user_id = ? AND r.status = 'active'
            """,
            (user_id,),
        ).fetchone()
    return {
        "xp": row["xp"],
        "wins": row["wins"],
        "created": row["created_count"],
        "joined": row["joined_count"],
        "active_joins": active["c"],
    }


def add_xp(user_id: int, amount: int) -> None:
    with get_connection() as conn:
        _ensure_user_stats(conn, user_id)
        conn.execute(
            "UPDATE user_stats SET xp = xp + ? WHERE user_id = ?",
            (amount, user_id),
        )


def increment_stat(user_id: int, field: str, amount: int = 1) -> None:
    allowed = {"wins", "created_count", "joined_count"}
    if field not in allowed:
        raise ValueError(field)
    with get_connection() as conn:
        _ensure_user_stats(conn, user_id)
        conn.execute(
            f"UPDATE user_stats SET {field} = {field} + ? WHERE user_id = ?",
            (amount, user_id),
        )


def record_winner(raffle_id: str, user_id: int, winner_name: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO winners (raffle_id, user_id, winner_name, won_at)
            VALUES (?, ?, ?, ?)
            """,
            (raffle_id, user_id, winner_name, _now()),
        )
        _ensure_user_stats(conn, user_id)
        conn.execute(
            "UPDATE user_stats SET wins = wins + 1, xp = xp + 50 WHERE user_id = ?",
            (user_id,),
        )


def get_recent_winners(limit: int = 5) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT winner_name, raffle_id FROM winners
            ORDER BY won_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [f"{r['winner_name']} ({r['raffle_id']})" for r in rows]


def get_leaderboard(limit: int = 15) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT us.user_id, us.wins, us.xp, u.first_name, u.username
            FROM user_stats us
            LEFT JOIN users u ON u.user_id = us.user_id
            WHERE us.wins > 0 OR us.xp > 0
            ORDER BY us.wins DESC, us.xp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def log_activity(
    event: str,
    detail: str | None = None,
    user_id: int | None = None,
    chat_id: int | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (user_id, chat_id, event, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, event, detail, _now()),
        )


def get_user_activity(user_id: int, limit: int = 10) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM activity_log
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return rows


def stop_raffle(raffle_id: str) -> None:
    set_raffle_status(raffle_id, "stopped")


def duplicate_raffle(raffle_id: str) -> str | None:
    raffle = get_raffle(raffle_id)
    if not raffle:
        return None
    new_id = create_raffle(
        creator_id=raffle["creator_id"],
        limit_participants=raffle["limit_participants"],
        raffle_type=raffle["raffle_type"],
    )
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE raffles SET
                hide_participants = ?,
                hide_buttons = ?,
                old_members_only = ?
            WHERE raffle_id = ?
            """,
            (
                raffle["hide_participants"],
                raffle["hide_buttons"],
                raffle["old_members_only"],
                new_id,
            ),
        )
    return new_id


def create_raffle(
    creator_id: int,
    limit_participants: int,
    raffle_type: str = "regular",
    chat_id: int | None = None,
    message_id: int | None = None,
    inline_message_id: str | None = None,
    hide_participants: bool = False,
    hide_buttons: bool = False,
    old_members_only: bool = False,
) -> str:
    raffle_id = generate_raffle_id("QR" if raffle_type == "quick" else "R")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raffles (
                raffle_id, creator_id, chat_id, message_id, inline_message_id,
                limit_participants, raffle_type, created_at,
                hide_participants, hide_buttons, old_members_only
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raffle_id,
                creator_id,
                chat_id,
                message_id,
                inline_message_id,
                limit_participants,
                raffle_type,
                _now(),
                1 if hide_participants else 0,
                1 if hide_buttons else 0,
                1 if old_members_only else 0,
            ),
        )
        _ensure_user_stats(conn, creator_id)
        conn.execute(
            "UPDATE user_stats SET created_count = created_count + 1, xp = xp + 10 WHERE user_id = ?",
            (creator_id,),
        )
        conn.execute(
            """
            INSERT INTO activity_log (user_id, chat_id, event, detail, created_at)
            VALUES (?, ?, 'create_raffle', ?, ?)
            """,
            (creator_id, chat_id, raffle_id, _now()),
        )
    return raffle_id


def get_raffle(raffle_id: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM raffles WHERE raffle_id = ?", (raffle_id,)
        ).fetchone()
    return row


def update_raffle_message(
    raffle_id: str,
    chat_id: int | None = None,
    message_id: int | None = None,
    inline_message_id: str | None = None,
) -> None:
    with get_connection() as conn:
        if chat_id is not None:
            conn.execute(
                "UPDATE raffles SET chat_id = ? WHERE raffle_id = ?",
                (chat_id, raffle_id),
            )
        if message_id is not None:
            conn.execute(
                "UPDATE raffles SET message_id = ? WHERE raffle_id = ?",
                (message_id, raffle_id),
            )
        if inline_message_id is not None:
            conn.execute(
                "UPDATE raffles SET inline_message_id = ? WHERE raffle_id = ?",
                (inline_message_id, raffle_id),
            )


def set_raffle_status(raffle_id: str, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE raffles SET status = ? WHERE raffle_id = ?",
            (status, raffle_id),
        )


def update_raffle(raffle_id: str, **kwargs) -> None:
    allowed = {"giveaway_text", "winners_count", "condition_channel", "boost_channel", 
               "vote_contestant", "premium_only", "anti_spam", "auto_draw", "chat_id",
               "condition_channel_ids", "condition_channel_type", "vote_code",
               "auto_draw_type", "auto_draw_value", "end_time", "status"}
    with get_connection() as conn:
        for key, val in kwargs.items():
            if key in allowed:
                conn.execute(
                    f"UPDATE raffles SET {key} = ? WHERE raffle_id = ?",
                    (1 if isinstance(val, bool) else val, raffle_id),
                )


def toggle_raffle_field(raffle_id: str, field: str) -> int:
    allowed = {"hide_participants", "hide_buttons", "old_members_only"}
    if field not in allowed:
        raise ValueError(f"Invalid field: {field}")
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {field} FROM raffles WHERE raffle_id = ?", (raffle_id,)
        ).fetchone()
        new_val = 0 if row[field] else 1
        conn.execute(
            f"UPDATE raffles SET {field} = ? WHERE raffle_id = ?",
            (new_val, raffle_id),
        )
    return new_val


def add_participant(
    raffle_id: str,
    user_id: int,
    username: str | None,
    first_name: str | None,
) -> bool:
    """Returns True if added, False if already exists."""
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO participants (raffle_id, user_id, username, first_name, join_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (raffle_id, user_id, username, first_name, _now()),
            )
            _ensure_user_stats(conn, user_id)
            conn.execute(
                "UPDATE user_stats SET joined_count = joined_count + 1, xp = xp + 5 WHERE user_id = ?",
                (user_id,),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def remove_participant(raffle_id: str, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM participants WHERE raffle_id = ? AND user_id = ?",
            (raffle_id, user_id),
        )


def get_participants(raffle_id: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM participants
            WHERE raffle_id = ?
            ORDER BY join_time ASC
            """,
            (raffle_id,),
        ).fetchall()
    return rows


def count_participants(raffle_id: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM participants WHERE raffle_id = ?",
            (raffle_id,),
        ).fetchone()
    return row["c"]


def pick_random_winner(raffle_id: str) -> sqlite3.Row | None:
    participants = get_participants(raffle_id)
    if not participants:
        return None
    return random.choice(participants)


def get_user_active_raffles(creator_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM raffles
            WHERE creator_id = ? AND status = 'active'
            ORDER BY created_at DESC
            """,
            (creator_id,),
        ).fetchall()
    return rows


def register_chat(
    chat_id: int, title: str, chat_type: str, registered_by: int
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO groups_channels (chat_id, title, type, registered_by, registered_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                type = excluded.type,
                registered_by = excluded.registered_by,
                registered_at = excluded.registered_at
            """,
            (chat_id, title, chat_type, registered_by, _now()),
        )


def get_registered_chats(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM groups_channels
            WHERE registered_by = ?
            ORDER BY registered_at DESC
            """,
            (user_id,),
        ).fetchall()
    return rows


def set_user_state(user_id: int, state: str, data: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_states (user_id, state, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state = excluded.state, data = excluded.data
            """,
            (user_id, state, data),
        )


def get_user_state(user_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM user_states WHERE user_id = ?", (user_id,)
        ).fetchone()


def clear_user_state(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))


def register_log_channel(user_id: int, chat_id: int, title: str) -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO log_channels (user_id, chat_id, title, code, registered_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                title = excluded.title,
                code = excluded.code,
                registered_at = excluded.registered_at
            """,
            (user_id, chat_id, title, code, _now()),
        )
    return code


def get_log_channels(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM log_channels
            WHERE user_id = ?
            ORDER BY registered_at DESC
            """,
            (user_id,),
        ).fetchall()
    return rows


def toggle_remind_on_win(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT remind_on_win FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO user_settings (user_id, remind_on_win) VALUES (?, 1)",
                (user_id,),
            )
            return 1
        new_val = 0 if row["remind_on_win"] else 1
        conn.execute(
            "UPDATE user_settings SET remind_on_win = ? WHERE user_id = ?",
            (new_val, user_id),
        )
        return new_val


def get_remind_on_win(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT remind_on_win FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return bool(row["remind_on_win"]) if row else False


def get_quick_settings(user_id: int) -> dict:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        row = conn.execute(
            """SELECT hide_participants, hide_buttons, old_members_only, default_limit, custom_message
               FROM user_settings WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
    if row:
        return {
            "hide_participants": bool(row["hide_participants"]),
            "hide_buttons": bool(row["hide_buttons"]),
            "old_members_only": bool(row["old_members_only"]),
            "default_limit": row["default_limit"],
            "custom_message": row["custom_message"] or "• مرحبا بكم في لعبه روليت 👑",
        }
    return {"hide_participants": False, "hide_buttons": False, "old_members_only": False, "default_limit": 10, "custom_message": "• مرحبا بكم في لعبه روليت 👑"}


def set_quick_setting(user_id: int, setting: str, value: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        conn.execute(
            f"UPDATE user_settings SET {setting} = ? WHERE user_id = ?",
            (value, user_id),
        )


def set_custom_message(user_id: int, message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        conn.execute(
            "UPDATE user_settings SET custom_message = ? WHERE user_id = ?",
            (message, user_id),
        )


def get_custom_message(user_id: int) -> str:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        row = conn.execute(
            "SELECT custom_message FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row and row["custom_message"]:
        return row["custom_message"]
    return "• مرحبا بكم في لعبه روليت 👑"


def reset_quick_settings(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        conn.execute(
            """UPDATE user_settings SET
                hide_participants = 0,
                custom_message = '• مرحبا بكم في لعبه روليت 👑'
            WHERE user_id = ?""",
            (user_id,),
        )


def count_user_active_participations(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT p.raffle_id) AS c
            FROM participants p
            JOIN raffles r ON r.raffle_id = p.raffle_id
            WHERE p.user_id = ? AND r.status = 'active'
            """,
            (user_id,),
        ).fetchone()
    return row["c"]


# ─── Competiciones ──────────────────────────────────────────────────────────

def generate_comp_id() -> str:
    digits = "".join(random.choices(string.digits, k=6))
    return f"CMP-{digits}"


def create_competition(
    creator_id: int,
    chat_id: int,
    title: str,
    max_contestants: int = 0,
    end_type: str = "time",
    end_value: int = 3600,
    win_notification: bool = True,
    results_announcement: bool = True,
    approval_system: bool = False,
    premium_only: bool = False,
) -> str:
    comp_id = generate_comp_id()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO competitions (
                comp_id, creator_id, chat_id, title, max_contestants,
                end_type, end_value, win_notification, results_announcement,
                approval_system, premium_only, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comp_id, creator_id, chat_id, title, max_contestants,
                end_type, end_value,
                1 if win_notification else 0,
                1 if results_announcement else 0,
                1 if approval_system else 0,
                1 if premium_only else 0,
                _now(),
            ),
        )
    return comp_id


def get_competition(comp_id: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competitions WHERE comp_id = ?", (comp_id,)
        ).fetchone()


def update_competition_message(comp_id: str, message_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE competitions SET message_id = ? WHERE comp_id = ?",
            (message_id, comp_id),
        )


def update_competition(comp_id: str, **kwargs) -> None:
    allowed = {"title", "max_contestants", "end_type", "end_value",
               "win_notification", "results_announcement",
               "approval_system", "premium_only", "status", "message_id"}
    with get_connection() as conn:
        for key, val in kwargs.items():
            if key in allowed:
                conn.execute(
                    f"UPDATE competitions SET {key} = ? WHERE comp_id = ?",
                    (1 if isinstance(val, bool) else val, comp_id),
                )


def add_comp_participant(comp_id: str, user_id: int, username: str | None, first_name: str | None) -> bool:
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO competition_participants (comp_id, user_id, username, first_name, joined_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (comp_id, user_id, username, first_name, _now()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_comp_participants(comp_id: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competition_participants WHERE comp_id = ? ORDER BY joined_at",
            (comp_id,),
        ).fetchall()


def count_comp_participants(comp_id: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM competition_participants WHERE comp_id = ?",
            (comp_id,),
        ).fetchone()
    return row["c"]


def vote_comp_participant(comp_id: str, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE competition_participants SET votes = votes + 1 WHERE comp_id = ? AND user_id = ?",
            (comp_id, user_id),
        )
        return cur.rowcount > 0


def approve_comp_participant(comp_id: str, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE competition_participants SET approved = 1 WHERE comp_id = ? AND user_id = ?",
            (comp_id, user_id),
        )
        return cur.rowcount > 0


def set_competition_status(comp_id: str, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE competitions SET status = ? WHERE comp_id = ?",
            (status, comp_id),
        )


def get_all_active_competitions() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competitions WHERE status = 'active' ORDER BY created_at"
        ).fetchall()


def get_user_active_competitions(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competitions WHERE creator_id = ? AND status IN ('active','paused') ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()


def get_chat_title(chat_id: int) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT title FROM groups_channels WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    return row["title"] if row else None


def delete_competition(comp_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM competition_participants WHERE comp_id = ?", (comp_id,))
        cur = conn.execute("DELETE FROM competitions WHERE comp_id = ?", (comp_id,))
        return cur.rowcount > 0


def remove_comp_participant(comp_id: str, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM competition_participants WHERE comp_id = ? AND user_id = ?",
            (comp_id, user_id),
        )
        return cur.rowcount > 0


def get_top_channels(limit: int = 10) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT gc.title, COUNT(p.id) AS total
            FROM participants p
            JOIN raffles r ON r.raffle_id = p.raffle_id
            JOIN groups_channels gc ON gc.chat_id = r.chat_id
            GROUP BY gc.chat_id
            ORDER BY total DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def unregister_chat(chat_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM groups_channels WHERE chat_id = ? AND registered_by = ?",
            (chat_id, user_id),
        )
        return cur.rowcount > 0


# ─── دوال التقديم والموافقة والتصويت للمسابقات ────────────────────────────

def apply_competition(contest_id: str, user_id: int, username: str | None, first_name: str | None) -> str:
    """ترجع 'pending' أو 'approved' أو 'exists' أو 'error'"""
    comp = get_competition(contest_id)
    if not comp:
        return "error"
    status = "pending" if comp["approval_system"] else "approved"
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO competition_applications (contest_id, user_id, username, first_name, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (contest_id, user_id, username, first_name, status, _now()),
            )
            return status
        except sqlite3.IntegrityError:
            return "exists"


def get_applications(contest_id: str, status: str | None = None) -> list[sqlite3.Row]:
    with get_connection() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM competition_applications WHERE contest_id = ? AND status = ? ORDER BY created_at",
                (contest_id, status),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM competition_applications WHERE contest_id = ? ORDER BY created_at",
            (contest_id,),
        ).fetchall()


def get_application(contest_id: str, user_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competition_applications WHERE contest_id = ? AND user_id = ?",
            (contest_id, user_id),
        ).fetchone()


def set_application_status(contest_id: str, user_id: int, status: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE competition_applications SET status = ? WHERE contest_id = ? AND user_id = ?",
            (status, contest_id, user_id),
        )
        return cur.rowcount > 0


def set_vote_msg_id(contest_id: str, user_id: int, msg_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE competition_applications SET vote_msg_id = ? WHERE contest_id = ? AND user_id = ?",
            (msg_id, contest_id, user_id),
        )


def vote_contestant(contest_id: str, contestant_id: int, voter_id: int) -> str:
    """ترجع 'ok' أو 'duplicate' أو 'error'"""
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO competition_votes (contest_id, contestant_id, voter_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (contest_id, contestant_id, voter_id, _now()),
            )
            return "ok"
        except sqlite3.IntegrityError:
            return "duplicate"


def get_vote_count(contest_id: str, contestant_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM competition_votes WHERE contest_id = ? AND contestant_id = ?",
            (contest_id, contestant_id),
        ).fetchone()
    return row["c"]


def get_approved_contestants(contest_id: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM competition_applications WHERE contest_id = ? AND status = 'approved' ORDER BY created_at",
            (contest_id,),
        ).fetchall()

def get_all_active_raffles() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM raffles WHERE status = 'active'").fetchall()

# ==========================================
# ADMIN DASHBOARD FUNCTIONS
# ==========================================

def get_total_users() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(user_id) FROM users").fetchone()[0]

def get_total_active_raffles() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM raffles WHERE status = 'active'").fetchone()[0]

def get_total_active_competitions() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM competitions WHERE status = 'active'").fetchone()[0]

def get_user_info(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def is_user_banned(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row["is_banned"]) if row else False

def set_user_ban(user_id: int, status: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (status, user_id))

def get_banned_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id, username, first_name FROM users WHERE is_banned = 1").fetchall()
        return [dict(r) for r in rows]



def get_active_raffles(limit=10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM raffles WHERE status = 'active' ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_active_competitions(limit=10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM competitions WHERE status = 'active' ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def force_delete_raffle(raffle_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM raffles WHERE raffle_id = ?", (raffle_id,))
        conn.execute("DELETE FROM participants WHERE raffle_id = ?", (raffle_id,))

def force_delete_competition(comp_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM competitions WHERE id = ?", (comp_id,))
        conn.execute("DELETE FROM competition_participants WHERE comp_id = ?", (comp_id,))

def cleanup_old_data() -> int:
    with get_connection() as conn:
        c1 = conn.execute("DELETE FROM raffles WHERE status != 'active'").rowcount
        return c1

def search_user_by_username(username: str) -> dict | None:
    username = username.lstrip('@')
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)).fetchone()
        return dict(row) if row else None

def set_user_ban_by_username(username: str, status: int) -> int | None:
    username = username.lstrip('@')
    with get_connection() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (username,)).fetchone()
        if not row:
            return None
        uid = row['user_id']
        conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (status, uid))
        return uid

def get_recent_users(limit=20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id, username, first_name, joined_date FROM users ORDER BY joined_date DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_recent_winners(limit=10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT w.raffle_id, w.user_id, w.winner_name, w.won_at FROM winners w ORDER BY w.id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_top_users(limit=10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT u.user_id, u.username, u.first_name, s.wins, s.xp FROM user_stats s JOIN users u ON u.user_id = s.user_id ORDER BY s.wins DESC, s.xp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_activity_log(limit=20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
