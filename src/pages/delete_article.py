import MySQLdb
from flask import flash, redirect, url_for, Blueprint
from misc.common import is_logged_in
from flask_mysqldb import MySQL


def construct_delete_article_page(database: MySQL) -> Blueprint:
    """
    Constructs the delete article page. This page is only accessible to the admin.
    :param database:
    :return:
    """
    delete_page = Blueprint('/delete_article/<string:id>', __name__)

    @delete_page.route('/delete_article/<string:id>', methods=['POST'])
    @is_logged_in
    def delete_article(id: str) -> str:
        """
        Remove the article specified by the id from the database.
        Render the delete_article page.
        :param id: The article id in the database.
        :return: Redirect to the delete_article page.
        """
        
        try:
            with database.connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM articles WHERE id = {id}")
                database.connection.commit()

            flash('Article Deleted', 'success')

        except MySQLdb._exceptions.OperationalError:
            flash('Article deletion failed', 'failure')

        return redirect(url_for('/dashboard.dashboard'))

    return delete_page
