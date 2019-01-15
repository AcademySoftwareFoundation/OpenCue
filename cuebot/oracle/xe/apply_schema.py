
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


def main(user, pwd, sql_file, sql_data_file=None):
    print "CONNECTING: {}  {}  {}".format(user, pwd, sql_file)
    connection = cx_Oracle.connect(user, pwd)
    cursor = connection.cursor()
    for statement in get_statements(sql_file):
        cursor.execute(statement)
    if sql_data_file:
      print 'APPLYING DATA FILE: {}'.format(sql_data_file)
      for statement in get_statements(sql_data_file):
          cursor.execute(statement)
    cursor.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='db user', default='cue')
    parser.add_argument('-p', '--pwd', help='db password to connect to cue user')
    parser.add_argument('-s', '--sql', help='path to SQL schema file')
    parser.add_argument('-d', '--sql-data', help='path to SQL file with inital data to populate')
    args = parser.parse_args()
    main(args.user, args.pwd, args.sql, args.sql_data)
