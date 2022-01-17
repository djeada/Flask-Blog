import MySQLdb
from flask import Blueprint, session, flash, redirect, url_for
from misc.common import is_logged_in

logout_page = Blueprint("logout", __name__)


@logout_page.route("/logout")
@is_logged_in
def logout() -> str:
    """
    Route to logout the user. Clears the session and redirects to the login page.
    :return: Redirect to the login page.
    """
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for("/login.login"))
