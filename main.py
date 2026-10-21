
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_NAME = "inventory.db"


# ---------------- DATABASE ----------------

def connect_db():
    return sqlite3.connect(DB_NAME)


# ---------------- LOAD PRODUCTS ----------------

def load_products(search_text=""):
    for item in product_table.get_children():
        product_table.delete(item)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_id, product_name, quantity, price, reorder_level
        FROM products
        WHERE product_name LIKE ?
        ORDER BY product_id ASC
    """, (f"%{search_text}%",))

    rows = cursor.fetchall()
    conn.close()



    for display_id, (pid, name, qty, price, level) in enumerate(rows, start=1):

        if qty == 0:
            status = "OUT OF STOCK"
            tag = "out"
        elif qty <= level:
            status = "LOW STOCK"
            tag = "low"
        else:
            status = "IN STOCK"
            tag = "normal"

        
    
        product_table.insert(
            "",
            "end",
            iid=str(pid),
            values=(
                display_id,
                name,
                qty,
                f"{price:.2f}",
                level,
                status
            ),
            tags=(tag,)
        )


# ---------------- SELECT PRODUCT ----------------

def select_product(event=None):
    selected = product_table.selection()

    if not selected:
        return

    row = product_table.item(selected[0], "values")

    name_entry.delete(0, tk.END)
    quantity_entry.delete(0, tk.END)
    price_entry.delete(0, tk.END)
    level_entry.delete(0, tk.END)

    name_entry.insert(0, row[1])
    quantity_entry.insert(0, row[2])
    price_entry.insert(0, row[3])
    level_entry.insert(0, row[4])


def get_selected_product_id():
    selected = product_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Product",
            "Please select a product row from the table."
        )
        return None

    # Return the real database ID, not the displayed ID.
    return int(selected[0])


# ---------------- FORM VALIDATION ----------------

def get_form_values():
    name = name_entry.get().strip()

    if not name:
        messagebox.showwarning("Validation", "Enter product name.")
        return None

    try:
        qty = int(quantity_entry.get())
        price = float(price_entry.get())
        level = int(level_entry.get())

        if qty < 0 or price <= 0 or level < 0:
            raise ValueError

    except ValueError:
        messagebox.showwarning(
            "Validation",
            "Quantity and alert level must be 0 or more. "
            "Price must be greater than 0."
        )
        return None

    return name, qty, price, level


# ---------------- CLEAR FORM ----------------

def clear_fields():
    name_entry.delete(0, tk.END)
    quantity_entry.delete(0, tk.END)
    price_entry.delete(0, tk.END)
    level_entry.delete(0, tk.END)
    level_entry.insert(0, "5")

    for item in product_table.selection():
        product_table.selection_remove(item)


# ---------------- ADD PRODUCT ----------------

def add_product():
    values = get_form_values()

    if values is None:
        return

    name, qty, price, level = values

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO products
            (product_name, quantity, price, reorder_level)
            VALUES (?, ?, ?, ?)
        """, (name, qty, price, level))

        pid = cursor.lastrowid

        if qty > 0:
            cursor.execute("""
                INSERT INTO stock_history
                (product_id, movement_type, quantity)
                VALUES (?, 'INITIAL STOCK', ?)
            """, (pid, qty))

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        messagebox.showerror("Database Error", str(error))
        return

    finally:
        conn.close()

    load_products(search_entry.get())
    clear_fields()
    messagebox.showinfo("Success", "Product added successfully!")


# ---------------- UPDATE PRODUCT ----------------

