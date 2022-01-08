from flask import Blueprint, render_template

def construct_articles_page(database):
    """
    Constructs the articles page. This page is accessible from the main page and
    does not require authentication.
    :param database: The database object.
    :return: The articles page blueprint.
    """

    articles_page = Blueprint('/articles', __name__)

    @articles_page.route('/articles')
    def articles():
        """
        Renders the articles page.
        :return: The rendered articles page.
        """

        with database.connection.cursor() as cursor:

            result = cursor.execute("SELECT * FROM articles")

            retrieved_articles = cursor.fetchall()

            if result <= 0:
                return render_template('articles.html', msg='No Articles Found')

            return render_template('articles.html', articles=retrieved_articles)


    return articles_page
