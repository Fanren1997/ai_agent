import re
import mysql.connector

def access_to_mysql_type(access_type):
    access_type = access_type.lower()
    if 'text' in access_type:
        length = re.search(r'\((\d+)\)', access_type)
        if length: return f"VARCHAR({length.group(1)})"
        return "VARCHAR(255)"
    elif 'long integer' in access_type: return "INT"
    elif 'datetime' in access_type: return "DATETIME"
    elif 'boolean' in access_type: return "TINYINT(1)"
    elif 'memo/hyperlink' in access_type: return "TEXT"
    else: return "TEXT" # Default to TEXT for unknown types

def sanitize_name(name, existing_names):
    # Remove brackets, replace spaces and special characters with underscores
    name = name.replace('[', '').replace(']', '')
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not name: # Handle empty names
        name = "column"
    original_name = name
    counter = 1
    while name in existing_names:
        name = f"{original_name}_{counter}"
        counter += 1
    return name

def parse_schema_and_create_tables(schema_file, db_config):
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_content = f.read()

    tables_sql = []
    # Split content by CREATE TABLE statements
    table_definitions = re.findall(r'CREATE TABLE \[(.*?)\]\s*\((.*?)\);', schema_content, re.DOTALL)

    system_tables = ["MSysObjects", "MSysACEs", "MSysQueries", "MSysRelationships", 
                     "MSysComplexColumns", "MSysComplexType_UnsignedByte", 
                     "MSysComplexType_Short", "MSysComplexType_Long", 
                     "MSysComplexType_IEEESingle", "MSysComplexType_IEEEDouble", 
                     "MSysComplexType_GUID", "MSysComplexType_Decimal", 
                     "MSysComplexType_Text", "MSysComplexType_Attachment", 
                     "MSysAccessStorage", "MSysNavPaneGroupCategories", 
                     "MSysNavPaneGroups", "MSysNavPaneGroupToObjects", 
                     "MSysNavPaneObjectIDs", "MSysResources", 
                     "MSysWSDPCacheComplexColumnMapping", "MSysWSDPChangeTokenMapping", 
                     "MSysWSDPRelationshipMapping", "MSysNameMap", "MSysSQLComments"]

    for table_name_raw, columns_raw in table_definitions:
        if table_name_raw in system_tables:
            print(f"Skipping system table: {table_name_raw}")
            continue

        table_name = sanitize_name(table_name_raw, []) # Table names should be unique globally
        columns_sql = []
        existing_column_names = set()
        # Split columns by comma, but be careful with commas inside parentheses
        column_definitions = re.findall(r'\s*\[(.*?)\]\s*(.*?)(?:,\s*|$)', columns_raw)

        for col_name_raw, col_type_raw in column_definitions:
            col_name = sanitize_name(col_name_raw.strip(), existing_column_names)
            existing_column_names.add(col_name)
            col_type = access_to_mysql_type(col_type_raw.strip())
            # Handle NOT NULL and PRIMARY KEY if present
            constraints = []
            if 'NOT NULL' in col_type_raw.upper():
                constraints.append('NOT NULL')
                col_type = col_type.replace('NOT NULL', '').strip()
            if 'PRIMARY KEY' in col_type_raw.upper():
                constraints.append('PRIMARY KEY')
                col_type = col_type.replace('PRIMARY KEY', '').strip()

            columns_sql.append(f"`{col_name}` {col_type} {' '.join(constraints)}")

        create_table_sql = f"CREATE TABLE `{table_name}` (\n  " + ",\n  ".join(columns_sql) + "\n);"
        tables_sql.append(create_table_sql)

    # Connect to MySQL and execute SQL
    try:
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()

        for sql in tables_sql:
            try:
                print(f"Executing:\n{sql}")
                cursor.execute(sql)
                print("Table created successfully.")
            except mysql.connector.Error as err:
                print(f"Failed to create table: {err}")
                print(f"SQL: {sql}")
        cnx.commit()

    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()

if __name__ == "__main__":
    db_config = {
        'host': 'localhost',
        'user': 'access_user',
        'password': 'wvqbIcZwf5/qgm8V',
        'database': 'access_migration_db'
    }
    parse_schema_and_create_tables('/home/ubuntu/access_schema.sql', db_config)


