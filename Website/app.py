from flask import Flask, render_template, request, g, Response, redirect, url_for, session,send_from_directory
import os, re, sqlite3, datetime
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from werkzeug.utils import secure_filename
import pandas as pd
from functools import wraps
import os, secrets


import unicodedata

ALLOWED_EXTENSIONS = {"csv", "xlsx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # 1) Unnamed-Spalten behandeln: falls nicht komplett leer -> als 'notes', sonst droppen
    new_cols = []
    drop_cols = []
    for i, c in enumerate(df.columns):
        name = str(c)
        if name.lower().startswith("unnamed:"):
            if not df.iloc[:, i].isna().all():
                new_cols.append("notes")
            else:
                new_cols.append(f"__drop_{i}")
                drop_cols.append(f"__drop_{i}")
        else:
            new_cols.append(name)
    df.columns = new_cols
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")

    # 2) Spalten via norm()+ALIASES kanonisieren
    canon = {}
    for c in df.columns:
        key = norm(str(c))
        canon[c] = ALIASES.get(key, key)  # unbekannt bleibt normalisierte Schreibweise
    df = df.rename(columns=canon)

    # 3) Datentyp & Trimmen
    df = df.fillna("").astype(str)
    df = df.applymap(lambda x: x.strip())

    # 4) Optionale Spalte 'notes' sicherstellen
    if "notes" not in df.columns:
        df["notes"] = ""

    return df


def norm(s: str) -> str:
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")  # ä->a, ö->o, ß->ss
    for ch in [" ", "_", "-", ".", "/"]:
        s = s.replace(ch, "")
    return s

# Alias-Lexikon (linke Seite = normalisiert)
ALIASES = {
    # name
    "name": "name",
    "kontakt": "name",
    "kunde": "name",
    "empfaenger": "name",
    "recipient": "name",
    "contactname": "name",

    # street
    "street": "street",
    "strasse": "street",
    "strasze": "street",
    "strassehausnummer": "street",
    "adresse": "street",
    "address": "street",
    "hausnummer": "street",  # falls nur eins da ist

    # zip
    "zip": "zip",
    "plz": "zip",
    "postalcode": "zip",
    "postcode": "zip",

    # city
    "city": "city",
    "ort": "city",
    "stadt": "city",
    "town": "city",

    # country
    "country": "country",
    "land": "country",

    # optional
    "phone": "phone",
    "telefon": "phone",
    "telefonnummer": "phone",
    "notes": "notes",
    "notizen": "notes",
    "bemerkungen": "notes",

    "lat": "lat",
    "lon": "lon",
    "lng": "lon",
    "longitude": "lon",
    "latitude": "lat",
}

# Erlaubte Dateitypen
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



def validate_address(street, zip_code, city, country):
    """Prüft, ob Adresse existiert über Nominatim API"""
    query = f"{street}, {zip_code} {city}, {country}"
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params, timeout=5, headers={"User-Agent": "kue-transportdrone"})
        data = response.json()
        if len(data) == 0:
            return False, None
        else:
            return True, data[0]  # Rückgabe: valid, Adressdaten
    except Exception as e:
        print("Adressprüfung fehlgeschlagen:", e)
        return False, None

DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# --- Datenbank-Handling ---
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)  # 10s warten statt sofort "locked"
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # Bestehende Orders-Tabelle
    db.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        street TEXT NOT NULL,
        zip TEXT NOT NULL,
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        notes TEXT,
        lat TEXT,
        lon TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Neue Tabelle für Extraorders
    db.execute("""
    CREATE TABLE IF NOT EXISTS extraorders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Neue Tabelle für Extraorder-Waypoints
    db.execute("""
    CREATE TABLE IF NOT EXISTS extraorder_waypoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES extraorders(id) ON DELETE CASCADE
    )
    """)

    db.commit()


# --- Formularvalidierung ---
def validate(form):
    errors = []

    def required(field, label):
        if not form.get(field, "").strip():
            errors.append(f"{label} ist ein Pflichtfeld.")

    required("name", "Name")
    required("street", "Straße & Hausnummer")
    required("zip", "PLZ")
    required("city", "Stadt")
    required("country", "Land")

    zip_code = form.get("zip", "").strip()
    if zip_code and not re.fullmatch(r"[A-Za-z0-9\- ]{3,10}", zip_code):
        errors.append("PLZ: Bitte 3–10 Zeichen (Ziffern/Buchstaben) verwenden.")

    phone = form.get("phone", "").strip()
    if phone and not re.fullmatch(r"[0-9+()\- ]{6,20}", phone):
        errors.append("Telefon: Ungültiges Format. Beispiel: +41 79 000 00 00")

    if form.get("street", "") and len(form.get("street", "").split()) < 2:
        errors.append("Straße & Hausnummer: Bitte beides angeben.")

    return errors

# --- Basic Auth für Admin ---
ADMIN_USER = os.environ.get("ADMIN_USER", "Tim")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "passwort")

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response("Auth erforderlich", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- Routes ---
@app.route("/")
def home():
    return render_template("home.html", title="Start", active="home")

@app.route("/about")
def about():
    return render_template("about.html", title="Über uns", active="about")

@app.route("/impressum")
def imprint():
    return render_template("imprint.html", title="Impressum & Datenschutz", active="imprint")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin"))
        else:
            error = "Falscher Benutzername oder Passwort."
    return render_template("login.html", error=error)

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in 
                ["name", "street", "zip", "city", "country", "notes"]}
        errors = validate(form)

        if not errors:
            valid, details = validate_address(form["street"], form["zip"], form["city"], form["country"])
            if not valid:
                errors.append("Adresse konnte nicht gefunden werden. Bitte prüfen Sie Ihre Eingaben.")
            else:
                lat = float(details["lat"])
                lon = float(details["lon"])
                # Schritt 2: Map anzeigen
                return render_template("order_map_step2.html",
                                       title="Ablageort wählen",
                                       form=form,
                                       lat=lat,
                                       lon=lon)

        return render_template("order.html", title="Auftrag", active="order", errors=errors, form=form)

    return render_template("order.html", title="Auftrag", active="order", form={})


def requires_login(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("logged_in"):
            # Weiterleitung zum Login
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrap

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# app.py


@app.route("/download/bulk-csv")
def download_bulk_csv():
    return send_from_directory(
        directory="static",
        path="bulk_template.csv",
        as_attachment=True,
        mimetype="text/csv; charset=utf-8",
        download_name="bulk_template.csv",
    )
@app.route("/bulk_upload", methods=["GET", "POST"])
def bulk_upload():
    if request.method == "GET":
        return render_template("bulk_upload.html")

    file = request.files.get("file")
    if not file or file.filename == "":
        return render_template("bulk_upload.html", error="Bitte eine Datei hochladen.")

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()

    try:
        if ext == "csv":
            # Auto-Delimiter, Fallback-Encoding
            data = file.read()
            import io
            try:
                df = pd.read_csv(io.BytesIO(data), sep=None, engine="python", dtype=str)
            except Exception:
                df = pd.read_csv(io.BytesIO(data), sep=None, engine="python", dtype=str, encoding="latin-1")
        elif ext == "xlsx":
            # benötigt: pip install openpyxl
            df = pd.read_excel(file, engine="openpyxl", dtype=str)
        else:
            return render_template("bulk_upload.html", error="Nur .csv oder .xlsx sind erlaubt.")
    except ImportError as ie:
        return render_template("bulk_upload.html", error=f"Parser fehlt: {ie}. Installiere z. B. 'openpyxl'.")
    except Exception as e:
        return render_template("bulk_upload.html", error=f"Datei konnte nicht gelesen werden: {e}")

    # Spalten normalisieren (fix für 'Unnamed: 5' -> notes, Aliases, Trimmen)
    df = normalize_dataframe(df)

    # Pflichtspalten prüfen
    required = {"name", "street", "zip", "city", "country"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        return render_template("bulk_upload.html", error=f"Spalten fehlen: {', '.join(missing)}")

    # Leere Zeilen raus
    df = df[(df["name"]!="") & (df["street"]!="") & (df["zip"]!="") & (df["city"]!="") & (df["country"]!="")]
    if df.empty:
        return render_template("bulk_upload.html", error="Keine gültigen Datensätze gefunden.")

    # Geokodieren (wie bei dir), mit Fallback
    geocoded = []
    for _, row in df.iterrows():
        query = f"{row['street']}, {row['zip']} {row['city']}, {row['country']}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 1}
        try:
            r = requests.get(url, params=params, headers={"User-Agent": "kue-transportdrone"}, timeout=6)
            data = r.json()
            if data:
                row_lat, row_lon = float(data[0]["lat"]), float(data[0]["lon"])
            else:
                row_lat, row_lon = 47.3769, 8.5417  # Zürich Fallback
        except Exception:
            row_lat, row_lon = 47.3769, 8.5417

        geocoded.append({
            "name": row["name"],
            "street": row["street"],
            "zip": row["zip"],
            "city": row["city"],
            "country": row["country"],
            "notes": row.get("notes", ""),
            "lat": row_lat,
            "lon": row_lon
        })

    # Direkt zur Map (dein Flow)
    return render_template("bulk_map.html", addresses=geocoded)

@app.route("/bulk_save", methods=["POST"])
def bulk_save():
    db = get_db()
    db.execute(
        "INSERT INTO orders (name, street, zip, city, country, notes, lat, lon, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            request.form["name"],
            request.form["street"],
            request.form["zip"],
            request.form["city"],
            request.form["country"],
            request.form.get("notes", ""),
            request.form["lat"],
            request.form["lon"],
            datetime.datetime.utcnow().isoformat()
        )
    )
    db.commit()
    return "OK"


@app.route("/admin")
@requires_login
def admin():
    db = get_db()

    # normale Aufträge
    orders = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()

    # extraorders mit waypoints
    extraorders = db.execute("SELECT * FROM extraorders ORDER BY id DESC").fetchall()
    result = []
    for eo in extraorders:
        waypoints = db.execute(
            "SELECT lat, lon FROM extraorder_waypoints WHERE order_id=?",
            (eo["id"],)
        ).fetchall()
        result.append({"order": eo, "waypoints": waypoints})

    return render_template(
        "admin.html",
        title="Admin",
        orders=orders,
        extraorders=result
    )

# --- Admin: Edit / Delete (Orders & Extraorders) ---

from flask import request, redirect, url_for, render_template

def _to_float(s):
    try:
        return float((s or "").replace(",", "."))
    except Exception:
        return None

@app.route("/admin/orders/edit/<int:order_id>", methods=["GET", "POST"])
@requires_auth
def edit_order(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return "Nicht gefunden", 404

    if request.method == "POST":
        f = request.form
        db.execute("""
            UPDATE orders
               SET name=?,
                   phone=?,
                   notes=?,
                   street=?,
                   zip=?,
                   city=?,
                   country=?,
                   lat=?,
                   lon=?
             WHERE id=?""",
            (
                (f.get("name") or "").strip(),
                (f.get("phone") or "").strip(),
                (f.get("notes") or "").strip(),
                (f.get("street") or "").strip(),
                (f.get("zip") or "").strip(),
                (f.get("city") or "").strip(),
                (f.get("country") or "").strip(),
                _to_float(f.get("lat")),
                _to_float(f.get("lon")),
                order_id,
            )
        )
        db.commit()
        return redirect(url_for("admin"))

    return render_template("edit_order.html", order=order)


@app.post("/admin/orders/delete/<int:order_id>")
@requires_auth
def delete_order(order_id):
    db = get_db()
    db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/extraorders/edit/<int:order_id>", methods=["GET", "POST"])
@requires_auth
def edit_extraorder(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM extraorders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return "Nicht gefunden", 404

    if request.method == "POST":
        f = request.form

        # 1) Stammdaten
        db.execute("""
            UPDATE extraorders
               SET name=?,
                   phone=?,
                   notes=?
             WHERE id=?""",
            (
                (f.get("name") or "").strip(),
                (f.get("phone") or "").strip(),
                (f.get("notes") or "").strip(),
                order_id,
            )
        )

        # 2) Waypoints (beliebig viele) – ersetzen
        lats = f.getlist("wp_lat")
        lons = f.getlist("wp_lon")

        db.execute("DELETE FROM extraorder_waypoints WHERE order_id=?", (order_id,))
        rows = []
        for la, lo in zip(lats, lons):
            lat = _to_float(la)
            lon = _to_float(lo)
            if lat is None or lon is None:
                continue
            rows.append((order_id, lat, lon))
        if rows:
            db.executemany(
                "INSERT INTO extraorder_waypoints (order_id, lat, lon) VALUES (?,?,?)",
                rows
            )

        db.commit()
        return redirect(url_for("admin"))

    # GET: vorhandene Waypoints für das Formular
    waypoints = db.execute(
        "SELECT id, lat, lon FROM extraorder_waypoints WHERE order_id=? ORDER BY id",
        (order_id,)
    ).fetchall()

    return render_template("edit_extraorder.html", order=order, waypoints=waypoints)


@app.post("/admin/extraorders/delete/<int:order_id>")
@requires_auth
def delete_extraorder(order_id):
    db = get_db()
    db.execute("DELETE FROM extraorders WHERE id=?", (order_id,))
    db.commit()
    return redirect(url_for("admin"))


@app.post("/admin/orders/bulk_delete")
@requires_auth
def bulk_delete_orders():
    db = get_db()
    ids = request.form.getlist("ids")
    if ids:
        db.executemany("DELETE FROM orders WHERE id=?", [(i,) for i in ids])
        db.commit()
    return redirect(url_for("admin"))

@app.post("/admin/extraorders/bulk_delete")
@requires_auth
def bulk_delete_extraorders():
    db = get_db()
    ids = request.form.getlist("ids")
    if ids:
        # Waypoints mitlöschen (falls kein ON DELETE CASCADE gesetzt ist):
        db.executemany("DELETE FROM extraorder_waypoints WHERE order_id=?", [(i,) for i in ids])
        db.executemany("DELETE FROM extraorders WHERE id=?", [(i,) for i in ids])
        db.commit()
    return redirect(url_for("admin"))


@app.route("/extraorder", methods=["GET", "POST"])
def extraorder():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("notes", "").strip()
        waypoint_count = int(request.form.get("waypoint_count", 0))

        errors = []
        if not name:
            errors.append("Name ist ein Pflichtfeld.")
        if waypoint_count == 0:
            errors.append("Bitte setzen Sie mindestens einen Waypoint.")

        if errors:
            return render_template(
                "extraorder.html",
                title="Extra Auftrag",
                active="extraorder",
                errors=errors,
                form=request.form
            )

        db = get_db()
        # Hauptauftrag speichern
        db.execute(
            "INSERT INTO extraorders (name, phone, notes, created_at) VALUES (?,?,?,?)",
            (name, phone, notes, datetime.datetime.utcnow().isoformat())
        )
        db.commit()
        job_id = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        # Waypoints speichern
        for i in range(waypoint_count):
            lat = request.form.get(f"lat_{i}")
            lon = request.form.get(f"lon_{i}")
            if lat and lon:
                db.execute(
                    "INSERT INTO extraorder_waypoints (order_id, lat, lon) VALUES (?,?,?)",
                    (job_id, float(lat), float(lon))
                )
        db.commit()

        return render_template(
            "extraorder.html",
            title="Extra Auftrag",
            active="extraorder",
            success=True,
            job_id=job_id
        )

    return render_template("extraorder.html", title="Extra Auftrag", active="extraorder", form={})

@app.route("/bulk_map", methods=["GET", "POST"])
def bulk_map():
    addresses = request.args.get("addresses")  # JSON von bulk_upload
    import json
    addresses = json.loads(addresses)

    # Index mitgeben (erste Adresse)
    return render_template("bulk_map.html", addresses=addresses, index=0)



@app.route("/order_map_step2", methods=["POST"])
def order_map_step2():
    form = {k: request.form.get(k, "").strip() for k in
            ["name", "street", "zip", "city", "country", "notes", "lat", "lon"]}

    # Debug-Ausgabe: siehst du im Terminal
    print("FORM DATA:", form)

    db = get_db()
    db.execute(
        """INSERT INTO orders (name, street, zip, city, country, notes, lat, lon, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (form["name"], form["street"], form["zip"], form["city"], form["country"],
         form["notes"], form["lat"], form["lon"], datetime.datetime.utcnow().isoformat())
    )
    db.commit()

    job_id = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

    return render_template("order_map_step2.html",
                           title="Ablageort wählen",
                           success=True,
                           job_id=job_id,
                           form=form,
                           lat=form["lat"],
                           lon=form["lon"])







if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)


