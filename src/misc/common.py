# Check if user logged in
from functools import wraps
from flask import flash, redirect, url_for, session
from wtforms import Form, StringField, TextAreaField, validators


def is_logged_in(f):
    """

    :param f:
    :return:
    """

    @wraps(f)
    def wrap(*args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


class ArticleForm(Form):
    """

    """
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])
