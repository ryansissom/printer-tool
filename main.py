import tkinter as tk
from tkinter import ttk
import requests
import win32print
from label_generator import (create_1x4_shelf_label, create_2x4_shelf_label, create_1x2_product_label, generate_codes,
                             create_1x3_product_label)
import pandas as pd
import os
import sys
import ctypes

# Handle paths dynamically based on how the script is run
if hasattr(sys, '_MEIPASS'):  # When running as .exe
    base_path = sys._MEIPASS  # Temporary folder
else:  # When running as a normal Python script
    base_path = os.path.abspath(".")




# Full path to the data file
data_file = os.path.join(base_path, "data.csv")

# Get the user's desktop path dynamically
# desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
# csv_folder = os.path.join(desktop_path, "Printer Program Files")
data = data_file
# Load the CSV file
df = pd.read_csv(data)
products_ids = sorted(df['Part ID'].dropna().astype(int).unique().tolist())
branches = df['Store Name'].dropna().unique().tolist()


def get_printers():
    """Fetch the list of installed printers."""
    return [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]

def send_to_printer(printer_name, zpl_file):
    """Send the ZPL file to the selected printer."""
    try:
        with open(zpl_file, "r") as file:
            zpl_data = file.read()

        # Open the printer
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            # Start a print job
            job = win32print.StartDocPrinter(hprinter, 1, ("Label Print Job", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, zpl_data.encode("utf-8"))
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

        print(f"ZPL sent to printer: {printer_name}")
    except Exception as e:
        print(f"Failed to send to printer: {e}")
def convert_to_zpl(png_file):
    """Send the PNG to the Labelary API and save the ZPL output."""
    url = "http://api.labelary.com/v1/graphics"
    try:
        with open(png_file, 'rb') as file:
            files = {'file': file}
            response = requests.post(url, files=files)

        if response.status_code == 200:
            zpl_file = png_file.replace(".png", ".zpl")
            with open(zpl_file, "w") as f:
                f.write(response.text)
            print(f"ZPL saved to {zpl_file}")
            return zpl_file
        else:
            print("Error:", response.status_code, response.text)
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def generate_labels():
    """Generate labels dynamically with a button click."""
    # Get user input
    po_number = po_entry.get()  # Unused for now
    product_number = product_combo.get()
    manufacturer_number = manufacturer_entry.get()
    bin_location = bin_combo.get()
    description = description_entry.get()
    manufacturer = provider_entry.get()
    num_copies = int(copies_combo.get())  # Get the number of copies

    label_file = None  # Initialize to handle cleanup properly
    zpl_file = None

    try:
        # Determine selected label type
        selected_label = label_var.get()
        if selected_label == "1x2":
            label_file = create_1x2_product_label(
                qr_data=manufacturer_number,
                barcode_data=product_number,
                description=description,
                bin_location=bin_location,
                product_code=product_number,
                title=manufacturer
            )
        elif selected_label == "1x3":
            label_file = create_1x3_product_label(
                qr_data=manufacturer_number,
                barcode_data=product_number,
                description=description,
                bin_location=bin_location,
                product_code=product_number,
                title=manufacturer
            )
        elif selected_label == "1x4":
            label_file = create_1x4_shelf_label(
                bin_location=bin_location,
                title="EquipmentShare"
            )
        elif selected_label == "2x4":
            label_file = create_2x4_shelf_label(
                bin_location=bin_location,
                title="EquipmentShare"
            )
        else:
            print("No label type selected.")
            return

        print(f"Label saved to temporary file: {label_file}")

        # Convert the generated file to ZPL
        zpl_file = convert_to_zpl(label_file)

        # Send the ZPL to the selected printer
        selected_printer = printer_combo.get()
        if selected_printer:
            for _ in range(num_copies):  # Print the label `num_copies` times
                send_to_printer(selected_printer, zpl_file)
        else:
            print("No printer selected.")
    finally:
        # Cleanup temporary files
        try:
            if label_file and os.path.exists(label_file):
                os.remove(label_file)
            if zpl_file and os.path.exists(zpl_file):
                os.remove(zpl_file)
            print("Temporary files cleaned up.")
        except Exception as e:
            print(f"Error during cleanup: {e}")



def filter_autocomplete(event):
    """Filter the dropdown options and keep the dropdown open."""
    typed_text = product_combo.get()  # Get the current input
    if typed_text == "":
        # Show all options if the input is empty
        product_combo['values'] = products_ids
    else:
        # Filter options that start with the typed text
        filtered = [item for item in products_ids if str(item).startswith(typed_text)]
        product_combo['values'] = filtered

def populate_fields():
    """Populate Manufacturer part number, Description, and Provider based on Product Number."""
    selected_product = product_combo.get()
    if selected_product:
        try:
            # Filter the dataframe for the selected product
            product_data = df[df['Part ID'] == int(selected_product)]

            if not product_data.empty:
                # Extract Manufacturer Number, Description, and Provider
                manufacturer_number = product_data['Part Number'].values[0] if 'Part Number' in product_data else ""
                description = product_data['Description'].values[0] if 'Description' in product_data else ""
                provider = product_data['Provider'].values[0] if 'Provider' in product_data else ""

                # Populate the Manufacturer field
                manufacturer_entry.delete(0, tk.END)
                manufacturer_entry.insert(0, manufacturer_number if pd.notna(manufacturer_number) else "")

                # Populate the Description field
                description_entry.delete(0, tk.END)
                description_entry.insert(0, description if pd.notna(description) else "")

                # Populate the Provider field
                provider_entry.delete(0, tk.END)
                provider_entry.insert(0, provider if pd.notna(provider) else "")
            else:
                # Clear fields if no matching product is found
                manufacturer_entry.delete(0, tk.END)
                description_entry.delete(0, tk.END)
                provider_entry.delete(0, tk.END)
        except ValueError:
            print("Invalid product ID format.")
    else:
        # Clear fields if the product combo is empty
        manufacturer_entry.delete(0, tk.END)
        description_entry.delete(0, tk.END)
        provider_entry.delete(0, tk.END)


def filter_bin_locations(event):
    """Filter bin locations based on user input."""
    typed_text = bin_combo.get()  # Get the current input
    selected_branch = branch_combo.get()

    if selected_branch:
        # Filter bins for the selected branch
        branch_bins = df[df['Store Name'] == selected_branch]['Bin Location'].dropna().unique().tolist()
    else:
        branch_bins = []  # Default to an empty list if no branch is selected

    if typed_text == "":
        # Show all bins if input is empty
        bin_combo['values'] = branch_bins
    else:
        # Filter options based on typed text
        filtered_bins = [bin for bin in branch_bins if bin.lower().startswith(typed_text.lower())]
        bin_combo['values'] = filtered_bins

def update_bin_locations(event):
    """Update Bin Location dropdown based on selected Branch Location."""
    selected_branch = branch_combo.get()
    if selected_branch:
        # Filter the dataframe for the selected branch
        branch_data = df[df['Store Name'] == selected_branch]

        if not branch_data.empty:
            # Get unique bin locations for the branch
            bin_locations = branch_data['Bin Location'].dropna().unique().tolist()
            bin_combo['values'] = sorted(bin_locations)  # Update dropdown
            if bin_locations:
                bin_combo.set(bin_locations[0])  # Set the first value as default
        else:
            bin_combo['values'] = []  # Clear dropdown if no bins found
            bin_combo.set("")  # Clear the current selection

LARGE_FONT = ("Arial", 12)  # Adjust size as needed
# Initialize Tkinter
root = tk.Tk()
root.title("Label Generator")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = int(screen_width * 0.5)  # 50% of screen width
window_height = int(screen_height * 0.5)  # 50% of screen height
root.geometry(f"{window_width}x{window_height}")
# Create a Canvas and a Scrollbar
canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

# Configure Canvas and Scrollbar
canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

# Create a window within the Canvas to hold the scrollable frame
canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_frame_configure(event):
    """Adjust the scroll region to include the entire scrollable frame."""
    canvas.configure(scrollregion=canvas.bbox("all"))

# Bind the frame resize event to adjust the canvas scroll region
scrollable_frame.bind("<Configure>", on_frame_configure)


# Create Left and Right Frames
left_frame = tk.Frame(scrollable_frame, width=400)
left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

right_frame = tk.Frame(scrollable_frame, width=400)
right_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

third_frame = tk.Frame(scrollable_frame, width=400)
third_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

# Left Frame Content
branch_label = tk.Label(left_frame, text="Select Branch:", font=LARGE_FONT)
branch_label.pack(pady=10, anchor="w")
branch_combo = ttk.Combobox(left_frame, values=branches, state="readonly", width=30, font=LARGE_FONT)
branch_combo.pack(pady=10, ipady=5)
branch_combo.current(0)
branch_combo.bind("<<ComboboxSelected>>", update_bin_locations)

product_label = tk.Label(left_frame, text="Product Number:", font=LARGE_FONT)
product_label.pack(pady=10, anchor="w")
product_combo = ttk.Combobox(left_frame, values=products_ids, state="normal", width=28, font=LARGE_FONT)
product_combo.pack(pady=10, ipady=5)
product_combo.focus()
product_combo.bind("<KeyRelease>", filter_autocomplete)

bin_label = tk.Label(left_frame, text="Bin Location:", font=LARGE_FONT)
bin_label.pack(pady=10, anchor="w")
bin_combo = ttk.Combobox(left_frame, state="normal", width=30, font=LARGE_FONT)
bin_combo.pack(pady=10, ipady=5)
bin_combo.set("")
bin_combo.bind("<KeyRelease>", filter_bin_locations)

po_label = tk.Label(left_frame, text="PO Number:", font=LARGE_FONT)
po_label.pack(pady=10, anchor="w")
po_entry = tk.Entry(left_frame, width=30, font=LARGE_FONT)
po_entry.pack(pady=10, ipady=5)

populate_button = tk.Button(left_frame, text="Auto-Fill Fields", command=populate_fields, font=LARGE_FONT)
populate_button.pack(pady=10)

# Right Frame Content
provider_label = tk.Label(right_frame, text="Provider:", font=LARGE_FONT)
provider_label.pack(pady=10, anchor="w")
provider_entry = tk.Entry(right_frame, width=30, font=LARGE_FONT)
provider_entry.pack(pady=10, ipady=5)

manufacturer_label = tk.Label(right_frame, text="Manufacturer Number:", font=LARGE_FONT)
manufacturer_label.pack(pady=10, anchor="w")
manufacturer_entry = tk.Entry(right_frame, width=30, font=LARGE_FONT)
manufacturer_entry.pack(pady=10, ipady=5)

description_label = tk.Label(right_frame, text="Description:", font=LARGE_FONT)
description_label.pack(pady=10, anchor="w")
description_entry = tk.Entry(right_frame, width=50, font=LARGE_FONT)
description_entry.pack(pady=10, ipady=5)

tk.Label(third_frame, text="Select Printer:", font=LARGE_FONT).pack(pady=10, anchor="w")
printers = get_printers()
printer_combo = ttk.Combobox(third_frame, values=printers, state="readonly", width=20, font=LARGE_FONT)
printer_combo.pack(pady=10, ipady=5)
printer_combo.current(0)

label_var = tk.StringVar(value="None")
tk.Label(third_frame, text="Select Label Type:", font=LARGE_FONT).pack(anchor="w")
tk.Radiobutton(third_frame, text="Product Label 1x2", variable=label_var, value="1x2", font=LARGE_FONT).pack(anchor="w", padx=20)
tk.Radiobutton(third_frame, text="Product Label 1x3", variable=label_var, value="1x3", font=LARGE_FONT).pack(anchor="w", padx=20)
tk.Radiobutton(third_frame, text="Shelf Label 1x4", variable=label_var, value="1x4", font=LARGE_FONT).pack(anchor="w", padx=20)
tk.Radiobutton(third_frame, text="Shelf Label 2x4", variable=label_var, value="2x4", font=LARGE_FONT).pack(anchor="w", padx=20)

# Add a label for the number of copies
copies_label = tk.Label(third_frame, text="Number of Copies:", font=LARGE_FONT)
copies_label.pack(anchor="w", padx=10, pady=10)
copies_combo = ttk.Combobox(third_frame, values=list(range(1, 11)), state="readonly", width=5, font=LARGE_FONT)
copies_combo.pack(anchor="w", padx=10, pady=10)
copies_combo.current(0)
# Blank for possible reason to print button

generate_button = tk.Button(third_frame, text="Generate and Print Label", command=generate_labels, font=LARGE_FONT)
generate_button.pack(pady=20)

root.mainloop()
