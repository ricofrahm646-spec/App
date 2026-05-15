import shutil
import os

class MT5Installer:
    def __init__(self, mt5_data_path):
        self.mt5_experts_path = os.path.join(mt5_data_path, "MQL5", "Experts")

    def install_expert(self, source_path):
        if not os.path.exists(source_path):
            return False

        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.mt5_experts_path, filename)

        print(f"Installing {filename} to {dest_path}")
        # shutil.copy(source_path, dest_path) # Simulated
        return True
