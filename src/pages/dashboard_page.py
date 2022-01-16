import MySQLdb
from flask import Blueprint, render_template, session
from misc.common import is_logged_in


def construct_dashboard_page(database):
    """
    Constructs the dashboard page. This page is only accessible to logged in users.
    If the user is not logged in, the user is redirected to the login page.
    :param database:
    :return:
    """
    dashboard_page = Blueprint('/dashboard', __name__)

    @dashboard_page.route('/dashboard')
    @is_logged_in
    def dashboard():
        """
        Renders the dashboard page.
        :return: Rendered dashboard page.
        """
        try:

            with database.connection.cursor() as cursor:

                # get articles from users that are logged in
                result = cursor.execute(f"SELECT * FROM articles WHERE author = '{session['username']}'")

                articles = cursor.fetchall()

                if result <= 0:
                    return render_template('dashboard.html', msg='No Articles Found')

                return render_template('dashboard.html', articles=articles)

        except MySQLdb._exceptions.OperationalError:
            return render_template('dashboard.html', msg='No Articles Found')

    return dashboard_page
