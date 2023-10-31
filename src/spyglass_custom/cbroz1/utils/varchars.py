import datajoint as dj
from datajoint_utilities.dj_search.lists import list_tables

from spyglass import *  # noqa: F401

LEAD = "common_nwbfile.nwbfile"
SCHEMA = "common_nwbfile"
TABLE = "nwbfile"
COLUMN = "nwb_file_name"
OLD_LEN = 64
NEW_LEN = 60


class ReduceVarchar:
    def __init__(
        self,
        schema=SCHEMA,
        table=TABLE,
        column=COLUMN,
        old_len=OLD_LEN,
        new_len=NEW_LEN,
        exec_direct=False,
        limit=None,
    ):
        self.schema = schema
        self.table = table
        self.column = column
        self.old_len = old_len
        self.new_len = new_len
        self._tables = []
        self.limit = int(limit) if limit else None
        self.exec_direct = exec_direct
        self._all_table_defs = {}
        self._all_full_table_defs = {}

    def get_tables(self):
        tables = list(set(list_tables(attribute=COLUMN)[::-1]))
        if self.limit and len(tables) > self.limit:
            return tables[: self.limit]
        return tables

    @property
    def tables(self):
        if not self._tables:
            self._tables = self.get_tables()
        return self._tables

    def exec(self, sql, exec_direct=None):
        if "CASCADE," in sql:
            __import__("pdb").set_trace()

        if not exec_direct:
            exec_direct = self.exec_direct
        if not exec_direct:
            with open("temp.sql", "a") as f:
                f.write(sql + "\n")
            return
        sql = sql.replace("\n", " ").replace("\t", " ")
        dj.conn().query(sql).fetchall()

    def _alt_tbl(self, table):
        return f"ALTER TABLE {table} \n\t"

    def _add_col_if_not_exist_sql(
        self, table_full, if_true="add", if_false=None
    ):
        schema, table = table_full.replace("`", "").split(".")
        if if_true == "add":
            if_true = (
                self._alt_tbl(table_full)
                + f"\tADD COLUMN {self.column}_new VARCHAR({self.new_len}) "
                + f"NOT NULL AFTER {self.column};"
            )
        if not if_false:
            if_false = "SELECT NULL FROM DUAL WHERE 1 = 0"
        return (
            "SELECT \n\tCASE WHEN \n\t\tcount1 < 1 \n\tTHEN\n\t(\n\t"
            + f"\tCONCAT('{if_true}')\n\t)\n\tELSE CONCAT('{if_false}')\n\tEND "
            + "INTO @sql\nFROM\n (\n\t SELECT\n\t\t (\n\t\t\t"
            + "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS\n\t\t\t"
            + f"WHERE table_name = '{table}'\n\t\t\t"
            + f"AND table_schema = '{schema}'\n\t\t\t"
            + f"AND column_name IN ('{self.column}_new')\n\t\t"
            + ") AS count1\n\t)\nAS counts;\n"
            + "PREPARE stmt FROM @sql;\nEXECUTE stmt;\nDEALLOCATE PREPARE stmt;"
        )

    def add_col_if_not_exist(self, table_full, if_true="add", if_false=""):
        self.exec(self._add_col_if_not_exist_sql(table_full, if_true, if_false))

    def _update_col_sql(self, table):
        return f"UPDATE {table} SET {self.column}_new = {self.column};"

    def update_col(self, table):
        self.exec(self._update_col_sql(table))

    def _rename_col_sql(self, table):
        str_templ = (
            self._alt_tbl(table)
            + "CHANGE COLUMN {0} {1} VARCHAR({2}) NOT NULL;\n"
        )
        return str_templ.format(
            self.column, self.column + "_old", self.old_len
        ) + str_templ.format(self.column + "_new", self.column, self.new_len)

    def rename_col(self, table):
        self.exec(self._rename_col_sql(table))

    def _drop_col_sql(self, table):
        return f"{self._alt_tbl(table)}DROP COLUMN {self.column}_old;"

    def drop_col(self, table):
        self.exec(self._drop_col_sql(table))

    def _filter_defs(self, table, type="all"):
        defs = self._all_table_defs.get(table)
        if type == "all":
            return [item for sublist in defs.values() for item in sublist]
        elif type == "sk":
            return defs["id"] + defs["fk"]
        return defs[type]

    def _full_table_def(self, table, force=False) -> list:
        if not force and self._all_full_table_defs.get(table):
            return self._all_full_table_defs[table]

        self._all_full_table_defs[table] = [
            line.rstrip(",")
            for line in (
                dj.conn().query(f"SHOW CREATE TABLE {table};").fetchall()[0][1]
            ).split("\n")
        ]

        return self._all_full_table_defs[table]

    def table_def(self, table, type="all", force=False):
        if not force and self._all_table_defs.get(table):
            return self._filter_defs(table, type)

        start = {"pk": "PRIMARY KEY", "fk": "CONSTRAINT", "id": "KEY"}
        all = [
            line.strip()
            for line in self._full_table_def(table, force=force)
            if COLUMN in line
        ]
        self._all_table_defs[table] = {
            k: [line for line in all if line.startswith(v)]
            for k, v in start.items()
        }

        return self._filter_defs(table, type)

    def _add_keys_sql(self, lines, table):
        if not lines:
            return ""
        if not isinstance(lines, list):
            lines = [lines]
        return (
            "\n".join([f"{self._alt_tbl(table)}ADD {line};" for line in lines])
            + "\n"
        )

    def add_keys(self, table, type="all"):
        lines = self.table_def(table, type=type)
        self.exec(self._add_keys_sql(lines, table))

    def _drop_keys_sql(self, lines, table):
        if not lines:
            return ""
        if not isinstance(lines, list):
            lines = [lines]
        ret = ""
        for line in lines:
            this_drop = self._alt_tbl(table) + "DROP "
            if line.startswith("CONSTRAINT"):
                ret += this_drop + "FOREIGN KEY " + line.split(" ")[1] + ";\n"
                continue
            ret += this_drop + line.split(" (")[0] + ";\n"
        return ret

    def drop_keys(self, table, type="all"):
        lines = self.table_def(table, type=type)
        self.exec(self._drop_keys_sql(lines, table))

    def main(self):
        # print("run main")
        if not self.exec_direct:
            with open("temp.sql", "w") as _:
                pass

        self.exec("USE information_schema;\n")

        for table in self.tables:
            self.add_col_if_not_exist(table)
            self.drop_keys(table, type="fk")
            self.drop_keys(table, type="id")

        for table in self.tables:
            self.drop_keys(table, type="pk")
            self.rename_col(table)
            self.drop_col(table)
            self.add_keys(table, type="id")
            self.add_keys(table, type="fk")


if __name__ == "__main__":
    import os
    import sys

    os.environ["DJ_SUPPORT_FILEPATH_MANAGEMENT"] = "TRUE"
    limit = sys.argv[1] if len(sys.argv) > 1 else None
    ReduceVarchar(limit=limit).main()
