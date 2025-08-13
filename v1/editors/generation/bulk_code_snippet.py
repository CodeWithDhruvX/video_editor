import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import re
from pathlib import Path

class CodeSnippetGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Snippet Folder Generator")
        self.root.geometry("800x700")
        
        # Configure style
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Generate.TButton', font=('Arial', 10, 'bold'))
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="📁 Code Snippet Folder Generator", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input method selection
        input_frame = ttk.LabelFrame(main_frame, text="Input Method", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        self.input_method = tk.StringVar(value="text")
        
        ttk.Radiobutton(input_frame, text="Paste JSON Text", variable=self.input_method, 
                       value="text", command=self.toggle_input_method).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(input_frame, text="Load JSON File", variable=self.input_method, 
                       value="file", command=self.toggle_input_method).grid(row=0, column=1, sticky=tk.W)
        
        # File selection frame
        self.file_frame = ttk.Frame(input_frame)
        self.file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.file_frame.columnconfigure(0, weight=1)
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, state="disabled")
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(self.file_frame, text="Browse", 
                                       command=self.browse_file, state="disabled")
        self.browse_button.grid(row=0, column=1)
        
        # JSON input text area
        json_frame = ttk.LabelFrame(main_frame, text="JSON Input", padding="10")
        json_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        json_frame.columnconfigure(0, weight=1)
        json_frame.rowconfigure(0, weight=1)
        
        self.json_text = scrolledtext.ScrolledText(json_frame, height=15, width=70)
        self.json_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Starting number
        ttk.Label(settings_frame, text="Starting Number:").grid(row=0, column=0, sticky=tk.W)
        self.start_number = tk.IntVar(value=1)
        start_spinbox = ttk.Spinbox(settings_frame, from_=1, to=999, width=10, 
                                   textvariable=self.start_number)
        start_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        # Output folder
        ttk.Label(settings_frame, text="Output Folder:").grid(row=0, column=2, sticky=tk.W)
        self.output_folder = tk.StringVar(value="./code_snippets")
        folder_entry = ttk.Entry(settings_frame, textvariable=self.output_folder, width=30)
        folder_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 5))
        
        ttk.Button(settings_frame, text="Browse", 
                  command=self.browse_output_folder).grid(row=0, column=4, padx=(5, 0))
        
        # Generate button
        generate_button = ttk.Button(main_frame, text="🚀 Generate Folders & Files", 
                                   command=self.generate_files, style='Generate.TButton')
        generate_button.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to generate files...")
        self.status_label.grid(row=5, column=0, columnspan=3)
        
        # Load sample data by default
        self.load_sample_data()
        
    def toggle_input_method(self):
        if self.input_method.get() == "file":
            self.file_entry.config(state="normal")
            self.browse_button.config(state="normal")
            self.json_text.config(state="disabled")
        else:
            self.file_entry.config(state="disabled")
            self.browse_button.config(state="disabled")
            self.json_text.config(state="normal")
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.json_text.config(state="normal")
                self.json_text.delete(1.0, tk.END)
                self.json_text.insert(1.0, content)
                self.json_text.config(state="disabled")
                self.status_label.config(text=f"Loaded file: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
    
    def detect_language(self, code):
        """Detect programming language from code content"""
        code_lower = code.lower().strip()
        
        # Go language detection
        if 'package main' in code_lower or 'func main()' in code_lower:
            return 'go'
        
        # Python detection
        if (code_lower.startswith('import ') or code_lower.startswith('from ') or 
            'def ' in code_lower or 'print(' in code_lower):
            return 'py'
        
        # JavaScript detection
        if ('function(' in code_lower or 'const ' in code_lower or 'let ' in code_lower or
            'console.log' in code_lower or 'document.' in code_lower):
            return 'js'
        
        # Java detection
        if ('public class' in code_lower or 'public static void main' in code_lower):
            return 'java'
        
        # C++ detection
        if ('#include' in code_lower or 'std::' in code_lower or 'cout' in code_lower):
            return 'cpp'
        
        # C detection
        if ('#include <stdio.h>' in code_lower or 'printf(' in code_lower):
            return 'c'
        
        # Default to txt if can't detect
        return 'txt'
    
    def sanitize_filename(self, title):
        """Sanitize title for use as filename"""
        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.lower()
    
    def generate_files(self):
        try:
            # Get JSON data
            if self.input_method.get() == "file" and self.file_path.get():
                with open(self.file_path.get(), 'r', encoding='utf-8') as f:
                    json_content = f.read()
            else:
                json_content = self.json_text.get(1.0, tk.END).strip()
            
            if not json_content:
                messagebox.showerror("Error", "Please provide JSON input")
                return
            
            # Parse JSON
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON format: {str(e)}")
                return
            
            # Validate JSON structure
            if 'snippets' not in data or not isinstance(data['snippets'], list):
                messagebox.showerror("Error", "JSON must contain 'snippets' array")
                return
            
            # Create output directory
            output_dir = Path(self.output_folder.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            start_num = self.start_number.get()
            created_files = []
            
            # Process each snippet
            for i, snippet in enumerate(data['snippets']):
                if not all(key in snippet for key in ['title', 'code']):
                    self.status_label.config(text=f"Skipping snippet {i+1}: missing required fields")
                    continue
                
                title = snippet['title']
                code = snippet['code']
                hook = snippet.get('hook', '')
                
                # Detect language and create filename
                lang_ext = self.detect_language(code)
                sanitized_title = self.sanitize_filename(title)
                file_num = start_num + i
                filename = f"{file_num}_{sanitized_title}.{lang_ext}"
                
                # Create file content
                file_content = code
                if hook:
                    # Add hook as comment at the top
                    comment_char = "//" if lang_ext in ['go', 'js', 'java', 'cpp', 'c'] else "#"
                    file_content = f"{comment_char} {hook}\n{comment_char} {title}\n\n{code}"
                
                # Write file
                file_path = output_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                created_files.append(filename)
                
                # Update status
                self.status_label.config(text=f"Creating file {i+1}/{len(data['snippets'])}: {filename}")
                self.root.update_idletasks()
            
            # Show completion message
            if created_files:
                message = f"Successfully created {len(created_files)} files in '{output_dir}':\n\n"
                message += "\n".join(created_files[:10])  # Show first 10 files
                if len(created_files) > 10:
                    message += f"\n... and {len(created_files) - 10} more files"
                
                messagebox.showinfo("Success", message)
                self.status_label.config(text=f"✅ Generated {len(created_files)} files successfully!")
            else:
                messagebox.showwarning("Warning", "No valid snippets found to process")
                self.status_label.config(text="⚠️ No files were created")
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_label.config(text="❌ Error occurred during generation")
    
    def load_sample_data(self):
        """Load the sample Go struct data"""
        sample_data = '''{
  "snippets": [
    {
      "title": "Your First Go Struct in 30 Seconds",
      "code": "package main\\nimport \\"fmt\\"\\n\\ntype Person struct { // Custom type\\n\\tName string\\n\\tAge  int\\n}\\n\\nfunc main() {\\n\\tp := Person{\\"Alice\\", 25} // Init\\n\\tfmt.Println(p.Name, p.Age)\\n}\\n// Output: Alice 25",
      "hook": "🚀 What would you name your first struct?"
    },
    {
      "title": "The Secret Behind Struct Tags",
      "code": "package main\\nimport (\\n\\t\\"encoding/json\\"\\n\\t\\"fmt\\"\\n)\\n\\ntype User struct {\\n\\tName string `json:\\"full_name\\"` // JSON tag\\n\\tAge  int    `json:\\"age\\"`\\n}\\n\\nfunc main() {\\n\\tu := User{\\"Bob\\", 30}\\n\\tdata, _ := json.Marshal(u)\\n\\tfmt.Println(string(data))\\n}\\n// Output: {\\"full_name\\":\\"Bob\\",\\"age\\":30}",
      "hook": "🤯 Ever seen these weird strings in Go structs?"
    }
  ]
}'''
        self.json_text.delete(1.0, tk.END)
        self.json_text.insert(1.0, sample_data)

def main():
    root = tk.Tk()
    app = CodeSnippetGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    main()