from flask import Blueprint, render_template

home_page = Blueprint('home', __name__)


@home_page.route('/')
def index():
    """
    Render the home page template on the / route.
    :return: The rendered home page template.
    """
    return render_template('home.html')
