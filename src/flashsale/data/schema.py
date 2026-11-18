from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    columns: str
    key: tuple[str, ...] = ()
    references: tuple[tuple[str, str, str], ...] = ()
    indexes: tuple[tuple[str, ...], ...] = ()
    unique: tuple[str, ...] = ()


def address(prefix: str) -> str:
    return ", ".join(f"{prefix}_{name} VARCHAR({size}) NOT NULL" for name, size in (
        ("street_1", 20), ("street_2", 20), ("city", 20), ("state", 2), ("zip", 9)
    ))


stock_dist = ", ".join(f"s_dist_{i:02d} CHAR(24) NOT NULL" for i in range(1, 11))
TABLES = {
    "warehouse": Table(
        f"w_id INT NOT NULL, w_name VARCHAR(10) NOT NULL, {address('w')}, "
        "w_tax INT NOT NULL, w_ytd BIGINT NOT NULL", ("w_id",)),
    "item": Table(
        "i_id INT NOT NULL, i_im_id INT NOT NULL, i_name VARCHAR(24) NOT NULL, "
        "i_price INT NOT NULL, i_data VARCHAR(50) NOT NULL", ("i_id",)),
    "district": Table(
        f"d_w_id INT NOT NULL, d_id INT NOT NULL, d_name VARCHAR(10) NOT NULL, {address('d')}, "
        "d_tax INT NOT NULL, d_ytd BIGINT NOT NULL, d_next_o_id BIGINT NOT NULL",
        ("d_w_id", "d_id"), (("d_w_id", "warehouse", "w_id"),)),
    "stock": Table(
        f"s_w_id INT NOT NULL, s_i_id INT NOT NULL, s_quantity BIGINT NOT NULL, {stock_dist}, "
        "s_ytd BIGINT NOT NULL, s_order_cnt BIGINT NOT NULL, s_remote_cnt BIGINT NOT NULL, "
        "s_data VARCHAR(50) NOT NULL", ("s_w_id", "s_i_id"),
        (("s_w_id", "warehouse", "w_id"), ("s_i_id", "item", "i_id"))),
    "customer": Table(
        "c_w_id INT NOT NULL, c_d_id INT NOT NULL, c_id INT NOT NULL, c_first VARCHAR(16) NOT NULL, "
        f"c_middle CHAR(2) NOT NULL, c_last VARCHAR(16) NOT NULL, {address('c')}, "
        "c_phone CHAR(16) NOT NULL, c_since DATETIME NOT NULL, c_credit CHAR(2) NOT NULL, "
        "c_credit_lim BIGINT NOT NULL, c_discount INT NOT NULL, c_balance BIGINT NOT NULL, "
        "c_ytd_payment BIGINT NOT NULL, c_payment_cnt INT NOT NULL, c_delivery_cnt INT NOT NULL, "
        "c_data VARCHAR(500) NOT NULL", ("c_w_id", "c_d_id", "c_id"),
        (("c_w_id,c_d_id", "district", "d_w_id,d_id"),),
        (("c_w_id", "c_d_id", "c_last", "c_first"),)),
    "history": Table(
        "h_c_w_id INT NOT NULL, h_c_d_id INT NOT NULL, h_c_id INT NOT NULL, h_w_id INT NOT NULL, "
        "h_d_id INT NOT NULL, h_date DATETIME NOT NULL, h_amount BIGINT NOT NULL, "
        "h_data VARCHAR(24) NOT NULL, request_id VARCHAR(64) NULL",
        references=(("h_c_w_id,h_c_d_id,h_c_id", "customer", "c_w_id,c_d_id,c_id"),
                    ("h_w_id,h_d_id", "district", "d_w_id,d_id")), unique=("request_id",)),
    "orders": Table(
        "o_w_id INT NOT NULL, o_d_id INT NOT NULL, o_id BIGINT NOT NULL, o_c_id INT NOT NULL, "
        "o_entry_d DATETIME NOT NULL, o_carrier_id INT NULL, o_ol_cnt INT NOT NULL, "
        "o_all_local INT NOT NULL, request_id VARCHAR(64) NULL, run_id CHAR(32) NULL",
        ("o_w_id", "o_d_id", "o_id"),
        (("o_w_id,o_d_id,o_c_id", "customer", "c_w_id,c_d_id,c_id"),),
        (("run_id",),), ("request_id",)),
    "new_order": Table(
        "no_w_id INT NOT NULL, no_d_id INT NOT NULL, no_o_id BIGINT NOT NULL, run_id CHAR(32) NULL",
        ("no_w_id", "no_d_id", "no_o_id"),
        (("no_w_id,no_d_id,no_o_id", "orders", "o_w_id,o_d_id,o_id"),), (("run_id",),)),
    "order_line": Table(
        "ol_w_id INT NOT NULL, ol_d_id INT NOT NULL, ol_o_id BIGINT NOT NULL, ol_number INT NOT NULL, "
        "ol_i_id INT NOT NULL, ol_supply_w_id INT NOT NULL, ol_delivery_d DATETIME NULL, "
        "ol_quantity INT NOT NULL, ol_amount BIGINT NOT NULL, ol_dist_info CHAR(24) NOT NULL, "
        "run_id CHAR(32) NULL",
        ("ol_w_id", "ol_d_id", "ol_o_id", "ol_number"),
        (("ol_w_id,ol_d_id,ol_o_id", "orders", "o_w_id,o_d_id,o_id"),
         ("ol_supply_w_id,ol_i_id", "stock", "s_w_id,s_i_id")), (("run_id",),)),
}


def ddl(name: str, tidb: bool) -> str:
    table = TABLES[name]
    definitions = [table.columns]
    if table.key:
        clustered = " CLUSTERED" if tidb else ""
        definitions.append(f"PRIMARY KEY ({','.join(table.key)}){clustered}")
    definitions.extend(f"UNIQUE KEY uq_{key} ({key})" for key in table.unique)
    definitions.extend(f"KEY ix_{'_'.join(index)} ({','.join(index)})" for index in table.indexes)
    definitions.extend(f"FOREIGN KEY ({source}) REFERENCES {parent} ({target})"
                       for source, parent, target in table.references)
    options = " SHARD_ROW_ID_BITS = 4 PRE_SPLIT_REGIONS = 4" if tidb and name == "history" else ""
    return f"CREATE TABLE {name} ({', '.join(definitions)}) ENGINE=InnoDB{options}"
