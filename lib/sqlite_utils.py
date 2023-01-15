import sqlite3

def exec_query(conn, query):
    try:
        c = conn.cursor()
        c.execute(query)
        conn.commit()
        return c.fetchall()
    except Exception as e:
        print(e)

class DBConnection:

    def __init__(self,path):
        try:
            conn = sqlite3.connect(path)
            self.conn,self.path= conn,path
            self.query("PRAGMA foreign_keys = ON;")

        except Exception as e:
            print('Cannot connect to db: ' + e)
 
    def query(self, query):
            c = self.conn.cursor()
            c.execute(query)
            self.conn.commit()
            res = c.fetchall()
            c.close()
            return res   

    def add(self,table,dic,columns=None):
        if columns==None:
            columns=list(dic.keys())
        #pragma table_info(organization)
        values=['"'+dic[column].replace('"',"'")+'"' if type(dic[column])==str else '""' if dic[column] is None else str(dic[column]) for column in columns]
        return  self.query('INSERT OR IGNORE INTO {} ({}) VALUES({})'.format(table,','.join(columns),','.join(values)))
    
    def add_or_update(self,table,dic,columns=None):
        primary_keys=[el[1] for el in self.query(f'SELECT * FROM pragma_table_info(\'{table}\') WHERE pk')]
        if not self.__table_exists(table):
            raise Exception('Table does not exist!')
        clause = ''
        for key in primary_keys:
            if key not in dic:
                raise Exception('You must give at least the primary key in order to add or update a row!')
            clause += ' AND ' + key + '= "' + dic[key] + '"'
        clause=clause[4:]
        if len(self.query(f'SELECT * FROM {table} WHERE {clause}'))<1:
            self.add(table,dic,columns)
            return
        if columns==None:
            columns=list(dic.keys())
        changes = ''.join([', '+col+' = "'+ dic[col].replace('"',"'")+'"' if type(dic[col])==str else '' if dic[col] is None else ', ' +col+' = '+ str(dic[col]) for col in columns])[1:]
        return  self.query(f'UPDATE {table} SET {changes} WHERE {clause}') 

    def get_rows(self,table:str,dic:dict=dict(), columns=None):
        if not self.__table_exists(table):
            raise Exception('Table does not exist!')
        clause = ''
        for key in list(dic.keys()):
            clause += ('' if not clause else ' AND ') + key + '= "' + dic[key] + '"'
        if columns==None:
            columns=[el[1] for el in self.query(f'SELECT * FROM pragma_table_info(\'{table}\')')]
        res = self.query('SELECT {} FROM {} WHERE {}'.format(', '.join(columns),table,clause) if clause else 'SELECT {} FROM {}'.format(', '.join(columns),table))
        return [dict(zip(columns,row)) for row in res]

    def __table_exists(self,table:str):
        return 1 if len(self.query(f'SELECT name FROM sqlite_master WHERE type="table" AND name="{table}";'))>0 else 0
    def close(self):
        self.conn.close()

    def __str__(self):
        return 'Database connection object'
