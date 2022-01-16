import MySQLdb
from flask import Blueprint, render_template


def construct_home_page(database):
    """
    Constructs the home page. This page is accessible from the main page and
    does not require authentication.
    :param database: The database object.
    :return: The home page blueprint.
    """

    home_page = Blueprint('home', __name__)

    @home_page.route('/')
    def index():
        """
        Render the home page template on the / route.
        :return: The rendered home page template.
        """
        try:

            with database.connection.cursor() as cursor:

                result = cursor.execute("SELECT * FROM articles")

                retrieved_articles = cursor.fetchall()

                if result <= 0:
                    return render_template('home.html')

                return render_template('home.html', articles=retrieved_articles)

        except MySQLdb._exceptions.OperationalError:
            return render_template('home.html')

    return home_page
