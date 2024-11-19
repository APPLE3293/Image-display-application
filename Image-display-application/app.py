import tkinter as tk
from tkinter import filedialog, Toplevel
from PIL import Image, ImageTk
import threading
import json
import os
import queue

class ImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片展示应用")
        self.root.geometry("1000x700")

        self.images = []
        self.image_labels = []
        self.image_paths = []
        self.image_cache = {}

        self.canvas = tk.Canvas(self.root)
        self.frame = tk.Frame(self.canvas)
        self.scroll_y = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.scroll_y.pack(side="right", fill="y")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), anchor="nw", window=self.frame)
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.button = tk.Button(self.root, text="加载图片", command=self.load_images)
        self.button.pack(pady=20)

        self.queue = queue.Queue()
        self.root.after(100, self.process_queue)

        self.load_saved_images()

    def load_images(self):
        file_paths = filedialog.askopenfilenames()
        if file_paths:
            threading.Thread(target=self.add_images, args=(file_paths,)).start()

    def add_images(self, file_paths):
        for file_path in file_paths:
            self.queue.put(lambda p=file_path: self.add_image(p))
            self.image_paths.append(file_path)
            self.save_image_paths()

    def add_image(self, file_path):
        if file_path in self.image_cache:
            img_tk = self.image_cache[file_path]
        else:
            try:
                img = Image.open(file_path)
                img = img.resize((300, 200), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                self.image_cache[file_path] = img_tk
            except Exception as e:
                print(f"加载图片失败: {e}")
                return

        self.queue.put(lambda: self.create_image_label(img_tk, file_path))

    def create_image_label(self, img_tk, file_path):
        row, col = divmod(len(self.image_labels), 5)
        label_frame = tk.Frame(self.frame)
        label_frame.grid(row=row, column=col, padx=10, pady=10)

        label = tk.Label(label_frame, image=img_tk)
        label.image = img_tk
        label.pack()

        delete_button = tk.Button(label_frame, text="删除", command=lambda: self.delete_image(file_path, label_frame))
        delete_button.pack()

        label.bind("<Button-1>", lambda e, p=file_path: self.image_clicked(p))
        self.images.append(img_tk)
        self.image_labels.append(label)

    def delete_image(self, file_path, label_frame):
        label_frame.destroy()
        index = self.image_paths.index(file_path)
        del self.images[index]
        del self.image_labels[index]
        self.image_paths.remove(file_path)
        self.save_image_paths()

    def image_clicked(self, file_path):
        top = Toplevel(self.root)
        top.title("放大图片")
        img = Image.open(file_path)
        img_tk = ImageTk.PhotoImage(img)

        canvas = tk.Canvas(top)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.img = img_tk
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)

        self.current_img = img
        self.scale_factor = 1.0

        def zoom(event):
            if event.delta > 0:
                self.scale_factor *= 1.1
            else:
                self.scale_factor /= 1.1

            width, height = int(self.current_img.width * self.scale_factor), int(self.current_img.height * self.scale_factor)
            img_resized = self.current_img.resize((width, height), Image.LANCZOS)
            img_tk_resized = ImageTk.PhotoImage(img_resized)

            canvas.img = img_tk_resized
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=img_tk_resized)

        def pan_start(event):
            canvas.scan_mark(event.x, event.y)

        def pan_move(event):
            canvas.scan_dragto(event.x, event.y, gain=1)

        canvas.bind("<MouseWheel>", zoom)
        canvas.bind("<ButtonPress-1>", pan_start)
        canvas.bind("<B1-Motion>", pan_move)

    def save_image_paths(self):
        with open("image_paths.json", "w") as f:
            json.dump(self.image_paths, f)

    def load_saved_images(self):
        if os.path.exists("image_paths.json"):
            with open("image_paths.json", "r") as f:
                self.image_paths = json.load(f)
            for file_path in self.image_paths:
                self.queue.put(lambda p=file_path: self.add_image(p))

    def process_queue(self):
        while not self.queue.empty():
            task = self.queue.get()
            task()
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root)
    root.mainloop()
