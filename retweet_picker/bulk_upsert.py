from django.db.backends.utils import CursorWrapper
from django.db import connection
import contextlib
from typing import List, Iterable
from io import StringIO
from retweet_picker.models import ContestUserAccounts

@contextlib.contextmanager
def setup_teardown_temp_tables(cursor: CursorWrapper):
    """Context manager for creating and dropping temp tables"""
    cursor.execute(
        '''
        DROP TABLE IF EXISTS temp_retweet_users;

        CREATE TEMPORARY TABLE temp_retweet_users AS
        SELECT * FROM retweet_picker_contestuseraccounts LIMIT 0;
        '''
    )
    try:
        yield
    finally:
        cursor.execute(
            '''
            DROP TABLE IF EXISTS temp_retweet_users;
            '''
        )


def create_tsv_file(rows: Iterable) -> StringIO:
    file = StringIO()
    for row in rows:
        file.write('\t'.join(value for value in row) + '\n')

    file.seek(0)
    return file


def populate_temp_table(cursor: CursorWrapper, retweet_users: List[ContestUserAccounts]):
    def generate_rows_from_retweet_users():
        for retweet_user in retweet_users:
            yield (str(retweet_user.user_id),
                   retweet_user.user_handle,
                   retweet_user.user_screen_name,
                   retweet_user.location,
                   retweet_user.profile_img,
                   str(retweet_user.account_created))

    tsv_file = create_tsv_file(generate_rows_from_retweet_users())
    cursor.copy_from(
        tsv_file,
        'temp_retweet_users',
        columns=('user_id', 'user_handle', 'user_screen_name', 'location', 'profile_img', 'account_created')
    )


def copy_from_temp_table(cursor: CursorWrapper):
    cursor.execute(
        '''
        INSERT INTO retweet_picker_contestuseraccounts (user_id, user_handle, user_screen_name, location, profile_img, account_created)
        SELECT tru.user_id, tru.user_handle, tru.user_screen_name, tru.location, tru.profile_img, tru.account_created
        FROM temp_retweet_users tru
        ON CONFLICT(user_id) 
        DO UPDATE SET (user_handle, user_screen_name, location, profile_img, account_created) = (EXCLUDED.user_handle, EXCLUDED.user_screen_name, EXCLUDED.location, EXCLUDED.profile_img, EXCLUDED.account_created)
        '''
    )


def bulk_upsert_retweet_contestants(retweet_users: List[ContestUserAccounts]):
    with connection.cursor() as cursor:
        with setup_teardown_temp_tables(cursor):
            populate_temp_table(cursor, retweet_users)
            copy_from_temp_table(cursor)
