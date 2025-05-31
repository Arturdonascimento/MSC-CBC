import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import struct
import hashlib
import unicodedata
from collections import Counter
import math
import os

print("Script iniciado com sucesso!")

def normalize_text(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def calculate_entropy(text):
    if not text:
        return 0.0
    counter = Counter(text)
    total = len(text)
    return -sum((count/total) * math.log2(count/total) for count in counter.values())

def calculate_faith_vector(text, n=2):
    if len(text) < n:
        return 1.0
    transitions = Counter(text[i:i+n] for i in range(len(text)-n+1))
    total = sum(transitions.values())
    p_i = [count/total for count in transitions.values()]
    return -sum(p * math.log2(p) for p in p_i if p > 0) if p_i else 1.0

def calculate_collapse_ratio(h_c, f_j):
    return h_c / f_j if f_j != 0 else h_c

def calculate_bcc_collapse(text):
    if not text:
        return 0.0
    n = len(text)
    rev_text = text[::-1]
    symmetry = sum(1 for i in range(n) if text[i] == rev_text[i]) / n
    return 1.0 - symmetry

def calculate_mgu_symmetry(ngram):
    return 1.0 / len(ngram) if ngram else 1.0

def generate_optimized_map(text, max_size=128):
    if not text:
        return []
    h_c = calculate_entropy(text)
    f_j = calculate_faith_vector(text)
    delta = calculate_collapse_ratio(h_c, f_j)
    size = min(max_size, max(42, int(len(text)**0.5 * delta)))
    ngrams = [text[i:i+2] for i in range(len(text)-1) if len(text[i:i+2]) == 2] + list(text)
    freq = Counter(ngrams)
    scored = [(ngram, count * calculate_mgu_symmetry(ngram)) for ngram, count in freq.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ngram for ngram, _ in scored[:size]]

def compress_text(original_text, symbol_map, mode):
    compressed = []
    i = 0
    while i < len(original_text):
        matched = False
        for ngram in sorted(symbol_map, key=len, reverse=True):
            if i + len(ngram) <= len(original_text) and original_text[i:i+len(ngram)] == ngram:
                compressed.append(symbol_map.index(ngram))
                i += len(ngram)
                matched = True
                break
        if not matched:
            if mode in ["CBC Híbrido", "Modo Δ-Colapso"]:
                compressed.append(0xFFFF)
                compressed.append(ord(original_text[i]))
            else:
                compressed.append(0)
            i += 1
    return compressed

def decompress_text(compressed_data, symbol_map):
    recovered = []
    i = 0
    while i < len(compressed_data):
        if compressed_data[i] == 0xFFFF and i + 1 < len(compressed_data):
            recovered.append(chr(compressed_data[i+1]))
            i += 2
        elif compressed_data[i] < len(symbol_map):
            recovered.append(symbol_map[compressed_data[i]])
            i += 1
        else:
            i += 1
    return ''.join(recovered)

def search_pattern(compressed_data, symbol_map, pattern):
    if not pattern or not compressed_data:
        return False
    pattern_delta = calculate_bcc_collapse(pattern)
    if pattern_delta < 0.3:
        return False
    resonance_step = max(1, int(len(compressed_data) * 0.1))
    pattern_ngrams = [pattern[i:i+2] for i in range(len(pattern)-1) if len(pattern[i:i+2]) == 2] + list(pattern)
    pattern_indices = []
    for ngram in pattern_ngrams:
        try:
            pattern_indices.append(symbol_map.index(ngram))
        except ValueError:
            return False
    for i in range(0, len(compressed_data) - len(pattern_indices) + 1, resonance_step):
        if compressed_data[i:i+len(pattern_indices)] == pattern_indices:
            return True
    return False

def save_compressed(file_path, compressed_data, symbol_map, original_text):
    if not original_text or not file_path:
        raise ValueError("Texto ou caminho do arquivo ausente.")
    
    normalized_text = normalize_text(original_text)
    h_c = calculate_entropy(normalized_text)
    f_j = calculate_faith_vector(normalized_text)
    delta = calculate_collapse_ratio(h_c, f_j)
    checksum = hashlib.sha512(original_text.encode('utf-8')).hexdigest()
    
    symbol_map = [str(ngram) for ngram in symbol_map if ngram and isinstance(ngram, str)]
    
    try:
        with open(file_path, 'wb') as f:
            f.write(struct.pack('>fff128s', h_c, f_j, delta, checksum.encode('utf-8')))
            f.write(struct.pack('>H', len(symbol_map)))
            for ngram in symbol_map:
                ngram_bytes = ngram.encode('utf-8')
                f.write(struct.pack('B', len(ngram_bytes)))
                f.write(ngram_bytes)
            for item in compressed_data:
                f.write(struct.pack('>H', item))
        file_size = os.path.getsize(file_path)
        if file_size < 142:
            raise IOError("Arquivo salvo com tamanho insuficiente")
    except Exception as e:
        raise IOError(f"Erro ao salvar arquivo: {str(e)}")

def load_compressed(file_path):
    try:
        file_size = os.path.getsize(file_path)
        if file_size < 142:
            raise ValueError("Arquivo corrompido: tamanho insuficiente")
        
        with open(file_path, 'rb') as f:
            header = f.read(12 + 128)
            if len(header) != 140:
                raise ValueError("Arquivo corrompido: cabeçalho incompleto")
            h_c, f_j, delta, checksum = struct.unpack('>fff128s', header)
            
            num_entries_data = f.read(2)
            if len(num_entries_data) != 2:
                raise ValueError("Arquivo corrompido: número de entradas ausente")
            num_entries = struct.unpack('>H', num_entries_data)[0]
            
            symbol_map = []
            for i in range(num_entries):
                ngram_len_data = f.read(1)
                if len(ngram_len_data) != 1:
                    raise ValueError(f"Arquivo corrompido: tamanho de n-grama ausente na entrada {i}")
                ngram_len = struct.unpack('B', ngram_len_data)[0]
                ngram_bytes = f.read(ngram_len)
                if len(ngram_bytes) != ngram_len:
                    raise ValueError(f"Arquivo corrompido: n-grama incompleto na entrada {i}, esperado {ngram_len} bytes")
                symbol_map.append(ngram_bytes.decode('utf-8', errors='replace'))
            
            compressed_data = []
            while True:
                data = f.read(2)
                if len(data) != 2:
                    break
                item = struct.unpack('>H', data)[0]
                compressed_data.append(item)
            if not compressed_data:
                raise ValueError("Arquivo corrompido: dados comprimidos ausentes")
            return compressed_data, symbol_map, h_c, f_j, delta, checksum.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Erro ao carregar arquivo: {str(e)}")

class CBCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CBC Compressor v4.10")
        self.root.geometry("600x400")
        self.file_path = None
        self.meira_protocol_active = True

        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 9))
        style.configure('TCombobox', font=('Arial', 9))

        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header = ttk.Label(main_frame, text="Sistema de Compressão Simbólica CBC/MSC v4.10", 
                          font=("Arial", 12, "bold"))
        header.pack(pady=(0, 10))

        self.text_box = tk.Text(main_frame, wrap=tk.WORD, height=12)
        self.text_box.pack(fill=tk.BOTH, expand=True, pady=5)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        self.mode_var = tk.StringVar(value="CBC Híbrido")
        mode_combo = ttk.Combobox(control_frame, textvariable=self.mode_var, 
                                 values=["CBC Puro", "CBC Híbrido", "Modo Δ-Colapso"],
                                 state="readonly", width=15)
        mode_combo.pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Selecionar Arquivo", command=self.select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Compactar", command=self.compress).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Descompactar", command=self.decompress).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Buscar Padrão", command=self.search).pack(side=tk.LEFT, padx=5)

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

    def validate_ethical_compression(self):
        prohibited_keywords = ["militar", "weapon", "arma", "guerra"]
        text = self.text_box.get(1.0, tk.END).lower()
        if any(keyword in text for keyword in prohibited_keywords):
            raise ValueError("Conteúdo militar detectado")

    def compress(self):
        if self.meira_protocol_active:
            self.validate_ethical_compression()
        original_text = self.text_box.get(1.0, tk.END).strip()
        if not original_text:
            messagebox.showwarning("Aviso", "Nenhum texto para compactar.")
            return

        mode = self.mode_var.get()
        self.status_var.set(f"Compactando em modo {mode}...")

        try:
            normalized_text = normalize_text(original_text)
            symbol_map = (generate_optimized_map(normalized_text) 
                          if mode == "CBC Puro" or mode == "Modo Δ-Colapso" 
                          else default_symbol_map)
            compressed = compress_text(original_text, symbol_map, mode)

            save_path = filedialog.asksaveasfilename(
                defaultextension=".cbc",
                filetypes=[("CBC Files", "*.cbc")]
            )

            if save_path:
                save_compressed(save_path, compressed, symbol_map, original_text)
                h_c = calculate_entropy(normalized_text)
                f_j = calculate_faith_vector(normalized_text)
                delta = calculate_collapse_ratio(h_c, f_j)
                bcc_collapse = calculate_bcc_collapse(normalized_text)
                self.status_var.set(f"Compactação concluída! H_C={h_c:.2f}, F_j={f_j:.2f}, Δ={delta:.2f}, Δ_b={bcc_collapse:.2f}")
                messagebox.showinfo("Sucesso", "Texto compactado com sucesso!")
            else:
                self.status_var.set("Compactação cancelada.")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na compactação: {str(e)}")
            self.status_var.set("Erro na compactação")

    def decompress(self):
        if not self.file_path or not self.file_path.endswith(".cbc"):
            messagebox.showwarning("Aviso", "Selecione um arquivo .cbc para descompactar.")
            return

        self.status_var.set("Descompactando...")

        try:
            compressed_data, symbol_map, h_c, f_j, delta, original_checksum = load_compressed(self.file_path)
            recovered_text = decompress_text(compressed_data, symbol_map)
            recovered_checksum = hashlib.sha512(recovered_text.encode('utf-8')).hexdigest()

            if recovered_checksum != original_checksum:
                messagebox.showerror("Erro", f"Falha na validação do checksum! Original: {original_checksum}, Recuperado: {recovered_checksum}")
                return

            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, recovered_text)
            self.status_var.set(f"Descompactação concluída! H_C={h_c:.2f}, F_j={f_j:.2f}, Δ={delta:.2f}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na descompactação: {str(e)}")
            self.status_var.set("Erro na descompactação")

    def search(self):
        pattern = self.text_box.get(1.0, tk.END).strip()
        if not pattern:
            messagebox.showwarning("Aviso", "Digite um padrão para buscar.")
            return

        if not self.file_path or not self.file_path.endswith(".cbc"):
            messagebox.showwarning("Aviso", "Selecione um arquivo .cbc para busca.")
            return

        try:
            compressed_data, symbol_map, _, _, _, _ = load_compressed(self.file_path)
            found = search_pattern(compressed_data, symbol_map, pattern)
            messagebox.showinfo("Resultado", f"Padrão {'encontrado' if found else 'não encontrado'}!")
            self.status_var.set("Busca concluída.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca: {str(e)}")
            self.status_var.set("Erro na busca")

default_symbol_map = list(" aãáàâbcçdeéêfghiíjklmnoóôõpqrstuúüvwxyz,.;!?()'-0123456789")

if __name__ == "__main__":
    root = tk.Tk()
    app = CBCApp(root)
    root.mainloop()