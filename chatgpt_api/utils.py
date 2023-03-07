from datetime import datetime
from colorama import Fore, Style


def time_now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def warn(text: str): print(f"{Fore.RED}{text}{Style.RESET_ALL}")
