# Responsive-Blog-Template
A simple blog written with Flask framework and MySQL database.

## Screenshots

### Home page

![home_screenshot](https://github.com/djeada/Responsive-Blog-Template/blob/main/resources/home_screenshot.png)

### Articles dashboard

![dashboard_screenshot](https://github.com/djeada/Responsive-Blog-Template/blob/main/resources/dashboard_screenshot.png)


## Features

The following features are included in this project:

* user authentication
* user registration
* create, edit and delete articles
* admin dashboard
* tags
* fully responsive, easily customizable design
* user friendly, easy to use interface

## How to setup the database?

The application can't function without a MySQL database. There are multiple ways to setup the database. Easiest way to locally setup a MySQL database is using docker.

First, you need make sure you have docker installed. If you don't, you can install it using the following command if you are on Debian-based Linux distribution:

    $ sudo apt-get update
    $ sudo apt-get install docker.io

Then, you need to create a docker container for your database:

    $ docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=secret_pass mysql

The container will be running on port 3306. The secret_pass is the password for the root user of the database. You can use any password you want.

You can find the container id by running the following command:

    $ docker ps

To ssh into the container, you can use the following command:

    $ docker exec -it <container_id> /bin/bash
    $ mysql -u root -psecret_pass

You can now create the database:

    $ CREATE DATABASE flask_db;

The last thing is two create expected tables. The app works with two tables:

    - `articles`
    - `users`

Table articles has the following columns:

    - `id`: primary key
    - `title`: string
    - `body`: text
    - `author`: string
    - `date`: datetime
    - `image`: string

Use the following command to create the table:

```MySQL
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body LONGTEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    image VARCHAR(255) default '/static/images/default.jpg'
);
```

Table users has the following columns:

    - `id`: primary key
    - `name`: string
    - `email`: string
    - `username`: string
    - `password`: string

```MySQL
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    email VARCHAR(40) NOT NULL,
    username VARCHAR(20) NOT NULL,
    password VARCHAR(255) NOT NULL
);
```

## Installation
 
You can run the application without the database, but you will not be able to create or edit articles. It is recommended to first setup the database.

### Using virtual env:
 
    $ git clone https://github.com/djeada/Responsive-Blog-Template.git
    $ cd Responsive-Blog-Template
    $ python3 -m venv env
    $ source env/bin/activate
    $ python3 src/app.py

### Using docker:

    $ docker run -d -p 5000:5000 -v /var/run/docker.sock:/var/run/docker.sock -v /home/user/Responsive-Blog-Template:/app djeada/flask-blog

## How to use?

If the application is running on localhost, you can access it using the following url:

    http://localhost:5000/

To register a new user, you can use the following url:

    http://localhost:5000/register

To login, you can use the following url:

    http://localhost:5000/login

To create, edit or delete articles, you need to login first. Then, you can use the following url:

    http://localhost:5000/dashboard

## TODO

- [x] Add exception handling to all python files that are interacting with the DB.
- [ ] Introduce variables to CSS.
- [ ] Test on different devices.
- [ ] Make full project specification.
- [x] Enable storing of images in the database.
- [ ] Add tags to the database.
