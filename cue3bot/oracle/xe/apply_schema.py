
import argparse
import cx_Oracle


SPLITTER_KEY = '-- SPLIT HERE!'


def get_statements(sql_file):
    with open(sql_file) as file_handle:
        statement = ''
        for line in file_handle:
            if line.startswith(SPLITTER_KEY):
                yield statement
                statement = ''
            else:
                statement += line


def main(user, pwd, sql_file):
    print "CONNECTING: {}  {}  {}".format(user, pwd, sql_file)
    connection = cx_Oracle.connect(user, pwd)
    cursor = connection.cursor()
    for statement in get_statements(sql_file):
        cursor.execute(statement)
    cursor.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='db user', default='cue3')
    parser.add_argument('-p', '--pwd', help='db password to connect to cue3 user')
    parser.add_argument('-s', '--sql', help='path to SQL schema file')
    args = parser.parse_args()
    main(args.user, args.pwd, args.sql)
