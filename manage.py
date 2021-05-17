# -*- coding: utf-8 -*-

import os
import click

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask.cli import with_appcontext

from app import create_app, db
from app.models import User, Role, Permission, Post

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


@click.command(name='deploy')
@with_appcontext
def deploy():
    from flask_migrate import upgrade
    from app.models import Role, User

    # обновить базу данных
    upgrade()

    # создать роли для пользователей
    Role.insert_roles()

    # создаем фейковых пользователей
    User.generate_fake(50)

    # фейковые посты
    Post.generate_fake()

    # объявить все пользователей как читающих самих себя
    User.add_self_follows()


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Permission=Permission, Post=Post)


@manager.command
def test():
    import unittest
    test = unittest.TestLoader().discover('test')
    unittest.TextTestRunner(verbosity=2).run(test)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    app.run()
