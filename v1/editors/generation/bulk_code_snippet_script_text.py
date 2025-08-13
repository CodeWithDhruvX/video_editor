import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re
import os
from pathlib import Path

class ScriptGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Script Generator - Topic-wise MD Files")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="YouTube Script Generator", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Script Input", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        
        # Text area with scrollbar
        self.text_area = scrolledtext.ScrolledText(
            input_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=25,
            font=('Consolas', 10)
        )
        self.text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        # Load file button
        self.load_btn = ttk.Button(button_frame, text="Load Script File", 
                                  command=self.load_file)
        self.load_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Generate button
        self.generate_btn = ttk.Button(button_frame, text="Generate MD Files", 
                                      command=self.generate_files, 
                                      style='Accent.TButton')
        self.generate_btn.grid(row=0, column=1, padx=10)
        
        # Clear button
        self.clear_btn = ttk.Button(button_frame, text="Clear Text", 
                                   command=self.clear_text)
        self.clear_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, padx=(0, 10))
        self.status_label = ttk.Label(status_frame, text="Ready to generate files", 
                                     foreground='green')
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        # Output directory selection
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dir_frame, text="Output Directory:").grid(row=0, column=0, padx=(0, 10))
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        self.dir_label = ttk.Label(dir_frame, textvariable=self.output_dir_var, 
                                  relief='sunken', width=50)
        self.dir_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.browse_btn = ttk.Button(dir_frame, text="Browse", 
                                    command=self.browse_directory)
        self.browse_btn.grid(row=0, column=2)
        
        # Sample text for demonstration
        sample_text = """Got it ✅
I'll take the **first three snippets** from your JSON and create 1.5–3 minute YouTube scripts...

## 🎬 **1. Pointer vs Value Receiver**

**Opening Hook (0:00–0:10)**
*(excited tone)*
"🤯 In Go, you can call a method and… nothing changes!..."

## 🎬 **2. Method Overloading Myth**

**Opening Hook (0:00–0:10)**
*(playfully dramatic)*
"🚫 Think you can write two functions with the same name in Go?..."

## 🎬 **3. Method on Non-Struct Types**

**Opening Hook (0:00–0:10)**
*(surprised tone)*
"😲 You can put methods… on an int?!..."
"""
        self.text_area.insert('1.0', sample_text)
        
    def load_file(self):
        """Load script content from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Script File",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_area.delete('1.0', tk.END)
                    self.text_area.insert('1.0', content)
                    self.update_status(f"Loaded file: {os.path.basename(file_path)}", 'green')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                self.update_status("Failed to load file", 'red')
    
    def browse_directory(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
            self.update_status(f"Output directory: {directory}", 'blue')
    
    def clear_text(self):
        """Clear the text area"""
        self.text_area.delete('1.0', tk.END)
        self.update_status("Text cleared", 'orange')
    
    def update_status(self, message, color='black'):
        """Update status label with message and color"""
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()
    
    def extract_scripts(self, content):
        """Extract individual scripts from the content"""
        # Pattern to match script titles like "## 🎬 **1. Title**" or "## 🎬 **2. Title**"
        pattern = r'## 🎬 \*\*(\d+)\.\s*([^*]+)\*\*'
        
        scripts = []
        matches = list(re.finditer(pattern, content))
        
        for i, match in enumerate(matches):
            number = match.group(1)
            title = match.group(2).strip()
            
            # Find the start and end of this script
            start_pos = match.start()
            
            if i + 1 < len(matches):
                # Not the last script - end before next script
                end_pos = matches[i + 1].start()
            else:
                # Last script - take till end
                end_pos = len(content)
            
            # Extract the script content
            script_content = content[start_pos:end_pos].strip()
            
            scripts.append({
                'number': number,
                'title': title,
                'content': script_content
            })
        
        return scripts
    
    def sanitize_filename(self, filename):
        """Sanitize filename by removing invalid characters"""
        # Replace invalid characters with underscores
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores and spaces
        sanitized = sanitized.strip('_ ')
        return sanitized
    
    def generate_files(self):
        """Generate separate MD files for each script"""
        content = self.text_area.get('1.0', tk.END).strip()
        
        if not content:
            messagebox.showwarning("Warning", "Please enter script content first!")
            return
        
        try:
            self.update_status("Parsing scripts...", 'blue')
            scripts = self.extract_scripts(content)
            
            if not scripts:
                messagebox.showwarning("Warning", 
                    "No scripts found! Make sure your content follows the format:\n"
                    "## 🎬 **1. Title**")
                self.update_status("No scripts found", 'red')
                return
            
            output_dir = Path(self.output_dir_var.get())
            output_dir.mkdir(exist_ok=True)
            
            generated_files = []
            
            for script in scripts:
                # Create filename: number_title.md
                title_clean = self.sanitize_filename(script['title'])
                filename = f"{script['number']}_{title_clean}.md"
                filepath = output_dir / filename
                
                # Write the script to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {script['title']}\n\n")
                    f.write(script['content'])
                
                generated_files.append(filename)
                self.update_status(f"Generated: {filename}", 'blue')
            
            # Show success message
            success_msg = f"Successfully generated {len(generated_files)} files:\n\n"
            success_msg += "\n".join(generated_files)
            success_msg += f"\n\nFiles saved to: {output_dir}"
            
            messagebox.showinfo("Success", success_msg)
            self.update_status(f"Generated {len(generated_files)} MD files successfully!", 'green')
            
        except Exception as e:
            error_msg = f"Error generating files: {str(e)}"
            messagebox.showerror("Error", error_msg)
            self.update_status("Error generating files", 'red')

def main():
    root = tk.Tk()
    
    # Configure style
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern theme
    
    # Configure custom button style
    style.configure('Accent.TButton', foreground='white', background='#0078d4')
    style.map('Accent.TButton', background=[('active', '#106ebe')])
    
    app = ScriptGeneratorApp(root)
    
    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()