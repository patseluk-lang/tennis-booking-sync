"""
Mock website of a municipal sports centre.

Run:    python fake_site.py
Open:   http://127.0.0.1:5000

Credentials:  player  /  tennis123
"""
import json
from pathlib import Path
from flask import Flask, request, session, redirect, render_template_string, abort

app = Flask(__name__)
app.secret_key = "dev-secret-not-for-production"

USERNAME = "player"
PASSWORD = "tennis123"

DATA = Path(__file__).parent / "reservations.json"

# Failure switch: when True, the site pretends to be broken.
# Needed to verify that the sync script does not wipe the calendar on failure.
BROKEN = False


LOGIN_PAGE = """
<!doctype html>
<title>Sports Centre - Login</title>
<h1>Municipal Sports Centre</h1>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post" action="/login">
  <p>Username: <input name="username"></p>
  <p>Password: <input name="password" type="password"></p>
  <p><button type="submit">Log in</button></p>
</form>
"""

RESERVATIONS_PAGE = """
<!doctype html>
<title>My reservations</title>
<h1>My tennis court reservations</h1>
<p>Logged in as {{ user }} - <a href="/logout">log out</a></p>
<table id="reservations" border="1" cellpadding="6">
  <thead>
    <tr><th>Date</th><th>Start</th><th>End</th><th>Court</th><th>Location</th></tr>
  </thead>
  <tbody>
  {% for r in reservations %}
    <tr>
      <td class="date">{{ r.date }}</td>
      <td class="start">{{ r.start }}</td>
      <td class="end">{{ r.end }}</td>
      <td class="court">{{ r.court }}</td>
      <td class="location">{{ r.location }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% if not reservations %}<p>You have no reservations.</p>{% endif %}
"""


@app.route("/")
def index():
    if not session.get("user"):
        return redirect("/login")
    return redirect("/reservations")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["user"] = USERNAME
            return redirect("/reservations")
        return render_template_string(LOGIN_PAGE, error="Invalid credentials")
    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/reservations")
def reservations():
    if BROKEN:
        abort(500)                      # the site "goes down"
    if not session.get("user"):
        return redirect("/login")       # not logged in - no data at all
    data = json.loads(DATA.read_text(encoding="utf-8"))
    return render_template_string(RESERVATIONS_PAGE, reservations=data, user=session["user"])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
