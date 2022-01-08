from flask import Blueprint, render_template

about_page = Blueprint('about', __name__)
@about_page.route('/about')
def index():
    """
    Render the about page.
    """
    return render_template('about.html')

