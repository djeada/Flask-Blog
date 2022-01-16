from flask import flash, redirect, url_for, Blueprint, render_template, session, request
from misc.common import is_logged_in, ArticleForm
import datetime


def construct_add_article_page(database):
    """
    Constructs the add article page. This page is only accessible to logged in users.
    If the user is not logged in, the user is redirected to the login page.
    :param database: The database object.
    :return: The add article page blueprint.
    """
    add_article_page = Blueprint('/add_article', __name__)

    @add_article_page.route('/add_article', methods=['GET', 'POST'])
    @is_logged_in
    def add_article():
        """
        Renders the add article page.
        :return: The rendered add article page.
        """
        form = ArticleForm(request.form)
        if request.method == 'POST' and form.validate():
            title = form.title.data
            body = form.body.data
            author = session['username']

            with database.connection.cursor() as cursor:
                cursor.execute (f"INSERT INTO articles(title, body, author, image) VALUES({title!r}, {body!r}, {author!r}, C:/Users/Adam/Downloads/cat.jpg)")
                database.connection.commit()

            flash('Article Created', 'success')

            return redirect(url_for('/dashboard.dashboard'))

        return render_template('add_article.html', form=form)

    return add_article_page
