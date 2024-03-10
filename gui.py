import tkinter as tk
import img_formatter as imF
from tkinter import filedialog
from PIL import Image, ImageTk

window = tk.Tk()
window.geometry("800x600")
window.title("Switcher")
window.maxsize(width=800, height=600)
window.minsize(width=800, height=600)
window.configure(bg="dark grey")

current_image = None
current_mask = None

open_style = {
    "bg": "green",
    "fg": "white",
    "font": ("Helvetica", 12, "bold"),
}

save_style = {
    "bg": "orange",
    "fg": "white",
    "font": ("Helvetica", 12, "bold"),
}

button_style = {
    "bg": "grey",
    "fg": "white",
    "font": ("Helvetica", 12, "bold"),
}

def open_image_dialog():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png")])
    if file_path:
        load_and_display_image(file_path)
        
def save_image_dialog():
    file_path = filedialog.asksaveasfilename(defaultextension=".png",filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg;*.jpeg"), ("All files", "*.*")])
    if file_path:
        current_image.save(file_path)

def load_and_display_image(file_path):
    image = Image.open(file_path)
    size_label_x.config(text="Width: " + str(image.width) + "px")
    size_label_y.config(text="Height: " + str(image.height) + "px")
    x_entry.delete(0, tk.END)
    y_entry.delete(0, tk.END)
    x_entry.insert(0, str(image.width))
    y_entry.insert(0, str(image.height))
    global current_image
    current_image = image.copy()
    image.thumbnail((300, 300))
    photo = ImageTk.PhotoImage(image)
    image_label_left.config(image=photo)
    image_label_left.photo = photo
    
def display_transformed_image(input):
    thumbnail_image = input.copy()
    thumbnail_image.thumbnail((300, 300))
    photo = ImageTk.PhotoImage(thumbnail_image)
    image_label_right.config(image=photo)
    image_label_right.photo = photo
    
def reorient_image():
    global current_image
    if not seam_input.get():
        seam_size = 100
    else:
        seam_size = int(seam_input.get())
    if not outpaint_input.get():
        outpaint_size = 400
    else:
        outpaint_size = int(outpaint_input.get())
    if not seed_input.get():
        seed = -1
    else:
        seed = int(seed_input.get())
    result = imF.automatic_reorientation(current_image, prompt_input.get(), seam_size, outpaint_size, seed, auto_prompt.get())
    current_image = result
    display_transformed_image(result)

#The width and height input in the gui need to be altered to a desired new value in order to achieve any Seam-carving effect
def simple_seam_carve_image():
    global current_image
    result = imF.display_seam_carving(current_image, int(x_input.get()), int(y_input.get()), current_mask, protect_people.get())
    current_image = result
    display_transformed_image(result)

def validate_number_input(I):
    if I.isdigit() or I == "":
        return True
    else:
        return False

open_image_button = tk.Button(window, text="Open Image", command=open_image_dialog, **open_style)
open_image_button.pack(pady=10, padx=10, side=tk.TOP)

save_image_button = tk.Button(window, text="Save Image", command=save_image_dialog, **save_style)
save_image_button.place(rely=0.55, relx=0.43)

arrow_image = Image.open("Images/arr.png")
arrow_image.thumbnail((100, 100))
arrow_photo = ImageTk.PhotoImage(arrow_image)
arrow_label = tk.Label(window, image=arrow_photo)
arrow_label.image = arrow_photo
arrow_label.configure(bg="dark grey")
arrow_label.place(relx=0.43, rely=0.33)

image_label_left = tk.Label(window)
image_label_left.place(relx=0.2, rely=0.4, anchor=tk.CENTER)
image_label_left.configure(bg="dark grey")

image_label_right = tk.Label(window)
image_label_right.place(relx=0.8, rely=0.4, anchor=tk.CENTER)
image_label_right.configure(bg="dark grey")

image_label_mask = tk.Label(window)
image_label_mask.place(relx=0.95, rely=0.94, anchor=tk.CENTER)
image_label_mask.configure(bg="dark grey")

size_label_x = tk.Label(window, text="Width: ")
size_label_x.place(relx=0.06, rely=0.64, anchor=tk.CENTER)

size_label_y = tk.Label(window, text="Height: ")
size_label_y.place(relx=0.17, rely=0.64, anchor=tk.CENTER)

switch_button = tk.Button(window, text="Switch Orientation", command=lambda: reorient_image(), **button_style)
seam_carve_button = tk.Button(window, text="Seamcarve", command=lambda: simple_seam_carve_image(), **button_style)

switch_button.place(rely=0.68, relx=0.68)
seam_carve_button.place(rely=0.68, relx=0.18)

protect_people = tk.BooleanVar()
people_mask_checkbox = tk.Checkbutton(window, text="Mask people", variable=protect_people)
people_mask_checkbox.place(relx= 0.50, rely=0.90)

auto_prompt = tk.BooleanVar()
auto_prompt_checkbox = tk.Checkbutton(window, text="Use auto-prompt", variable=auto_prompt)
auto_prompt_checkbox.place(relx= 0.50, rely=0.95)

enter_x_label = tk.Label(window, text="Width: ")
enter_x_label.place(relx=0.33, rely=0.78)
x_input = tk.StringVar()
x_entry = tk.Entry(window, width=9, textvariable=x_input, validate="key", validatecommand=(window.register(validate_number_input), "%P"))
x_entry.place(relx= 0.39, rely=0.78)

enter_y_label = tk.Label(window, text="Height: ")
enter_y_label.place(relx=0.48, rely=0.78)
y_input = tk.StringVar()
y_entry = tk.Entry(window, width=9, textvariable=y_input, validate="key", validatecommand=(window.register(validate_number_input), "%P"))
y_entry.place(relx= 0.545, rely=0.78)

prompt_label = tk.Label(window, text="Prompt: ")
prompt_label.place(relx=0.20, rely=0.85)
prompt_input = tk.StringVar()
prompt_entry = tk.Entry(window, width=80, textvariable=prompt_input)
prompt_entry.place(relx=0.27, rely=0.85)

seam_amount_label = tk.Label(window, text="Seam carving size per step: ")
seam_amount_label.place(relx=0.20, rely=0.90)
seam_input = tk.StringVar()
seam_entry = tk.Entry(window, width=9, textvariable=seam_input, validate="key", validatecommand=(window.register(validate_number_input), "%P"))
seam_entry.place(relx=0.4, rely=0.90)

outpaint_amount_label = tk.Label(window, text="Outpainting size per step: ")
outpaint_amount_label.place(relx=0.20, rely=0.95)
outpaint_input = tk.StringVar()
outpaint_entry = tk.Entry(window, width=9, textvariable=outpaint_input, validate="key", validatecommand=(window.register(validate_number_input), "%P"))
outpaint_entry.place(relx=0.4, rely=0.95)

seed_label = tk.Label(window, text="Seed: ")
seed_label.place(relx=0.65, rely=0.90)
seed_input = tk.StringVar()
seed_entry = tk.Entry(window, width=9, textvariable=seed_input, validate="key", validatecommand=(window.register(validate_number_input), "%P"))
seed_entry.place(relx=0.70, rely=0.90)

window.mainloop()