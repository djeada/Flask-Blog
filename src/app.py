from flask_mysqldb import MySQL
from pathlib import Path
from pages.home_page import home_page
from pages.about_page import about_page
from pages.logout_page import logout_page
from pages.login_page import construct_login_page
from pages.add_article import construct_add_article_page
from pages.edit_article import construct_edit_article_page
from pages.delete_article import construct_delete_article_page
from pages.dashboard_page import construct_dashboard_page
from pages.register_page import construct_register_form_page
from pages.single_article_page import construct_article_page
from pages.articles_page import construct_articles_page

from misc.blog_flask import BlogFlask

CREDENTIALS_PATH = Path('credentials.json')

if __name__ == '__main__':

    # Initialize the application
    app = BlogFlask(CREDENTIALS_PATH, __name__)
    
    # Initialize the database
    database = MySQL(app)

    # create all the pages
    pages = [
        home_page,
        about_page,
        logout_page,
        construct_login_page(database),
        construct_add_article_page(database),
        construct_edit_article_page(database),
        construct_delete_article_page(database),
        construct_dashboard_page(database),
        construct_register_form_page(database),
        construct_article_page(database),
        construct_articles_page(database)
    ]

    for page in pages:
        app.register_blueprint(page)

    # Run the application
    app.run(debug=True)
    
