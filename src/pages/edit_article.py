import MySQLdb
from flask import flash, redirect, url_for, Blueprint, request, render_template
from misc.common import is_logged_in, ArticleForm
from flask_mysqldb import MySQL


def construct_edit_article_page(database: MySQL) -> Blueprint:
    """
    Wrapper function for constructing the edit article page. This way we can 
    pass the database object to the blueprint.
    :param database:
    :return:
    """
    edit_article_page = Blueprint('/edit_article/<string:id>', __name__)

    @edit_article_page.route('/edit_article/<string:id>', methods=['GET', 'POST'])
    @is_logged_in
    def edit_article(id: str) -> str:
        """
        Constructs the edit article page. If the user is not logged in, redirects to the login page.
        If the user is logged in, the page is rendered.
        :param id: The article id in the database.
        :return: Rendered template.
        """

        try:
            with database.connection.cursor() as cursor:
                cursor.execute(f'SELECT * FROM articles WHERE id = {id}')
                article = cursor.fetchone()

        except MySQLdb._exceptions.OperationalError:
            flash("Can't display the article", 'failure')
            return redirect(url_for('/dashboard.dashboard'))
 
        # Fill the form fields
        form = ArticleForm(request.form)
        form.title.data = article['title']
        form.body.data = article['body']

        if request.method == 'POST' and form.validate():
            title = request.form['title']
            body = request.form['body']

            try:
                with database.connection.cursor() as cursor:
                    cursor.execute(f"UPDATE articles SET title = {title!r}, body = {body!r} WHERE id = {id!r}")
                    database.connection.commit()

                flash('Article Updated', 'success')
                return redirect(url_for('/dashboard.dashboard'))

            except MySQLdb._exceptions.OperationalError:
                flash("Can't update the article", 'failure')
                return redirect(url_for('/dashboard.dashboard'))

        return render_template('edit_article.html', form=form)

    return edit_article_page
