import MySQLdb
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt


def construct_login_page(database: MySQL) -> Blueprint:
    """
    Constructs the login page. This page is used to log in to the application. 
    It is also used to create a new user.
    :param database: The database object.
    :return: The login page blueprint.
    """
    login_page = Blueprint('/login', __name__)

    @login_page.route('/login', methods=['GET', 'POST'])
    def login() -> str:
        """
        Renders the login page.
        :return: The rendered login page.
        """
        if request.method == 'POST':
            username = request.form['username']
            password_candidate = request.form['password']

            try:

                with database.connection.cursor() as cursor:
                    result = cursor.execute(f'SELECT * FROM users WHERE username = {username!r}')

                    if result > 0:
                        data = cursor.fetchone()
                        password = data['password']

                        if sha256_crypt.verify(password_candidate, password):
                            session['logged_in'] = True
                            session['username'] = username

                            flash('You are now logged in', 'success')
                            return redirect(url_for('/dashboard.dashboard'))
                        else:
                            return render_template('login.html', error='Invalid login')

                    else:
                        return render_template('login.html', error='Username not found')

            except MySQLdb._exceptions.OperationalError:
                return render_template('login.html', error='Connection error')

        return render_template('login.html')

    return login_page
