
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
from collections import Counter
import unicodedata
import os

def normalize_text(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text) 
                   if unicodedata.category(c) != 'Mn')

def generate_optimized_map(text, size=42):
    freq = Counter(text)
    return [char for char, _ in freq.most_common(size)]

def compress_text(text, symbol_map, mode):
    compressed = []
    for c in text:
        if c in symbol_map:
            compressed.append(symbol_map.index(c))
        elif mode == "CBC Híbrido":
            compressed.append(f'CHAR:{ord(c)}')
    return compressed

def decompress_text(compressed_data, symbol_map):
    recovered = []
    for item in compressed_data:
        if isinstance(item, int) and item < len(symbol_map):
            recovered.append(symbol_map[item])
        elif isinstance(item, str) and item.startswith('CHAR:'):
            char_code = int(item.split(':')[1])
            recovered.append(chr(char_code))
    return ''.join(recovered)

def save_compressed(file_path, compressed_data, symbol_map):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({
            "compressed": compressed_data,
            "symbol_map": symbol_map
        }, f, ensure_ascii=False)

def load_compressed(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["compressed"], data["symbol_map"]

class CBCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CBC Compressor v3.3")
        self.root.geometry("600x400")
        self.file_path = None

        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 9))
        style.configure('TCombobox', font=('Arial', 9))

        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header = ttk.Label(main_frame, text="Sistema de Compressão Simbólica CBC/MSC", 
                          font=("Arial", 12, "bold"))
        header.pack(pady=(0, 10))

        self.text_box = tk.Text(main_frame, wrap=tk.WORD, height=12)
        self.text_box.pack(fill=tk.BOTH, expand=True, pady=5)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        self.mode_var = tk.StringVar(value="CBC Híbrido")
        mode_combo = ttk.Combobox(control_frame, textvariable=self.mode_var, 
                                 values=["CBC Puro", "CBC Híbrido"], state="readonly", width=15)
        mode_combo.pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Selecionar Arquivo", command=self.select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Compactar", command=self.compress).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Descompactar", command=self.decompress).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[
            ("Text files", "*.txt"), 
            ("CBC files", "*.cbc")
        ])
        if not self.file_path:
            return

        self.status_var.set(f"Arquivo selecionado: {os.path.basename(self.file_path)}")

        if self.file_path.endswith(".txt"):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_box.delete(1.0, tk.END)
                self.text_box.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao ler arquivo: {str(e)}")

    def compress(self):
        text = self.text_box.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Aviso", "Nenhum texto para compactar.")
            return

        mode = self.mode_var.get()
        self.status_var.set(f"Compactando em modo {mode}...")

        try:
            normalized_text = normalize_text(text)
            symbol_map = (generate_optimized_map(normalized_text) 
                          if mode == "CBC Puro" 
                          else default_symbol_map)

            compressed = compress_text(normalized_text, symbol_map, mode)

            save_path = filedialog.asksaveasfilename(
                defaultextension=".cbc",
                filetypes=[("CBC Files", "*.cbc")]
            )

            if save_path:
                save_compressed(save_path, compressed, symbol_map)
                self.status_var.set(f"Compactação concluída! Tamanho: {len(compressed)} elementos")
                messagebox.showinfo("Sucesso", "Texto compactado com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na compactação: {str(e)}")
            self.status_var.set("Erro na compactação")

    def decompress(self):
        if not self.file_path or not self.file_path.endswith(".cbc"):
            messagebox.showwarning("Aviso", "Selecione um arquivo .cbc para descompactar.")
            return

        self.status_var.set("Descompactando...")

        try:
            compressed_data, symbol_map = load_compressed(self.file_path)
            recovered_text = decompress_text(compressed_data, symbol_map)

            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, recovered_text)
            self.status_var.set("Descompactação concluída com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na descompactação: {str(e)}")
            self.status_var.set("Erro na descompactação")

# Mapa simbólico padrão otimizado para português
default_symbol_map = list(" aãáàâbcçdeéêfghiíjklmnoóôõpqrstuúüvwxyz,.;!?()'-0123456789")

if __name__ == "__main__":
    root = tk.Tk()
    app = CBCApp(root)
    root.mainloop()