def update_product():
    pid = get_selected_product_id()

    if pid is None:
        return

    values = get_form_values()

    if values is None:
        return

    name, qty, price, level = values

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE products
            SET product_name = ?,
                quantity = ?,
                price = ?,
                reorder_level = ?
            WHERE product_id = ?
        """, (name, qty, price, level, pid))

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        messagebox.showerror("Database Error", str(error))
        return

    finally:
        conn.close()

    load_products(search_entry.get())
    clear_fields()
    messagebox.showinfo("Success", "Product updated successfully!")


# ---------------- DELETE PRODUCT ----------------

def delete_product():
    pid = get_selected_product_id()

    if pid is None:
        return

    if not messagebox.askyesno(
        "Confirm Delete",
        "Delete this product and its stock history?"
    ):
        return

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM stock_history WHERE product_id = ?",
            (pid,)
        )
        cursor.execute(
            "DELETE FROM products WHERE product_id = ?",
            (pid,)
        )

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        messagebox.showerror("Database Error", str(error))
        return

    finally:
        conn.close()

    load_products(search_entry.get())
    clear_fields()
    messagebox.showinfo("Deleted", "Product deleted successfully.")


# ---------------- STOCK IN / STOCK OUT ----------------

def change_stock(movement_type):
    pid = get_selected_product_id()

    if pid is None:
        return

    try:
        amount = int(stock_amount_entry.get())

        if amount <= 0:
            raise ValueError

    except ValueError:
        messagebox.showwarning(
            "Invalid Quantity",
            "Enter a whole number greater than zero."
        )
        return

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT quantity, reorder_level
            FROM products
            WHERE product_id = ?
        """, (pid,))

        product = cursor.fetchone()

        if product is None:
            messagebox.showerror("Error", "Product not found.")
            return

        current_qty, alert_level = product

        if movement_type == "STOCK OUT":
            if amount > current_qty:
                messagebox.showerror(
                    "Insufficient Stock",
                    f"Available stock: {current_qty}"
                )
                return

            new_qty = current_qty - amount
        else:
            new_qty = current_qty + amount

        cursor.execute("""
            UPDATE products
            SET quantity = ?
            WHERE product_id = ?
        """, (new_qty, pid))

        cursor.execute("""
            INSERT INTO stock_history
            (product_id, movement_type, quantity)
            VALUES (?, ?, ?)
        """, (pid, movement_type, amount))

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        messagebox.showerror("Database Error", str(error))
        return

    finally:
        conn.close()

    load_products(search_entry.get())

    # Reselect the same product using its real database ID.
    if product_table.exists(str(pid)):
        product_table.selection_set(str(pid))
        product_table.focus(str(pid))
        product_table.see(str(pid))
        select_product()

    stock_amount_entry.delete(0, tk.END)

    if new_qty == 0:
        messagebox.showwarning(
            "Out of Stock",
            "Stock is now zero!"
        )
    elif new_qty <= alert_level:
        messagebox.showwarning(
            "Low Stock",
            f"Only {new_qty} units remaining."
        )
    else:
        messagebox.showinfo(
            "Success",
            f"{movement_type} completed!\n"
            f"Remaining stock: {new_qty}"
        )


# ---------------- LOW STOCK ALERT ----------------

def check_low_stock():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_name, quantity, reorder_level
        FROM products
        WHERE quantity <= reorder_level
        ORDER BY quantity
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        messagebox.showinfo(
            "Stock Alert",
            "No low-stock products."
        )
        return

    details = "\n".join(
        f"{name}: {qty} left (alert level: {level})"
        for name, qty, level in rows
    )

    messagebox.showwarning("Low Stock Alert", details)


# ---------------- STOCK HISTORY ----------------

