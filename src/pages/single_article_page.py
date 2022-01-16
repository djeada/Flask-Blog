import MySQLdb
from flask import Blueprint, render_template
from flask_mysqldb import MySQL


def construct_article_page(database: MySQL) -> Blueprint:
    """
    Constructs the single article page.
    :param database: The database object.
    :return: Single article page blueprint.
    """
    article_page = Blueprint('/article/<string:id>/', __name__)

    @article_page.route('/article/<string:id>/')
    def article(id: str) -> str:
        """
        Renders the article page.
        :param id: The article id in the database.
        :return: Rendered article page.
        """

        try:

            with database.connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM articles WHERE id = {id}")
                retrieved_article = cursor.fetchone()

            return render_template('article.html', article=retrieved_article)

        except MySQLdb._exceptions.OperationalError:
            return render_template('article.html', msg='Article not found')

    return article_page
