from flask import Blueprint, render_template


def construct_article_page(database):
    """
    Constructs the single article page.
    :param database: The database object.
    :return: Single article page blueprint.
    """
    article_page = Blueprint('/article/<string:id>/', __name__)

    @article_page.route('/article/<string:id>/')
    def article(id):
        """
        Renders the article page.
        :param id: The article id in the database.
        :return: Rendered article page.
        """

        with database.connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM articles WHERE id = {id}")
            retrieved_article = cursor.fetchone()

        return render_template('article.html', article=retrieved_article)

    return article_page
