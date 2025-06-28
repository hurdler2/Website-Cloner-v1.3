import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse, unquote
import threading
import logging
from collections import deque
import time

# --- Configure Logger ---
LOG_FILE_NAME = "cloner_log.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOG_FILE_NAME, encoding='utf-8')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- Constants ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- Web Cloning Logic ---

def download_html(url, output_path):
    logger.info(f"Downloading HTML: {url} -> {output_path}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        html_content = response.text
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML content successfully saved: {output_path}")
        return html_content
    except requests.exceptions.RequestException as e:
        logger.error(f"HTML download error '{url}': {e}")
        raise Exception(f"Error downloading HTML content: {e}")
    except Exception as e:
        logger.error(f"HTML file writing error '{output_path}': {e}")
        raise Exception(f"Error writing HTML content to file: {e}")


def download_asset(asset_url, output_dir):
    logger.info(f"Downloading asset: {asset_url}")
    parsed_asset_url = urlparse(asset_url)

    path_segments = parsed_asset_url.path.strip('/').split('/')
    path_segments = [unquote(s) for s in path_segments]

    file_name = path_segments[-1] if path_segments else "index.html"

    if not file_name and parsed_asset_url.path.endswith('/'):
        file_name = "index.html"

    if not os.path.splitext(file_name)[1] and not file_name:
        file_name = "default_asset"

    local_asset_path_relative_to_output = os.path.join(*path_segments[:-1], file_name) if path_segments else file_name
    output_full_path = os.path.join(output_dir, local_asset_path_relative_to_output)

    try:
        os.makedirs(os.path.dirname(output_full_path), exist_ok=True)
        response = requests.get(asset_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        if 'text' in response.headers.get('Content-Type', ''):
            with open(output_full_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
        else:
            with open(output_full_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"Asset successfully downloaded: {output_full_path}")
        return local_asset_path_relative_to_output
    except requests.exceptions.RequestException as e:
        logger.error(f"Asset download error '{asset_url}': {e}")
        raise Exception(f"Error downloading asset '{asset_url}': {e}")
    except Exception as e:
        logger.error(f"Asset file writing error '{output_full_path}': {e}")
        raise Exception(f"Error writing file '{output_full_path}': {e}")


class WebClonerApp:
    def __init__(self, master):
        self.master = master
        master.title("AMY Web Cloner")
        master.geometry("850x620")
        master.resizable(False, False)

        # --- Style Settings ---
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam' genellikle stabil bir temadır. Deneyebilirsiniz: 'alt', 'default', 'aqua' (macOS), 'vista' (Windows)

        self.style.configure('TLabel', font=('Calibri', 12))
        self.style.configure('TButton', font=('Calibri', 12, 'bold'), foreground='white')
        self.style.configure('TMenubutton', font=('Calibri', 12))

        self.main_frame = ttk.Frame(master, padding="20 20 20 20", relief="raised")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(2, weight=1)

        self.center_frame = ttk.Frame(self.main_frame, padding="0 0 0 0")
        self.center_frame.grid(row=1, column=1, sticky="nsew")

        self.center_frame.grid_columnconfigure(0, weight=2)
        self.center_frame.grid_columnconfigure(1, weight=5)
        self.center_frame.grid_columnconfigure(2, weight=1)

        # --- Application Title ---
        self.title_label = ttk.Label(self.center_frame, text="Web Site Cloner Tool", font=('Calibri', 24, 'bold'), foreground='#333333')
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(0, 30), sticky="n")

        # URL Input
        self.url_label = ttk.Label(self.center_frame, text="Start URL:")
        self.url_label.grid(row=1, column=0, sticky="e", padx=(0, 10), pady=10)
        # tk.Entry kullanırken bg ve insertbackground birlikte
        self.url_entry = tk.Entry(self.center_frame, font=('Calibri', 12), bg='white', insertbackground='black', fg='black')
        self.url_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=10)
        self.url_entry.insert(0, "https://www.example.com")

        # Kayıt Dizini Seçimi
        self.path_label = ttk.Label(self.center_frame, text="Save Directory:")
        self.path_label.grid(row=2, column=0, sticky="e", padx=(0, 10), pady=10)
        # tk.Entry kullanırken bg ve insertbackground birlikte
        self.path_entry = tk.Entry(self.center_frame, font=('Calibri', 12), bg='white', insertbackground='black', fg='black')
        self.path_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=10)
        self.default_output_dir = os.path.join(os.path.expanduser("~"), "cloned_websites")
        self.path_entry.insert(0, self.default_output_dir)

        self.browse_button = ttk.Button(self.center_frame, text="Browse")
        self.browse_button.grid(row=2, column=2, padx=(10, 0), pady=10)
        self.browse_button.config(command=self.browse_directory)

        # Derinlik Seçimi
        self.depth_label = ttk.Label(self.center_frame, text="Cloning Depth (0=Only Homepage):")
        self.depth_label.grid(row=3, column=0, sticky="e", padx=(0, 10), pady=10)
        self.depth_var = tk.StringVar(master)
        self.depth_var.set("1")
        self.depth_options = [str(i) for i in range(0, 6)] + ["Unlimited"]
        self.depth_menu = ttk.OptionMenu(self.center_frame, self.depth_var, *self.depth_options)
        self.depth_menu.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=10)

        # Klonla Butonu
        self.clone_button = ttk.Button(self.center_frame, text="Start Cloning", command=self.start_cloning)
        self.clone_button.grid(row=4, column=0, columnspan=3, pady=25, ipadx=30, ipady=12)
        self.style.configure('Start.TButton', background='#28a745', foreground='white')
        self.clone_button.config(style='Start.TButton')

        # Durdur Butonu
        self.stop_button = ttk.Button(self.center_frame, text="Stop Cloning", command=self.stop_cloning, state=tk.DISABLED)
        self.stop_button.grid(row=5, column=0, columnspan=3, pady=(0, 20), ipadx=30, ipady=12)
        self.style.configure('Stop.TButton', background='#dc3545', foreground='white')
        self.style.map('Stop.TButton', background=[('disabled', '#cccccc'), ('!disabled', '#dc3545')])
        self.stop_button.config(style='Stop.TButton')

        # Durum Mesajı
        self.status_label = ttk.Label(self.center_frame, text="Ready", foreground="blue", font=('Calibri', 12, 'italic'))
        self.status_label.grid(row=6, column=0, columnspan=3, pady=(0, 20))

        # --- Developer Note ---
        self.developer_label = ttk.Label(self.center_frame, text="This application was lovingly developed by AMY.", font=('Calibri', 10, 'italic'), foreground='gray')
        self.developer_label.grid(row=7, column=0, columnspan=3, pady=(10, 0))

        self.stop_cloning_flag = False

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.path_entry.get())
        if directory:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)

    def set_status(self, message, color="black"):
        self.master.after(0, lambda: self.status_label.config(text=message, foreground=color))

    def show_messagebox(self, title, message, is_error=False):
        if is_error:
            self.master.after(0, lambda: messagebox.showerror(title, message))
        else:
            self.master.after(0, lambda: messagebox.showinfo(title, message))

    def start_cloning(self):
        target_url = self.url_entry.get()
        output_dir = self.path_entry.get()
        depth_str = self.depth_var.get()

        max_depth = -1
        if depth_str == "Unlimited":
            max_depth = -1
        else:
            try:
                max_depth = int(depth_str)
            except ValueError:
                self.show_messagebox("Input Error", "Invalid cloning depth.", True)
                logger.warning(f"Cloning not started: Invalid depth: {depth_str}")
                return

        if not target_url:
            self.show_messagebox("Input Error", "Please enter a URL to clone.", True)
            logger.warning("Cloning not started: URL not entered.")
            return
        if not output_dir:
            self.show_messagebox("Input Error", "Please select a save directory.", True)
            logger.warning("Cloning not started: Save directory not selected.")
            return

        self.set_status("Cloning process started...", "orange")
        self.clone_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.DISABLED)
        self.depth_menu.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.stop_cloning_flag = False
        logger.info(f"Cloning process started. URL: {target_url}, Target Directory: {output_dir}, Depth: {max_depth}")

        self.cloning_thread = threading.Thread(target=self._clone_process, args=(target_url, output_dir, max_depth))
        self.cloning_thread.start()

    def stop_cloning(self):
        self.stop_cloning_flag = True
        self.set_status("Stopping cloning process...", "red")
        logger.info("Cloning process stopping requested by user.")

    def _clone_process(self, target_url, output_directory, max_depth):
        try:
            os.makedirs(output_directory, exist_ok=True)
            base_url_parsed = urlparse(target_url)
            base_domain = base_url_parsed.netloc

            urls_to_visit = deque([(target_url, 0)])
            visited_urls = set()

            cloned_html_files = {}
            total_pages_cloned = 0

            while urls_to_visit and not self.stop_cloning_flag:
                current_url, current_depth = urls_to_visit.popleft()

                if max_depth != -1 and current_depth > max_depth:
                    logger.info(f"Depth limit exceeded, skipping: {current_url} (Depth: {current_depth})")
                    continue

                normalized_url = urlparse(current_url)._replace(query="", fragment="").geturl()
                if normalized_url in visited_urls:
                    logger.info(f"Already visited, skipping: {normalized_url}")
                    continue

                visited_urls.add(normalized_url)
                logger.info(f"Processing current URL: {current_url} (Depth: {current_depth})")

                self.set_status(f"Downloading page ({total_pages_cloned + 1}): {current_url}", "blue")

                parsed_current_url = urlparse(current_url)
                url_path_segments = [unquote(s) for s in parsed_current_url.path.strip('/').split('/') if s]

                if not url_path_segments:
                    page_file_name = "index.html"
                    page_dir = ""
                else:
                    if '.' in url_path_segments[-1] and url_path_segments[-1].split('.')[-1].isalnum():
                        page_file_name = url_path_segments[-1]
                        page_dir = os.path.join(*url_path_segments[:-1])
                    else:
                        page_file_name = "index.html"
                        page_dir = os.path.join(*url_path_segments)

                page_output_subdir = os.path.join(output_directory, base_domain, page_dir)
                os.makedirs(page_output_subdir, exist_ok=True)
                page_output_path = os.path.join(page_output_subdir, page_file_name)

                local_cloned_html_path = os.path.relpath(page_output_path, output_directory)
                cloned_html_files[(normalized_url, current_depth)] = local_cloned_html_path

                html_content = download_html(current_url, page_output_path)

                if not html_content:
                    logger.warning(f"Failed to download HTML content: {current_url}. Skipping.")
                    continue

                soup = BeautifulSoup(html_content, 'html.parser')
                elements_to_update = []

                for tag_name, attr_name in [('link', 'href'), ('script', 'src'), ('img', 'src'), ('source', 'srcset'), ('a', 'href')]:
                    for element in soup.find_all(tag_name, **{attr_name: True}):
                        elements_to_update.append((element, attr_name))

                for i, (element, attr) in enumerate(elements_to_update):
                    original_url = element.get(attr)
                    if not original_url:
                        continue

                    full_asset_url = urljoin(current_url, original_url)
                    parsed_full_asset_url = urlparse(full_asset_url)

                    if parsed_full_asset_url.netloc == base_domain:
                        try:
                            if element.name == 'a' and (parsed_full_asset_url.path.endswith('/') or '.' not in parsed_full_asset_url.path.split('/')[-1]):
                                next_url = parsed_full_asset_url.geturl()
                                normalized_next_url = urlparse(next_url)._replace(query="", fragment="").geturl()
                                if normalized_next_url not in visited_urls:
                                    urls_to_visit.append((next_url, current_depth + 1))
                                    logger.debug(f"Added to queue: {next_url} (Depth: {current_depth + 1})")

                            if attr == 'srcset':
                                updated_srcset_parts = []
                                for part in original_url.split(','):
                                    url_part = part.strip().split(' ')[0]
                                    desc_part = ' '.join(part.strip().split(' ')[1:])
                                    full_src_url = urljoin(current_url, url_part)
                                    local_path = download_asset(full_src_url, output_directory)
                                    if local_path:
                                        updated_srcset_parts.append(f"{local_path} {desc_part}".strip())
                                    else:
                                        updated_srcset_parts.append(part)
                                element['srcset'] = ', '.join(updated_srcset_parts)
                            else:
                                local_path = download_asset(full_asset_url, output_directory)
                                if local_path:
                                    element[attr] = local_path
                                else:
                                    element[attr] = original_url
                        except Exception as asset_err:
                            logger.error(f"Error processing asset or internal link ({full_asset_url}): {asset_err}")
                            element[attr] = original_url
                    else:
                        logger.debug(f"External link skipped: {full_asset_url}")
                        element[attr] = original_url

                updated_html_content = soup.prettify(formatter="html")
                with open(page_output_path, 'w', encoding='utf-8') as f:
                    f.write(updated_html_content)
                logger.info(f"Updated HTML content saved: {page_output_path}")
                total_pages_cloned += 1

            if self.stop_cloning_flag:
                self.set_status(f"Cloning stopped by user. {total_pages_cloned} pages and assets downloaded. Log file: {LOG_FILE_NAME}", "red")
                self.show_messagebox("Stopped", f"Web site cloning stopped by the user.\n{total_pages_cloned} pages downloaded.\nLocation: {output_directory}\nCheck '{LOG_FILE_NAME}' for details.")
                logger.info("Cloning process stopped by user.")
            else:
                self.set_status(f"Cloning completed! {total_pages_cloned} pages and assets cloned. Log file: {LOG_FILE_NAME}", "green")
                self.show_messagebox("Success", f"Web site successfully cloned!\nTotal {total_pages_cloned} pages downloaded.\nLocation: {output_directory}\nCheck '{LOG_FILE_NAME}' for details.")
                logger.info("Cloning process successfully completed.")

        except Exception as e:
            self.set_status(f"An unexpected error occurred during cloning: {e}", "red")
            self.show_messagebox("Error", f"An error occurred during cloning:\n{e}\nCheck '{LOG_FILE_NAME}' for details.", True)
            logger.critical(f"Cloning process stopped due to an unexpected error: {e}", exc_info=True)
        finally:
            self.clone_button.config(state=tk.NORMAL)
            self.browse_button.config(state=tk.NORMAL)
            self.depth_menu.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            logger.info("Clone button re-enabled.")

# --- Start Application ---
if __name__ == '__main__':
    root = tk.Tk()
    app = WebClonerApp(root)
    root.mainloop()