import winreg
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

class RegistryManager:
    def __init__(self):
        self.registry_file = Path("registry_entries.json")
        self.registered_entries: Dict[str, List[str]] = self._load_registry_entries()
        
        if getattr(sys, 'frozen', False):
            base_dir = Path(os.path.dirname(sys.executable))
        else:
            base_dir = Path(__file__).parent
        
        icon_path = base_dir / "assets" / "menuitem.ico"
        if not icon_path.exists():
            logging.warning(f"Icon file not found at {icon_path}, checking alternate locations")
            alt_locations = [
                Path(os.getcwd()) / "assets" / "menuitem.ico",
                Path(os.path.dirname(os.path.abspath(sys.argv[0]))) / "assets" / "menuitem.ico",
                Path(os.path.abspath(".")) / "assets" / "menuitem.ico"
            ]
            
            for alt_path in alt_locations:
                if alt_path.exists():
                    icon_path = alt_path
                    logging.info(f"Found icon at alternate location: {icon_path}")
                    break
            else:
                logging.warning(f"Icon not found in any of the alternate locations, using default icon path")

        self.icon_path = str(icon_path.resolve())
        logging.info(f"Using icon path: {self.icon_path}")
        
        if not os.path.exists(self.icon_path):
            logging.warning(f"Icon file does not exist at resolved path: {self.icon_path}")
        else:
            logging.info(f"Icon file confirmed at: {self.icon_path}")
    
    def _load_registry_entries(self) -> Dict[str, List[str]]:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logging.error("Failed to load registry entries file, creating new one")
                return {}
        return {}
    
    def _save_registry_entries(self):
        with open(self.registry_file, 'w') as f:
            json.dump(self.registered_entries, f, indent=4)
    
    def add_context_menu_for_extension(self, ext: str, formats: Set[str], exe_path: str) -> None:
        if not ext.startswith('.'):
            ext = f'.{ext}'
            
        try:
            if not os.path.exists(self.icon_path):
                logging.warning(f"Icon file not found at {self.icon_path}, checking in exe directory")
                exe_dir = Path(os.path.dirname(exe_path))
                alt_icon_paths = [
                    exe_dir / "assets" / "menuitem.ico",
                    exe_dir / "menuitem.ico",
                    Path(os.path.dirname(os.path.abspath(sys.argv[0]))) / "assets" / "menuitem.ico"
                ]
                
                for alt_path in alt_icon_paths:
                    if alt_path.exists():
                        self.icon_path = str(alt_path.resolve())
                        logging.info(f"Using icon from alternate location: {self.icon_path}")
                        break
                else:
                    logging.warning(f"Icon not found in any alternate locations, continuing without icon")

            ext_key_path = f"Software\\Classes\\SystemFileAssociations\\{ext}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, ext_key_path, 0, winreg.KEY_WRITE) as ext_key:
                shell_key_path = f"{ext_key_path}\\shell"
                
                menu_name = f"Convert {ext[1:].upper()}"
                menu_key_path = f"{shell_key_path}\\{menu_name}"
                
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, menu_key_path, 0, winreg.KEY_WRITE) as menu_key:
                    winreg.SetValueEx(menu_key, "", 0, winreg.REG_SZ, menu_name)
                    if os.path.exists(self.icon_path):
                        winreg.SetValueEx(menu_key, "Icon", 0, winreg.REG_SZ, self.icon_path)
                    winreg.SetValueEx(menu_key, "MUIVerb", 0, winreg.REG_SZ, menu_name)
                    winreg.SetValueEx(menu_key, "ExtendedSubCommandsKey", 0, winreg.REG_SZ, f"{ext[1:].upper()}ConvertCommands")
                
                subcommands_key_path = f"Software\\Classes\\{ext[1:].upper()}ConvertCommands"
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, subcommands_key_path, 0, winreg.KEY_WRITE) as subcommands_key:
                    subcommands_shell_path = f"{subcommands_key_path}\\Shell"
                    
                    if ext not in self.registered_entries:
                        self.registered_entries[ext] = []
                    
                    self.registered_entries[ext].extend([
                        ext_key_path,
                        shell_key_path,
                        menu_key_path,
                        subcommands_key_path,
                        subcommands_shell_path
                    ])
                    
                    for fmt in formats:
                        if fmt.lower() != ext[1:].lower():
                            fmt_key_path = f"{subcommands_shell_path}\\to_{fmt}"
                            cmd_key_path = f"{fmt_key_path}\\command"
                            
                            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, fmt_key_path, 0, winreg.KEY_WRITE) as fmt_key:
                                fmt_label = f"Convert to {fmt.upper()}"
                                winreg.SetValueEx(fmt_key, "", 0, winreg.REG_SZ, fmt_label)
                                winreg.SetValueEx(fmt_key, "MUIVerb", 0, winreg.REG_SZ, fmt_label)
                            
                            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, cmd_key_path, 0, winreg.KEY_WRITE) as cmd_key:
                                command = f'"{exe_path}" -f {fmt} "%1"'
                                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
                            
                            self.registered_entries[ext].extend([
                                fmt_key_path,
                                cmd_key_path
                            ])
                
                self._save_registry_entries()
                logging.info(f"Added context menu entries for {ext}")
                
        except Exception as e:
            logging.error(f"Failed to add context menu for {ext}: {str(e)}")
            raise
    
    def remove_context_menu_for_extension(self, ext: str) -> None:
        if not ext.startswith('.'):
            ext = f'.{ext}'
            
        if ext in self.registered_entries:
            for key_path in reversed(self.registered_entries[ext]):
                try:
                    self._delete_key_recursive(winreg.HKEY_CURRENT_USER, key_path)
                except WindowsError as e:
                    if e.winerror != 2:
                        logging.error(f"Failed to remove registry key {key_path}: {str(e)}")
            
            del self.registered_entries[ext]
            self._save_registry_entries()
            logging.info(f"Removed context menu entries for {ext}")
    
    def _delete_key_recursive(self, root_key, key_path):
        try:
            key = winreg.OpenKey(root_key, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
            
            subkey_count = winreg.QueryInfoKey(key)[0]
            
            for i in range(subkey_count):
                try:
                    subkey_name = winreg.EnumKey(key, 0)
                    subkey_path = f"{key_path}\\{subkey_name}"
                    
                    self._delete_key_recursive(root_key, subkey_path)
                except WindowsError:
                    continue
            
            winreg.CloseKey(key)
            
            winreg.DeleteKey(root_key, key_path)
        except Exception as e:
            logging.error(f"Error deleting key {key_path}: {e}")
            raise
    
    def remove_all_context_menus(self) -> None:
        extensions = list(self.registered_entries.keys())
        for ext in extensions:
            self.remove_context_menu_for_extension(ext)
    
    def get_registered_extensions(self) -> List[str]:
        return list(self.registered_entries.keys()) 