def show_history():
    window = tk.Toplevel(root)
    window.title("Stock Movement History")
    window.geometry("750x350")

    columns = ("ID", "Product", "Movement", "Quantity", "Date")

    history_table = ttk.Treeview(
        window,
        columns=columns,
        show="headings"
    )

    for column in columns:
        history_table.heading(column, text=column)
        history_table.column(column, width=140, anchor="center")

    scrollbar = ttk.Scrollbar(
        window,
        orient="vertical",
        command=history_table.yview
    )

    history_table.configure(yscrollcommand=scrollbar.set)

    history_table.pack(
        side="left", fill="both", expand=True, padx=(10, 0), pady=10
    )
    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT h.history_id,
               p.product_name,
               h.movement_type,
               h.quantity,
               h.movement_date
        FROM stock_history h
        JOIN products p ON p.product_id = h.product_id
        ORDER BY h.history_id DESC
    """)

    for record in cursor.fetchall():
        history_table.insert("", "end", values=record)

    conn.close()


# ---------------- SEARCH ----------------

def search_products():
    load_products(search_entry.get().strip())


def show_all_products():
    search_entry.delete(0, tk.END)
    load_products()


# ---------------- MAIN WINDOW ----------------

root = tk.Tk()
root.title("Smart Inventory Management System")
root.geometry("1100x700")
root.minsize(900, 600)

tk.Label(
    root,
    text="Smart Inventory Management System",
    font=("Arial", 20, "bold")
).pack(pady=12)


# Product form
form = tk.Frame(root)
form.pack(pady=5)

tk.Label(form, text="Product Name").grid(
    row=0, column=0, padx=5, pady=5
)
name_entry = tk.Entry(form, width=20)
name_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(form, text="Quantity").grid(
    row=0, column=2, padx=5, pady=5
)
quantity_entry = tk.Entry(form, width=12)
quantity_entry.grid(row=0, column=3, padx=5, pady=5)

tk.Label(form, text="Price").grid(
    row=1, column=0, padx=5, pady=5
)
price_entry = tk.Entry(form, width=20)
price_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(form, text="Alert Level").grid(
    row=1, column=2, padx=5, pady=5
)
level_entry = tk.Entry(form, width=12)
level_entry.grid(row=1, column=3, padx=5, pady=5)
level_entry.insert(0, "5")


# Product buttons
buttons = tk.Frame(root)
buttons.pack(pady=8)

tk.Button(
    buttons, text="Add Product", command=add_product
).grid(row=0, column=0, padx=4, pady=4)

tk.Button(
    buttons, text="Update Details", command=update_product
).grid(row=0, column=1, padx=4, pady=4)

tk.Button(
    buttons, text="Delete Product", command=delete_product
).grid(row=0, column=2, padx=4, pady=4)

tk.Button(
    buttons, text="Clear Fields", command=clear_fields
).grid(row=0, column=3, padx=4, pady=4)

tk.Button(
    buttons, text="Low Stock Alert", command=check_low_stock
).grid(row=0, column=4, padx=4, pady=4)

tk.Button(
    buttons, text="Stock History", command=show_history
).grid(row=0, column=5, padx=4, pady=4)


# Stock controls
stock_frame = tk.Frame(root)
stock_frame.pack(pady=5)

tk.Label(stock_frame, text="Stock Quantity:").grid(
    row=0, column=0, padx=5
)

stock_amount_entry = tk.Entry(stock_frame, width=12)
stock_amount_entry.grid(row=0, column=1, padx=5)

tk.Button(
    stock_frame,
    text="Stock In (+)",
    command=lambda: change_stock("STOCK IN")
).grid(row=0, column=2, padx=5)

tk.Button(
    stock_frame,
    text="Stock Out / Sell (-)",
    command=lambda: change_stock("STOCK OUT")
).grid(row=0, column=3, padx=5)


# Search controls
search_frame = tk.Frame(root)
search_frame.pack(pady=8)

tk.Label(search_frame, text="Search Product:").grid(
    row=0, column=0, padx=5
)

search_entry = tk.Entry(search_frame, width=25)
search_entry.grid(row=0, column=1, padx=5)

tk.Button(
    search_frame,
    text="Search",
    command=search_products
).grid(row=0, column=2, padx=5)

tk.Button(
    search_frame,
    text="Show All",
    command=show_all_products
).grid(row=0, column=3, padx=5)


# Product table
table_frame = tk.Frame(root)
table_frame.pack(fill="both", expand=True, padx=12, pady=10)

columns = (
    "ID", "Name", "Quantity", "Price", "Alert Level", "Status"
)

product_table = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings",
    selectmode="browse"
)

for column in columns:
    product_table.heading(column, text=column)
    product_table.column(column, width=150, anchor="center")

# Color coding for stock status
product_table.tag_configure(
    "out",
    background="#cc0000",
    foreground="white"
)

product_table.tag_configure(
    "low",
    background="#ff9999",
    foreground="black"
)

product_table.tag_configure(
    "normal",
    background="#d9f2d9",
    foreground="black"
)

scrollbar = ttk.Scrollbar(
    table_frame,
    orient="vertical",
    command=product_table.yview
)

product_table.configure(yscrollcommand=scrollbar.set)

product_table.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

product_table.bind("<<TreeviewSelect>>", select_product)

load_products()
root.mainloop()
